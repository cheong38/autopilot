#!/bin/bash
# pipeline-check.sh - Check CI pipeline status for a specific commit
# Usage: pipeline-check.sh [--wait] [--timeout 600] [--sha <SHA>]
# Output: PIPELINE_STATUS (passing|failing|pending|unknown)

set -euo pipefail

WAIT=false
TIMEOUT=600
POLL_INTERVAL=15
SHA_OVERRIDE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --wait) WAIT=true; shift ;;
        --timeout) TIMEOUT="$2"; shift 2 ;;
        --sha) SHA_OVERRIDE="$2"; shift 2 ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

# Detect VCS provider
REMOTE_URL="$(git remote get-url origin 2>/dev/null || echo "")"
VCS_PROVIDER="unknown"
if echo "$REMOTE_URL" | grep -q "github.com"; then
    VCS_PROVIDER="github"
elif echo "$REMOTE_URL" | grep -qi "gitlab"; then
    VCS_PROVIDER="gitlab"
fi

# Get current branch
BRANCH="$(git branch --show-current)"

check_github_status() {
    SHA="${SHA_OVERRIDE:-$(git rev-parse HEAD)}"

    # Check combined status
    STATUS_JSON="$(gh api "repos/{owner}/{repo}/commits/${SHA}/check-runs" --jq '.check_runs | map(.conclusion) | unique' 2>/dev/null || echo "[]")"

    if echo "$STATUS_JSON" | grep -q "failure"; then
        echo "failing"
    elif echo "$STATUS_JSON" | grep -q "null"; then
        echo "pending"
    elif echo "$STATUS_JSON" | grep -q "success"; then
        echo "passing"
    else
        # Try status API as fallback
        COMBINED="$(gh api "repos/{owner}/{repo}/commits/${SHA}/status" --jq '.state' 2>/dev/null || echo "unknown")"
        case "$COMBINED" in
            success) echo "passing" ;;
            failure) echo "failing" ;;
            pending) echo "pending" ;;
            *) echo "unknown" ;;
        esac
    fi
}

check_gitlab_status() {
    SHA="${SHA_OVERRIDE:-$(git rev-parse HEAD)}"
    STATUS="$(glab api "projects/:id/repository/commits/${SHA}/statuses" --jq '.[0].status' 2>/dev/null || echo "unknown")"

    case "$STATUS" in
        success) echo "passing" ;;
        failed) echo "failing" ;;
        pending|running) echo "pending" ;;
        *) echo "unknown" ;;
    esac
}

get_status() {
    case "$VCS_PROVIDER" in
        github) check_github_status ;;
        gitlab) check_gitlab_status ;;
        *) echo "unknown" ;;
    esac
}

if [ "$WAIT" = true ]; then
    ELAPSED=0
    while [ $ELAPSED -lt "$TIMEOUT" ]; do
        STATUS="$(get_status)"
        if [ "$STATUS" = "passing" ] || [ "$STATUS" = "failing" ]; then
            echo "PIPELINE_STATUS=${STATUS}"
            exit 0
        fi
        echo "Pipeline status: ${STATUS} (waiting... ${ELAPSED}s/${TIMEOUT}s)" >&2
        sleep "$POLL_INTERVAL"
        ELAPSED=$((ELAPSED + POLL_INTERVAL))
    done
    echo "PIPELINE_STATUS=timeout"
    exit 1
else
    STATUS="$(get_status)"
    echo "PIPELINE_STATUS=${STATUS}"
fi
