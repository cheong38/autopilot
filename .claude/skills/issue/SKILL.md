---
name: issue
description: |
  Create and refine issues (story, task, bug) through iterative review cycles.
  Orchestrates create → review → address loop until APPROVED.
  Supports GitHub, GitLab, and Jira as issue trackers.
  Auto-detects issue type or accepts explicit --story, --task, --bug flags.

  Trigger: "/issue <requirements>", "create issue for ...", "create story/task/bug for ..."
  Keywords: issue, story, task, bug, user story, create issue, feature request, bug report
---

# Issue Skill

Create well-structured issues (story, task, or bug) with iterative review until quality is approved.

## Language Matching

Write issues in the same language the user uses.
Structural labels stay in English; content matches user's language.

## Status Footer (MANDATORY)

**Every message** the orchestrator outputs to the user MUST end with a status context block.
This helps the user track the current state across long-running workflows.

```
---
Current Issue: #<number> <issue-url>
```

For the Jira Sub-Issue flow, use:
```
---
Parent Issue: <PARENT-KEY> <parent-issue-url>
Current Sub-Issue: <SUB-KEY> (<i>/<N>) <sub-issue-url>
```

**Rules**:
- Append this footer to ALL orchestrator messages (step transitions, summaries, errors, completions)
- `Current Issue`: Set after issue creation (Step 6). Before creation, omit this line.
- `Parent Issue` / `Current Sub-Issue`: Used in Jira Sub-Issue flow. Show parent from Step 1, sub-issue after creation.

## Usage

```
/issue <requirements>                         Create issue (auto-detect type)
/issue --story <requirements>                 Create user story
/issue --task <requirements>                  Create task
/issue --bug <requirements>                   Create bug report
/issue --split <requirements>                 Analyze and split into multiple issues
/issue --edit <issue-number> <instruction>    Edit existing issue
/issue --no-brainstorm <requirements>         Skip ambiguity check / brainstorming
/issue <JIRA-KEY>                            Read Jira issue → create [Implement] sub-issues
```

## Issue Types

### Story (`--story`)
User-centric feature request following "As a / I want to / So that" format.
Reviewed against INVEST criteria and acceptance criteria quality.

**Auto-detect indicators**: "사용자가", "As a user", "I want to", "feature", "기능", user-centric language, "할 수 있도록"

### Task (`--task`)
Technical or operational work item with clear done criteria.
Reviewed for clarity, completeness, and verifiable done criteria.

**Auto-detect indicators**: "설정", "구성", "마이그레이션", "configure", "setup", "migrate", "refactor", "update", "upgrade", "create", "integrate", technical/operational language

### Bug (`--bug`)
Bug report with reproduction steps and expected vs actual behavior.
Reviewed for reproducibility, environment info, and fix verification criteria.

**Auto-detect indicators**: "버그", "에러", "오류", "안됨", "깨짐", "bug", "error", "broken", "crash", "fix", "not working", "regression", "fails", "unexpected"

### Type Auto-Detection

When no flag is provided:
1. Scan user input for type-specific indicators above
2. If confidence is high (clear indicators found) → assign type automatically
3. If ambiguous → ask the user with three options (Story, Task, Bug)

### Type Identification by Provider

**GitHub/GitLab**: Use title prefix `[Story]`/`[Task]`/`[Bug]` + matching label (`story`/`task`/`bug`). Labels customizable via `.claude/issue.yaml`.
**Jira**: Uses native issue type field — no title prefix or label needed.

**Title formats**: `[Story] As a <role>, I want to <goal>` | `[Task] <imperative action>` | `[Bug] <concise description>`

## Provider Detection

See [Provider Detection](~/.claude/skills/_shared/provider-detection.md) for detection algorithm and provider-specific commands.

## Orchestration Flow

### Single Issue (default)

