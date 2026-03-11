# Autopilot Tracing System & Deploy-Verify Design

**Date**: 2026-03-02
**Status**: Approved
**Scope**: Three features — (1) execution tracing/observability, (2) post-deploy verification, (3) verification-first prerequisite resolution

---

## 1. Goals

- **Debugging & Diagnosis**: Trace back failed executions to identify where and why failures occurred
- **Cost Optimization**: Identify token/time-heavy steps, optimize model selection and prompts
- **Transparency & Audit**: Full session history reviewable post-execution with decision rationale

## 2. Architecture Decision

**Approach B**: Separate trace files + dedicated scripts.

- Trace data stored in `.claude/autopilot-traces/{session-id}.json` (project-relative)
- Separate from `autopilot-state.json` (concerns separation)
- Schema designed for mechanical OTEL migration (unique IDs, parent references, epoch timestamps, flat attributes)
- **NOT** OTEL-native at this stage — hierarchy is fixed (4 levels: session → step → issue → sub_step), no distributed tracing needed

## 3. Data Model

### 3.1 Hierarchy (4 levels)

```
Session Trace (root, kind=session)
├── Step Span (kind=step: INGEST, CREATE, DAG-BUILD, VERIFY-INFRA-CHECK, ...)
│   ├── attributes: {model_requested, total_tokens, tool_uses, ...}
│   └── events: [{name, timestamp, attributes}]
└── Issue Span (kind=issue: per issue lifecycle)
    ├── Sub-step Span (kind=sub_step: plan, plan-review, implement, code-review, code-fix, deploy-verify, ...)
    │   └── attributes: {model_requested, total_tokens, attempt, verdict, ...}
    └── events: [verification_result, error, retry, auth_handoff, ...]
```

**Simple path**: Uses the same 4-level hierarchy but with fewer steps:
```
Session Trace (root)
├── CLASSIFY (step)
├── WHY-CONTEXT (step)
├── ISSUE (step, contains issue creation + review sub-steps)
├── IMPL (issue, contains plan/impl/review/deploy-verify sub-steps)
├── VERIFY (step)
└── REPORT (step)
```

### 3.2 Span Schema

```json
{
  "id": "uuid-v4",
  "parent_id": "parent-uuid | null",
  "name": "IMPL-LOOP/issue-42/code-review",
  "kind": "session | step | issue | sub_step",
  "status": "ok | error | skipped",
  "start_time_ms": 1709251200000,
  "end_time_ms": 1709251320000,
  "duration_ms": 120000,
  "attributes": {
    "model_requested": "opus | sonnet | haiku",
    "total_tokens": 45230,
    "input_tokens": null,
    "output_tokens": null,
    "tool_uses": 12,
    "attempt": 1,
    "max_attempts": 3,
    "agent_type": "sub_agent | inline | team",
    "session_type": "new | resumed",
    "skill_invoked": "/issue-impl",
    "issue_number": 42,
    "complexity": "simple | medium | complex",
    "step_index": 6,
    "error_message": null,
    "error_category": "network | syntax | review_reject | test_fail | ci_fail | merge_conflict | auth_fail",
    "verdict": "APPROVE | NEEDS_WORK",
    "verification_method": "playwright | cli | api | manual",
    "verification_result": true,
    "dag_ready_set": [41, 43],
    "context_compaction_count": 0,
    "wip_buffer_flushes": 2,
    "decision_points": "simple path selected: 2 issues"
  },
  "notes": "3분 소요됐으나 토큰은 8.2K만 사용. CI 파이프라인 대기(~2분)가 대부분.",
  "events": [
    {
      "name": "retry",
      "timestamp_ms": 1709251260000,
      "attributes": {"reason": "code_review_needs_work", "attempt": 2}
    }
  ]
}
```

Note: `input_tokens` and `output_tokens` are reserved for future Claude Code support. Currently null.

### 3.3 OTEL Migration Path

Each field maps mechanically to OTEL:
- `id` → `span_id`
- `parent_id` → `parent_span_id`
- Session root `id` → `trace_id` (all spans within a session share this value as their trace_id)
- `start_time_ms` × 1,000,000 → `start_time_unix_nano`
- `attributes` dict → OTEL span attributes (flat key-value)
- `events` → OTEL span events
- `status` → OTEL SpanStatus (ok/error)

