---
name: issue-impl
description: |
  Full implementation lifecycle from issue to deployed code.
  Orchestrates: plan → complexity-gated review → implement → code-review → issue-ref-gate → CI gate → merge → deploy → auto-recovery.
  Supports GitHub, GitLab, and Jira as issue trackers.
  Works with all issue types: story, task, and bug.

  Trigger: "/issue-impl <issue>", "implement issue #123", "implement issue KIH-42"
  Keywords: implement issue, implement story, implement task, fix bug, full lifecycle, end-to-end implementation
---

# Issue-Impl Skill

Full implementation lifecycle orchestrator: plan → complexity-gated review → implement → code-review → issue-ref-gate → CI gate → merge → deploy → auto-recovery.
Works with all issue types (story, task, bug) created by the `/issue` skill.

## Language Matching

Match the user's language for all output. Structural labels stay in English.

## Status Footer (MANDATORY)

**Every message** the orchestrator outputs to the user MUST end with a status context block.

```
---
Current Issue: #<number> <issue-url>
Current Worktree: <worktree-path>
Deploy Version: <short-sha or "pending">
```

- Append to ALL orchestrator messages. Internal step outputs excluded.
- `Current Worktree`: omit before Step 2. `Deploy Version`: "pending" until merge, then `git rev-parse --short HEAD`.

## Usage

```
/issue-impl <issue-number>              Implement from GitHub/GitLab issue
/issue-impl <issue-url>                 Implement from issue URL
/issue-impl #42                         Shorthand (GitHub/GitLab)
/issue-impl KIH-42                      Implement from Jira issue
```

## Prerequisites

- Issue must exist (create via `/issue` skill first)
- Git repository with remote configured
- **GitHub**: `gh` CLI authenticated | **GitLab**: `glab` CLI authenticated | **Jira**: MCP server configured

## Provider Detection

See [Provider Detection](~/.claude/skills/_shared/provider-detection.md) for detection algorithm, provider-specific commands, and lock management.

**Note**: Jira is an issue tracker only. VCS operations (branches, PRs/MRs) still use GitHub or GitLab based on the git remote.

## Sub-Agent Dispatch

Reviews (Step 5d, Step 8) are executed by separate sub-agents. See [Sub-Agent Dispatch](~/.claude/skills/_shared/sub-agent-dispatch.md) for dispatch mechanism and platform-specific invocation.

