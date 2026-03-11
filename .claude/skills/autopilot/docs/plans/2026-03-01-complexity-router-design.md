# Autopilot Complexity Router Design

**Date**: 2026-03-01
**Status**: Approved
**Approach**: A. Complexity Router

## Problem

Autopilot rejects simple tasks (bug fixes, typo corrections, single-file changes) because its 12-step flow is framed entirely around PRD/multi-issue decomposition. The LLM reads the heavy process and concludes "this task doesn't fit autopilot."

## Solution

Add a **CLASSIFY** step (Step 0.3) after META-ISSUE creation. Classify input as `simple` or `complex`. Route to the appropriate path.

## Classification Criteria

All 5 must be YES for `simple`:

1. Solvable with a single issue
2. Requirements are clear (no clarification needed)
3. No dependencies on other issues
4. No non-functional requirements (NFRs)
5. Does not span multiple domains/components

Confidence < 90% → fallback to `complex` (safe direction).

### Examples

| Input | Classification | Reason |
|-------|---------------|--------|
| `.env.example 환경변수 오타 수정` | simple | 1 issue, clear, no deps |
| `README에 설치 가이드 추가` | simple | 1 issue, clear, no deps |
| `인증 시스템에 JWT 추가` | complex | Multi-component, NFRs |
| `결제 API 연동` | complex | Multi-domain, deps |

## Flow Comparison

### Complex Path (existing, unchanged)

```
0.  META-ISSUE → 0.3 CLASSIFY(complex) → 0.5 WHY-CONTEXT → 1. INGEST →
1.5 VERIFY-PLAN → 2. UL-CHECK → 2.5 CLARIFY → 3. DECOMPOSE →
3.5 CONFIRM → 4. CREATE → 4.5 RECONCILE → 5. DAG-BUILD →
5.5 DAG-CONFIRM → 6. IMPL-LOOP → 6.5 VERIFY → 7. TRIAGE →
8. CHECKPOINT → 9. LOOP → 10. FOLLOWUP → 11. FINAL-VERIFY → 12. REPORT
```

### Simple Path (new)

```
0.   META-ISSUE       Create session tracking issue + lock
0.3  CLASSIFY          Determine simple vs complex
0.5  WHY-CONTEXT       Project exploration (lightweight: README + related files)
S1.  ISSUE             /issue (with review cycle) → 1 issue
S2.  IMPL              /issue-impl → plan → implement → PR → code-review
S3.  VERIFY            Playwright/CLI/test verification
S4.  REPORT            Result summary + close meta-issue
```

### Skipped Steps (simple path)

- INGEST — input IS the requirement
- UL-CHECK — not needed for simple tasks
- CLARIFY — already clear
- DECOMPOSE/CONFIRM — single issue
- DAG-BUILD/DAG-CONFIRM — no dependencies
- TRIAGE/FOLLOWUP — single issue
- FINAL-VERIFY — covered by S3

## SKILL.md Changes

### 1. Description & Triggers

Expand framing from PRD-only to include bugs, simple tasks.

Before:
```
End-to-end implementation orchestrator from PRD/requirements to deployed, verified code.
Trigger: "/autopilot <PRD or requirements>", "auto implement", "implement this PRD"
```

After:
```
End-to-end implementation orchestrator. Handles everything from PRDs to simple bug fixes.
Auto-classifies complexity and routes to the appropriate path.
Trigger: "/autopilot <PRD or requirements or task description>", "auto implement",
         "implement this PRD", "이 이슈 해결해줘", "이 버그 고쳐"
```

### 2. Orchestration Flow Diagram

Insert `0.3 CLASSIFY` and add simple branch.

### 3. Step 0.3: CLASSIFY (new section)

Full classification criteria, confidence threshold, state storage, examples.

### 4. Simple Path Steps (new section)

S1-S4 with detailed instructions for each step.

### 5. Status Footer

Add `Mode: simple | complex` field. Simple path omits `Progress: <done>/<total>`.

```
---
Meta-Issue: #<number> <url>
Step: <step_name>
Mode: simple
Current: #<issue> <action>
```

### 6. Report Format

Simple path report:

```
AUTOPILOT_RESULT_BEGIN
META_ISSUE=<number>
MODE=simple
ISSUE=<number>
PR=<number>
VERIFIED=<true|false>
STATUS=<complete|partial>
AUTOPILOT_RESULT_END
```

### 7. Resume Protocol

Add simple path re-entry logic.

## Files Changed

| File | Change |
|------|--------|
| `SKILL.md` | Add CLASSIFY step, simple path, updated description/triggers |
| `scripts/autopilot-state.py` | Add `complexity` field support |
| `scripts/checklist.py` | Add `autopilot-simple` checklist type |
| `references/resume-protocol.md` | Add simple path re-entry |

## Files NOT Changed

- All `/issue`, `/issue-impl`, `/issue-dag` skill files
- Existing references (verification-matrix, agent-delegation, etc.)
- Complex path steps (0.5 through 12)

## Success Criteria

When a simple task (e.g., "fix typo in .env.example") is given to `/autopilot`:
1. No rejection ("this isn't an autopilot task")
2. Classified as `simple` automatically
3. Completes: issue creation (with review) → implementation → code review → verification
4. Reports result and closes meta-issue
