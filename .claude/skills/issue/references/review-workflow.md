# Review Workflow

## Step 7: Review Issue (Sub-Agent)

The review is executed by a **separate sub-agent** to isolate the reviewer perspective from the orchestrator. See "Sub-Agent Dispatch" section in SKILL.md.

### 7a. Collect Context (Orchestrator)

1. Fetch the issue content:
   - **GitHub:** `gh issue view <ISSUE_NUMBER> --json title,body`
   - **GitLab:** `glab issue view <ISSUE_NUMBER>`
   - **Jira (sub-issue):** `mcp__jira__jira_get` with path `/rest/api/3/issue/<SUB_ISSUE_KEY>` — read the sub-issue's `summary` and `description` fields.
2. Read the review criteria file: `~/.claude/skills/issue/references/review-criteria-<TYPE>.md`

### 7b. Construct Review Prompt

Build a **self-contained** prompt embedding all context. The sub-agent must not read any files.

~~~text
You are a strict issue quality reviewer.

## Issue
**Type**: <story|task|bug>
**Title**: <issue title>
**Body**:
<full issue body>

## Review Criteria
<paste full contents of review-criteria-<TYPE>.md>

## Instructions
1. Evaluate the issue against EACH criterion in the review criteria
2. Classify every finding by severity:
   - CRITICAL: Missing core element (blocks approval)
   - MAJOR: Significant gap (blocks approval)
   - MINOR: Improvement (non-blocking)
   - SUGGESTION(STRONG): Recommended (non-blocking)
   - SUGGESTION(WEAK): Optional (non-blocking)
3. Determine verdict:
   - APPROVE: Only MINOR + SUGGESTION(WEAK) remain
   - NEEDS_WORK: Any CRITICAL or MAJOR findings
4. Write the review in markdown, then emit structured output

## Required Structured Output

REVIEW_RESULT_BEGIN
ISSUE=<number-or-key>
TYPE=<story|task|bug>
VERDICT=<APPROVE|NEEDS_WORK>
CRITICAL_COUNT=<n>
MAJOR_COUNT=<n>
MINOR_COUNT=<n>
SUGGESTION_COUNT=<n>
SUMMARY=<one-line summary>
PROVIDER=<github|gitlab|jira>
REVIEW_RESULT_END

Do NOT explore or fetch any files. All context is provided above.
~~~

### 7c. Dispatch to Sub-Agent

**Claude Code:**
```
Task(subagent_type="general-purpose", model="sonnet", max_turns=5, prompt=<review_prompt>)
```

**OpenCode / Codex:**
Execute the review prompt as an isolated sub-agent step using the platform's native mechanism (e.g., agent spawn, isolated execution context). If no sub-agent tool exists, execute the review inline as the orchestrator with a clear role separation marker (`--- REVIEWER START ---` / `--- REVIEWER END ---`).

### 7d. Process Result (Orchestrator)

1. Parse the sub-agent response for the `REVIEW_RESULT` structured block (between BEGIN/END markers)
2. Post the review markdown as a comment:
   - **GitHub:** `gh issue comment <ISSUE_NUMBER> --body "<review markdown>"`
   - **GitLab:** `glab issue note <ISSUE_NUMBER> --message "<review markdown>"`
   - **Jira:** `mcp__jira__jira_post` to `/rest/api/3/issue/<KEY>/comment`
3. Record review: `checklist.py add-review issue <issue> <iteration> <verdict> "<summary>"`
4. Update step: `checklist.py update issue <issue> 7 done`

## Step 8: Address Feedback (if NEEDS_WORK)

Execute the following steps to address review findings.

1. Read the review comment from Step 7
2. For each finding, apply critic stance evaluation:
   - **Accept**: Valid point, make the change
   - **Accept with modification**: Good intent, adjust approach
   - **Clarify**: Based on misunderstanding, add cross-reference
   - **Decline**: Conflicts with issue constraints (explain why)
3. Update the issue:
   - **GitHub:** `gh issue edit <ISSUE_NUMBER> --body "<updated body>"`
   - **GitLab:** `glab issue edit <ISSUE_NUMBER> --description "<updated body>"`
   - **Jira (sub-issue):** Update the sub-issue description via `mcp__jira__jira_put`:
     ```
     mcp__jira__jira_put with:
       path: "/rest/api/3/issue/<SUB_ISSUE_KEY>"
       body: {
         "fields": {
           "description": {
             "type": "doc",
             "version": 1,
             "content": [
               {
                 "type": "codeBlock",
                 "attrs": {"language": "markdown"},
                 "content": [{"type": "text", "text": "<updated issue markdown content>"}]
               }
             ]
           }
         }
       }
     ```
4. Reply explaining changes:
   - **GitHub:** `gh issue comment <ISSUE_NUMBER> --body "Addressed review feedback: ..."`
   - **GitLab:** `glab issue note <ISSUE_NUMBER> --message "Addressed review feedback: ..."`
   - **Jira (sub-issue):** Post a comment on the sub-issue explaining changes:
     ```
     mcp__jira__jira_post with:
       path: "/rest/api/3/issue/<SUB_ISSUE_KEY>/comment"
       body: {"body": {"type": "doc", "version": 1, "content": [
         {"type": "paragraph", "content": [
           {"type": "text", "text": "Addressed review feedback: <changes summary>"}
         ]}
       ]}}
     ```

Emit structured output:

```
ISSUE_RESULT_BEGIN
ISSUE=<number-or-key>
ISSUE_URL=<url>
TYPE=<story|task|bug>
CHANGES_MADE=<count>
CHANGES_DECLINED=<count>
STATUS=updated
PROVIDER=<github|gitlab|jira>
ISSUE_RESULT_END
```

After completion:
1. Update step 8
2. Go back to Step 7 (review again) with incremented iteration
3. Max 3 iterations total; if still NEEDS_WORK after 3, present to user for manual decision
