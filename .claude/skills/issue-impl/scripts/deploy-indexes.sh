#!/bin/bash
# deploy-indexes.sh - Deploy Firestore indexes and wait for build completion
# Usage: deploy-indexes.sh [--project <project-id>] [--no-wait]
#
# IMPORTANT: This script deploys from the correct directory (project root)
# to avoid the silent failure when deploying from a subdirectory.

set -euo pipefail

PROJECT=""
WAIT=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --project) PROJECT="$2"; shift 2 ;;
        --no-wait) WAIT=false; shift ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

# Find project root (where firestore.indexes.json lives)
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Search for firestore.indexes.json
INDEX_FILE=""
for candidate in \
    "${REPO_ROOT}/firestore.indexes.json" \
    "${REPO_ROOT}/apps/api/firestore.indexes.json" \
    "${REPO_ROOT}/firebase/firestore.indexes.json"; do
    if [ -f "$candidate" ]; then
        INDEX_FILE="$candidate"
        break
    fi
done

if [ -z "$INDEX_FILE" ]; then
    echo "ERROR: firestore.indexes.json not found in project" >&2
    exit 1
fi

INDEX_DIR="$(dirname "$INDEX_FILE")"
echo "Found indexes at: ${INDEX_FILE}" >&2
echo "Deploying from: ${INDEX_DIR}" >&2

# Build deploy command as array
DEPLOY_CMD=(firebase deploy --only firestore:indexes)
if [ -n "$PROJECT" ]; then
    DEPLOY_CMD+=(--project="${PROJECT}")
fi

# Deploy from the directory containing firestore.indexes.json
cd "$INDEX_DIR"
echo "Running: ${DEPLOY_CMD[*]}" >&2
"${DEPLOY_CMD[@]}"

if [ "$WAIT" = true ]; then
    echo "Waiting for indexes to build..." >&2
    sleep 10

    # Check index status
    LIST_CMD=(firebase firestore:indexes)
    if [ -n "$PROJECT" ]; then
        LIST_CMD+=(--project="${PROJECT}")
    fi

    MAX_WAIT=300
    ELAPSED=0
    POLL=15

    while [ $ELAPSED -lt $MAX_WAIT ]; do
        STATUS="$("${LIST_CMD[@]}" 2>/dev/null || echo "error")"
        if echo "$STATUS" | grep -q "CREATING"; then
            echo "Indexes still building... (${ELAPSED}s/${MAX_WAIT}s)" >&2
            sleep $POLL
            ELAPSED=$((ELAPSED + POLL))
        else
            echo "INDEX_DEPLOY=success"
            echo "All indexes are ready." >&2
            exit 0
        fi
    done

    echo "INDEX_DEPLOY=timeout"
    echo "WARNING: Index build timed out after ${MAX_WAIT}s. Check Firebase Console." >&2
    exit 1
else
    echo "INDEX_DEPLOY=deployed"
    echo "Indexes deployed. Check Firebase Console for build status." >&2
fi
