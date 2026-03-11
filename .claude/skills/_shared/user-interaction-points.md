# User Interaction Points (UIP) Catalog

Platform-neutral interaction pattern for `/issue`, `/issue-impl`, `/issue-dag`, `/autopilot` skills.

## Pattern Format

All interaction points use this format in SKILL.md:

```markdown
> **User Interaction** (UIP-XX): 한국어 설명 / English description

| Option | Action |
|--------|--------|
| **Label** | What happens |
| **Other** | 사용자 자유 입력 / User provides custom input |
```

Every table includes an explicit **Other** row for free-form input.

---

## `/issue` Skill

### UIP-01 — Issue Type Confirmation (Step 2)

Auto-detected type shown as "(Recommended)".

| Option | Action |
|--------|--------|
| **Story (Recommended)** | Use auto-detected story type |
| **Task** | Override to task |
| **Bug** | Override to bug |
| **Other** | 사용자 자유 입력 / User provides custom input |

**Default**: Auto-detected type. **When**: Confidence is high but user has final say.

### UIP-05 — Issue Draft Preview (Step 6)

Present full draft before creating.

| Option | Action |
|--------|--------|
| **Create** | Create the issue as drafted |
| **Edit** | Modify draft before creating |
| **Cancel** | Abort issue creation |
| **Other** | 사용자 자유 입력 / User provides custom input |

**Default**: Create.

### UIP-09 — DAG Sync Failure (Step 5.5)

DAG sync failed; issue creation can still proceed.

| Option | Action |
|--------|--------|
| **Skip** | Proceed without DAG analysis |
| **Retry** | Retry DAG sync |
| **Abort** | Abort issue creation |
| **Other** | 사용자 자유 입력 / User provides custom input |

**Default**: Skip.

### UIP-14 — Missing Template Sections (Step 6)

Template section has no data from discovery.

| Option | Action |
|--------|--------|
| **TBD** | Fill with TBD placeholder |
| **Input** | Provide content now |
| **N/A** | Mark section as not applicable |
| **Other** | 사용자 자유 입력 / User provides custom input |

**Default**: TBD. **Per section**: Asked for each missing section.

---

## `/issue-impl` Skill

### UIP-03 — Complexity Assessment Confirmation (Step 5a)

| Option | Action |
|--------|--------|
| **Accept** | Proceed with assessed complexity |
| **Override Simple** | Force simple path (5b) |
| **Override Complex** | Force complex path (5d) |
| **Other** | 사용자 자유 입력 / User provides custom input |

**Default**: Accept.

### UIP-04 — Done Criteria Unmet (Step 8c)

Code review found unchecked done criteria.

| Option | Action |
|--------|--------|
| **Fix** | Address unmet criteria before merge |
| **Override** | Force approve despite unmet criteria |
| **Defer** | Mark as follow-up, proceed with merge |
| **Other** | 사용자 자유 입력 / User provides custom input |

**Default**: Fix.

### UIP-06 — PR/MR Preview (Step 7)

Present PR title + body before creating.

| Option | Action |
|--------|--------|
| **Create** | Create PR/MR as drafted |
| **Edit** | Modify title/body before creating |
| **Cancel** | Abort PR creation |
| **Other** | 사용자 자유 입력 / User provides custom input |

**Default**: Create.

### UIP-10 — Rebase Conflict (Step 5.5)

Conflict during `git rebase origin/main`.

| Option | Action |
|--------|--------|
| **Auto-resolve** | Attempt automatic conflict resolution |
| **Abort rebase** | `git rebase --abort`, continue on current base |
| **Manual** | Pause for user to resolve manually |
| **Other** | 사용자 자유 입력 / User provides custom input |

**Default**: Manual.

### UIP-11 — Max Iteration Reached (Step 5 & 8)

Plan or code review hit 3 iterations without approval.

| Option | Action |
|--------|--------|
| **Force approve** | Override and proceed |
| **One more** | Allow one additional review iteration |
| **Abort** | Stop implementation |
| **Other** | 사용자 자유 입력 / User provides custom input |

**Default**: Force approve.

### UIP-15 — Context Load Decision (Step 3.5)

Previous session context found for this issue.

| Option | Action |
|--------|--------|
| **Continue** | Resume from previous session context |
| **Start fresh** | Ignore previous context, start from scratch |
| **Other** | 사용자 자유 입력 / User provides custom input |

**Default**: Continue.

---

## `/issue-dag` Skill

### UIP-07 — DAG Mutation Confirmation (Step 3)

Before executing a destructive DAG change (add/remove node, add/remove edge).

| Option | Action |
|--------|--------|
| **Confirm** | Execute the change |
| **Cancel** | Abort the operation |
| **Other** | 사용자 자유 입력 / User provides custom input |

**Default**: Confirm.

### UIP-08 — Wiki Push Confirmation (Step 4)

Before pushing DAG changes to Wiki.

| Option | Action |
|--------|--------|
| **Push** | Push changes to Wiki now |
| **Defer** | Keep changes local, push later |
| **Other** | 사용자 자유 입력 / User provides custom input |

**Default**: Push.

### UIP-12 — Cycle Detected on Edge Add (Error Handling)

Adding an edge would create a circular dependency.

| Option | Action |
|--------|--------|
| **Cancel edge** | Do not add the proposed edge |
| **Remove existing** | Remove the conflicting existing edge, then add new one |
| **Force** | Add edge anyway (breaks DAG invariant — not recommended) |
| **Other** | 사용자 자유 입력 / User provides custom input |

**Default**: Cancel edge.

---

