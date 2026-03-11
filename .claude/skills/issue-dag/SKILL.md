---
name: issue-dag
description: |
  Manage issue dependencies as a DAG (Directed Acyclic Graph) stored in Wiki or local file.
  Provides CRUD operations, dependency analysis, duplicate detection, and visualization.
  Used by /issue and /issue-impl for pre-creation analysis and post-completion updates.

  Trigger: "/issue-dag", "/issue-dag <command>"
  Keywords: dag, dependency, depends on, blocks, blocked by, duplicate, ready, parallel, issue graph
---

# Issue DAG Skill

Manage issue relationships (dependencies, duplicates) as a Directed Acyclic Graph.
DAG is stored as JSON in GitHub/GitLab Wiki or local file (`.claude/dag/`).

## Language Matching

Output messages match the user's language. Structural labels stay in English.

## Provider Support

**GitHub/GitLab Wiki** with **local fallback**. Backend auto-detected from git remote:
- **GitHub**: Wiki at `github.com/<owner>/<repo>.wiki.git`
- **GitLab**: Wiki at `gitlab.com/<group>/<project>.wiki.git`
- **Other/none**: Local storage at `.claude/dag/issue-dag.json`

Detection: see `~/.claude/skills/_shared/provider-detection.md`.

### Local Mode

When no Wiki provider is detected (or `dag.backend: local` in config):
- DAG stored at `<project-root>/.claude/dag/issue-dag.json`
- `push` is a no-op — prints: "DAG is stored locally. Commit `.claude/dag/` to share."
- Not shared across team members unless committed to git
- All analysis features (ready, parallel, similar, etc.) work identically

## Configuration

Reads `.claude/issue.yaml`:

| Key | Values | Default | Description |
|-----|--------|---------|-------------|
| `dag.backend` | `auto`, `github-wiki`, `gitlab-wiki`, `local` | `auto` | DAG storage backend |

**auto** (default): Detect provider from git remote → try Wiki → fall back to local.

## Usage

```
/issue-dag                                  DAG summary (node count, edge count, ready issues)
/issue-dag add #42                          Add existing issue to DAG
/issue-dag link #43 --depends-on #42        Add dependency edge (43 depends on 42)
/issue-dag link #45 --duplicated-by #42     Mark 45 as duplicate of 42
/issue-dag remove #42                       Remove issue from DAG (and its edges)
/issue-dag unlink #43 --from #42            Remove edge between 43 and 42
/issue-dag import                           Import all open issues into DAG
/issue-dag import --all                     Import all issues (open + closed)
/issue-dag sync                             Pull latest DAG from Wiki
/issue-dag push [message]                   Push DAG changes to Wiki
/issue-dag ready                            List issues ready to work on (all blockers closed)
/issue-dag parallel                         List groups of issues workable simultaneously
/issue-dag check #42                        Check blocker status and dependency chain
/issue-dag viz                              Output Mermaid diagram of the DAG
/issue-dag topo-sort                        Show topologically sorted issue order
/issue-dag detect-cycle                     Check for circular dependencies
/issue-dag orphans                          Find nodes with no edges
/issue-dag similar --keywords "auth,login"  Find similar/duplicate issues
/issue-dag similar --title "로그인 구현"     Find similar by title
/issue-dag similar --paths "src/auth/*"     Find similar by touched paths
/issue-dag ul-lookup --term "auth"          Look up UL canonical term
/issue-dag ul-add --canonical "인증" --aliases "auth,login"  Add UL term
/issue-dag ul-scan --dir .                  Scan codebase for UL candidates
/issue-dag sync-issues                      Sync dependency sections to all issue bodies
```

## Orchestration Flow

### Step 1: Provider Check

Provider is auto-detected by `dag-sync.sh`. No manual check needed — the sync command handles GitHub Wiki, GitLab Wiki, and local fallback transparently.

### Step 2: Sync DAG

```bash
bash ~/.claude/skills/issue-dag/scripts/dag-sync.sh pull
```

Parse structured output between `DAG_SYNC_RESULT_BEGIN` / `DAG_SYNC_RESULT_END`.
Extract `DAG_FILE` path for subsequent operations.

If pull fails (Wiki not enabled):
- Show error with activation instructions
- Exit gracefully — do not block calling skill

### Step 3: Execute Command

Route to the appropriate `dag-analyze.py` subcommand.

