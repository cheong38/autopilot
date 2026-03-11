# Jira Sub-Issue Flow

## Jira Sub-Issue Lifecycle

```
┌──────────────────────────────────────────────────────────────────┐
│                   JIRA SUB-ISSUE LIFECYCLE                        │
├──────────────────────────────────────────────────────────────────┤
│  1. FETCH      │ Read Jira parent issue + all comments           │
│  1.5 SCOPE     │ Decompose requirements into sub-issues          │
│  1.6 CONFIRM   │ Present decomposition → user approves/adjusts   │
│  3. DETECT     │ Jira (already known from key pattern)           │
│                │                                                 │
│  FOR EACH sub-issue i of N:                                      │
│  │  2. TYPE    │ Determine type from scope analysis              │
│  │  4. DISCOVER│ Ask missing info (per sub-issue)                │
│  │  5. CHECKLIST│ Init per-sub-issue checklist                   │
│  │  6. CREATE  │ Create Jira sub-issue: [Implement] <title>      │
│  │  7. REVIEW  │ Evaluate sub-issue quality                      │
│  │  8. ADDRESS │ IF NEEDS_WORK → address review feedback         │
│  │  9. LOOP    │ Repeat 7-8 until APPROVED (max 3)              │
│  │                                                               │
│  10. DONE      │ Show summary table of all sub-issues            │
└──────────────────────────────────────────────────────────────────┘
```

## Jira Parent Issue Input

When the input is a Jira issue key (matches `XXX-123` pattern) with no additional requirements text, switch to the **Jira Sub-Issue flow**:

1. Fetch the parent Jira issue:
   ```
   mcp__jira__jira_get with path "/rest/api/3/issue/<ISSUE_KEY>"
   ```
2. Fetch all comments:
   ```
   mcp__jira__jira_get with path "/rest/api/3/issue/<ISSUE_KEY>/comment"
   ```
3. Extract requirements from:
   - Issue summary and description
   - All comment bodies (ordered chronologically, latest takes priority for conflicts)
4. Use the extracted requirements as input for Step 1.5 (Scope Analysis)
5. Proceed with the Jira Sub-Issue flow (always decompose, skip to Step 1.5)

## Jira Sub-Issue Creation (Step 6)

For the Jira Sub-Issue flow, create a new sub-issue under the parent issue. Extract the project key from the parent issue key (e.g., `KIH` from `KIH-42`).

```
mcp__jira__jira_post with:
  path: "/rest/api/3/issue"
  body: {
    "fields": {
      "project": {"key": "<PROJECT_KEY>"},
      "parent": {"key": "<PARENT_ISSUE_KEY>"},
      "summary": "[Implement] <title>",
      "issuetype": {"name": "<subtask_type from config, default: 하위 작업>"},
      "description": {
        "type": "doc",
        "version": 1,
        "content": [
          {
            "type": "codeBlock",
            "attrs": {"language": "markdown"},
            "content": [{"type": "text", "text": "<issue markdown content>"}]
          }
        ]
      }
    }
  }
```

**Title format for Jira sub-issues**: Always use `[Implement] <title>` as the summary.
- The `<title>` follows the same rules as the detected type (imperative for Task, "As a..." for Story, etc.)
- Examples: `[Implement] 결제 목록 조회 API 구현`, `[Implement] Set up OAuth provider configuration`

**After creation**: Parse the response to get the new sub-issue key (e.g., `KIH-43`). Use this key for subsequent review and update operations.