## `/autopilot` Skill

### UIP-17 — Requirement Clarification (Step 2.5)

Requirement confidence is below threshold; needs user input.

| Option | Action |
|--------|--------|
| **<Recommended interpretation>** | Use this interpretation and proceed |
| **<Alternative A>** | Use alternative interpretation A |
| **<Alternative B>** | Use alternative interpretation B |
| **Other** | 사용자 자유 입력 / User provides custom input |

**Default**: Recommended interpretation. **When**: Confidence < `confidence_threshold` (default 99%).

### UIP-18 — Verification Strategy Unclear (Step 1.5)

Cannot determine how to verify a requirement.

| Option | Action |
|--------|--------|
| **Playwright (Recommended)** | Use browser automation to verify |
| **CLI/API** | Use curl, httpie, or CLI tools |
| **Manual** | Provide step-by-step guide for user |
| **Other** | 사용자 자유 입력 / User provides custom input |

**Default**: Playwright.

### UIP-19 — New UL Term Definition (Step 2)

New domain term found that is not in the UL dictionary.

| Option | Action |
|--------|--------|
| **Define now (Recommended)** | User provides canonical name, aliases, domain |
| **Skip** | Proceed without adding to UL |
| **Not a domain term** | Exclude from UL consideration |
| **Other** | 사용자 자유 입력 / User provides custom input |

**Default**: Define now.

### UIP-20 — Issue Decomposition Confirmation (Step 3.5)

Decomposition confidence is below threshold.

| Option | Action |
|--------|--------|
| **Approve (Recommended)** | Create issues as decomposed |
| **Modify** | User adjusts the issue list |
| **Re-decompose** | Redo decomposition with different strategy |
| **Other** | 사용자 자유 입력 / User provides custom input |

**Default**: Approve.

### UIP-21 — DAG Execution Order Confirmation (Step 5.5)

DAG is complex; execution order needs user review.

| Option | Action |
|--------|--------|
| **Approve (Recommended)** | Proceed with proposed execution order |
| **Reorder** | User specifies different execution order |
| **Visualize** | Show Mermaid diagram, then ask again |
| **Other** | 사용자 자유 입력 / User provides custom input |

**Default**: Approve.

### UIP-22 — Credentials Needed for Verification (Step 6.5)

Verification requires authentication or environment setup.

| Option | Action |
|--------|--------|
| **Provide now (Recommended)** | User provides credentials/setup |
| **Skip verification** | Mark as manually verified later |
| **Other** | 사용자 자유 입력 / User provides custom input |

**Default**: Provide now.

### UIP-23 — Verification Failure Triage Override (Step 7)

Auto-classification of verification failure severity is uncertain.

| Option | Action |
|--------|--------|
| **Accept classification (Recommended)** | Proceed with auto-classified severity |
| **Override to blocking** | Force blocking classification |
| **Override to non-blocking** | Force non-blocking classification |
| **Other** | 사용자 자유 입력 / User provides custom input |

**Default**: Accept classification. **When**: Auto-classification confidence < 95%.

### UIP-24 — Follow-up Round Limit Reached (Step 10)

Follow-up rounds exceeded `max_followup_rounds` (default 3).

| Option | Action |
|--------|--------|
| **Stop (Recommended)** | Halt. Report remaining open issues for manual resolution. |
| **One more round** | Allow one additional follow-up round |
| **Force complete** | Mark remaining issues as deferred, proceed to REPORT |
| **Other** | 사용자 자유 입력 / User provides custom input |

**Default**: Stop.

### UIP-25 — Session Lock Conflict on Resume (Resume Protocol)

Another autopilot session holds the lock on the meta-issue.

| Option | Action |
|--------|--------|
| **Force override (Recommended)** | Break stale lock and resume (if lock > 2h old) |
| **Wait** | Abort resume, let the other session finish |
| **Abort other** | Force-release the other session's lock |
| **Other** | 사용자 자유 입력 / User provides custom input |

**Default**: Force override (if stale).

### UIP-26 — Implementation Failure Escalation (Step 6)

Implementation failed after max retries for an issue.

| Option | Action |
|--------|--------|
| **Skip issue (Recommended)** | Create bug issue, move to next ready |
| **Retry** | One more implementation attempt |
| **Abort autopilot** | Stop entire session |
| **Other** | 사용자 자유 입력 / User provides custom input |

**Default**: Skip issue.

### UIP-27 — User Problem Clarification (Step 0.5)

Triggered when the user's underlying problem is vague or missing from the input. Part of the WHY-CONTEXT step.

> **User Interaction** (UIP-27): 사용자 문제 파악 / User problem clarification

| Option | Action |
|--------|--------|
| **<Auto-extracted recommended interpretation>** | Proceed with this interpretation |
| **<Alternative A>** | Project-context-based alternative interpretation |
| **<Alternative B>** | Different perspective alternative |
| **Other** | 사용자 자유 입력 / User provides custom input |

**Default**: Auto-extracted interpretation.

### UIP-28 — Decision Context Clarification (Step 0.5)

Triggered when the decision background (technical/non-technical constraints, trade-off criteria) is vague or missing. Part of the WHY-CONTEXT step.

> **User Interaction** (UIP-28): 의사결정 맥락 파악 / Decision context clarification

| Option | Action |
|--------|--------|
| **<Auto-extracted from tech stack/patterns>** | Proceed with this context |
| **<Alternative A>** | Different constraint interpretation |
| **<Alternative B>** | Different trade-off criterion |
| **Other** | 사용자 자유 입력 / User provides custom input |

**Default**: Auto-extracted context.