For mutation operations (add, link, remove, unlink), present UIP-07 before executing:

> **User Interaction** (UIP-07): DAG 변경 작업 확인 / Confirm DAG mutation

| Option | Action |
|--------|--------|
| **Confirm (Recommended)** | Execute the change |
| **Cancel** | Abort the operation |
| **Other** | 사용자 자유 입력 / User provides custom input |

#### Summary (default, no subcommand)

```bash
python3 ~/.claude/skills/issue-dag/scripts/dag-analyze.py --dag-file "$DAG_FILE" list-nodes
python3 ~/.claude/skills/issue-dag/scripts/dag-analyze.py --dag-file "$DAG_FILE" list-edges
```

Present: total nodes, total edges, open/closed counts.

#### Add Node (`add #N`)

1. Fetch issue from tracker: `gh issue view <N> --json title,labels,body`
2. Extract type (story/task/bug from labels), keywords, touched_paths
3. Add to DAG:
```bash
python3 ~/.claude/skills/issue-dag/scripts/dag-analyze.py --dag-file "$DAG_FILE" \
  add-node --id "<N>" --title "<title>" --type "<type>" \
  --keywords "<k1>,<k2>" --paths "<p1>,<p2>"
```

#### Link (`link #A --depends-on #B` or `link #A --duplicated-by #B`)

```bash
python3 ~/.claude/skills/issue-dag/scripts/dag-analyze.py --dag-file "$DAG_FILE" \
  add-edge --from "<A>" --to "<B>" --type "depends_on"
```

For `--duplicated-by`:
```bash
python3 ~/.claude/skills/issue-dag/scripts/dag-analyze.py --dag-file "$DAG_FILE" \
  add-edge --from "<A>" --to "<B>" --type "duplicated_by"
```

#### Remove Node (`remove #N`)

```bash
python3 ~/.claude/skills/issue-dag/scripts/dag-analyze.py --dag-file "$DAG_FILE" \
  remove-node --id "<N>"
```

#### Unlink (`unlink #A --from #B`)

```bash
python3 ~/.claude/skills/issue-dag/scripts/dag-analyze.py --dag-file "$DAG_FILE" \
  remove-edge --from "<A>" --to "<B>"
```

#### Sync (`sync`)

Already done in Step 2. Re-run if needed:
```bash
bash ~/.claude/skills/issue-dag/scripts/dag-sync.sh pull
```

#### Push (`push [message]`)

```bash
bash ~/.claude/skills/issue-dag/scripts/dag-sync.sh push "<message>"
```

#### Ready (`ready`)

```bash
python3 ~/.claude/skills/issue-dag/scripts/dag-analyze.py --dag-file "$DAG_FILE" ready
```

Returns JSON array of issues whose all `depends_on` targets are `closed`.

#### Parallel (`parallel`)

```bash
python3 ~/.claude/skills/issue-dag/scripts/dag-analyze.py --dag-file "$DAG_FILE" parallel
```

Returns groups of independent ready issues that can be worked on simultaneously.

#### Check (`check #N`)

```bash
python3 ~/.claude/skills/issue-dag/scripts/dag-analyze.py --dag-file "$DAG_FILE" check --id "<N>"
```

Returns: `is_ready`, `blockers` (open dependencies), `dependents` (issues blocked by this one).

#### Viz (`viz`)

```bash
python3 ~/.claude/skills/issue-dag/scripts/dag-analyze.py --dag-file "$DAG_FILE" viz
```

Outputs a Mermaid diagram string. Closed nodes shown with checkmark and green styling.

#### Topo-sort (`topo-sort`)

```bash
python3 ~/.claude/skills/issue-dag/scripts/dag-analyze.py --dag-file "$DAG_FILE" topo-sort
```

Returns all nodes in topological order (respecting dependency chains).

#### Detect-cycle (`detect-cycle`)

```bash
python3 ~/.claude/skills/issue-dag/scripts/dag-analyze.py --dag-file "$DAG_FILE" detect-cycle
```

Exits with error if cycles detected. Used as validation before push.

#### Orphans (`orphans`)

```bash
python3 ~/.claude/skills/issue-dag/scripts/dag-analyze.py --dag-file "$DAG_FILE" orphans
```

Returns nodes with no edges (neither from nor to). Useful for finding disconnected issues.

#### Similar (`similar`)

