#!/usr/bin/env bash
# dag-sync.sh — Sync issue DAG with Wiki (GitHub/GitLab) or local fallback
#
# Usage:
#   dag-sync.sh pull              Clone or pull wiki repo (or init local)
#   dag-sync.sh push [message]    Commit and push changes
#   dag-sync.sh init              Create empty DAG + UL dictionary
#   dag-sync.sh path              Print path to local DAG file
#
# Supports: GitHub Wiki, GitLab Wiki, local fallback
# Cache: /tmp/issue-dag-wiki/<owner>-<repo>/

set -euo pipefail

DAG_FILENAME="issue-dag.json"
UL_FILENAME="ubiquitous-language.json"
CACHE_BASE="/tmp/issue-dag-wiki"
MAX_PUSH_RETRIES=3
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAG_ANALYZE="$SCRIPT_DIR/dag-analyze.py"

# ─── Helpers ─────────────────────────────────────────────────

error() { echo "ERROR: $*" >&2; exit 1; }
info()  { echo "INFO: $*" >&2; }

detect_provider() {
    local remote="$1"
    if [[ "$remote" == *"github.com"* ]]; then
        echo "github"
    elif [[ "$remote" == *"gitlab"* ]]; then
        echo "gitlab"
    else
        echo "unknown"
    fi
}

extract_repo() {
    local remote="$1"
    local provider="$2"
    local repo
    case "$provider" in
        github)
            repo=$(echo "$remote" | sed -E 's#.*github\.com[:/]##; s#\.git$##')
            ;;
        gitlab)
            if [[ "$remote" == git@* ]]; then
                # SSH: git@gitlab.com:group/project.git → group/project
                repo=$(echo "$remote" | sed -E 's#^[^:]+:##; s#\.git$##')
            else
                # HTTPS: https://gitlab.com/group/project.git → group/project
                repo=$(echo "$remote" | sed -E 's#https?://[^/]+/##; s#\.git$##')
            fi
            ;;
        *)
            repo=""
            ;;
    esac
    echo "$repo"
}

build_wiki_url() {
    local remote="$1"
    local provider="$2"
    local repo="$3"
    case "$provider" in
        github)
            if [[ "$remote" == git@* ]]; then
                echo "git@github.com:${repo}.wiki.git"
            else
                echo "https://github.com/${repo}.wiki.git"
            fi
            ;;
        gitlab)
            if [[ "$remote" == git@* ]]; then
                local host
                host=$(echo "$remote" | sed -E 's#git@([^:]+):.*#\1#')
                echo "git@${host}:${repo}.wiki.git"
            else
                local base
                base=$(echo "$remote" | sed -E 's#(https?://[^/]+)/.*#\1#')
                echo "${base}/${repo}.wiki.git"
            fi
            ;;
        *)
            echo ""
            ;;
    esac
}

detect_repo() {
    local remote
    remote=$(git remote get-url origin 2>/dev/null) || error "No git remote 'origin' found"

    local provider
    provider=$(detect_provider "$remote")

    local repo
    repo=$(extract_repo "$remote" "$provider")

    if [[ -z "$repo" || "$repo" == "$remote" ]]; then
        if [[ "$provider" == "unknown" ]]; then
            # Return provider info for structured output
            echo "unknown||$remote"
            return 0
        fi
        error "Could not extract owner/repo from remote: $remote"
    fi

    echo "$provider|$repo|$remote"
}

parse_detect_result() {
    local result="$1"
    DETECTED_PROVIDER=$(echo "$result" | cut -d'|' -f1)
    DETECTED_REPO=$(echo "$result" | cut -d'|' -f2)
    DETECTED_REMOTE=$(echo "$result" | cut -d'|' -f3)
}

cache_dir() {
    local repo="$1"
    local safe_name="${repo//\//-}"
    echo "$CACHE_BASE/$safe_name"
}

wiki_url() {
    local provider="$1"
    local repo="$2"
    local remote="$3"
    build_wiki_url "$remote" "$provider" "$repo"
}

dag_file_path() {
    local repo="$1"
    echo "$(cache_dir "$repo")/$DAG_FILENAME"
}

local_dag_dir() {
    local toplevel
    toplevel=$(git rev-parse --show-toplevel 2>/dev/null) || toplevel="."
    echo "$toplevel/.claude/dag"
}

emit_result() {
    echo "DAG_SYNC_RESULT_BEGIN"
    for kv in "$@"; do
        echo "$kv"
    done
    echo "DAG_SYNC_RESULT_END"
}

read_dag_backend_config() {
    local toplevel
    toplevel=$(git rev-parse --show-toplevel 2>/dev/null) || toplevel="."
    local config_file="$toplevel/.claude/issue.yaml"
    if [[ -f "$config_file" ]]; then
        # Parse dag.backend from YAML (simple grep, no yq dependency)
        local backend
        backend=$(grep -A5 '^dag:' "$config_file" 2>/dev/null | grep 'backend:' | sed 's/.*backend:\s*//' | tr -d '[:space:]' | head -1)
        echo "${backend:-auto}"
    else
        echo "auto"
    fi
}

