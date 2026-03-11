# Agent Delegation Strategy

Dynamic delegation based on context size. Referenced by Step 6 (IMPL-LOOP).

## Context Size Thresholds

| Context Size | Issue Count | Strategy | Rationale |
|-------------|-------------|----------|-----------|
| Small | 1–`context_threshold.medium` (default 4) | Inline | Low overhead, simple coordination |
| Medium | `medium`–`large` (default 4–9) | Sub-agents per issue-impl | Isolate implementation context |
| Large | `large`+ (default 9+) | Agent team | Parallel where safe, clean contexts |

**Goal**: Each agent's context should contain only what it needs. The orchestrator holds global state; workers hold only their assigned issue's scope.

## Inline Execution (Small)

The orchestrator directly invokes `/issue-impl <issue_number>` in its own context.

- Pros: No dispatch overhead, full context continuity
- Cons: Context window fills with implementation details
- Use when: ≤ 3 issues, simple implementations

## Sub-Agent Execution (Medium)

Dispatch `/issue-impl` to a sub-agent per issue:

```
Task tool:
  subagent_type: "general-purpose"
  model: "sonnet"  (or "opus" for 4+ phase issues)
  prompt: |
    ## Why Context (Judgment Guide)
    <Why Context narrative from meta-issue>

    <embedded issue-impl SKILL.md content>
    <issue context: title, body, acceptance criteria, verification method>
    <relevant reference files>
```

Following [Sub-Agent Dispatch](~/.claude/skills/_shared/sub-agent-dispatch.md) pattern:
> "Embed ALL context in the prompt. The sub-agent MUST NOT explore or fetch files."

**Exception**: `/issue-impl` sub-agents need file access (they write code), so they use `subagent_type="general-purpose"` with full tool access.

**Output parsing**: Orchestrator parses `IMPL_RESULT_BEGIN/END` from sub-agent response.

## Agent Team Execution (Large)

For large issue sets with parallelization opportunities:

```
Orchestrator (autopilot)  ← embeds ## Why Context in each worker prompt
├── Worker-1: issue-impl #42  (files: src/auth/*)      model=sonnet
├── Worker-2: issue-impl #43  (files: src/billing/*)   model=sonnet  ← parallel OK
└── Worker-3: issue-impl #44  (files: src/auth/*)      model=sonnet  ← queued after #42
```

### Parallel Execution Safety

When multiple issues are DAG-ready simultaneously:

1. Check `dag-analyze.py parallel` for groups of independent issues
2. For each parallel group, verify file path disjointness (compare `touched_paths`)
3. **Disjoint paths** → may run concurrently in separate workers
4. **Overlapping paths** → serialize execution

### Merge Ordering Protocol

1. All workers complete implementation + pass CI independently
2. Orchestrator serializes merges: lowest issue number first
3. After each merge, remaining workers rebase on updated main
4. If rebase conflicts → worker resolves, re-runs tests, re-submits

## Self-Review Sub-Agent

For complex self-reviews requiring fresh perspective:

```
Task tool:
  subagent_type: "general-purpose"
  model: "sonnet"
  max_turns: 3
  prompt: |
    <review criteria from references/self-review-criteria.md>
    <prompt from references/self-review-prompt-template.md>
```
