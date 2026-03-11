# State Block Formats

Structured output blocks used by the autopilot orchestrator for inter-step communication.

## META Block (Step 0)

```
AUTOPILOT_META_BEGIN
META_ISSUE=<number>
META_URL=<url>
PROVIDER=<github|gitlab|jira>
SESSION_ID=<uuid>
STATUS=locked
AUTOPILOT_META_END
```

## INGEST Block (Step 1)

```
AUTOPILOT_INGEST_BEGIN
TOTAL_REQUIREMENTS=<N>
REQUIREMENTS=<JSON array of {id, text, type_hint, confidence}>
STATUS=parsed
AUTOPILOT_INGEST_END
```

## DECOMPOSE Block (Step 3)

```
AUTOPILOT_DECOMPOSE_BEGIN
TOTAL_ISSUES=<N>
ISSUES=<JSON array of {title, type, requirement_ids, verification_methods, depends_on}>
STATUS=decomposed
AUTOPILOT_DECOMPOSE_END
```

## CHECKPOINT Block (Step 8)

```
AUTOPILOT_CHECKPOINT_BEGIN
COMPLETED_ISSUE=<number> VERIFIED=<true|false> REMAINING_READY=<N> TOTAL_COMPLETED=<N>/<total>
AUTOPILOT_CHECKPOINT_END
```

## RESULT Block (Step 12)

```
AUTOPILOT_RESULT_BEGIN
META_ISSUE=<number>
TOTAL_CREATED=<N>
TOTAL_IMPLEMENTED=<N>
AUTO_VERIFIED=<N>
MANUAL_VERIFIED=<N>
FOLLOWUP_ROUNDS=<N>
STATUS=<complete|partial>
AUTOPILOT_RESULT_END
```

## ABORT Block

```
AUTOPILOT_ABORT_BEGIN
META_ISSUE=<number>
STEP_AT_ABORT=<step_name>
COMPLETED=<N>/<total>
REASON=<user_requested|error|blocked>
AUTOPILOT_ABORT_END
```
