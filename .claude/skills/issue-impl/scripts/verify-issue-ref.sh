#!/bin/bash
# verify-issue-ref.sh - Verify commit messages contain issue references
# Why: Enforces issue-reference policy so merges are blocked when commits lack a reference.
# Usage: verify-issue-ref.sh [--base <sha>] [--head <sha>] [--check-pr-title <title>]
# Output: Structured block with ISSUE_REF_CHECK_BEGIN/END markers
# Exit:  0 = pass, 1 = fail

set -euo pipefail

BASE=""
HEAD="HEAD"
CHECK_PR_TITLE=""

# Pattern: GitHub #123 or Jira ABC-123
ISSUE_REF_PATTERN='(#[0-9]+|[A-Z][A-Z0-9]+-[0-9]+)'

while [[ $# -gt 0 ]]; do
    case $1 in
        --base) BASE="$2"; shift 2 ;;
        --head) HEAD="$2"; shift 2 ;;
        --check-pr-title) CHECK_PR_TITLE="$2"; shift 2 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

# Determine commit range
if [ -z "$BASE" ]; then
    # Auto-detect: use merge-base with origin/main (or origin/master)
    DEFAULT_BRANCH="$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo 'main')"
    BASE="$(git merge-base "origin/${DEFAULT_BRANCH}" "$HEAD" 2>/dev/null || echo "")"
    if [ -z "$BASE" ]; then
        echo "ERROR: Cannot determine base commit. Provide --base explicitly." >&2
        exit 1
    fi
fi

# Collect commit SHAs (exclude merge commits)
COMMITS="$(git log --no-merges --format='%H' "${BASE}..${HEAD}" 2>/dev/null || echo "")"

if [ -z "$COMMITS" ]; then
    # No commits in range — pass vacuously
    cat <<EOF
ISSUE_REF_CHECK_BEGIN
STATUS=pass
TOTAL_COMMITS=0
MISSING_COUNT=0
MISSING_COMMITS=
DETECTED_KEYS=
ISSUE_REF_CHECK_END
EOF
    exit 0
fi

TOTAL=0
MISSING_COUNT=0
MISSING_LIST=""
ALL_KEYS=""

while IFS= read -r SHA; do
    TOTAL=$((TOTAL + 1))
    # Get full commit message (subject + body)
    MSG="$(git log -1 --format='%B' "$SHA")"
    KEYS="$(echo "$MSG" | grep -oE "$ISSUE_REF_PATTERN" || true)"
    if [ -z "$KEYS" ]; then
        MISSING_COUNT=$((MISSING_COUNT + 1))
        if [ -n "$MISSING_LIST" ]; then
            MISSING_LIST="${MISSING_LIST},${SHA:0:12}"
        else
            MISSING_LIST="${SHA:0:12}"
        fi
    else
        # Accumulate detected keys
        while IFS= read -r KEY; do
            if [ -n "$KEY" ]; then
                if [ -n "$ALL_KEYS" ]; then
                    ALL_KEYS="${ALL_KEYS},${KEY}"
                else
                    ALL_KEYS="${KEY}"
                fi
            fi
        done <<< "$KEYS"
    fi
done <<< "$COMMITS"

# Optional: check PR title for squash-merge workflows
PR_TITLE_HAS_REF=false
if [ -n "$CHECK_PR_TITLE" ]; then
    PR_KEYS="$(echo "$CHECK_PR_TITLE" | grep -oE "$ISSUE_REF_PATTERN" || true)"
    if [ -n "$PR_KEYS" ]; then
        PR_TITLE_HAS_REF=true
        while IFS= read -r KEY; do
            if [ -n "$KEY" ]; then
                if [ -n "$ALL_KEYS" ]; then
                    ALL_KEYS="${ALL_KEYS},${KEY}"
                else
                    ALL_KEYS="${KEY}"
                fi
            fi
        done <<< "$PR_KEYS"
    fi
fi

# Deduplicate keys
ALL_KEYS="$(echo "$ALL_KEYS" | tr ',' '\n' | sort -u | paste -sd ',' -)"

# Determine status
STATUS="pass"
if [ "$MISSING_COUNT" -gt 0 ]; then
    # If PR title has a ref (squash workflow), treat as pass
    if [ "$PR_TITLE_HAS_REF" = true ]; then
        STATUS="pass"
    else
        STATUS="fail"
    fi
fi

cat <<EOF
ISSUE_REF_CHECK_BEGIN
STATUS=${STATUS}
TOTAL_COMMITS=${TOTAL}
MISSING_COUNT=${MISSING_COUNT}
MISSING_COMMITS=${MISSING_LIST}
DETECTED_KEYS=${ALL_KEYS}
ISSUE_REF_CHECK_END
EOF

if [ "$STATUS" = "fail" ]; then
    exit 1
else
    exit 0
fi
