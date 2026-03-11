---
name: autopilot
description: |
  End-to-end implementation orchestrator. Handles PRDs, requirements, bug fixes, and simple tasks.
  Chains /issue, /issue-dag, /issue-impl skills automatically.
  Parses requirements, creates issues, builds dependency DAG, implements in topological order,
  verifies via Playwright/CLI/tests, handles follow-ups until zero remain.
  Supports GitHub, GitLab, and Jira as issue trackers.

  Trigger: "/autopilot <PRD or requirements>", "auto implement", "implement this PRD",
    "이 이슈 해결해줘", "이 버그 고쳐"
  Keywords: autopilot, prd, end-to-end, full implementation, auto implement, orchestrate,
    bug fix, simple task, 단순 작업
---

# Autopilot Skill

End-to-end orchestrator: PRD/requirements → issues → DAG → implement → verify → follow-up loop.

## Language Matching

Match the user's language for all output. Structural labels stay in English.
UL terms always use canonical form from the UL dictionary.

## Usage

```
/autopilot <PRD file path>           Parse PRD file, decompose, implement all
/autopilot <URL>                     Fetch PRD from URL
/autopilot <free text>               Treat input as requirements
/autopilot --resume                  Resume interrupted session
/autopilot --status                  Show current progress
/autopilot --abort                   Abort current session gracefully
```

## Prerequisites

- Git repository with remote configured
- **GitHub**: `gh` CLI authenticated | **GitLab**: `glab` CLI authenticated | **Jira**: MCP server configured
- `/issue`, `/issue-dag`, `/issue-impl` skills installed at `~/.claude/skills/`
- Playwright MCP configured (for web verification; optional — falls back to manual)

## Configuration

Reads `.claude/autopilot.yaml` (optional). All values have sensible defaults.

| Key | Default | Description |
|-----|---------|-------------|
| `confidence_threshold` | `99` | Minimum confidence % before auto-proceeding on requirements |
| `max_followup_rounds` | `3` | Maximum follow-up rounds before escalating to user |
| `context_threshold.medium` | `4` | Issue count threshold for sub-agent delegation |
| `context_threshold.large` | `9` | Issue count threshold for agent team delegation |
| `dag_confirm_threshold` | `5` | Node count above which DAG confirmation is shown |
| `classify_confidence` | `90` | Minimum confidence % for simple classification |
| `verification_timeout` | `300` | Seconds to wait for verification before fallback |

## Status Footer (MANDATORY)

Every orchestrator message MUST end with:

```
---
Meta-Issue: #<number> <url>
Mode: simple | complex
Step: <step_name> (<number>)
Progress: <done>/<total> issues | Follow-up Round: <N>
Current: #<issue> <action>
```

`Current` only during IMPL-LOOP. `Meta-Issue` only after Step 0. Simple mode: omit `Progress` line (always 1 issue).

<HARD-GATE>
MANDATORY: /autopilot이 호출되면 반드시 Step 0 (META-ISSUE)부터 순서대로 실행하라.
작업이 아무리 단순해도 이 단계를 건너뛸 수 없다.
프로젝트 파일을 직접 Edit/Write하거나, /issue-impl 없이 수동 구현하는 것은 프로토콜 위반이다.
Simple path(S1-S4)가 이미 경량화된 플로우이므로 추가 단축은 불필요하다.
NOTE: PreToolUse hook이 Step 0 미완료 시 Edit/Write를 물리적으로 차단한다.
</HARD-GATE>

## Orchestration Flow