A simple Python script can transform the JSON to OTEL protobuf/JSON format. All spans in one session file share the root span's `id` as their `trace_id`.

### 3.4 Additional Data Points (beyond user's initial list)

| Field | Purpose |
|-------|---------|
| `attempt` / `max_attempts` | Retry pattern analysis → prompt quality improvement |
| `complexity` | Post-hoc validation of complexity classification accuracy |
| `verification_method` + `verification_result` | Which verification was used, did it pass |
| `decision_points` | Branch decisions and rationale |
| `error_category` | Structured error classification |
| `dag_ready_set` | Parallel execution opportunity analysis |
| `context_compaction_count` | Session length/complexity indicator |
| `wip_buffer_flushes` | Progress save frequency |
| `notes` | Natural language observations about anomalies |

### 3.5 Token Measurement Strategy

- Primary: Parse `<usage>` tags from Agent tool results (`total_tokens`, `tool_uses`, `duration_ms`)
- Model: Record "requested model" from skill YAML config / sub-agent dispatch rules
- Schema reserves `input_tokens` and `output_tokens` fields (optional, currently null) for future Claude Code support
- Input/output split NOT estimated via tokenizer (too inaccurate — skill only sees prompt fragment, not full context)

### 3.6 Session ID

The trace session ID is the same UUID as `autopilot-state.json`'s `session_id`. The `trace_session_id` field added to `autopilot-state.json` links the two files:

```json
// autopilot-state.json
{
  "session_id": "abc-123",
  "trace_session_id": "abc-123",  // same value, explicit link
  ...
}
```

## 4. File Structure

```
.claude/                                    (project-relative)
├── autopilot-state.json                    (existing, add trace_session_id field)
├── autopilot-traces/
│   ├── {session-id}.json                   (per-session trace)
│   └── index.json                          (session list + summary metadata)
```

### 4.1 index.json Schema

```json
{
  "sessions": [
    {
      "session_id": "abc-123",
      "meta_issue": {"number": 10, "url": "..."},
      "started_at_ms": 1709251200000,
      "ended_at_ms": 1709254800000,
      "duration_ms": 3600000,
      "total_tokens": 342100,
      "total_tool_uses": 87,
      "issue_count": 3,
      "status": "complete | partial | aborted",
      "complexity": "simple | complex",
      "provider": "github | gitlab | jira"
    }
  ]
}
```

### 4.2 Trace File Retention Policy

- **Default**: Keep last 50 session trace files
- **Cleanup**: When `trace.py finalize` runs, if file count exceeds 50, delete oldest files
- **Archive**: Before deletion, append summary metrics to `index.json` (entry remains, file removed)
- **Override**: Configurable via `autopilot.yaml` key `trace_retention_count` (default: 50)

## 5. Implementation Components

### 5.1 `trace.py` — Tracing Engine (CLI)

```bash
python trace.py init --session-id $SID
python trace.py start-span --session $SID --name "NAME" --kind "step" --parent $PID --attr key=val
python trace.py end-span --session $SID --span $SPAN_ID --status ok --attr total_tokens=N
python trace.py add-event --session $SID --span $SPAN_ID --name "retry" --attr reason=X
python trace.py add-notes --session $SID --span $SPAN_ID --notes "natural language observation"
python trace.py finalize --session $SID
```

The `--session-id` for `init` uses the same UUID from `autopilot-state.json`'s `session_id`.

### 5.2 `trace-report.py` — Report Generator

```bash
python trace-report.py summary --session $SID --format markdown    # issue comment
python trace-report.py compare --sessions $S1 $S2                  # cross-session comparison
python trace-report.py bottleneck --session $SID                   # top-N token consumers
python trace-report.py review-stats --last 10                      # review pattern analysis
python trace-report.py list                                        # all sessions
```

#### `compare` output format

```markdown
## Session Comparison: abc-123 vs def-456

| Metric | abc-123 | def-456 | Delta |
|--------|---------|---------|-------|
| Duration | 42m 15s | 38m 02s | -10% |
| Total Tokens | 342,100 | 289,400 | -15% |
| Issues | 3 | 3 | — |
| Avg Tokens/Issue | 114,033 | 96,467 | -15% |
| Review Retries | 3 | 1 | -67% |
| CI Failures | 1 | 0 | -100% |

### Notable Differences
- abc-123 had 2 extra code review retries on issue #42 (lint failures)
- def-456 benefited from memory update: "isort --profile black" rule
```

