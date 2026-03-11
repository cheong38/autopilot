# Bug Review Criteria

## Severity Tiers

| Tier | Label | Blocks Approval? | Description |
|------|-------|-------------------|-------------|
| CRITICAL | Missing core element | YES | Bug report is fundamentally incomplete |
| MAJOR | Significant gap | YES | Bug report has notable quality issues |
| MINOR | Improvement | NO | Report could be better but is acceptable |
| SUGGESTION(STRONG) | Recommended | NO | Best practice recommendation |
| SUGGESTION(WEAK) | Optional | NO | Stylistic or preferential |

## Approval Rule

**APPROVE when**: Only MINOR and SUGGESTION(WEAK) findings remain.
**NEEDS_WORK when**: Any CRITICAL or MAJOR findings exist.

## Review Checklist

### 1. Baseline (MAJOR if missing)
- [ ] Git SHA is specified (pinpoints exact codebase state)
- [ ] Branch name is specified
- [ ] If code has changed since SHA, implementing agent can detect drift via `git diff`

### 2. Root Cause (CRITICAL if missing, MAJOR if vague)
- [ ] Clearly explains WHAT is broken and WHY
- [ ] Includes exact error message or exception text if available
- [ ] Root cause is specific enough to guide the fix (not just "it crashes")

### 3. Steps to Reproduce (MAJOR if missing for UI bugs, MINOR for code-level bugs with Code Snapshot)
- [ ] Clear, numbered steps provided
- [ ] Steps are specific enough for anyone to follow
- [ ] Starting state/preconditions described
- [ ] For agent-generated RCA bugs: test scenario description is acceptable in place of manual steps

### 4. Expected vs Actual Behavior (CRITICAL if missing)
- [ ] Expected behavior clearly described
- [ ] Actual behavior clearly described
- [ ] Difference between expected and actual is obvious

### 5. Code Snapshot (CRITICAL if missing for code-level bugs)
- [ ] Actual current code included (not just file path or line number)
- [ ] Code block includes file path as comment for search anchor
- [ ] Problem area is annotated (e.g., `# ← problem: ...`)
- [ ] Code is sufficient for implementing agent to locate the exact position
- [ ] Line numbers are NOT the sole identifier (code content is the anchor)

### 6. Blast Radius (MAJOR if missing for code-level bugs)
- [ ] All callers/paths affected by the bug are listed
- [ ] Each path is marked as Fact or Inference
- [ ] Re-verification command is provided (e.g., `grep -r "function" src/`)
- [ ] Determination is clear: single-site fix vs shared-layer fix

### 7. Confidence Markers (MAJOR if missing)
- [ ] Claims are separated into Fact vs Inference
- [ ] Each Fact states how it was confirmed (code read, log evidence)
- [ ] Each Inference states how to verify (command, file to read)
- [ ] No unqualified assertions that could mislead the implementing agent

### 8. Action Items (CRITICAL if missing, MAJOR if ambiguous)
- [ ] Actions are ordered with explicit dependencies (→ notation)
- [ ] **No "or" / "또는" options** — single execution path only
- [ ] If a decision could not be made, it appears in Escalation (not as an option here)
- [ ] Each action is specific enough to implement without further research
- [ ] Independent actions are marked as such

### 9. File Scope (MAJOR if missing)
- [ ] "Modify" files are listed with what to change
- [ ] "Create" files are listed (new test files, etc.)
- [ ] "Do Not Modify" boundaries are specified with rationale
- [ ] Scope prevents implementing agent from touching unrelated layers/interfaces

### 10. Verification (CRITICAL if missing)
- [ ] Machine-executable commands are provided (copy-pasteable)
- [ ] Commands include existing tests, new tests, type check, lint
- [ ] Success criteria explicitly stated (e.g., "all exit 0")
- [ ] Commands are sufficient for the implementing agent to self-verify
- [ ] No verification step requires human judgment or external system access

### 11. Escalation Criteria (MAJOR if missing)
- [ ] Conditions for human intervention are explicitly listed
- [ ] Each condition explains WHY human is needed (not just "if something goes wrong")
- [ ] Implementing agent can evaluate these conditions autonomously
- [ ] If no escalation conditions exist, section states "None — proceed autonomously"

### 12. Dependencies (MINOR if missing when relevant)
- [ ] Depends on: upstream issues identified with `#N` references
- [ ] Blocks: downstream issues identified with `#N` references

### 13. Pipeline Metadata (SUGGESTION(WEAK))
- [ ] Model name and version included
- [ ] RCA timestamp included
- [ ] Session ID included (for audit trail)

### 14. Language & Clarity (MINOR)
- [ ] Written in user's language consistently
- [ ] Clear and unambiguous wording
- [ ] Technical terms are appropriate

## Review Output Format

```markdown
## Bug Review

**Verdict**: APPROVE / NEEDS_WORK
**Issue**: #<number>
**Type**: Bug

### Findings

#### CRITICAL
- [Finding description] → [Suggested fix]

#### MAJOR
- [Finding description] → [Suggested fix]

#### MINOR
- [Finding description] → [Suggested improvement]

#### SUGGESTIONS
- [STRONG] [Recommendation]
- [WEAK] [Optional improvement]

### Summary
[1-2 sentence overall assessment]
```