## Orchestration Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                   ISSUE-IMPL LIFECYCLE                             │
├──────────────────────────────────────────────────────────────────┤
│  1.  FETCH         │ Read issue (GitHub/GitLab/Jira)              │
│  1.3 DAG-CHECK     │ Check blockers in DAG                       │
│  1.5 SESSION-LOCK  │ Check lock → acquire → session-start comment │
│  2.  SETUP         │ Create worktree via setup-worktree.sh        │
│  3.  CHECKLIST     │ Init checklist at /tmp/skill-checklists/     │
│  3.5 LOAD-CONTEXT  │ Load previous Progress Updates from issue    │
│  4.  PLAN          │ Create vertical-slice plan                   │
│  4a. PLAN-POST     │ Post plan to issue tracker as comment        │
│  5.  REVIEW        │ Complexity-gated plan review                 │
│  5.5 SYNC          │ Rebase on main before implementation         │
│  6.  IMPLEMENT     │ Implement with TDD per phase                 │
│  6.5 PHASE-SAVE    │ After each phase: flush WIP buffer to issue  │
│  7.  PR/MR         │ Create pull/merge request                    │
│  8.  CODE-REVIEW   │ Evaluate code quality                        │
│  9.  CODE-LOOP     │ IF REQUEST_CHANGES → address (max 3x)       │
│  9a. ISSUE-REF     │ Verify commits reference issue               │
│  9b. CI-GATE       │ Wait for PR CI to pass before merge          │
│ 10.  MERGE         │ Squash merge PR/MR                           │
│ 10.5 DAG-UPDATE    │ Mark closed in DAG, show next-ready (GitHub) │
│ 11.  DEPLOY        │ Wait for main pipeline, verify deployment    │
│ 11a. HOTFIX        │ IF failing → analyze, create issue, fix      │
│ 11.5 SESSION-END   │ Flush buffer → release lock                  │
│ 12.  CLEANUP       │ Remove worktree, update checklist            │
├──────────────────────────────────────────────────────────────────┤
│  ABORT (any time)  │ Flush → comment → unlock → remove worktree  │
└──────────────────────────────────────────────────────────────────┘
```

## Step-by-Step Instructions

### Step 1: Fetch Issue

Detect the provider, then fetch using the provider-specific "View issue" command (see Provider Detection reference). Extract: title, acceptance criteria (or done/fix criteria), task outline, NFRs.

For Jira, also fetch the latest comment via `/rest/api/3/issue/<KEY>/comment`.

### Step 1.3: DAG Readiness Check

**Purpose**: Check if the issue has open blockers in the DAG before acquiring a session lock. Placed before Session Lock to avoid unnecessary lock acquire/release if the user decides to abort.

**Provider check**: DAG supports GitHub Wiki, GitLab Wiki, and local fallback. The `dag-sync.sh pull` command auto-detects the backend. For environments without Wiki support, DAG falls back to local storage automatically.

**Procedure**:

1. Sync DAG: run `dag-sync.sh pull` — parse structured output between `DAG_SYNC_RESULT_BEGIN/END`
2. Check `STATUS` field:
   - `STATUS=ok` → extract `DAG_FILE` path, proceed to check blockers
   - `STATUS=skipped` → log skip reason, proceed to Step 1.5
   - `STATUS=error` → log warning, proceed to Step 1.5 (best-effort)
3. Call `dag-analyze.py check --id <ISSUE> --dag-file "$DAG_FILE"` — returns JSON:
   ```json
   {"id": "42", "is_ready": false, "blockers": [{"id": "41", "title": "...", "status": "open"}], "dependents": ["43"]}
   ```

**If blockers exist** (open dependencies):

Present the blocker list and let the user decide:

| Option | Action |
|--------|--------|
| **Handle blockers first** | Show blocker issues with links. Exit without acquiring session lock. |
| **Proceed anyway** | Log warning and continue to Step 1.5 (Session Lock). |
| **Abort** | Exit immediately — no lock acquired, no worktree created. |
| **Other** | 사용자 자유 입력 / User provides custom input |

**If no blockers**: Continue to Step 1.5.

**Graceful degradation**: If DAG sync fails (Wiki unavailable, network error), log a warning and skip to Step 1.5. DAG check is best-effort — never blocks the implementation workflow.

### Step 1.5: Session Lock

Acquire a session lock on the issue to prevent concurrent work. See [Session Management](references/session-management.md) for full lock check, acquire, and session-start comment procedures.

**Summary**: Check lock → if locked and stale (>2h), offer force override → acquire lock → post session-start comment.

### Step 2: Setup Worktree (MANDATORY)

**CRITICAL**: A worktree MUST be created before any implementation work begins.

```bash
~/.claude/skills/issue-impl/scripts/setup-worktree.sh <issue-key> <feature-name>
```

Parse output between `WORKTREE_SETUP_BEGIN` / `WORKTREE_SETUP_END` to get `BRANCH_NAME`, `WORKTREE_DIR`, `MAIN_REPO`. ALL subsequent work happens in the worktree directory.

### Step 3: Initialize Checklist

```bash
python3 ~/.claude/skills/issue-impl/scripts/checklist.py create issue-impl <issue-key> --title "<title>"
```

### Step 3.5: Load Previous Context

After worktree setup, load context from previous sessions. See [Session Management](references/session-management.md) for context loading from Progress Update comments.

**Summary**: Scan issue comments for latest `**Progress Update**` → extract Done/Decisions/Next/Changed Files → use to inform plan (skip completed work).

> **User Interaction** (UIP-15): 이전 세션 컨텍스트 발견 / Previous session context found

| Option | Action |
|--------|--------|
| **Continue (Recommended)** | Resume from previous session context |
| **Start fresh** | Ignore previous context, start from scratch |
| **Other** | 사용자 자유 입력 / User provides custom input |

Present when previous Progress Update comments are found for this issue.

### Step 4: Plan

1. Read issue content from Step 1
2. Explore codebase in worktree; read CLAUDE.md, README.md
3. Read [Plan Template](references/plan-template.md) and [TDD Workflow](references/tdd-workflow.md)
4. Decompose into vertical slices (each phase: Domain + App + Infra + API + UI, starting with E2E test)
5. **Bug issues**: grep all callers, decide fix layer, verify fallback values, document environment impact
6. Write plan to `<WORKTREE_DIR>/plan.md`

```
PLAN_RESULT_BEGIN
PLAN_FILE=<path>
TOTAL_PHASES=<n>
STATUS=created
PLAN_RESULT_END
```

Update checklist: `checklist.py update issue-impl <issue> 3 done`

### Step 4a: Post Plan to Issue Tracker

Post plan as comment using the provider-specific "Add comment" command (see Provider Detection reference). For Jira, wrap in an ADF `codeBlock` with `language: "markdown"`.

### Step 5: Plan Review (Complexity-Gated)

#### Step 5a: Complexity Assessment

| Signal | Simple | Medium | Complex |
|--------|--------|--------|---------|
| Phase count | 1 | 2-3 | 4+ |
| Issue type | bug | task | story |
| New domain entities | 0 | 1-2 | 3+ |
| Architecture decisions | none | minor | significant |

- **Simple**: ALL <= Simple → 5b | **Medium**: ANY = Medium, NONE = Complex → 5c | **Complex**: ANY = Complex → 5d

```
COMPLEXITY_ASSESSMENT_BEGIN
PHASE_COUNT=<n> | ISSUE_TYPE=<bug|task|story> | NEW_ENTITIES=<n>
ARCH_DECISIONS=<none|minor|significant> | COMPLEXITY=<SIMPLE|MEDIUM|COMPLEX>
REVIEW_PATH=<5b|5c|5d>
COMPLEXITY_ASSESSMENT_END
```

> **User Interaction** (UIP-03): 복잡도 평가 결과 확인 / Confirm complexity assessment result

| Option | Action |
|--------|--------|
| **Accept (Recommended)** | Proceed with assessed complexity |
| **Override Simple** | Force simple review path (5b) |
| **Override Complex** | Force complex review path (5d) |
| **Other** | 사용자 자유 입력 / User provides custom input |

#### Step 5b: Inline Checklist (Simple)

Orchestrator verifies directly — no sub-agent.

- [ ] Tests cover the failure/change scenario
- [ ] Quality gate defined (lint, typecheck, test)
- [ ] No broken existing functionality
- **Bug-only**: [ ] All callers identified | [ ] Correct fix layer | [ ] Fallback values work in prod | [ ] Degrade paths have warning logging

All pass → APPROVE → Step 5.5. Any fail → fix inline (max 3 iterations).

#### Step 5c: Inline Review (Medium)

Orchestrator evaluates **Priority 1 only** — no sub-agent.

- [ ] Vertical slices (Domain + App + Infra + API per phase)
- [ ] Per-phase deployability
- [ ] E2E test first per phase
- [ ] TDD cycle: RED → GREEN → REFACTOR
- **Bug-only**: also apply 5b bug checklist

Only MINOR/SUGGESTION → APPROVE. Any CRITICAL/MAJOR → NEEDS_WORK (max 3 iterations).

#### Step 5d: Full Review (Complex — Sub-Agent)

1. Read plan from `<WORKTREE_DIR>/plan.md` + review criteria from [Plan Review Criteria](references/plan-review-criteria.md)
2. Build prompt using [Plan Review Prompt Template](references/plan-review-prompt-template.md) — embed all context so sub-agent needs no file access
3. Dispatch per Sub-Agent Dispatch mechanism; parse `PLAN_REVIEW_RESULT` block

#### After Plan Review (all paths)

1. Record: `checklist.py add-review issue-impl <issue> <iteration> <verdict> "<summary>" --phase plan`
2. NEEDS_WORK → address feedback, re-review (max 3 iterations). If max reached, present UIP-11.
3. APPROVE → update step 5 done, proceed to Step 5.5

> **User Interaction** (UIP-11): 최대 리뷰 반복 도달 / Max review iterations reached (plan or code review)

| Option | Action |
|--------|--------|
| **Force approve (Recommended)** | Override and proceed |
| **One more** | Allow one additional review iteration |
| **Abort** | Stop implementation |
| **Other** | 사용자 자유 입력 / User provides custom input |

Applies to both plan review (Step 5) and code review (Step 8) max iteration limits.

### Step 5.5: Sync with Main

**MANDATORY** before implementation:

```bash
cd <WORKTREE_DIR> && git fetch origin main && git rebase origin/main
```

If conflicts occur during rebase, present UIP-10:

> **User Interaction** (UIP-10): 리베이스 충돌 발생 / Rebase conflict detected

| Option | Action |
|--------|--------|
| **Manual (Recommended)** | Pause for user to resolve conflicts manually |
| **Auto-resolve** | Attempt automatic conflict resolution |
| **Abort rebase** | `git rebase --abort`, continue on current base |
| **Other** | 사용자 자유 입력 / User provides custom input |

If no conflicts, proceed directly to Step 6.

### Step 6: Implement

#### Pre-Implementation Sync

```bash
cd <WORKTREE_DIR> && git fetch origin main && git rebase origin/main
```

#### Instructions

1. Read plan at `<WORKTREE_DIR>/plan.md` and [TDD Workflow](references/tdd-workflow.md)
2. **CRITICAL**: ALL work MUST happen inside `<WORKTREE_DIR>`
3. For each phase, strict TDD:
   a. **E2E TEST** first → verify FAILS
   b. **RED** → failing unit/integration tests
   c. **GREEN** → implement to pass
   d. **REFACTOR** → clean up, tests stay green
   e. **QUALITY GATES**: full test suite + lint + type check (all must pass before commit)
   f. **COMMIT**: `[<ISSUE>] Phase N - Description`
4. After EACH phase: update issue body — check off phase task AND satisfied Done Criteria checkboxes using provider-specific "Edit issue" command. Only check off criteria **fully met**.
5. **DOC/SKILL SYNC**: Before each phase commit, verify that docs/skills corresponding to changed file paths are updated (per knowledge-maintenance mapping). The `doc_sync_check.py` hook enforces this automatically.

```
IMPL_RESULT_BEGIN
PHASES_COMPLETED=<n>
TOTAL_PHASES=<n>
FINAL_COMMIT=<hash>
STATUS=<completed|failed>
SUMMARY=<one-line summary>
IMPL_RESULT_END
```

### Step 6.5: Phase Save

After each implementation phase, flush the WIP buffer. See [Session Management](references/session-management.md) for phase save procedure.

**Summary**: Read `.claude/wip-buffer.md` → post as `**Progress Update**` comment → reset buffer → continue next phase.

### Step 7: Create PR/MR

```bash
cd <WORKTREE_DIR>
git push -u origin <BRANCH_NAME>
```

Before creating, present the draft PR/MR to the user:

> **User Interaction** (UIP-06): PR/MR 프리뷰 / PR/MR preview before creation

| Option | Action |
|--------|--------|
| **Create (Recommended)** | Create PR/MR as drafted |
| **Edit** | Modify title/body before creating |
| **Cancel** | Abort PR creation |
| **Other** | 사용자 자유 입력 / User provides custom input |

**GitHub:** `gh pr create --title "[#<ISSUE>] <desc>" --body "<summary + Closes #N + test plan>"`
**GitLab:** `glab mr create --title "[<ISSUE>] <desc>" --description "<summary + Closes #N + test plan>" --remove-source-branch`
**Jira:** Use VCS provider command above; include issue key `[<KEY>]` in title.

Update step 8 done.

### Step 8: Code Review (Sub-Agent)

#### 8a. Collect Context

1. Fetch diff: GitHub `gh pr diff <N>` / GitLab `glab mr diff <N>`
2. Read [Code Review Criteria](references/code-review-criteria.md)
3. Prepare codebase summary (architecture, layers, patterns)
4. Fetch issue body → extract Done Criteria checkboxes (`- [ ]` / `- [x]`)

#### 8b. Construct and Dispatch

Build prompt using [Code Review Prompt Template](references/code-review-prompt-template.md) — embed all context. Dispatch per Sub-Agent Dispatch mechanism.

#### 8c. Process Result

Parse `CODE_REVIEW_RESULT` block. **Done Criteria Gate**: if `DONE_CRITERIA_CHECKED` != `DONE_CRITERIA_TOTAL` → present UIP-04:

> **User Interaction** (UIP-04): Done Criteria 미충족 / Done criteria not fully met

| Option | Action |
|--------|--------|
| **Fix (Recommended)** | Address unmet criteria before merge |
| **Override** | Force approve despite unmet criteria |
| **Defer** | Mark unmet criteria as follow-up, proceed with merge |
| **Other** | 사용자 자유 입력 / User provides custom input |

Post review using provider-specific "Review PR/MR" command. Record: `checklist.py add-review issue-impl <issue> <iteration> <verdict> "<summary>" --phase code`

REQUEST_CHANGES → address feedback, push fixes, re-review (max 3 iterations; if max reached, present UIP-11). APPROVE → proceed.

### Step 9a: Issue Reference Gate (MANDATORY)

**CRITICAL**: Must pass before merge. Fail-close — missing issue ref blocks merge.

```bash
cd <WORKTREE_DIR>
~/.claude/skills/issue-impl/scripts/verify-issue-ref.sh \
  --base "$(git merge-base origin/main HEAD)" --head HEAD --check-pr-title "<PR_TITLE>"