### 5.3 Issue Comment Format

```markdown
## Autopilot Trace Summary

**Session**: `abc-123` | **Duration**: 42m 15s | **Total Tokens**: 342,100 | **Tool Uses**: 87

### Execution Timeline
| # | Step | Duration | Tokens | Model | Status | Notes |
|---|------|----------|--------|-------|--------|-------|
| 1 | INGEST | 2m 10s | 12,400 | sonnet | OK | parsed 5 requirements |
| ... | ... | ... | ... | ... | ... | ... |

### Insights

**Cost Anomalies:**
- IMPL #42 plan: 120K tokens (35% of total).
  Cause: full src/ directory included in prompt context.
  → Improve: selective file inclusion in plan prompt

**Time Anomalies:**
- deploy-verify: 5m (0 tokens). CI pipeline wait 3m + Playwright 2m.
  → Normal range, no action needed

**Review Patterns:**
- code-review avg 1.7 attempts/issue. Repeated feedback: "missing error handling" (2/3).
  → Improve: add error handling checklist to issue-impl prompt

**Failure Patterns:**
- CI failure: lint rule violation (import order) — 5 occurrences across last 3 sessions
  → Recurring pattern confirmed
- Merge conflict: DAG missing dependency between #41 and #43 (same file modified)
  → Consider file conflict detection in DAG-BUILD

### Suggested Updates (confidence >= 90%)

| Target | File | Suggestion | Confidence | Reason |
|--------|------|------------|------------|--------|
| Memory | patterns.md | "Project enforces isort --profile black" | 95% | 5 identical lint failures across 3 sessions |
| Skill | issue-impl/SKILL.md | Add auto lint --fix before code-review | 92% | Lint failures = 40% of review retries |
| — | — | (no other suggestions meet 90% threshold) | — | — |

<details><summary>Full trace JSON</summary>...</details>
```

### 5.4 Anomaly Detection Rules

| Pattern | Meaning | Note Template |
|---------|---------|---------------|
| Long duration + few tokens | External wait (CI, deploy, auth) | "{duration} but only {tokens} tokens. {cause} occupied ~{pct}%" |
| Short duration + many tokens | Heavy generation or large context | "{tokens} tokens in {duration}. Prompt context likely oversized" |
| High retry count | Prompt/instruction quality issue | "Review {n} attempts. Repeated feedback: {common_issue}" |
| Spike vs previous sessions | Regression or inefficiency | "Tokens {pct}% higher than avg. Cause: {reason}" |
| Excessive tool uses | Exploration inefficiency | "{tool_uses} tool calls, {dominant_tool} used {count} times" |

### 5.5 Insight-to-Action Pipeline

Each insight follows: **Metric → Cause Analysis → Concrete Action**

- Never output "tokens were high" without explaining why
- Always propose a specific change (file, line, rule) when confidence >= 90%
- Cross-reference with previous sessions when available (via index.json)

## 6. Deploy-Verify Workflow (Autopilot Enhancement)

### 6.1 Relationship to Existing Step 6.5

The existing Step 6.5 (VERIFY) becomes **PRE-DEPLOY-VERIFY** — it covers local/CI-level verification before merge. The new steps 6.6-6.7 cover **post-merge, post-deploy** verification against the actual running environment.

```
6.5. PRE-DEPLOY-VERIFY (existing, renamed)
     - Local tests, CI pipeline pass
     - Unit/integration tests in the worktree

6.6. DEPLOY-DETECT (new, after merge)
     - Detect deployment environment (dev/staging/prod)
     - Identify deploy URL, method (Vercel, Docker, manual, etc.)

6.7. DEPLOY-VERIFY (new, post-deploy)
     - Verify against the actual deployed environment
     - Uses test accounts/data isolated from production
```

### 6.2 Deploy-Verify Sub-steps

