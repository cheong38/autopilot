# Bug Report Template

## Bug Report

**Title**: [concise description of the bug]

## Baseline

- Git SHA: [`<sha>`]
- Branch: [branch name]

## Root Cause

[What is broken and why. Include exact error message if available.]

> "exact error message from logs or stack trace"

## Steps to Reproduce

[Numbered steps to trigger the bug, OR a test scenario description.
For agent-generated RCA bugs, a failing test case is preferred over manual steps.]

1. [Step 1]
2. [Step 2]
3. [Step 3]
4. Result: [observed failure]

## Expected vs Actual Behavior

**Expected**: [what should happen]
**Actual**: [what happens instead]

## Code Snapshot

[Actual current code that needs changing. Use code blocks with file path.
This is a search anchor for the implementing agent — do NOT rely on line numbers alone,
as they may shift between sessions.]

```python
# path/to/file.py — method_name:
def method_name(...):
    try:
        ...
    except (SomeError) as e:
        ...
    # ← problem: OtherError escapes this except
```

## Blast Radius

[All code paths affected by this bug. Include re-verification command
so the implementing agent can discover paths added after RCA time.]

- `path/to/caller1.py` — description [Fact]
- `path/to/caller2.py` — description [Inference, verify]

Re-verify: `grep -r "function_name" src/`

## Confidence

[Separate facts from inferences. The implementing agent uses this
to decide what to verify before acting on claims.]

| Claim | Level | Verification |
|-------|-------|--------------|
| [specific claim] | Fact | [how confirmed: code read / log evidence] |
| [specific claim] | Inference | [how to verify: command or file to read] |

## Action Items

[Single execution path with dependencies. No "or" / "또는" options.
RCA agent MUST decide. If a decision cannot be made, move to Escalation.]

1. [action description] → (2의 전제)
2. [action description] → (3의 전제)
3. [action description]
4. [action description] (독립, 어느 시점이든 가능)

## File Scope

[Explicit modification boundaries. "Do Not Modify" prevents the implementing agent
from touching layers or interfaces that should remain stable.]

| Action | Path | Note |
|--------|------|------|
| Modify | `path/to/file.py` | [what to change] |
| Create | `tests/path/to/test.py` | [new test file] |
| Do Not Modify | `domain/` | [reason: layer boundary] |
| Do Not Modify | `SomeProtocol` interface | [reason: contract stability] |

## Verification

[Machine-executable commands. ALL must exit 0 for the fix to be considered complete.
The implementing agent runs these after implementation and MUST NOT mark done until all pass.]

```bash
# Existing tests still pass
test_command_1

# New regression test passes
test_command_2

# Type check
typecheck_command

# Lint
lint_command
```

Success criteria:
- All commands exit 0
- [additional criteria if needed, e.g., "no 500 responses from the modified endpoint"]

## Escalation Criteria

[Conditions under which the implementing agent MUST stop and request human intervention.
If none of these conditions are met, the agent proceeds autonomously.]

- [condition] → [why human is needed]
- [condition] → [why human is needed]

## Dependencies

[Only include if applicable. Use `#N` issue references for auto-linking.
When DAG analysis detects relationships (Step 5.5/5.6), these are auto-populated.]
- Depends on #[N] — [why this bug fix needs it]
- Duplicated by #[K] — [if detected as duplicate of existing issue]

## Blocks

[Only include if applicable. Use `#N` issue references for GitHub auto-linking.
Auto-populated from DAG reverse dependency analysis.]

> 이 Bug Fix를 완료해야 아래 이슈를 진행할 수 있습니다.

- Blocks #[N] — [what is waiting on this bug fix]

---

## Pipeline Metadata (optional)

[Agent provenance and session context. Useful for auditing and pipeline optimization.]

| Key | Value |
|-----|-------|
| Model | [model name and version] |
| RCA Timestamp | [ISO 8601 UTC] |
| Session ID | [session identifier] |
