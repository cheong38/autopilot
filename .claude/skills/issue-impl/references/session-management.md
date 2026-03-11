# Session Management

Detailed session lifecycle for issue-impl. Referenced from SKILL.md Steps 1.5, 3.5, 6.5, 11a, 11.5, and Abort.

## Step 1.5: Session Lock

### Check Lock

Use the lock management commands from `~/.claude/skills/_shared/provider-detection.md`.

**If locked:**
1. Fetch the latest comment on the issue to find the last session timestamp
2. Calculate staleness: if last comment > 2 hours ago → offer force override
3. Display:
   ```
   Issue <ref> is currently locked (wip).
   Last activity: <timestamp> (<duration> ago)

   Options:
   1. Force override (take over session)
   2. Abort
   ```
4. If user chooses abort → stop issue-impl entirely
5. If force override → proceed (lock already held)

**If not locked** → acquire lock and proceed.

### Acquire Lock

Use the lock commands from the shared provider-detection reference.

### Post Session-Start Comment

```markdown
**Session Start** (<ISO-8601 timestamp>)
- Machine: <hostname from `hostname` command>
- Path: <worktree directory>
- Issue-Impl: starting
```

## Step 3.5: Load Context

After worktree is created and checklist initialized, load previous session context.

1. Fetch issue body + all comments (already fetched in Step 1, reuse data)
2. Scan comments for `**Progress Update**` markers — find the **latest** one
3. Scan comments for `**Session Start**` / `**Session End**` / `**Session Aborted**` markers
4. If a previous Progress Update exists, extract:
   - What was done (## Done section)
   - Key decisions (## Decisions section)
   - What was planned next (## Next section)
   - Changed files (## Changed Files section)
5. Use extracted context to inform plan creation (Step 4) — skip already-completed work

If no previous context exists, this is a fresh session — proceed normally.

## WIP Buffer

### Location

`<WORKTREE_DIR>/.claude/wip-buffer.md`

### Template

```markdown
# WIP Buffer — <issue-ref>

## Current Task
<!-- What you're working on right now -->

## Done
<!-- Completed items this session -->

## Decisions
<!-- Key decisions and rationale -->

## Next
<!-- What to do next -->

## Changed Files
<!-- Files modified this session -->
```

### Buffer Lifecycle

1. **Created** at Step 3.5 (after worktree + context load)
2. **Updated** by Claude during work (CLAUDE.md behavioral instruction)
3. **Flushed** at Step 6.5 (after each phase) and Step 11.5 (session end)
4. **Auto-flushed** by PreCompact hook if compaction triggers
5. **Deleted** at Step 12 (cleanup)

## Step 6.5: Phase Save

After each implementation phase completes:

1. Read `.claude/wip-buffer.md`
2. If buffer has content beyond skeleton:
   - Format as issue comment:
     ```markdown
     **Progress Update** (<ISO-8601 timestamp>)

     <buffer content>
     ```
   - Post comment using provider-specific commands
3. Reset buffer to skeleton template (preserve issue reference)
4. Continue to next phase

## Step 11.5: Session End

After deploy & verify, before worktree cleanup:

1. If buffer has content → flush (same as Phase Save)
2. Post session-end comment:
   ```markdown
   **Session End** (<ISO-8601 timestamp>)
   - Machine: <hostname>
   - Result: completed successfully
   - PR/MR: #<number>
   ```
3. Release lock (remove `wip` label / transition Jira status back)

### Session End on Deployment Failure

배포 실패로 핫픽스 플로우(Step 11a)를 시작할 경우:

1. 버퍼 flush (same as Phase Save)
2. Post session-end comment:
   ```markdown
   **Session End** (<ISO-8601 timestamp>)
   - Machine: <hostname>
   - Result: deployment failed — hotfix issue #<N> created
   - PR/MR: #<number>
   - Hotfix: #<hotfix-number>
   ```
3. Release lock (핫픽스가 새 세션으로 lock을 다시 잡음)

## Abort Procedure

Triggered by user saying "abort", "cancel", "중단", or `/issue-impl --abort`.

1. If buffer has content → flush as:
   ```markdown
   **Session Aborted** (<ISO-8601 timestamp>)
   - Reason: <user-provided or "user requested abort">

   <buffer content>
   ```
2. Post abort comment to issue
3. Release lock
4. Remove worktree: `git worktree remove <WORKTREE_DIR> --force`
5. Display:
   ```
   Session aborted on <issue-ref>.
   Buffer flushed, lock released, worktree removed.
   Issue remains open — resume with /issue-impl <ref>.
   ```