```
6.7. DEPLOY-VERIFY
     6.7.1. TEST-DATA-SETUP
            - Create/verify test account and data
            - Ensure isolation from production data
            - Maintain persistent test fixtures across sessions
            - Test credentials: NEVER committed to git
              (use .env.test in .gitignore, or CI secrets, or prompt user)

     6.7.2. VERIFY-ATTEMPT (fallback chain)
            Priority 1: Playwright browser automation
              - Real browser interactions against deployed URL
              - Screenshot capture for evidence
            Priority 2: CLI / API Call / DB Query
              - curl, httpie, or custom CLI tools
              - Direct database queries via safe read-only access
            Priority 3: Step-by-step manual guide
              - Numbered checklist for human to follow
              - Clear expected vs actual comparison points
              - Human confirms each step via prompt

     6.7.3. AUTH-HANDOFF (when authentication required)
            Triggers:
              - Playwright detects login page
              - API returns 401/403
              - DB access denied
            Resolution:
              - Web: "Please log in at the browser window" → Playwright waits → continues
              - API: "Please enter your API key" → accepts via prompt → continues
            Security:
              - Credentials entered by user, never stored in trace files
              - Trace records only: auth_type, wait_duration, resolved (not the credentials)
            Trace records: auth_type, wait_duration, resolved

     6.7.4. CLEANUP (optional)
            - Remove test data created during verification
            - Or mark for retention (reuse in future sessions)
```

### 6.3 SKILL.md Integration

Current SKILL.md is at 497/500 lines. Strategy:
- Deploy-verify details → `references/deploy-verify.md` (new file)
- Tracing protocol → `references/tracing-protocol.md` (new file)
- SKILL.md adds only step numbers and reference pointers (~10 lines)
- Reclaim lines by moving existing verbose sections to references if needed

### 6.4 Verification Fallback Chain

```
Can Playwright reach the deploy URL?
├── Yes → Run Playwright scenarios
│   ├── Auth required? → AUTH-HANDOFF → retry
│   └── Pass/Fail → record result
└── No → Can CLI/API reach the service?
    ├── Yes → Run CLI/API verification
    └── No → Generate step-by-step manual guide
         └── User confirms → record result
```

## 7. Verification-First Prerequisite Resolution

### 7.1 Principle

Before implementing any feature issue, verify that the verification infrastructure exists at the **project level**. If it doesn't, create prerequisite issues to set it up first.

### 7.2 New Step: VERIFY-INFRA-CHECK (before IMPL-LOOP)

```
5.7. VERIFY-INFRA-CHECK (new, between DAG-CONFIRM and IMPL-LOOP)
     Run ONCE per project (not per-issue). Check:

     1. Does the project have the required verification infrastructure?
        - CI: Is a CI pipeline configured? (check .github/workflows, .gitlab-ci.yml, etc.)
        - Playwright: Is Playwright installed? Config file exists?
        - Deploy target: Is there a deploy URL or deploy config?
        - Test data: Do test accounts/fixtures exist?
        - Auth: Are test credentials accessible?

     2. If any verification prerequisite is missing:
        a. Create prerequisite issue(s) for the missing infrastructure:
           - "Set up CI pipeline for project X"
           - "Configure E2E test environment with Playwright"
           - "Create test account and seed data for staging"
           - "Set up deployment pipeline to dev/staging server"
        b. Add prerequisite issues to DAG as dependencies (blockers for ALL feature issues)
        c. Implement prerequisite issues FIRST via /issue-impl
        d. Prerequisite issues use manual verification fallback
           (they CANNOT trigger recursive VERIFY-INFRA-CHECK — recursion depth = 0)
        e. Re-verify infrastructure after prereq implementation

     3. If all verification prerequisites exist:
        - Proceed to IMPL-LOOP as normal
```

### 7.3 Recursion Guard

Prerequisite issues (infra setup) skip VERIFY-INFRA-CHECK to prevent infinite recursion:
- Feature issues: VERIFY-INFRA-CHECK → required
- Prerequisite issues: VERIFY-INFRA-CHECK → skipped, use manual verification or simple CLI checks
- This is enforced by tagging prereq issues with `type: prereq-infra` in the DAG

### 7.4 Prerequisite Issue Categories

