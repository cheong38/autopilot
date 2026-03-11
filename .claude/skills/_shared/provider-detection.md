# Provider Detection & Commands

Shared reference for issue tracker and VCS provider detection. Used by `/issue`, `/issue-impl`, `/planner`, and session management.

## Detection Algorithm

1. **Check `.claude/issue.yaml`** for explicit config (fallback: `.claude/story.yaml`)
2. **If issue key matches `XXX-123` pattern** (e.g., KIH-456) → **Jira**
3. **Check git remote URL**: `git remote get-url origin`
   - Contains `github.com` → **GitHub** (use `gh` CLI)
   - Contains `gitlab` → **GitLab** (use `glab` CLI)
4. **If ambiguous** → ask the user

**Note**: Jira is an issue tracker only. VCS operations (branches, PRs/MRs) still use GitHub or GitLab based on the git remote.

## Provider-Specific Commands

| Operation | GitHub (`gh`) | GitLab (`glab`) | Jira (MCP) |
|-----------|---------------|-----------------|------------|
| View issue | `gh issue view <N> --json title,body,labels` | `glab issue view <N>` | `mcp__jira__jira_get` path `/rest/api/3/issue/<KEY>` |
| Edit issue | `gh issue edit <N> --body "..."` | `glab issue edit <N> --description "..."` | `mcp__jira__jira_put` path `/rest/api/3/issue/<KEY>` |
| Add comment | `gh issue comment <N> --body "..."` | `glab issue note <N> --message "..."` | `mcp__jira__jira_post` path `/rest/api/3/issue/<KEY>/comment` |
| Create issue | `gh issue create --title "..." --body "..." --label "<type>"` | `glab issue create --title "..." --description "..." --label "<type>"` | `mcp__jira__jira_post` path `/rest/api/3/issue` |
| Create PR/MR | `gh pr create --title "..." --body "..."` | `glab mr create --title "..." --description "..."` | N/A (use VCS provider) |
| Review PR/MR | `gh pr review <N> --approve/--request-changes` | `glab mr approve <N>` / comment | N/A |
| Merge PR/MR | `gh pr merge <N> --squash --delete-branch` | `glab mr merge <N> --squash --remove-source-branch` | N/A |
| PR/MR diff | `gh pr diff <N>` | `glab mr diff <N>` | N/A |

## Lock Management

| Operation | GitHub | GitLab | Jira |
|-----------|--------|--------|------|
| Check lock | `gh issue view <N> --json labels -q '.labels[].name'` → look for `wip` | `glab issue view <N> --output json` → parse labels for `wip` | `mcp__jira__jira_get` → check `fields.status.name` == "In Progress" |
| Acquire lock | `gh issue edit <N> --add-label "wip"` | Read existing labels, append `wip`, `glab issue edit <N> --label "<all>"` | Fetch transitions → find "In Progress" → `mcp__jira__jira_post` to transitions endpoint |
| Release lock | `gh issue edit <N> --remove-label "wip"` | Read labels, filter out `wip`, set remaining | Fetch transitions → find back transition (e.g., "To Do") → post transition |

## Configuration

Reads `.claude/issue.yaml` (fallback: `.claude/story.yaml`):

```yaml
tracker: github | gitlab | jira
github:
  labels: { story: story, task: task, bug: bug }
  title_prefix: true
gitlab:
  labels: { story: story, task: task, bug: bug }
  title_prefix: true
jira:
  project: KIH
  subtask_type: "하위 작업"
```