```
┌──────────────────────────────────────────────────────────────────┐
│                      ISSUE LIFECYCLE                              │
├──────────────────────────────────────────────────────────────────┤
│  1. PARSE      │ Extract requirements from user input            │
│  1.5 SCOPE     │ Analyze scope → single or multi-issue?          │
│  2. TYPE       │ Detect or ask issue type (story/task/bug)       │
│  3. DETECT     │ Detect provider (GitHub/GitLab/Jira)            │
│  3.5 AMBIGUITY │ Evaluate input → trigger brainstorming if vague │
│  4. DISCOVER   │ Ask missing info                                │
│  5. CHECKLIST  │ Create checklist at /tmp/skill-checklists/      │
│  5.5 DAG       │ Analyze DAG for similar/duplicate issues        │
│  5.6 CONFIRM   │ Present candidates → user decides action        │
│  6. CREATE     │ Draft + create issue                            │
│  6.5 DAG UPD   │ Register new issue in DAG + edges               │
│  7. REVIEW     │ Evaluate issue quality                          │
│  8. ADDRESS    │ IF NEEDS_WORK → address review feedback         │
│  9. LOOP       │ Repeat 7-8 until APPROVE (max 3 iterations)    │
│ 10. DONE       │ Update checklist, show summary                  │
└──────────────────────────────────────────────────────────────────┘
```

### Multi-Issue (when scope analysis detects multiple issues)

See [Multi-Issue Flow](references/multi-issue-flow.md) for the full multi-issue lifecycle, scope analysis, split confirmation, and execution loop.

### Jira Sub-Issue Flow (when input is a Jira key)

See [Jira Sub-Issue Flow](references/jira-sub-issue-flow.md) for the Jira parent issue workflow and sub-issue creation.

## Sub-Agent Dispatch

Reviews (Step 7) are executed by a separate sub-agent. See [Sub-Agent Dispatch](~/.claude/skills/_shared/sub-agent-dispatch.md) for dispatch mechanism and platform-specific invocation.

## Step-by-Step Instructions

### Step 1: Parse Requirements

Extract from user input:
- **Issue type**: story, task, or bug (from flag or auto-detect)
- **Core info**: varies by type (see Step 4)

#### Jira Parent Issue Input

When the input is a Jira issue key (matches `XXX-123` pattern) with no additional requirements text, switch to the **Jira Sub-Issue flow**. See [Jira Sub-Issue Flow](references/jira-sub-issue-flow.md) for fetching parent issue, extracting requirements, and creating sub-issues.

### Step 1.5: Scope Analysis / Step 1.6: Confirm Split / Multi-Issue Execution Loop

See [Multi-Issue Flow](references/multi-issue-flow.md) for scope analysis triggers, decomposition criteria, split confirmation, and execution loop.

**Quick reference**: If single issue detected (one Actor + one value unit + no `--split` flag) → skip to Step 2.

---

### Step 2: Determine Issue Type

**Note**: Steps 2 and 3 are unchanged from the original flow. After Step 3, proceed to Step 3.5.

**If flag provided** (`--story`, `--task`, `--bug`): use that type directly.

**If no flag**: auto-detect using keyword analysis:

```
1. Count story indicators in user input
2. Count task indicators in user input
3. Count bug indicators in user input
4. If one type scores significantly higher → use that type
5. If ambiguous → ask the user (see UIP-01 below)
```

> **User Interaction** (UIP-01): 자동 감지된 이슈 타입 확인 / Confirm auto-detected issue type

| Option | Action |
|--------|--------|
| **Story (Recommended)** | Use auto-detected story type (or whichever was detected) |
| **Task** | Override to task |
| **Bug** | Override to bug |
| **Other** | 사용자 자유 입력 / User provides custom input |

Show detected type as "(Recommended)". If confidence is high, present for confirmation; if ambiguous, present without recommendation.

### Step 3: Detect Provider

```
1. Check if .claude/issue.yaml exists → read tracker setting
   (Fallback: check .claude/story.yaml for backward compatibility)
2. If user provided a Jira issue key (XXX-123 pattern) → Jira
3. Run: git remote get-url origin
   - github.com → GitHub
   - gitlab → GitLab
4. If unclear → ask the user
```

Store the detected provider for use in subsequent steps.

### Step 3.5: Ambiguity Check

Evaluate user input to determine if brainstorming is needed before discovery.

**Triggers brainstorming** (inline, within `/issue` orchestration):
- Input is extremely short or vague (no specific action/scope)
- Story type with unclear acceptance criteria
- Single-line description with no clear requirements structure

**Skips brainstorming**:
- `--bug` flag with concrete reproduction steps or multiple bug indicators
- Clear task description with defined scope (task indicators + >30 chars)
- `--no-brainstorm` flag explicitly set
- Input contains clear requirements patterns (Given/When/Then, acceptance criteria, done criteria)

