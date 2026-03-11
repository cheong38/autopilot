# Meta-Issue Creation Commands

Provider-specific commands for creating the autopilot meta-issue (Step 0).

## GitHub

```bash
gh issue create --title "[Task] Autopilot: <summary>" --body "<body>" --label "task,autopilot"
```

## GitLab

```bash
glab issue create --title "[Task] Autopilot: <summary>" --description "<body>" --label "task,autopilot"
```

## Jira

Create via Jira MCP with type `Task`, label `autopilot`.
