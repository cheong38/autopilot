# Resume Protocol

Per-step re-entry behavior when resuming an interrupted autopilot session via `/autopilot --resume`.

## General Flow

1. Resolve state file: `$(git rev-parse --show-toplevel)/.claude/autopilot-state.json`
2. If not found → error: "No session. Start with `/autopilot <PRD>`"
3. Check session lock on meta-issue → UIP-25 if conflict
4. Load state, identify `current_step`
5. Apply per-step re-entry behavior below

## Per-Step Re-entry

### WHY-CONTEXT (Step 0.5)

**Behavior**: Skip if meta-issue body has `## Why Context` section. Re-run if missing.

Check the meta-issue body for a `## Why Context` section. If present, the context was already captured and can be read directly. If missing, re-run Step 0.5 to explore the project and elicit the why context from the user.

### INGEST / CLARIFY (Steps 1–2.5)

**Behavior**: Restart from beginning.

These steps are idempotent — re-parsing the PRD and re-clarifying with the user produces the same result. The state file's `requirements` array is overwritten.

### DECOMPOSE (Step 3)

**Behavior**: Restart decomposition using cached requirements from state.

The `requirements` array in state was populated during INGEST. DECOMPOSE uses these cached requirements rather than re-parsing the PRD. This avoids re-running INGEST/CLARIFY.

### CREATE (Step 4)

**Behavior**: Skip already-created issues.

For each planned issue, check if an issue with matching title already exists (via `gh issue list` / `glab issue list` / Jira search). If found, skip creation and ensure the existing issue is in state. Only create issues that don't yet exist.

### DAG-BUILD (Step 5)

**Behavior**: Re-sync and reconcile.

1. Pull latest DAG: `dag-sync.sh pull`
2. Run RECONCILE (Step 4.5) to verify all issues are nodes
3. Rebuild missing edges from decomposition data in state
4. Validate no cycles, push

### IMPL-LOOP (Step 6)

**Behavior**: Skip closed+verified issues.

1. Query DAG for `ready` issues
2. For each ready issue, check state: if `status: "closed"` AND `verified: true`, skip
3. Resume from first un-verified ready issue
4. The `current_issue` field in state indicates where the previous session stopped

### FOLLOWUP (Step 10)

**Behavior**: Continue from current `followup_round`.

1. Load `followup_round` from state
2. Re-query DAG for remaining open nodes
3. Continue follow-up loop from current round number

### VERIFY-PLAN / UL-CHECK (Steps 1.5–2)

**Behavior**: Restart alongside INGEST. These are part of the INGEST/CLARIFY group and re-run idempotently.

### CONFIRM (Step 3.5)

**Behavior**: Skip. Confirmation was already given; decomposition data is in state.

### RECONCILE (Step 4.5)

**Behavior**: Re-run. Quick idempotent check that all issues exist as DAG nodes.

### DAG-CONFIRM (Step 5.5)

**Behavior**: Skip. Confirmation was already given; DAG is persisted.

### VERIFY-INFRA-CHECK (Step 5.7)

**Behavior**: Re-run. Quick check that verification infrastructure exists for planned issue types.

### PRE-DEPLOY-VERIFY / DEPLOY-DETECT / DEPLOY-VERIFY (Steps 6.5–6.7)

**Behavior**: Re-run for the current issue. These are per-issue steps within IMPL-LOOP.

### TRIAGE (Step 7)

**Behavior**: Re-run. Classify any outstanding verification failures.

### CHECKPOINT (Step 8)

**Behavior**: Re-run. Save state and advance to next ready issue.

### LOOP (Step 9)

**Behavior**: Re-enter IMPL-LOOP if ready issues remain.

### FINAL-VERIFY (Step 11)

**Behavior**: Re-run integration tests.

Full integration verification is re-run since partial verification state is not reliable.

### REPORT (Step 12)

**Behavior**: Re-run. Generate final summary and close meta-issue.

## Simple Path Re-entry

When `complexity == "simple"` in state, use the simple resume path instead of complex per-step re-entry.

### CLASSIFY (Step 0.3)

**Behavior**: Check state `complexity` field. If set (`simple` or `complex`), skip classification. If `null`, re-run classification.

### ISSUE (Step S1)

**Behavior**: Check state `issues` array. If an issue exists, skip creation and proceed to IMPL. If empty, create the issue.

### IMPL (Step S2)

**Behavior**: Delegate to `/issue-impl <issue_number>`. The `/issue-impl` skill has its own resume mechanism (session lock, worktree detection). Simply re-invoke it.

### VERIFY (Step S3)

**Behavior**: Always re-run. Partial verification state is not reliable.

### REPORT (Step S4)

**Behavior**: Always re-run. Ensures final state is consistent.

### Re-entry Decision

The re-entry point is determined by `current_step` + `complexity == "simple"`:
1. Load state → check `complexity`
2. If `complexity == "simple"` → use simple path steps above
3. Find the latest incomplete step in `autopilot-simple` checklist
4. Resume from that step

## Lock Handling

Session lock uses the same mechanism as `issue-impl` (meta-issue comment with `SESSION_LOCK` marker).

- Lock age > 2 hours → considered stale, "Force override" recommended
- Lock age ≤ 2 hours → another session may be active, "Wait" recommended