**When triggered**:
1. Ask clarifying questions one at a time to refine requirements
2. Propose 2-3 approaches with trade-offs and a recommendation
3. Clarified requirements flow directly into Step 4 (Discovery)

**What is NOT done** (these belong to the brainstorming/planner skill, not issue creation):
- Write design doc
- Invoke writing-plans

See `tests/test_ambiguity_check.py` for the heuristic logic and test cases.

### Step 4: Guided Discovery

Ask only for MISSING information. Questions vary by type:

#### For Story type:
1. **User Role** (if vague): "Who is the primary user for this feature?"
2. **Business Value** (if missing): "Why is this valuable? What benefit does it provide?"
3. **Acceptance Criteria** (always ask): "What conditions must be met? (2-5 specific, testable criteria)"
4. **NFRs** (optional): "Any performance, security, or other constraints? (or 'none')"

#### For Task type:
1. **Objective** (if vague): "What specifically needs to be accomplished?"
2. **Done Criteria** (always ask): "How do we know this task is complete? (2-5 verifiable criteria)"
3. **Dependencies** (if relevant): "Are there any dependencies or prerequisites?"
4. **Constraints** (optional): "Any technical constraints or requirements?"

#### For Bug type:
1. **Steps to Reproduce** (always ask if missing): "How can we reproduce this bug? (step by step)"
2. **Expected Behavior** (if missing): "What should happen instead?"
3. **Environment** (if missing): "What environment/version/browser is this occurring in?"
4. **Fix Criteria** (always ask): "How should we verify the fix? (1-3 criteria)"

### Step 5: Initialize Checklist

```bash
python3 ~/.claude/skills/issue/scripts/checklist.py create issue <issue-key> --title "<title>" --type <story|task|bug>
```

Update steps as you progress:
```bash
python3 ~/.claude/skills/issue/scripts/checklist.py update issue <issue-key> <step-number> done
```

### Step 5.5: DAG Analysis

Before issue creation, check for similar or duplicate issues in the DAG.

**Provider support**: GitHub Wiki, GitLab Wiki, or local fallback. The `dag-sync.sh` command auto-detects the backend.

1. Sync DAG:
```bash
bash ~/.claude/skills/issue-dag/scripts/dag-sync.sh pull
```

2. Parse structured output between `DAG_SYNC_RESULT_BEGIN` / `DAG_SYNC_RESULT_END`:
   - `STATUS=ok` → extract `DAG_FILE` path, proceed to step 3
   - `STATUS=skipped` → log "DAG analysis skipped (unsupported provider)", proceed to Step 6
   - `STATUS=error` → present UIP-09 below

3. Extract keywords from Discovery (Step 4) results and title draft. Normalize keywords to UL canonical terms if UL dictionary is available.

4. Run similarity search:
```bash
python3 ~/.claude/skills/issue-dag/scripts/dag-analyze.py --dag-file "$DAG_FILE" \
  similar --keywords "<k1>,<k2>" --paths "<p1>,<p2>" --title "<draft title>"
```

5. If candidates found (score >= 0.15), proceed to Step 5.6.
6. If no candidates, proceed directly to Step 6.
7. If DAG sync fails (Wiki not available, network error), present UIP-09 below.

> **User Interaction** (UIP-09): DAG 동기화 실패 시 처리 / DAG sync failure handling

| Option | Action |
|--------|--------|
| **Skip (Recommended)** | Proceed without DAG analysis |
| **Retry** | Retry DAG sync |
| **Abort** | Abort issue creation |
| **Other** | 사용자 자유 입력 / User provides custom input |

### Step 5.6: User Confirmation Gate

When similar/duplicate candidates are found in Step 5.5, present them to the user.

**Present candidates** sorted by similarity score with confidence levels:
- `>= 0.5`: High confidence duplicate
- `0.3 - 0.5`: Likely related
- `0.15 - 0.3`: Possibly related

**User options**:

| Option | Action |
|--------|--------|
| "Create anyway" | Create issue as independent node in DAG |
| "Create with dependency" | Create issue + add `depends_on` edge + insert `blocked by #N` in body |
| "Add to existing issue" | Edit existing issue instead of creating new one (switches to edit mode) |
| "Cancel" / "Abort" | Abort issue creation |
| **Other** | 사용자 자유 입력 / User provides custom input |

When no candidates found, this step is automatically skipped.

