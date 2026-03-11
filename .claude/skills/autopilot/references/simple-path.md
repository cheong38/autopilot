# Simple Path (Steps S1–S4)

Streamlined workflow for single-issue tasks classified as **simple** by Step 0.3 CLASSIFY.

## Prerequisites

- Step 0: META-ISSUE completed (meta-issue created, session locked, state initialized)
- Step 0.3: CLASSIFY determined `complexity = simple`
- `autopilot-simple` checklist created: `checklist.py create autopilot-simple <meta-issue>`

<HARD-GATE>
Step S1(ISSUE)은 /issue 스킬을, Step S2(IMPL)는 /issue-impl 스킬을 통해 실행하라.
직접 gh issue create, git commit, gh pr create 등을 수동 실행하는 것은 프로토콜 위반이다.
</HARD-GATE>

## Step S1: ISSUE

Create a single issue for the task.

1. Invoke `/issue` with the task description (includes review cycle)
2. Parse `ISSUE_RESULT_BEGIN/END` output
3. Store in state: `autopilot-state.py add-issue --id <N> --url <URL> --type <type> --title "<title>"`
4. Include `## Context` section in issue body with Why Context from meta-issue

**Fallback**: If `/issue` blocks on UIP-05, create directly via provider CLI:
- GitHub: `gh issue create --title "<title>" --body "<body>" --label "task,autopilot"`
- GitLab: `glab issue create --title "<title>" --description "<body>" --label "task,autopilot"`
- Jira: Create via Jira MCP with type `Task`, label `autopilot`

Query ready sub-tasks: `checklist.py ready-subtasks autopilot-simple <meta-issue> 3`. Execute all returned, mark each done. Repeat until `checklist.py check-step autopilot-simple <meta-issue> 3` returns `COMPLETE`.

## Step S2: IMPL

Implement the issue using the full `/issue-impl` lifecycle.

1. Execute `/issue-impl <issue_number>`
2. `/issue-impl` internally handles: plan → implement → code-review (Step 8) → CI gate → merge
3. Wait for completion — do not proceed until PR is merged or escalation occurs

**Failure**: If `/issue-impl` fails after retries → UIP-26 (skip/retry/abort). See [Error Recovery](error-recovery.md).

Query ready sub-tasks: `checklist.py ready-subtasks autopilot-simple <meta-issue> 4`. Execute all returned, mark each done. Repeat until `checklist.py check-step autopilot-simple <meta-issue> 4` returns `COMPLETE`.

## Step S3: VERIFY

Verify the implementation meets requirements.

1. Use the verification method from the requirement (auto-extracted or user-specified)
2. Priority: Playwright → CLI/API → Test suite → Manual fallback
3. See [Verification Matrix](verification-matrix.md) for templates

**Pass** → mark verified:
```bash
autopilot-state.py update-issue --id <N> --status closed --verified true
```

**Fail** → create follow-up bug via `/issue --bug --no-brainstorm`, then:

**교훈 즉시 포착**: Follow-up bug 생성 시 원인 분석 후 state에 기록.
```bash
autopilot-state.py add-lesson \
  --step "VERIFY" \
  --category "<verification|diagnosis|scope|protocol>" \
  --summary "<한 줄 요약>" \
  --detail "<상세 원인 및 교훈>" \
  --evidence "#<이슈>, PR #<PR>"
```

Re-enter IMPL (Step S2) for the bug. Max 1 follow-up cycle in simple path; if still failing, escalate to user.

Query ready sub-tasks: `checklist.py ready-subtasks autopilot-simple <meta-issue> 5`. Execute all returned, mark each done. Repeat until `checklist.py check-step autopilot-simple <meta-issue> 5` returns `COMPLETE`.

## Step S4: REPORT

Finalize and report results.

1. Update session status:
   ```bash
   # complete: issue implemented and verified
   # partial: issue remains open or unverified
   autopilot-state.py update --field status --value <complete|partial>
   ```
2. **RETROSPECTIVE** (축소):
   a. `autopilot-state.py query --field lessons` → 교훈이 없으면 skip
   b. 교훈이 있으면 프로젝트 메모리 `## Autopilot Lessons`에 기록 (중복 시 Recurrence 추가)
   c. 검증 우선순위(Playwright → CLI → Manual) 준수 여부 확인
3. Post summary on meta-issue (교훈이 있으면 `## Lessons Learned` 섹션 포함)
4. Close meta-issue
5. Release session lock

**Result output**:

```
AUTOPILOT_RESULT_BEGIN
MODE=simple
META_ISSUE=<number>
ISSUE=<N>
PR=<N>
STATUS=<complete|partial>
AUTOPILOT_RESULT_END
```

Query ready sub-tasks: `checklist.py ready-subtasks autopilot-simple <meta-issue> 6`. Execute all returned, mark each done. Repeat until `checklist.py check-step autopilot-simple <meta-issue> 6` returns `COMPLETE`.

## Status Footer (Simple Mode)

```
---
Meta-Issue: #<number> <url>
Mode: simple
Step: <step_name> (<S1|S2|S3|S4>)
Current: #<issue> <action>
```

Note: `Progress` line is omitted in simple mode (always 1 issue).

## Tracing Span Mapping (Simple Path)

Simple path records 6 step spans. See [Tracing Protocol](tracing-protocol.md).

| Step | Span Name | Kind | Notes |
|------|-----------|------|-------|
| META-ISSUE | (auto: root) | session | Created by `trace.py init` |
| CLASSIFY | CLASSIFY | step | |
| WHY-CONTEXT | WHY-CONTEXT | step | |
| S1: ISSUE | ISSUE | step | |
| S2: IMPL | IMPL | step | Contains issue span (kind=issue) |
| S3: VERIFY | VERIFY | step | |
| S4: REPORT | REPORT | step | Includes `trace.py finalize` |

Issue spans inside IMPL follow the same rules as complex path (see tracing-protocol.md).

## Error Recovery

| Scenario | Action |
|----------|--------|
| `/issue` skill fails | Retry once → direct creation fallback |
| `/issue-impl` fails 3x | UIP-26 (skip/retry/abort) |
| Verification timeout | Mark as manual, present steps to user |
| Network failure | Retry with exponential backoff (3 attempts) |