| Category | Example Issue | Verification That It Works |
|----------|--------------|---------------------------|
| CI Pipeline | "Set up GitHub Actions CI for lint + test" | `gh run list` shows successful run |
| E2E Test Env | "Configure Playwright with test fixtures" | `npx playwright test --list` shows tests |
| Deploy Target | "Set up Vercel preview deployments" | Deploy URL accessible after push |
| Test Data | "Create test account + seed data for staging" | Login with test credentials succeeds |
| Auth Config | "Store test API keys in .env.test" | API call with test key returns 200 |

Note: Test credentials (API keys, passwords) must NEVER be committed to git. Use `.env.test` (in `.gitignore`), CI/CD secrets, or prompt user for input.

### 7.5 DAG Integration

Prerequisite issues are added as **blocking dependencies** in the DAG:

```
Before:
  issue-41 (feature A) → issue-42 (feature B) → issue-43 (feature C)

After VERIFY-INFRA-CHECK (CI missing, no test account):
  prereq-1 (set up CI) ──┐
  prereq-2 (test account) ┤
                           ├→ issue-41 → issue-42 → issue-43
```

Prerequisite issues are implemented via the same `/issue-impl` flow, including their own tracing spans.

### 7.6 Trace Recording

Prerequisite resolution is recorded as spans:

```
VERIFY-INFRA-CHECK
├── check-ci                 → status: ok
├── check-playwright         → status: missing
├── check-deploy-target      → status: ok
├── check-test-data          → status: missing
├── prereq-create/prereq-1   → "Configure Playwright" (issue creation span)
├── prereq-create/prereq-2   → "Create test account" (issue creation span)
├── prereq-impl/prereq-1     → (full IMPL-LOOP sub-trace, no recursive infra check)
├── prereq-impl/prereq-2     → (full IMPL-LOOP sub-trace, no recursive infra check)
└── re-verify                → status: all_ok
```

## 8. Backward Compatibility

- **Old sessions without tracing**: The tracing system is additive. If `trace_session_id` is absent from `autopilot-state.json`, tracing is skipped gracefully (no error, just no trace output).
- **Old SKILL.md without new steps**: New steps are in `references/` files. If the references don't exist, the skill operates as before.
- **Gradual rollout**: Tracing can be enabled incrementally — start with trace.py + JSON, add issue comments later, add insights last.

## 9. Changed Files Summary

| File | Change |
|------|--------|
| `autopilot/SKILL.md` | Add steps 5.7, 6.5 rename, 6.6-6.7 (references only), tracing directives (~10 lines) |
| `autopilot/references/deploy-verify.md` | **NEW** — deploy-verify protocol |
| `autopilot/references/verify-infra-check.md` | **NEW** — verification prerequisite resolution protocol |
| `autopilot/references/tracing-protocol.md` | **NEW** — tracing rules, anomaly patterns, insight generation |
| `autopilot/scripts/trace.py` | **NEW** — trace recording engine |
| `autopilot/scripts/trace-report.py` | **NEW** — summary/insight generator |
| `autopilot/scripts/autopilot-state.py` | Add `trace_session_id` field |
| `issue-impl/SKILL.md` | Add deploy-verify awareness + trace result block output |

## 10. Non-Goals (explicit exclusions)

- No OTEL backend integration (Jaeger/Tempo) at this stage
- No input/output token split (not reliably measurable currently)
- No real-time dashboard (JSON + issue comments sufficient)
- No automatic application of suggested updates (human approval required)

## 11. Success Criteria

1. Every autopilot session produces a `{session-id}.json` trace file
2. Meta-issue receives a trace summary comment with timeline + insights
3. Anomaly patterns are detected and explained with causes (metric → cause → action)
4. Setting update suggestions appear only when confidence >= 90%
5. Deploy-verify runs after merge with fallback chain (Playwright → CLI → manual)
6. Auth handoff works for web login and API key scenarios (credentials never stored in traces)
7. Trace data can be mechanically converted to OTEL spans via script
8. VERIFY-INFRA-CHECK creates prerequisite issues when verification infrastructure is missing
9. Prerequisite issues are added as DAG blockers and implemented before feature issues
10. Prerequisite issues do NOT trigger recursive VERIFY-INFRA-CHECK (recursion guard)
11. Trace files are retained up to configured limit with automatic cleanup
12. Simple path sessions produce traces with the same schema (fewer spans, same structure)