```bash
python3 ~/.claude/skills/issue-dag/scripts/dag-analyze.py --dag-file "$DAG_FILE" \
  similar --keywords "auth,login" --paths "src/auth/*" --title "로그인 구현" \
  --threshold 0.15
```

Finds existing DAG nodes similar to the query using composite weighted scoring:
- Keywords (0.5 weight): Jaccard similarity after UL normalization
- Touched paths (0.3 weight): Jaccard similarity of glob patterns
- Title tokens (0.2 weight): Jaccard similarity of word tokens

Returns JSON array of `{id, title, score}` sorted by score descending. Default threshold: 0.15.

UL dictionary is auto-loaded from `ubiquitous-language.json` in the DAG file directory.

#### UL Lookup (`ul-lookup`)

```bash
python3 ~/.claude/skills/issue-dag/scripts/dag-analyze.py --dag-file "$DAG_FILE" \
  ul-lookup --term "auth"
```

Look up a term in the Ubiquitous Language dictionary. Returns `{canonical, aliases, domain}` or `{canonical: null}` if not found.

#### UL Add (`ul-add`)

```bash
python3 ~/.claude/skills/issue-dag/scripts/dag-analyze.py --dag-file "$DAG_FILE" \
  ul-add --canonical "인증" --aliases "auth,login,signin" --domain "identity"
```

Add or merge a term into the UL dictionary. If canonical already exists, aliases are merged.

#### UL Scan (`ul-scan`)

```bash
python3 ~/.claude/skills/issue-dag/scripts/dag-analyze.py --dag-file "$DAG_FILE" \
  ul-scan --dir "."
```

Scan a directory for potential UL candidates (class names, glossary files). Returns JSON array of suggestions.

#### Sync Issues (`sync-issues`)

Bulk sync all dependency sections to GitHub issue bodies:

```bash
python3 ~/.claude/skills/issue-dag/scripts/dag-analyze.py --dag-file "$DAG_FILE" dep-section --id all
```

Returns JSON `{"<id>": "<markdown>", ...}` for all issues with edges. For each issue:
1. Read body: `gh issue view <N> --json body --jq '.body'`
2. Replace `<!-- issue-dag:begin -->...<!-- issue-dag:end -->` block, or append if missing
3. Update: `gh issue edit <N> --body "$UPDATED_BODY"`

#### Import (`import` / `import --all`)

Bulk import issues from the tracker into the DAG:

1. **DAG sync** (Step 2)

2. **Fetch issues** from tracker:
   - GitHub: `gh issue list --state open --json number,title,labels,body --limit 500`
   - GitHub (--all): `gh issue list --state all --json number,title,labels,body --limit 500`
   - GitLab: `glab issue list --per-page 100` (paginate as needed)

3. **Normalize JSON**: Convert provider-specific fields to common format:
   - GitHub: `number` → `id`, `labels[].name` → `labels`
   - GitLab: `iid` → `id`, `description` → `body`

4. **Confirm (UIP-13)**: Display issue count, provider, DAG file path.

> **User Interaction** (UIP-13): Import 확인 / Confirm bulk import

| Option | Action |
|--------|--------|
| **Import (Recommended)** | Execute import |
| **Preview** | Show first 10 issues, then ask again |
| **Cancel** | Abort |
| **Other** | 사용자 자유 입력 / User provides custom input |

5. **Run import**: Pipe normalized JSON to `dag-analyze.py import-issues`:
```bash
echo "$NORMALIZED_JSON" | python3 ~/.claude/skills/issue-dag/scripts/dag-analyze.py \
  --dag-file "$DAG_FILE" import-issues
```

6. **Report results**: Show counts for added/updated/skipped nodes, edges, cycles, duplicates.

7. **Handle duplicates (UIP-16)**: For each detected duplicate pair:

> **User Interaction** (UIP-16): 중복 처리 / Handle detected duplicate

| Option | Action |
|--------|--------|
| **Link** | Add `duplicated_by` edge between the pair |
| **Skip (Recommended)** | Ignore this duplicate pair |
| **Other** | 사용자 자유 입력 / User provides custom input |

8. **Handle cycles (UIP-12)**: Report using existing cycle detection pattern.

9. **Sync issue bodies**: Update dependency sections in issue bodies:
```bash
python3 ~/.claude/skills/issue-dag/scripts/dag-analyze.py --dag-file "$DAG_FILE" dep-section --id all
```
Then update each issue body via `gh issue edit` / `glab issue edit`.