# ─── Commands ────────────────────────────────────────────────

wiki_activation_hint() {
    local provider="$1"
    local repo="$2"
    case "$provider" in
        github)
            echo "Go to: https://github.com/${repo}/settings → Features → Wiki"
            ;;
        gitlab)
            echo "Go to: Settings → General → Visibility → Wiki (enable it)"
            ;;
        *)
            echo "Enable the Wiki feature in your repository settings"
            ;;
    esac
}

setup_local_fallback() {
    local action="$1"
    local dag_dir
    dag_dir=$(local_dag_dir)
    mkdir -p "$dag_dir"
    local dag_path="$dag_dir/$DAG_FILENAME"
    local ul_path="$dag_dir/$UL_FILENAME"

    if [[ "$action" == "init" || ! -f "$dag_path" ]]; then
        python3 "$DAG_ANALYZE" --dag-file "$dag_path" init --repo "local/project" --force
    fi
    if [[ ! -f "$ul_path" ]]; then
        echo '{"terms": []}' > "$ul_path"
    fi

    emit_result "ACTION=$action" "STATUS=ok" "DAG_FILE=$dag_path" "UL_FILE=$ul_path" "BACKEND=local"
}

cmd_pull() {
    local detect_result
    detect_result=$(detect_repo)
    parse_detect_result "$detect_result"

    local backend_config
    backend_config=$(read_dag_backend_config)

    # Forced local mode
    if [[ "$backend_config" == "local" ]]; then
        setup_local_fallback "pull"
        return 0
    fi

    # Forced specific wiki backend
    if [[ "$backend_config" == "github-wiki" ]]; then
        DETECTED_PROVIDER="github"
    elif [[ "$backend_config" == "gitlab-wiki" ]]; then
        DETECTED_PROVIDER="gitlab"
    fi

    # Unknown provider → local fallback
    if [[ "$DETECTED_PROVIDER" == "unknown" ]]; then
        if [[ "$backend_config" == "auto" ]]; then
            info "No supported Wiki provider detected. Using local DAG storage."
            setup_local_fallback "pull"
            return 0
        fi
        emit_result "ACTION=pull" "STATUS=skipped" "SKIP_REASON=non_supported_provider"
        exit 0
    fi

    local repo="$DETECTED_REPO"
    local remote="$DETECTED_REMOTE"
    local dir
    dir=$(cache_dir "$repo")
    local url
    url=$(wiki_url "$DETECTED_PROVIDER" "$repo" "$remote")

    if [[ -z "$url" ]]; then
        info "Could not build Wiki URL. Using local DAG storage."
        setup_local_fallback "pull"
        return 0
    fi

    if [[ -d "$dir/.git" ]]; then
        info "Pulling latest from wiki..."
        git -C "$dir" pull --rebase --quiet 2>/dev/null || {
            info "Pull failed, re-cloning..."
            rm -rf "$dir"
            git clone --quiet "$url" "$dir" 2>/dev/null || {
                local hint
                hint=$(wiki_activation_hint "$DETECTED_PROVIDER" "$repo")
                if [[ "$backend_config" == "auto" ]]; then
                    info "Wiki clone failed. Falling back to local DAG storage."
                    setup_local_fallback "pull"
                    return 0
                fi
                emit_result "ACTION=pull" "STATUS=error" "ERROR_REASON=clone_failed" "HINT=$hint"
                exit 1
            }
        }
    else
        info "Cloning wiki repo..."
        mkdir -p "$CACHE_BASE"
        git clone --quiet "$url" "$dir" 2>/dev/null || {
            local hint
            hint=$(wiki_activation_hint "$DETECTED_PROVIDER" "$repo")
            if [[ "$backend_config" == "auto" ]]; then
                info "Wiki clone failed. Falling back to local DAG storage."
                setup_local_fallback "pull"
                return 0
            fi
            emit_result "ACTION=pull" "STATUS=error" "ERROR_REASON=clone_failed" "HINT=$hint"
            exit 1
        }
    fi

    local dag_path="$dir/$DAG_FILENAME"
    if [[ ! -f "$dag_path" ]]; then
        info "No $DAG_FILENAME found in wiki. Run 'dag-sync.sh init' to create one."
    fi

    emit_result "ACTION=pull" "STATUS=ok" "REPO=$repo" "DAG_FILE=$dag_path" "BACKEND=${DETECTED_PROVIDER}-wiki"
}

