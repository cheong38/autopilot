# Sub-Agent Dispatch

Shared reference for dispatching isolated review tasks to sub-agents. Used by `/issue` (Step 7: issue review) and `/issue-impl` (Step 5d: plan review, Step 8: code review).

## Dispatch Mechanism

| Platform | Mechanism | Invocation |
|----------|-----------|------------|
| **Claude Code** | `Task` tool | `Task(subagent_type="general-purpose", model="sonnet", max_turns=5, prompt=<review_prompt>)` |
| **OpenCode** | `Task` tool (built-in) | Same interface, runs as separate session |
| **Codex** | Sequential step | Execute review as self-contained sequential step |
| **Fallback** | Inline | Orchestrator executes review directly (no isolation) |

## Model Policy

All sub-agent dispatches MUST use `model="sonnet"` or `model="opus"`. Never use `model="haiku"`. Haiku lacks the reasoning depth required for quality-critical tasks (code review, issue review, architecture feedback).

## Detection Logic

1. `Task` tool available → use it (works on both Claude Code and OpenCode)
2. No `Task` tool → execute review as inline sequential step
3. Inline fallback → orchestrator performs review directly (no isolation)

## Prompt Rule

Embed ALL context (issue content / plan / PR diff, review criteria, output format) in the prompt. The sub-agent MUST NOT explore or fetch files.

**WHY-CONTEXT propagation rule**: Every sub-agent/team-worker prompt MUST include the `## Why Context` block read from the meta-issue body. This context serves as the reference criterion for trade-off decisions.

## OpenCode-Specific Notes

OpenCode's Task tool has known issues:

- **Timeout**: No default timeout — set `provider.<name>.options.timeout` in `opencode.json` (e.g., `1200000` for 20 min)
- **Permission**: Ensure `"permission": { "task": "allow" }` in `opencode.json` (use string `"allow"`, not boolean)
- **Stateless sessions**: Sub-agent sessions close immediately after returning
- **TUI feedback**: Parent may show only "loading" — use `Ctrl+X` → arrow keys to inspect

If the Task tool call hangs or returns no result, fall back to **inline execution**.
