# Tracing Protocol

Rules for recording autopilot execution traces using `trace.py`.

## Initialization

After Step 0 (META-ISSUE), initialize tracing:
```bash
python3 ~/.claude/skills/autopilot/scripts/trace.py init \
  --session-id "$SESSION_ID" \
  --meta-issue-number "$META_ISSUE" \
  --meta-issue-url "$META_URL"
```
Store session_id: `autopilot-state.py update --field trace_session_id --value "$SESSION_ID"`

## Span Mapping

Each orchestration step maps to a span:

| Step | Span Name | Kind | Notes |
|------|-----------|------|-------|
| META-ISSUE | (auto: root) | session | Created by `init` |
| CLASSIFY | CLASSIFY | step | |
| WHY-CONTEXT | WHY-CONTEXT | step | |
| INGEST | INGEST | step | |
| VERIFY-PLAN | VERIFY-PLAN | step | |
| UL-CHECK | UL-CHECK | step | |
| CLARIFY | CLARIFY | step | |
| DECOMPOSE | DECOMPOSE | step | |
| CREATE | CREATE | step | |
| DAG-BUILD | DAG-BUILD | step | |
| VERIFY-INFRA-CHECK | VERIFY-INFRA-CHECK | step | Phase 5 |
| IMPL-LOOP | IMPL-LOOP | step | Contains issue spans |
| PRE-DEPLOY-VERIFY | PRE-DEPLOY-VERIFY | step | Renamed from VERIFY |
| DEPLOY-DETECT | DEPLOY-DETECT | step | Phase 4 |
| DEPLOY-VERIFY | DEPLOY-VERIFY | step | Phase 4 |
| TRIAGE | TRIAGE | step | |
| CHECKPOINT | CHECKPOINT | step | |
| FOLLOWUP | FOLLOWUP | step | |
| FINAL-VERIFY | FINAL-VERIFY | step | |
| REPORT | REPORT | step | |

### Issue Spans (inside IMPL-LOOP)

Each `/issue-impl` invocation creates:
```bash
ISSUE_SPAN=$(trace.py start-span --session $SID --name "issue-$ISSUE_NUM" --kind issue \
  --attr issue_number=$ISSUE_NUM --attr skill_invoked=issue-impl)
```

### Sub-step Spans (inside issue)

Review cycles, CI checks, etc.:
```bash
SUB_SPAN=$(trace.py start-span --session $SID --name "code-review" --kind sub_step \
  --attr attempt=1 --attr verdict=APPROVE)
```

## `<usage>` Tag Parsing

After Agent tool returns from `/issue-impl`:

1. Search result for `<usage>...</usage>` block
2. **Present**: Extract `total_tokens`, `tool_uses`, `duration_ms` → pass via `end-span --attr`
3. **Absent**: Record `total_tokens=null`, `tool_uses=null` (no error, status=ok)
4. **Parse failure**: Record `total_tokens=null`, add warning notes via `add-notes`

## Error Handling

On span error:
```bash
trace.py end-span --session $SID --span-id $SPAN --status error \
  --attr error_message="CI pipeline failed" --attr error_category=ci_failure
```

Error categories: `ci_failure`, `review_rejection`, `test_failure`, `timeout`, `auth_failure`, `unknown`

## Anomaly Detection Rules

Record notes when detecting:

1. **Long duration + few tokens**: External wait (CI, deploy, user input)
2. **Short duration + many tokens**: Excessive context loading
3. **High retry count** (>3 attempts): Prompt quality issue
4. **Token spike** vs session average: Regression or inefficiency
5. **Excessive tool_uses** (>50 per issue): Exploration inefficiency

Notes format (3-part): `"metric: <value> | cause: <hypothesis> | action: <recommendation>"`

## Insight Generation

When `confidence ≥ 90%` across ≥ 3 sessions, suggest configuration updates.
Example: If retry count consistently > 3, suggest increasing `max_retries` or improving review criteria.

## Simple Path Tracing

Simple path records 6 step spans: CLASSIFY, WHY-CONTEXT, ISSUE, IMPL, VERIFY, REPORT.
Same span creation rules apply; fewer steps.

## Finalization

At Step 12 (REPORT):
```bash
trace.py finalize --session $SID \
  --attr total_tokens=$TOTAL_TOKENS \
  --attr total_tool_uses=$TOTAL_TOOL_USES \
  --attr complexity=$COMPLEXITY \
  --attr provider=$PROVIDER
```