### Step 6: Create Issue

Execute the following steps sequentially to create the issue.

#### Instructions

The template is the **canonical structure**. The issue body MUST use every section heading from the template. Do NOT substitute, reorder, or omit sections — even if the input already has its own structure (e.g., RCA format from AGENTS.md).

1. Read the template at `~/.claude/skills/issue/references/<type>-template.md`
2. Read examples at `~/.claude/skills/issue/references/examples.md`
3. Draft the issue using **exactly the section headings** from the template — map input data into the template sections
4. Verify every template section is present in the draft; if input lacks data for a section, present UIP-14 per section:

> **User Interaction** (UIP-14): 누락된 템플릿 섹션 처리 / Handle missing template sections

| Option | Action |
|--------|--------|
| **TBD (Recommended)** | Fill with TBD placeholder |
| **Input** | User provides content for this section now |
| **N/A** | Mark section as not applicable |
| **Other** | 사용자 자유 입력 / User provides custom input |

Ask per missing section. Multiple sections may trigger multiple interactions.

5. Validate against type-specific criteria

> **User Interaction** (UIP-05): 이슈 초안 프리뷰 / Issue draft preview before creation

| Option | Action |
|--------|--------|
| **Create (Recommended)** | Create the issue as drafted |
| **Edit** | Modify draft before creating |
| **Cancel** | Abort issue creation |
| **Other** | 사용자 자유 입력 / User provides custom input |

Present the full draft (title + body) to the user before executing creation commands.

#### Title Formatting

Format the title with a type prefix:
- Story: `[Story] As a <role>, I want to <goal>`
- Task: `[Task] <imperative action title>`
- Bug: `[Bug] <concise bug description>`

#### Ensure Labels Exist

Before creating an issue, ensure the required label exists. If it doesn't, create it silently.

**GitHub:**
```bash
gh label create "<type>" --description "<Type> issue" --color "ededed" 2>/dev/null || true
```

**GitLab:** Labels are created automatically if they don't exist.

#### Create by Provider

**GitHub:**
```bash
gh issue create --title "[<Type>] <title>" --body "<issue body>" --label "<type>"
```

**GitLab:**
```bash
glab issue create --title "[<Type>] <title>" --description "<issue body>" --label "<type>"
```

**Jira (Sub-Issue Creation):**

See [Jira Sub-Issue Flow](references/jira-sub-issue-flow.md) for the full Jira sub-issue creation payload and title format rules.

#### Structured Output

After creating the issue, emit:

```
ISSUE_RESULT_BEGIN
ISSUE_NUMBER=<number>
ISSUE_URL=<url>
TITLE=<title>
TYPE=<story|task|bug>
STATUS=created
PROVIDER=<github|gitlab|jira>
ISSUE_RESULT_END
```

After completion:
1. Parse the structured output
2. Update step: `checklist.py update issue <issue> 6 done`
3. Proceed to Step 6.5

### Step 6.5: Post-Creation DAG Update

After successful issue creation, register the new issue in the DAG.

**Provider support**: GitHub Wiki, GitLab Wiki, or local fallback. If DAG sync in Step 5.5 returned `STATUS=skipped`, skip this step too.

1. Extract keywords from issue body and normalize to UL canonical terms:
```bash
python3 ~/.claude/skills/issue-dag/scripts/dag-analyze.py --dag-file "$DAG_FILE" \
  add-node --id "<issue-number>" --title "<title>" --type "<type>" \
  --keywords "<k1>,<k2>" --paths "<p1>,<p2>"
```

2. If user chose "Create with dependency" in Step 5.6, add edge:
```bash
python3 ~/.claude/skills/issue-dag/scripts/dag-analyze.py --dag-file "$DAG_FILE" \
  add-edge --from "<new-issue>" --to "<dependency-issue>" --type "depends_on"
```

3. Push updated DAG:
```bash
bash ~/.claude/skills/issue-dag/scripts/dag-sync.sh push "Add #<N> to DAG"
```

4. If DAG update fails, log warning and continue (issue is already created; DAG is best-effort).

**Relationship references in issue body**: When dependencies exist, ensure the issue body includes:
- `blocked by #N` for depends_on edges
- `blocks #M` for reverse references
- `duplicated by #K` for duplicate edges

These references are inserted in the Dependencies/Blocks sections of the issue template.

### Step 7: Review Issue (Sub-Agent)