cmd_push() {
    local detect_result
    detect_result=$(detect_repo)
    parse_detect_result "$detect_result"

    local backend_config
    backend_config=$(read_dag_backend_config)

    local message="${1:-Update issue DAG}"

    # Local backend: push is a no-op with informational message
    if [[ "$backend_config" == "local" || "$DETECTED_PROVIDER" == "unknown" ]]; then
        local dag_dir
        dag_dir=$(local_dag_dir)
        local dag_path="$dag_dir/$DAG_FILENAME"
        info "DAG is stored locally. Commit .claude/dag/ to share with team."
        emit_result "ACTION=push" "STATUS=ok" "DAG_FILE=$dag_path" "BACKEND=local" "NOTE=local_only"
        return 0
    fi

    local repo="$DETECTED_REPO"
    local dir
    dir=$(cache_dir "$repo")

    # If wiki was never cloned (e.g. pull fell back to local), treat as local
    if [[ ! -d "$dir/.git" ]]; then
        local dag_dir
        dag_dir=$(local_dag_dir)
        if [[ -f "$dag_dir/$DAG_FILENAME" ]]; then
            info "Wiki not available. DAG is stored locally. Commit .claude/dag/ to share with team."
            emit_result "ACTION=push" "STATUS=ok" "DAG_FILE=$dag_dir/$DAG_FILENAME" "BACKEND=local" "NOTE=local_only"
            return 0
        fi
        error "Wiki not cloned and no local DAG found. Run 'dag-sync.sh pull' first."
    fi

    # Validate DAG before pushing
    local dag_path="$dir/$DAG_FILENAME"
    if [[ -f "$dag_path" ]]; then
        python3 "$DAG_ANALYZE" --dag-file "$dag_path" validate || {
            error "DAG validation failed. Fix errors before pushing."
        }
    fi

    cd "$dir"

    # Check for changes
    if git diff --quiet && git diff --cached --quiet; then
        info "No changes to push"
        emit_result "ACTION=push" "STATUS=no_changes" "REPO=$repo" "BACKEND=${DETECTED_PROVIDER}-wiki"
        return 0
    fi

    git add -A

    local retry=0
    while (( retry < MAX_PUSH_RETRIES )); do
        git commit --quiet -m "$message [$DETECTED_PROVIDER]" 2>/dev/null || true

        if git push --quiet 2>/dev/null; then
            emit_result "ACTION=push" "STATUS=ok" "REPO=$repo" "DAG_FILE=$dag_path" "BACKEND=${DETECTED_PROVIDER}-wiki"
            return 0
        fi

        info "Push failed (attempt $((retry+1))/$MAX_PUSH_RETRIES). Pulling and retrying..."
        git pull --rebase --quiet 2>/dev/null || {
            info "Rebase conflict detected. Attempting JSON merge..."
            git rebase --abort 2>/dev/null || true
            git pull --quiet --strategy-option=theirs 2>/dev/null || true
        }
        git add -A
        retry=$((retry + 1))
    done

    emit_result "ACTION=push" "STATUS=error" "ERROR_REASON=push_failed" "REPO=$repo"
    exit 1
}

cmd_init() {
    local detect_result
    detect_result=$(detect_repo)
    parse_detect_result "$detect_result"

    local backend_config
    backend_config=$(read_dag_backend_config)

    # Local backend or unknown provider → local init
    if [[ "$backend_config" == "local" || "$DETECTED_PROVIDER" == "unknown" ]]; then
        setup_local_fallback "init"
        return 0
    fi

    local repo="$DETECTED_REPO"
    local dir
    dir=$(cache_dir "$repo")

    # Ensure wiki is cloned
    if [[ ! -d "$dir/.git" ]]; then
        cmd_pull
    fi

    local dag_path="$dir/$DAG_FILENAME"
    python3 "$DAG_ANALYZE" --dag-file "$dag_path" init --repo "$repo" --force

    # Create empty UL dictionary if not exists
    local ul_path="$dir/$UL_FILENAME"
    if [[ ! -f "$ul_path" ]]; then
        echo '{"terms": []}' > "$ul_path"
        info "Created empty UL dictionary at $ul_path"
    fi

    emit_result "ACTION=init" "STATUS=ok" "REPO=$repo" "DAG_FILE=$dag_path" "UL_FILE=$ul_path" "BACKEND=${DETECTED_PROVIDER}-wiki"
}

cmd_path() {
    local detect_result
    detect_result=$(detect_repo)
    parse_detect_result "$detect_result"

    local backend_config
    backend_config=$(read_dag_backend_config)

    if [[ "$backend_config" == "local" || "$DETECTED_PROVIDER" == "unknown" ]]; then
        local dag_dir
        dag_dir=$(local_dag_dir)
        echo "$dag_dir/$DAG_FILENAME"
    else
        dag_file_path "$DETECTED_REPO"
    fi
}

# ─── Main ────────────────────────────────────────────────────

# Guard: skip main when sourced (for testing)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    case "${1:-}" in
        pull)   cmd_pull ;;
        push)   cmd_push "${2:-Update issue DAG}" ;;
        init)   cmd_init ;;
        path)   cmd_path ;;
        *)
            echo "Usage: dag-sync.sh {pull|push|init|path}" >&2
            echo "  pull              Clone or pull wiki repo" >&2
            echo "  push [message]    Commit and push changes" >&2
            echo "  init              Create empty DAG + UL dictionary" >&2
            echo "  path              Print local DAG file path" >&2
            exit 1
            ;;
    esac
fi
