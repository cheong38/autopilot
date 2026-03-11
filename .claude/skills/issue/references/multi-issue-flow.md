# Multi-Issue Flow

## Multi-Issue Lifecycle

```
┌──────────────────────────────────────────────────────────────────┐
│                   MULTI-ISSUE LIFECYCLE                           │
├──────────────────────────────────────────────────────────────────┤
│  1. PARSE      │ Extract requirements from user input            │
│  1.5 SCOPE     │ Decompose into N independent issues             │
│  1.6 CONFIRM   │ Present split plan → user approves/adjusts      │
│  3. DETECT     │ Detect provider (once, shared across all)       │
│                │                                                 │
│  FOR EACH issue i of N:                                          │
│  │  2. TYPE    │ Use proposed type from scope analysis           │
│  │  4. DISCOVER│ Ask missing info (per issue)                    │
│  │  5-9. CREATE/REVIEW/ADDRESS loop (same as single issue)       │
│                │                                                 │
│  10. DONE      │ Show summary table of ALL created issues        │
└──────────────────────────────────────────────────────────────────┘
```

## Step 1.5: Scope Analysis

Analyze whether the requirements should be split into multiple issues.

**Trigger conditions** (any of these activates scope analysis):
- `--split` flag is explicitly provided → always perform decomposition
- Input is a Jira parent issue key (Jira Sub-Issue flow) → always perform decomposition
- Two or more distinct Actor/user roles are mentioned
- Two or more independently valuable capabilities are identified
- Compound requirement expressions: "그리고", "또한", "and also", "additionally"

**Decomposition criteria — value units delivered to Actors**:
- Each Story delivers **one independent value** to **one Actor**
- Different Actors mentioned → separate Stories
- Same Actor but independently valuable capabilities → separate Stories
- Non-functional technical work (not directly delivering Actor value) → Task

**Analysis process**:
1. Identify all Actors/user roles in the requirements
2. For each Actor, identify distinct value units they receive
3. Identify technical enablers that don't directly deliver Actor value
4. Propose issue decomposition:

```
| # | Type  | Actor           | Title                        | Scope Summary          |
|---|-------|-----------------|------------------------------|------------------------|
| 1 | Story | End user        | [Story] User authentication  | Login, logout, session |
| 2 | Story | Admin           | [Story] User management      | CRUD, role assignment  |
| 3 | Task  | (technical)     | [Task] Set up OAuth config   | OAuth provider setup   |
```

**If single issue detected** (only one Actor + one value unit + no `--split` flag):
→ Skip to Step 2, proceed with normal single-issue flow.

## Step 1.6: Confirm Split

Present the decomposition plan and ask the user for confirmation:

> "요구사항을 N개 이슈로 분리하겠습니다. 어떻게 진행할까요?"
> (or in English: "Split requirements into N issues. How to proceed?")
>
> Options:
> 1. "Proceed with proposed split" (proceed as-is)
> 2. "Modify and split" (user adjusts the split, then proceed)
> 3. "Keep as single issue" (skip split, use original single-issue flow)

- **Proceed**: Enter multi-issue execution loop (see below)
- **Modify**: Let user adjust issue boundaries, then proceed with modified plan
- **Keep as single**: Fall back to normal single-issue flow from Step 2

## Multi-Issue Execution Loop

When split is confirmed, execute the following for each proposed issue:

```
provider = detect_provider()  # Step 3 — done once, shared

for each proposed_issue in split_plan:
    Step 2: TYPE    → Use type from scope analysis (Story/Task/Bug)
    Step 4: DISCOVER → Ask only missing info for THIS specific issue
    Step 5: CHECKLIST → Initialize per-issue checklist
    Step 6: CREATE  → Draft + create this issue
    Step 7: REVIEW  → Evaluate issue quality
    Step 8: ADDRESS → If NEEDS_WORK, address review feedback
    Step 9: LOOP    → Repeat 7-8 until APPROVED (max 3 iterations)
```

After all issues are created, proceed to Step 10 (Done).