```

Parse `ISSUE_REF_CHECK_BEGIN`/`END` for STATUS, TOTAL_COMMITS, MISSING_COUNT, MISSING_COMMITS, DETECTED_KEYS.

**PASS** → Step 9b. **FAIL** → block merge; offer: reword commits, amend last commit, or fix PR title. Re-run after fix. See [Issue Reference Enforcement](references/issue-ref-enforcement.md).

### Step 9b: Pre-Merge CI Gate (MANDATORY)

Merge 전 PR/MR 브랜치의 CI가 통과되었는지 확인한다.

1. PR HEAD SHA 확인:
   ```bash
   cd <WORKTREE_DIR>
   PR_HEAD_SHA="$(git rev-parse HEAD)"
   ```

2. CI 대기:
   ```bash
   ~/.claude/skills/issue-impl/scripts/pipeline-check.sh --wait --timeout 600 --sha "$PR_HEAD_SHA"
   ```

3. 결과 처리:
   - `PIPELINE_STATUS=passing` → Step 10으로 진행
   - `PIPELINE_STATUS=failing` → CI 로그 분석 후 worktree에서 수정, push, re-review (max 3 iterations)
   - `PIPELINE_STATUS=timeout` → 사용자에게 알림, 대기 연장 또는 중단 선택

**IMPORTANT**: CI가 pass하지 않으면 절대 merge하지 않는다.

```
CI_GATE_BEGIN
PR_HEAD_SHA=<sha>
PIPELINE_STATUS=<passing|failing|timeout>
ITERATION=<n>
CI_GATE_END
```

### Step 10: Merge

**GitHub:** `gh pr merge <N> --squash` (do NOT use `--delete-branch` — it fails inside worktrees because git cannot checkout main when it is already checked out in the main worktree. Remote branch deletion is handled separately below.)
**GitLab:** `glab mr merge <N> --squash` (do NOT use `--remove-source-branch` for the same reason; use GitLab's "Delete source branch" MR setting instead, or delete after worktree cleanup.)

After successful merge, delete the remote branch:
```bash
git push origin --delete <BRANCH_NAME>
```

### Step 10.5: DAG Status Update (Best-Effort)

**Purpose**: After merge, update the DAG to mark the issue as closed and identify newly unblocked issues.

**Provider check**: DAG supports GitHub Wiki, GitLab Wiki, and local fallback. The `dag-sync.sh` commands auto-detect the backend.

**Procedure**:

1. Sync DAG: run `dag-sync.sh pull` — parse `DAG_SYNC_RESULT_BEGIN/END` output
2. If `STATUS=ok`, extract `DAG_FILE` path, then:
   - Update node status: `dag-analyze.py update-node --id <ISSUE> --status closed --dag-file "$DAG_FILE"`
   - Query newly ready issues: `dag-analyze.py ready --dag-file "$DAG_FILE"` → JSON array:
     ```json
     [{"id": "43", "title": "...", "type": "task"}]
     ```
   - Query parallel workable: `dag-analyze.py parallel --dag-file "$DAG_FILE"` → JSON array of groups:
     ```json
     [[{"id": "43", "title": "..."}, {"id": "44", "title": "..."}]]
     ```
3. Push: run `dag-sync.sh push "Close #<ISSUE>"`
4. If `STATUS=skipped` or `STATUS=error`, log and skip — DAG update is best-effort.

**Next-ready identification**: After marking the current issue as closed, check which issues were previously blocked by this issue and are now ready (all their blockers are closed).

**Failure handling**: DAG update is best-effort. If sync or push fails, display a warning and proceed to Step 11 (Deploy). Never block deployment for a DAG update failure. Suggest: "Run `/issue-dag sync` manually to update the DAG."

### Step 11: Deploy & Verify

Merge 후 main 브랜치의 CI/배포 파이프라인이 성공하는지 확인한다.

1. main의 최신 커밋 SHA 가져오기:
   ```bash
   cd <WORKTREE_DIR> && git fetch origin main && MERGE_SHA=$(git rev-parse origin/main)
   ```

2. 파이프라인 대기:
   ```bash
   ~/.claude/skills/issue-impl/scripts/pipeline-check.sh --wait --timeout 600 --sha "$MERGE_SHA"
   ```

3. 결과 처리:
   - `PIPELINE_STATUS=passing` → Step 11.5로 진행
   - `PIPELINE_STATUS=failing` → Step 11a (Deployment Failure Recovery)로 진행
   - `PIPELINE_STATUS=timeout` → 사용자에게 알림 후 재대기 또는 Step 11a로 진행

For Jira, post deployment comment via "Add comment" command.

### Step 11.1: DEPLOY-DETECT (Optional)

Detect deployment environment after merge. Only runs when called from autopilot.
See [Deploy-Verify](~/.claude/skills/autopilot/references/deploy-verify.md) Section 6.6.

Detection order: Vercel → Docker → K8s → CI deploy step → Ask user (UIP-27).

### Step 11.2: DEPLOY-VERIFY (Optional)

Post-deploy verification in live environment. Only runs when called from autopilot.
See [Deploy-Verify](~/.claude/skills/autopilot/references/deploy-verify.md) Section 6.7.

Fallback: Playwright → CLI/API → Manual guide. Auth handoff via UIP-28.

```
DEPLOY_VERIFY_RESULT_BEGIN
METHOD=playwright|cli|api|manual
STATUS=pass|fail|skip
AUTH_HANDOFF=true|false
DEPLOY_VERIFY_RESULT_END
```

### Step 11a: Deployment Failure Recovery

Post-merge 파이프라인 실패 시 자동 복구 절차.

#### 11a-1. 실패 분석

- **GitHub**: `gh run list --branch main --limit 5` → 실패한 run 식별 → `gh run view <RUN_ID> --log-failed`
- **GitLab**: `glab ci list --branch main` → `glab ci view <PIPELINE_ID>`
- 실패 원인 요약 (어떤 job이 실패했는지, 에러 메시지, 스택 트레이스)

#### 11a-2. 핫픽스 이슈 생성

`/issue --bug` 스킬을 통해 핫픽스 이슈 생성:
- Title: `[Hotfix] <원본 이슈 ref> merge 후 파이프라인 실패: <실패 요약>`
- Body에 포함:
  - 원본 이슈 reference
  - 실패한 파이프라인 로그 요약
  - 실패 원인 분석
  - Fix Criteria: 파이프라인 재통과

`HOTFIX_ISSUE_RESULT` 블록에서 `ISSUE_NUMBER`, `ISSUE_URL` 파싱.

#### 11a-3. 핫픽스 구현

`/issue-impl <HOTFIX_ISSUE>` 실행하여 핫픽스 구현:
- 새 worktree에서 수정
- TDD 사이클 적용
- PR 생성 → code review → CI gate → merge → 배포 확인
- (재귀적으로 동일한 플로우 적용)

#### 11a-4. 배포 재확인

핫픽스 issue-impl 완료 후 원래 세션으로 돌아와서:

```bash
~/.claude/skills/issue-impl/scripts/pipeline-check.sh --wait --timeout 600 --sha "$(git rev-parse origin/main)"
```

- passing 확인 → Step 11.5로 진행

```
DEPLOY_RECOVERY_BEGIN
ORIGINAL_ISSUE=<number>
HOTFIX_ISSUE=<number>
FAILURE_SUMMARY=<one-line>
RECOVERY_STATUS=<recovered|failed>
DEPLOY_RECOVERY_END
```

**NOTE**: 핫픽스 issue-impl 자체도 실패하면 (max depth 1), 사용자에게 수동 개입 요청. 재귀 깊이는 1로 제한하여 무한 루프를 방지한다.

### Step 11.5: Session End

After deployment verification, close the session. See [Session Management](references/session-management.md) for session end and lock release.

**Summary**: Flush remaining buffer → post `**Session End**` comment → release lock (remove `wip` label / Jira transition).

### Step 12: Cleanup

```bash
cd <MAIN_REPO>
git worktree remove <WORKTREE_DIR> --force
git branch -D <BRANCH_NAME>   # safe after merge; worktree must be removed first
git pull origin main
```

Verify: `git status` (up to date) + `git log --oneline -1` (merge commit visible).

### Completion Summary

```
Issue Implementation Complete
Issue: <#number or KEY> - <title>
Branch: <branch> (merged) | PR/MR: #<N> (squash merged)
Deployed Version: <short-sha>
Phases: <n> | Reviews: Plan(<n>), Code(<n>) | Pipeline: passing
Next Ready Issues: #<N1> "<title1>", #<N2> "<title2>"
Parallel Workable: [#<N1>, #<N2>] (independent of each other)
```

**Next Ready Issues**: Populated from Step 10.5 DAG Update. Shows issues that became unblocked after this issue was completed. If DAG is unavailable, this line is omitted.

## Abort

If the user requests abort ("abort", "cancel", "중단해", or `/issue-impl --abort`), follow the abort procedure in [Session Management](references/session-management.md).

**Summary**: Flush buffer → post `**Session Aborted**` comment with reason → release lock → remove worktree → leave issue open for future resume.

## Error Recovery

- **Pre-merge pipeline failure** (Step 9b): CI 로그 분석 → worktree에서 수정 → push → re-review (max 3 iterations)
- **Post-merge pipeline failure** (Step 11): 실패 분석 → `/issue --bug`로 핫픽스 이슈 생성 → `/issue-impl`로 구현 (max depth 1)
- **Step failure**: re-run from beginning (max 3 retries)
- **Max iterations** (plan/code review hit 3x): present UIP-11 to user → force approve, one more, or abort

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/checklist.py` | Checklist CRUD |
| `scripts/setup-worktree.sh` | Git worktree creation |
| `scripts/verify-issue-ref.sh` | Issue reference validation |
| `scripts/pipeline-check.sh` | CI pipeline check |
| `scripts/deploy-indexes.sh` | Firestore index deployment |

## Maintenance

Run before structural changes: `python3 ~/.claude/skills/issue/scripts/lint_skill.py ~/.claude/skills/issue-impl && python3 ~/.claude/skills/issue-impl/scripts/test_prompts.py`

## References

- [Plan Template](references/plan-template.md)
- [Plan Review Criteria](references/plan-review-criteria.md)
- [Code Review Criteria](references/code-review-criteria.md)
- [TDD Workflow](references/tdd-workflow.md)
- [Issue Reference Enforcement](references/issue-ref-enforcement.md)
- [Session Management](references/session-management.md)
- [Plan Review Prompt Template](references/plan-review-prompt-template.md)
- [Code Review Prompt Template](references/code-review-prompt-template.md)
- [Provider Detection](~/.claude/skills/_shared/provider-detection.md)
- [Sub-Agent Dispatch](~/.claude/skills/_shared/sub-agent-dispatch.md)
- [User Interaction Points](~/.claude/skills/_shared/user-interaction-points.md) — UIP catalog (UIP-03, 04, 06, 10, 11, 15)