```
0.  META-ISSUE   Create session tracking issue + lock
0.3 CLASSIFY     Auto-classify simple vs complex
    └─ simple → See references/simple-path.md
0.5 WHY-CONTEXT  Explore project + elicit "why" context
1.  INGEST       Parse PRD/text → extract requirements
1.5 VERIFY-PLAN  Establish verification strategy per feature
2.  UL-CHECK     Load UL dict, scan for new terms
2.5 CLARIFY      Ask user until 99%+ confidence on ALL reqs
3.  DECOMPOSE    Requirements → issue list
3.5 CONFIRM      Ask user ONLY if confidence < threshold
4.  CREATE       /issue --no-brainstorm per issue
4.5 RECONCILE    Verify all issues in DAG
5.  DAG-BUILD    Add edges, validate, push
5.5 DAG-CONFIRM  Ask user ONLY if topology ambiguous
5.7 VERIFY-INFRA-CHECK  Check verification infra exists
6.  IMPL-LOOP    /issue-impl per DAG-ready order
6.5 PRE-DEPLOY-VERIFY   Auto-verify → manual fallback
6.6 DEPLOY-DETECT       Detect deployment environment
6.7 DEPLOY-VERIFY       Post-deploy verification
7.  TRIAGE       Classify verify failures
8.  CHECKPOINT   DAG update, save state, next ready
9.  LOOP         Ready issues remain → back to 6
10. FOLLOWUP     Collect follow-ups → /issue → DAG → loop
11. FINAL-VERIFY Integration verification
12. REPORT       Final summary, close meta-issue
```

**State update rule**: After each step's checklist update, also update `current_step`:
`autopilot-state.py update --field current_step --value <STEP_NAME>` (e.g., `WHY-CONTEXT`, `INGEST`, `VERIFY-PLAN`, `UL-CHECK`, `CLARIFY`, `DAG-CONFIRM`, `IMPL-LOOP`, `REPORT`).

## Anti-Pattern: "This Is Too Simple For The Full Protocol"

Simple path(S1-S4)는 이미 4단계로 경량화된 플로우다.
"간단해서 생략"은 autopilot의 가치(end-to-end 자동화, 검증, 추적)를 무효화한다.

## Step-by-Step Detail

**Checklist rule**: Query ready sub-tasks: `checklist.py ready-subtasks autopilot <meta-issue> <step_num>`. Execute all returned sub-tasks (parallel-safe). After each, `checklist.py update autopilot <meta-issue> <id> done`. Repeat until `checklist.py check-step autopilot <meta-issue> <step_num>` returns `COMPLETE`.

### Step 0: META-ISSUE

Create a tracking issue for the session. Provides persistent anchor for state.

1. Detect provider ([Provider Detection](~/.claude/skills/_shared/provider-detection.md))
2. Ensure labels exist (GitHub only):
   ```bash
   gh label create "task" --description "Task issue" --color "ededed" 2>/dev/null || true
   gh label create "autopilot" --description "Autopilot session" --color "1d76db" 2>/dev/null || true
   ```
3. Create issue: → See [Meta-Issue Creation Commands](references/meta-issue-creation-cmds.md)
4. Acquire session lock (same as `issue-impl` Step 1.5)
5. Initialize checklist: `python3 ~/.claude/skills/autopilot/scripts/checklist.py create autopilot <meta-issue>`
6. Store in state: `python3 ~/.claude/skills/autopilot/scripts/autopilot-state.py create --meta-issue <N> --meta-url <URL> --provider <p> --source <src>`
7. Initialize tracing: `trace.py init --session-id $SESSION_ID --meta-issue-number $N --meta-issue-url $URL`. See [Tracing Protocol](references/tracing-protocol.md).

