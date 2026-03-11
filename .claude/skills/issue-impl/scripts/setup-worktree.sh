#!/bin/bash
# setup-worktree.sh - Create a git worktree for isolated implementation
# Usage: setup-worktree.sh <issue-key> <feature-name>
# Output: Structured block with WORKTREE_SETUP_BEGIN/END markers

set -euo pipefail

ISSUE_KEY="${1:?Usage: setup-worktree.sh <issue-key> <feature-name>}"
FEATURE_NAME="${2:?Usage: setup-worktree.sh <issue-key> <feature-name>}"

# Detect main repo
MAIN_REPO="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
REPO_NAME="$(basename "$MAIN_REPO")"

# Sanitize feature name for branch
FEATURE_SLUG="$(echo "$FEATURE_NAME" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//' | sed 's/-$//')"

# Build branch and worktree paths
BRANCH_NAME="feat/${ISSUE_KEY}-${FEATURE_SLUG}"
WORKTREE_BASE="/tmp/impl-worktrees/${REPO_NAME}"
WORKTREE_DIR="${WORKTREE_BASE}/${BRANCH_NAME//\//-}"

# Create worktree directory
mkdir -p "$WORKTREE_BASE"

# Check if branch already exists
if git -C "$MAIN_REPO" show-ref --verify --quiet "refs/heads/${BRANCH_NAME}" 2>/dev/null; then
    # Branch exists - check if worktree already set up
    if [ -d "$WORKTREE_DIR" ]; then
        echo "Worktree already exists at: $WORKTREE_DIR" >&2
    else
        git -C "$MAIN_REPO" worktree add "$WORKTREE_DIR" "$BRANCH_NAME"
    fi
else
    # Create new branch from main/master
    DEFAULT_BRANCH="$(git -C "$MAIN_REPO" symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo 'main')"
    git -C "$MAIN_REPO" worktree add -b "$BRANCH_NAME" "$WORKTREE_DIR" "origin/${DEFAULT_BRANCH}"
fi

# Output structured result
cat <<EOF
WORKTREE_SETUP_BEGIN
ISSUE_KEY=${ISSUE_KEY}
FEATURE_NAME=${FEATURE_NAME}
FEATURE_SLUG=${FEATURE_SLUG}
BRANCH_NAME=${BRANCH_NAME}
WORKTREE_DIR=${WORKTREE_DIR}
MAIN_REPO=${MAIN_REPO}
REPO_NAME=${REPO_NAME}
WORKTREE_SETUP_END
EOF