See [Review Workflow](references/review-workflow.md) for the full review dispatch, prompt construction, and feedback addressing process.

**Summary**: Orchestrator collects issue content + review criteria → constructs self-contained prompt → dispatches to sub-agent → processes verdict (APPROVE/NEEDS_WORK) → posts review as comment.

### Step 8: Address Feedback (if NEEDS_WORK)

See [Review Workflow](references/review-workflow.md) for the feedback addressing process.

**Summary**: Read review → evaluate each finding (accept/modify/clarify/decline) → update issue → post response comment → return to Step 7 (max 3 iterations).

### Step 9: Completion

When APPROVED:
1. Update checklist step 9 to done
2. Display summary based on mode:

#### Single Issue Output

```
Issue Created and Approved

Type: <Story|Task|Bug>
Issue: <#number or KEY> - <title>
URL: <url>
Provider: <github|gitlab|jira>
Reviews: <iteration count> iteration(s)
Verdict: APPROVED

The issue is ready for implementation planning.
Next: /issue-impl <#number or KEY>
```

#### Multi-Issue Output

Show summary table with columns: #, Type, Issue, Title, Status, Reviews.
- All approved: "Issues Created and Approved (N/N)" + `Next: /issue-impl #<first>`
- Partial: "Issues Created (X/N approved)" + note which issues need manual review

## Edit Mode

When invoked with `--edit <issue> <instruction>`:

1. **Detect provider** from issue format (Jira key vs number + git remote)
2. Fetch current content:
   - GitHub: `gh issue view <issue> --json title,body`
   - GitLab: `glab issue view <issue>`
   - Jira: `mcp__jira__jira_get` to fetch issue + latest comment
3. Apply the edit instruction to the issue content
4. Show diff (before/after)
5. Ask user to confirm
6. Update:
   - GitHub: `gh issue edit <issue> --body "<updated body>"`
   - GitLab: `glab issue edit <issue> --description "<updated body>"`
   - Jira: Post updated content as new comment via `mcp__jira__jira_post`

## Configuration

Reads `.claude/issue.yaml` (fallback: `.claude/story.yaml`).

| Key | GitHub/GitLab | Jira |
|-----|--------------|------|
| `tracker` | `github` or `gitlab` | `jira` |
| `<provider>.labels` | `{story, task, bug}` (customizable) | N/A (native type) |
| `<provider>.title_prefix` | `true` (default) | N/A |
| `jira.project` | N/A | Project key (e.g., `KIH`) |
| `jira.subtask_type` | N/A | Sub-task type name (default: `하위 작업`) |

**Defaults**: Auto-detect provider from git remote. GitHub/GitLab: `title_prefix: true`, labels: `story`/`task`/`bug`. Jira: native issue type field.

## Maintenance

### Integrity Checks

Run before any structural change to SKILL.md:

```bash
python3 ~/.claude/skills/issue/scripts/lint_skill.py ~/.claude/skills/issue
python3 ~/.claude/skills/issue/scripts/test_prompts.py
```

### Structure

This file uses progressive disclosure: core orchestration stays inline, detailed sub-flows are in reference files.
The agent reads SKILL.md first; reference files are loaded only when the relevant flow is triggered.

## References

### Workflow References
- [Multi-Issue Flow](references/multi-issue-flow.md) — scope analysis, split confirmation, execution loop
- [Jira Sub-Issue Flow](references/jira-sub-issue-flow.md) — parent issue parsing, sub-issue creation
- [Review Workflow](references/review-workflow.md) — review dispatch, prompt construction, feedback addressing

### Shared References
- [Provider Detection](~/.claude/skills/_shared/provider-detection.md) — detection algorithm, provider commands
- [Sub-Agent Dispatch](~/.claude/skills/_shared/sub-agent-dispatch.md) — dispatch mechanism, platform notes
- [User Interaction Points](~/.claude/skills/_shared/user-interaction-points.md) — UIP catalog (UIP-01, 05, 09, 14)

### Templates & Criteria
- [Story Template](references/story-template.md)
- [Task Template](references/task-template.md)
- [Bug Template](references/bug-template.md)
- [Story Review Criteria](references/review-criteria-story.md)
- [Task Review Criteria](references/review-criteria-task.md)
- [Bug Review Criteria](references/review-criteria-bug.md)
- [Examples](references/examples.md)