→ See [State Block Formats](references/state-block-formats.md#meta-block-step-0)

### Step 0.3: CLASSIFY

Determine if the task is **simple** (single issue, clear requirements) or **complex** (multi-issue PRD).

**Simple criteria** (ALL must be true, confidence ≥ `classify_confidence`):
1. Single issue expected (not multi-feature)
2. Requirements are unambiguous
3. No cross-issue dependencies
4. No NFRs (performance, security constraints)
5. Single domain (not cross-cutting)

**Simple** → `autopilot-state.py update --field complexity --value simple` → `checklist.py create autopilot-simple <meta-issue>` → enter [Simple Path](references/simple-path.md).
**Complex** (or confidence < `classify_confidence`) → `autopilot-state.py update --field complexity --value complex` → continue to Step 0.5.

### Step 0.5: WHY-CONTEXT

Explore project context and elicit **why** — the user's underlying problem and decision background.

1. Explore: README, docs, code structure, recent commits
2. Auto-extract `user_problem` and `decision_context` from input (PRD/text)
3. If either dimension is vague or missing → ask via UIP-27 (user problem) or UIP-28 (decision context), one at a time, options + Other. See [User Interaction Points](~/.claude/skills/_shared/user-interaction-points.md).
4. Generate narrative → update meta-issue body with `## Why Context` section (structured fields + summary)
5. Propagation: all downstream agents receive this context. See [Agent Delegation](references/agent-delegation.md).

### Step 1: INGEST

**Input detection**: File (`.md`,`.txt`,`.pdf`) → Read | URL → WebFetch | Free text → direct.
See [Ingest Formats](references/ingest-formats.md) for parsing rules.

**Extract**: Feature list, acceptance criteria, NFRs, constraints, out-of-scope.

**Self-review**: All requirements extracted? None ambiguous? Out-of-scope defined?

→ See [State Block Formats](references/state-block-formats.md#ingest-block-step-1)

Store each requirement in state individually (do NOT use `update --field requirements`):
```bash
autopilot-state.py add-requirement --id "REQ-1" --text "<requirement text>" --confidence 100 \
    --verification-method "cli" --verification-status "pending"
```

### Step 1.5: VERIFY-PLAN

Establish verification strategy **before** implementation planning.

For each requirement, classify:
- **Auto**: Playwright (web), curl/CLI (API), test suite (logic)
- **Semi-auto**: Needs credentials → list what is needed
- **Manual**: Step-by-step guide for user

If unclear → present UIP-18:

> **User Interaction** (UIP-18): 검증 전략 불명확 / Verification strategy unclear

| Option | Action |
|--------|--------|
| **Playwright (Recommended)** | Browser automation |
| **CLI/API** | curl, httpie, CLI tools |
| **Manual** | Step-by-step guide |
| **Other** | 사용자 자유 입력 / User provides custom input |

**Self-review**: Every requirement has a verification method?

### Step 2: UL-CHECK

1. Sync DAG: `bash ~/.claude/skills/issue-dag/scripts/dag-sync.sh pull`
2. Load `ubiquitous-language.json` if exists
3. Scan PRD for domain terms not in UL
4. For each new term → present UIP-19:

> **User Interaction** (UIP-19): 새 UL 용어 정의 / New UL term definition

| Option | Action |
|--------|--------|
| **Define now (Recommended)** | Provide canonical name, aliases, domain |
| **Skip** | Proceed without adding |
| **Not a domain term** | Exclude from UL |
| **Other** | 사용자 자유 입력 / User provides custom input |

5. Register: `python3 ~/.claude/skills/issue-dag/scripts/dag-analyze.py --dag-file "$DAG_FILE" ul-add --canonical "<term>" --aliases "<a>" --domain "<d>"`

**Skip if**: No UL dictionary and no domain model.

**Self-review**: All new terms registered with correct domain?

### Step 2.5: CLARIFY

For each requirement with confidence < `confidence_threshold` (default 99%):

> **User Interaction** (UIP-17): 요구사항 명확화 / Requirement clarification

| Option | Action |
|--------|--------|
| **<Recommended interpretation>** | Use this and proceed |
| **<Alternative A>** | Alternative interpretation A |
| **<Alternative B>** | Alternative interpretation B |
| **Other** | 사용자 자유 입력 / User provides custom input |

Repeat until ALL requirements ≥ `confidence_threshold`.

**Anti-pattern**: Never batch multiple uncertain requirements into one question.

**Self-review**: All 99%+? Verification matrix still valid after clarification?

### Step 3: DECOMPOSE

Convert clarified requirements into concrete issue specifications.

Map each requirement to issue type (story/task/bug), identify dependencies, link verification methods.
**Heuristics**: one actor + one value unit = one issue; separate infra from features; extract shared prerequisites.

**Self-review**: No duplicates? No gaps? No circular deps? Each issue ≤ 3 phases? All have `requirement_ids` + `verification_methods`?

→ See [State Block Formats](references/state-block-formats.md#decompose-block-step-3)

### Step 3.5: CONFIRM (Conditional)

**Only if** confidence < `confidence_threshold` → present UIP-20:

> **User Interaction** (UIP-20): 이슈 분해 확인 / Issue decomposition confirmation

| Option | Action |
|--------|--------|
| **Approve (Recommended)** | Create issues as decomposed |
| **Modify** | User adjusts the issue list |
| **Re-decompose** | Redo with different strategy |
| **Other** | 사용자 자유 입력 / User provides custom input |

**Auto-skip** when confident.

### Step 4: CREATE

For each issue (dependency order):
1. Invoke `/issue --no-brainstorm` with the specification
2. Parse `ISSUE_RESULT_BEGIN/END` output, store in state:
   ```bash
   autopilot-state.py add-issue --id <ISSUE_NUMBER> --url <ISSUE_URL> --type <story|task|bug> --title "<title>" \
       --requirement-ids "REQ-1,REQ-2" --verification-methods "cli,playwright"
   ```
3. Include `## Context` section in issue body with Why Context narrative from meta-issue
4. Self-review: title matches, type matches

**Fallback** (if `/issue` blocks on UIP-05): create directly via `gh issue create` / `glab issue create` / Jira MCP.

### Step 4.5: RECONCILE

Verify all created issues exist as DAG nodes. For each issue in state, run `dag-analyze.py check --id <N>`. Register any missing nodes:
```bash
dag-analyze.py --dag-file "$DAG_FILE" add-node --id <ISSUE_NUMBER> --title "<title>" --type <story|task|bug>
```
Note: `add-node` does NOT accept `--url`. Only `--id`, `--title`, `--type` are required. Optional: `--status`, `--keywords`, `--paths`.

### Step 5: DAG-BUILD

1. Add dependency edges: `dag-analyze.py add-edge --from <A> --to <B> --type depends_on`
2. Validate no cycles: `dag-analyze.py detect-cycle`
3. Push: `dag-sync.sh push "Build DAG for autopilot session"`

**Self-review**: No cycles? All nodes present? Edges correct?

### Step 5.5: DAG-CONFIRM (Conditional)

**Only if**:
- DAG has > `dag_confirm_threshold` (default 5) nodes with complex cross-dependencies
- Topological sort has multiple valid orderings with different risk profiles

Otherwise auto-skip. When triggered → present UIP-21:

> **User Interaction** (UIP-21): DAG 실행 순서 확인 / DAG execution order confirmation

| Option | Action |
|--------|--------|
| **Approve (Recommended)** | Proceed with proposed execution order |
| **Reorder** | User specifies different execution order |
| **Visualize** | Show Mermaid diagram, then ask again |
| **Other** | 사용자 자유 입력 / User provides custom input |

When "Visualize" selected, display via `dag-analyze.py viz`.

### Step 5.7: VERIFY-INFRA-CHECK

Check project verification infrastructure exists. If missing, create prerequisite issues as DAG blockers.
Skip if any issue has `type: prereq-infra` (recursion prevention).
→ See [Verify-Infra-Check](references/verify-infra-check.md)

### Step 6: IMPL-LOOP

Loop until `dag-analyze.py ready` returns empty:

1. Query ready: `dag-analyze.py --dag-file "$DAG_FILE" ready`
2. Select next issue (first in ready list)
3. Execute `/issue-impl <issue_number>`. Parse `<usage>` from Agent result → `end-span --attr`. See [Tracing Protocol](references/tracing-protocol.md).
4. Self-review: done criteria met? PR merged? (`gh pr view <N> --json state --jq '.state'` → `MERGED`) Pipeline passed?
5. Verify (Step 6.5) → Triage if failed (Step 7) → Checkpoint (Step 8)

**Agent delegation**: Based on context size — see [Agent Delegation](references/agent-delegation.md).

**Implementation failure** (after 3 retries) → present UIP-26:

> **User Interaction** (UIP-26): 구현 반복 실패 / Implementation failure escalation

| Option | Action |
|--------|--------|
| **Skip issue (Recommended)** | Create bug issue, move to next ready |
| **Retry** | One more implementation attempt |
| **Abort autopilot** | Stop entire session |
| **Other** | 사용자 자유 입력 / User provides custom input |

### Step 6.5: PRE-DEPLOY-VERIFY

Priority: Playwright → CLI → Test suite → Credential-gated (UIP-22) → Manual fallback.
See [Verification Matrix](references/verification-matrix.md) for templates.

> **User Interaction** (UIP-22): 인증 정보 필요 / Credentials needed

| Option | Action |
|--------|--------|
| **Provide now (Recommended)** | User provides credentials/setup |
| **Skip verification** | Mark as manually verified later |
| **Other** | 사용자 자유 입력 / User provides custom input |

**Pass** → mark verified in state:
```bash
autopilot-state.py update-issue --id <ISSUE_NUMBER> --status closed --verified true
```
**Fail** → Step 7 (Triage).

### Step 6.6: DEPLOY-DETECT

Detect deployment environment after merge. → See [Deploy-Verify](references/deploy-verify.md) Section 6.6.

### Step 6.7: DEPLOY-VERIFY

Post-deploy verification with fallback chain. → See [Deploy-Verify](references/deploy-verify.md) Section 6.7.

### Step 7: TRIAGE

1. Check dependents via `dag-analyze.py check --id "<FAILED>"`
2. **Blocking** (open dependents) → create bug via `/issue --bug --no-brainstorm`, add edge, re-enter IMPL-LOOP
3. **Non-blocking** → create bug, defer to FOLLOWUP (Step 10)

UIP-23 (triage override) only if auto-classification confidence < 95%.

### Step 8: CHECKPOINT

Update DAG node status → query next ready → save state → post progress comment → push DAG.

→ See [State Block Formats](references/state-block-formats.md#checkpoint-block-step-8)

### Step 9: LOOP

Ready issues remain → back to Step 6. No ready + unclosed → alert user.

### Step 10: FOLLOWUP

After all original issues complete:
1. Collect follow-ups: bugs from Step 7, `FOLLOWUP_ITEMS` from issue-impl, open DAG nodes
2. Create new issues via `/issue --no-brainstorm`, register in DAG
3. **교훈 즉시 포착**: Follow-up이 발생하면 원인을 분석하여 state에 기록한다.

   분석 항목:
   - 초기 진단에서 놓친 것은 무엇인가?
   - 검증 방법 우선순위(Playwright → CLI → Manual)를 따랐는가?
   - 클라이언트-서버 양쪽을 모두 분석했는가?
   - Self-review에서 통과시킨 항목 중 실제로 문제가 있었던 것은?

   기록:
   ```bash
   autopilot-state.py add-lesson \
     --step "<발생_단계>" \
     --category "<verification|diagnosis|scope|protocol>" \
     --summary "<한 줄 요약>" \
     --detail "<상세 원인 및 교훈>" \
     --evidence "#<이슈>, PR #<PR>"
   ```

4. Re-enter IMPL-LOOP (Step 6), increment `followup_round`

Max `max_followup_rounds` (default 3). After limit → present UIP-24:

> **User Interaction** (UIP-24): 후속 작업 한도 도달 / Follow-up round limit

| Option | Action |
|--------|--------|
| **Stop (Recommended)** | Report remaining open issues |
| **One more round** | Allow one additional round |
| **Force complete** | Defer remaining, proceed to REPORT |
| **Other** | 사용자 자유 입력 / User provides custom input |

### Step 11: FINAL-VERIFY

Cross-feature integration verification (skip already-verified issues):
1. Full test suite across all changes
2. Playwright E2E for multi-feature journeys (web) or integration tests (API)
3. Failure → create follow-up → Step 10 (subject to round limit)

### Step 12: REPORT

→ See [State Block Formats](references/state-block-formats.md#result-block-step-12)

Update session status based on result:
```bash
# complete: all issues implemented and verified
# partial: some issues remain open or unverified
autopilot-state.py update --field status --value <complete|partial>
```

Finalize tracing: `trace.py finalize --session $SID --attr total_tokens=$T --attr provider=$P`. Run `trace-report.py summary` → post on meta-issue. See [Tracing Protocol](references/tracing-protocol.md).

**RETROSPECTIVE** (Step 12 하위):

1. State에서 교훈 조회: `autopilot-state.py query --field lessons`
2. 교훈이 없으면 skip
3. 교훈이 있으면:
   a. 프로젝트 메모리(`~/.claude/projects/<project>/memory/MEMORY.md`)의
      `## Autopilot Lessons` 섹션에 기록
   b. 기존 유사 항목이 있으면 새 항목 대신 "Recurrence" 날짜 추가
   c. Meta-issue에 `## Lessons Learned` 섹션 추가
4. 기록 형식:
   ```
   ### <교훈 제목> (<날짜>)
   - 상황: <무엇이 발생했는지>
   - 원인: <왜 빠뜨렸는지>
   - 교훈: <다음에 어떻게 해야 하는지>
   - 관련: #<이슈>, PR #<PR>
   ```

Post final report on meta-issue → close meta-issue → release session lock.

## Abort

On `/autopilot --abort`, "abort", "cancel": update status → flush state → post abort comment → release lock → leave meta-issue open for resume.

```bash
autopilot-state.py update --field status --value aborted
```

**Abort 회고**: IMPL-LOOP 이후(`current_step` ∈ {`IMPL-LOOP`, `PRE-DEPLOY-VERIFY`, `DEPLOY-DETECT`, `DEPLOY-VERIFY`, `TRIAGE`, `CHECKPOINT`, `FOLLOWUP`, `FINAL-VERIFY`}) abort된 경우, state에 lessons가 있으면 REPORT의 RETROSPECTIVE와 동일하게 프로젝트 메모리에 기록한다.

→ See [State Block Formats](references/state-block-formats.md#abort-block)

## Resume Protocol

`/autopilot --resume`: load state → check lock → re-enter at `current_step`.
See [Resume Protocol](references/resume-protocol.md) for per-step re-entry behavior.

> **User Interaction** (UIP-25): 세션 충돌 / Session lock conflict

| Option | Action |
|--------|--------|
| **Force override (Recommended)** | Break stale lock (>2h) |
| **Wait** | Let other session finish |
| **Abort other** | Force-release other lock |
| **Other** | 사용자 자유 입력 / User provides custom input |

## User Interaction Policy

Default: fully automatic. Interrupt only at defined UIPs (17–28).
Format: one question at a time, recommended option first, custom input (`Other`) always available.
See [User Interaction Points](~/.claude/skills/_shared/user-interaction-points.md) for full catalog.

## Error Recovery

See [Error Recovery](references/error-recovery.md).

## Self-Review Protocol

Every step includes self-review per [Self-Review Criteria](references/self-review-criteria.md). Complex reviews: delegate to sub-agent (`model=sonnet`, `max_turns=3`) using [Self-Review Prompt Template](references/self-review-prompt-template.md).

## Dependencies & References

Skills: `/issue` (`--no-brainstorm`), `/issue-dag` (scripts: `dag-analyze.py`, `dag-sync.sh`), `/issue-impl`, Playwright MCP (optional).

References: [Ingest Formats](references/ingest-formats.md), [Verification Matrix](references/verification-matrix.md), [Agent Delegation](references/agent-delegation.md), [Resume Protocol](references/resume-protocol.md), [Self-Review Criteria](references/self-review-criteria.md), [Self-Review Prompt Template](references/self-review-prompt-template.md), [Simple Path](references/simple-path.md), [Error Recovery](references/error-recovery.md).

Shared: [Provider Detection](~/.claude/skills/_shared/provider-detection.md), [Sub-Agent Dispatch](~/.claude/skills/_shared/sub-agent-dispatch.md), [User Interaction Points](~/.claude/skills/_shared/user-interaction-points.md) (UIP-17–28).

## Maintenance

Run before any structural change to SKILL.md:

```bash
python3 ~/.claude/skills/issue/scripts/lint_skill.py ~/.claude/skills/autopilot
python3 ~/.claude/skills/autopilot/scripts/test_prompts.py
python3 -m unittest discover -s ~/.claude/skills/autopilot/tests -v
```