10. **Push (UIP-08)**: Use existing push pattern.

### Step 4: Auto-Push (if data changed)

After any mutation (add, link, remove, unlink, update-node), present UIP-08:

> **User Interaction** (UIP-08): Wiki 푸시 확인 / Confirm push to Wiki

| Option | Action |
|--------|--------|
| **Push (Recommended)** | Push changes to Wiki now |
| **Defer** | Keep changes local, push later |
| **Other** | 사용자 자유 입력 / User provides custom input |

If user selects Push:
```bash
bash ~/.claude/skills/issue-dag/scripts/dag-sync.sh push "Update DAG: <action description>"
```

### Step 4.5: Sync Issue Bodies (after edge mutations)

After any edge mutation (link, unlink, remove node), sync the dependency section in affected GitHub issue bodies.
This keeps issue bodies in sync with the DAG as single source of truth.

**When to run**: After `add-edge`, `remove-edge`, or `remove-node` completes successfully.

1. Get affected issue IDs:
```bash
python3 ~/.claude/skills/issue-dag/scripts/dag-analyze.py --dag-file "$DAG_FILE" \
  affected-issues --from "<A>" --to "<B>"
```

2. Get the dependency section markdown for each affected issue:
```bash
python3 ~/.claude/skills/issue-dag/scripts/dag-analyze.py --dag-file "$DAG_FILE" \
  dep-section --id "<comma-separated-ids>"
```

Returns JSON: `{"<id>": "<markdown section>", ...}`. Empty string means the issue has no edges (remove the section).

3. For each affected issue, update the body:
   - Read current body: `gh issue view <N> --json body --jq '.body'`
   - If body contains `<!-- issue-dag:begin -->...<!-- issue-dag:end -->`, replace that block
   - Otherwise, append the section to the end of the body
   - If the section is empty (no edges left), remove the existing block
   - Write: `gh issue edit <N> --body "$UPDATED_BODY"`

**Section format** (HTML comment markers for machine parsing):
```markdown
<!-- issue-dag:begin -->
## Dependencies (auto-managed by issue-dag)

- **Depends on**: #42, #43
- **Blocks**: #100
- **Duplicate of**: #528
- **Duplicated by**: #531

<!-- issue-dag:end -->
```

**Bulk sync**: Use `dep-section --id all` to regenerate sections for all issues with edges.

### Step 5: Report

Output structured result:

```
DAG_RESULT_BEGIN
ACTION=<command>
STATUS=<ok|error>
DETAIL=<human-readable summary>
DAG_RESULT_END
```

## Error Handling

- **Wiki not available**: Show activation instructions, exit gracefully
- **Node already exists**: Show existing node info, suggest update
- **Cycle detected**: Block edge creation, show cycle path, present UIP-12:

> **User Interaction** (UIP-12): 순환 의존성 감지 / Cycle detected on edge add

| Option | Action |
|--------|--------|
| **Cancel edge (Recommended)** | Do not add the proposed edge |
| **Remove existing** | Remove the conflicting existing edge, then add new one |
| **Force** | Add edge anyway (breaks DAG invariant — not recommended) |
| **Other** | 사용자 자유 입력 / User provides custom input |
- **Network failure**: Show error, suggest manual `sync` later
- **Unsupported provider**: Auto-fallback to local storage (or skip if not `auto` mode)

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `scripts/dag-sync.sh` | Wiki clone/pull/push with conflict retry |
| `scripts/dag-analyze.py` | DAG CRUD, validation, analysis |

## Schema Reference

See `references/dag-schema.json` for the full JSON schema.
See `references/similarity.md` for similarity scoring details.

### Node Types
- `story` — User-facing feature
- `task` — Technical/operational work
- `bug` — Defect report

### Edge Types
- `depends_on` — Source cannot start until target is completed
- `duplicated_by` — Source is a duplicate of target

### Status Values
- `open` — Issue is active
- `closed` — Issue is completed

## Maintenance

Run before structural changes:
```bash
python3 ~/.claude/skills/issue/scripts/lint_skill.py ~/.claude/skills/issue-dag
python3 -m unittest discover -s ~/.claude/skills/issue-dag/tests -v
```

## References

- [User Interaction Points](~/.claude/skills/_shared/user-interaction-points.md) — UIP catalog (UIP-07, 08, 12)
