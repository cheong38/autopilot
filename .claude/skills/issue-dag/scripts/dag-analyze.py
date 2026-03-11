#!/usr/bin/env python3
"""DAG analysis and CRUD tool for issue dependency management.

Uses only Python 3.9+ standard library. No external packages.

Usage:
    dag-analyze.py add-node --id ID --title TITLE --type TYPE [--status STATUS] [--keywords K1,K2] [--paths P1,P2]
    dag-analyze.py add-edge --from FROM --to TO --type TYPE
    dag-analyze.py remove-node --id ID
    dag-analyze.py remove-edge --from FROM --to TO
    dag-analyze.py get-node --id ID
    dag-analyze.py list-nodes [--status STATUS]
    dag-analyze.py list-edges
    dag-analyze.py update-node --id ID [--status STATUS] [--title TITLE] [--keywords K1,K2] [--paths P1,P2]
    dag-analyze.py init --repo OWNER/REPO
"""

import argparse
import json
import re
import sys
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

DAG_FILENAME = "issue-dag.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def empty_dag(repo: str) -> dict:
    return {
        "version": 1,
        "repo": repo,
        "updated_at": now_iso(),
        "nodes": {},
        "edges": [],
    }


def load_dag(path: Path) -> dict:
    if not path.exists():
        print(f"ERROR: DAG file not found: {path}", file=sys.stderr)
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_dag(dag: dict, path: Path) -> None:
    dag["updated_at"] = now_iso()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dag, f, indent=2, ensure_ascii=False)
        f.write("\n")


def validate_dag(dag: dict) -> list[str]:
    """Basic structural validation without external jsonschema package."""
    errors = []
    if dag.get("version") != 1:
        errors.append(f"Invalid version: {dag.get('version')}, expected 1")
    if not isinstance(dag.get("repo"), str) or "/" not in dag.get("repo", ""):
        errors.append(f"Invalid repo format: {dag.get('repo')}, expected owner/repo")
    if not isinstance(dag.get("nodes"), dict):
        errors.append("nodes must be an object")
    if not isinstance(dag.get("edges"), list):
        errors.append("edges must be an array")

    valid_types = {"story", "task", "bug"}
    valid_statuses = {"open", "closed"}
    valid_edge_types = {"depends_on", "duplicated_by"}

    for nid, node in dag.get("nodes", {}).items():
        if not isinstance(node, dict):
            errors.append(f"Node {nid}: must be an object")
            continue
        if node.get("type") not in valid_types:
            errors.append(f"Node {nid}: invalid type '{node.get('type')}'")
        if node.get("status") not in valid_statuses:
            errors.append(f"Node {nid}: invalid status '{node.get('status')}'")
        if not isinstance(node.get("keywords"), list):
            errors.append(f"Node {nid}: keywords must be an array")
        if not isinstance(node.get("touched_paths"), list):
            errors.append(f"Node {nid}: touched_paths must be an array")

    for i, edge in enumerate(dag.get("edges", [])):
        if not isinstance(edge, dict):
            errors.append(f"Edge {i}: must be an object")
            continue
        if edge.get("type") not in valid_edge_types:
            errors.append(f"Edge {i}: invalid type '{edge.get('type')}'")
        if edge.get("from") not in dag.get("nodes", {}):
            errors.append(f"Edge {i}: 'from' node '{edge.get('from')}' not found")
        if edge.get("to") not in dag.get("nodes", {}):
            errors.append(f"Edge {i}: 'to' node '{edge.get('to')}' not found")

    # Check for cycles in depends_on edges
    if not errors:  # Only check cycles if structure is valid
        cycles = detect_cycles(dag)
        for cycle in cycles:
            errors.append(f"Cycle detected: {' -> '.join(cycle)}")

    return errors


def find_dag_file(dag_file_arg: str | None) -> Path:
    """Resolve DAG file path."""
    if dag_file_arg:
        return Path(dag_file_arg)
    # Default: look in /tmp/issue-dag-wiki/<owner>-<repo>/issue-dag.json
    # Fallback: current directory
    cwd = Path.cwd()
    local = cwd / DAG_FILENAME
    if local.exists():
        return local
    # Try to find in /tmp cache
    tmp_base = Path("/tmp/issue-dag-wiki")
    if tmp_base.exists():
        for repo_dir in tmp_base.iterdir():
            candidate = repo_dir / DAG_FILENAME
            if candidate.exists():
                return candidate
    return local  # default to cwd


# ─── CRUD Commands ───────────────────────────────────────────

def cmd_init(args):
    path = Path(args.dag_file) if args.dag_file else Path(DAG_FILENAME)
    if path.exists() and not args.force:
        print(f"ERROR: {path} already exists. Use --force to overwrite.", file=sys.stderr)
        sys.exit(1)
    dag = empty_dag(args.repo)
    save_dag(dag, path)
    print(f"Initialized empty DAG at {path} for {args.repo}")


def cmd_add_node(args):
    path = find_dag_file(args.dag_file)
    dag = load_dag(path)
    nid = str(args.id)

    if nid in dag["nodes"]:
        print(f"ERROR: Node {nid} already exists", file=sys.stderr)
        sys.exit(1)

    keywords = [k.strip() for k in args.keywords.split(",")] if args.keywords else []
    paths = [p.strip() for p in args.paths.split(",")] if args.paths else []

    dag["nodes"][nid] = {
        "title": args.title,
        "type": args.type,
        "status": args.status or "open",
        "keywords": keywords,
        "touched_paths": paths,
        "created_at": now_iso(),
    }
    save_dag(dag, path)
    print(f"Added node {nid}: {args.title}")


def cmd_add_edge(args):
    path = find_dag_file(args.dag_file)
    dag = load_dag(path)
    src = str(getattr(args, "from"))
    dst = str(args.to)

    if src not in dag["nodes"]:
        print(f"ERROR: Source node {src} not found", file=sys.stderr)
        sys.exit(1)
    if dst not in dag["nodes"]:
        print(f"ERROR: Target node {dst} not found", file=sys.stderr)
        sys.exit(1)

    # Check duplicate
    for edge in dag["edges"]:
        if edge["from"] == src and edge["to"] == dst and edge["type"] == args.type:
            print(f"ERROR: Edge {src} -> {dst} ({args.type}) already exists", file=sys.stderr)
            sys.exit(1)

    dag["edges"].append({"from": src, "to": dst, "type": args.type})

    # Check for cycles before saving
    if args.type == "depends_on":
        cycles = detect_cycles(dag)
        if cycles:
            dag["edges"].pop()  # Remove the tentative edge
            cycle_str = " -> ".join(cycles[0])
            print(f"ERROR: Adding edge {src} -> {dst} would create a cycle: {cycle_str}", file=sys.stderr)
            sys.exit(1)

    save_dag(dag, path)
    print(f"Added edge: {src} -> {dst} ({args.type})")


def cmd_remove_node(args):
    path = find_dag_file(args.dag_file)
    dag = load_dag(path)
    nid = str(args.id)

    if nid not in dag["nodes"]:
        print(f"ERROR: Node {nid} not found", file=sys.stderr)
        sys.exit(1)

    del dag["nodes"][nid]
    dag["edges"] = [e for e in dag["edges"] if e["from"] != nid and e["to"] != nid]
    save_dag(dag, path)
    print(f"Removed node {nid} and its edges")


def cmd_remove_edge(args):
    path = find_dag_file(args.dag_file)
    dag = load_dag(path)
    src = str(getattr(args, "from"))
    dst = str(args.to)

    before = len(dag["edges"])
    dag["edges"] = [
        e for e in dag["edges"]
        if not (e["from"] == src and e["to"] == dst)
    ]
    if len(dag["edges"]) == before:
        print(f"ERROR: Edge {src} -> {dst} not found", file=sys.stderr)
        sys.exit(1)

    save_dag(dag, path)
    print(f"Removed edge: {src} -> {dst}")


def cmd_get_node(args):
    path = find_dag_file(args.dag_file)
    dag = load_dag(path)
    nid = str(args.id)

    if nid not in dag["nodes"]:
        print(f"ERROR: Node {nid} not found", file=sys.stderr)
        sys.exit(1)

    node = dag["nodes"][nid]
    deps = [e["to"] for e in dag["edges"] if e["from"] == nid and e["type"] == "depends_on"]
    blocks = [e["from"] for e in dag["edges"] if e["to"] == nid and e["type"] == "depends_on"]
    dupes = [e["to"] for e in dag["edges"] if e["from"] == nid and e["type"] == "duplicated_by"]

    result = {
        "id": nid,
        **node,
        "depends_on": deps,
        "blocked_by_this": blocks,
        "duplicated_by": dupes,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_update_node(args):
    path = find_dag_file(args.dag_file)
    dag = load_dag(path)
    nid = str(args.id)

    if nid not in dag["nodes"]:
        print(f"ERROR: Node {nid} not found", file=sys.stderr)
        sys.exit(1)

    node = dag["nodes"][nid]
    if args.status:
        node["status"] = args.status
    if args.title:
        node["title"] = args.title
    if args.keywords is not None:
        node["keywords"] = [k.strip() for k in args.keywords.split(",")]
    if args.paths is not None:
        node["touched_paths"] = [p.strip() for p in args.paths.split(",")]

    save_dag(dag, path)
    print(f"Updated node {nid}")


def cmd_list_nodes(args):
    path = find_dag_file(args.dag_file)
    dag = load_dag(path)

    nodes = dag["nodes"]
    if args.status:
        nodes = {k: v for k, v in nodes.items() if v["status"] == args.status}

    result = []
    for nid, node in nodes.items():
        result.append({"id": nid, **node})

    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_list_edges(args):
    path = find_dag_file(args.dag_file)
    dag = load_dag(path)
    print(json.dumps(dag["edges"], indent=2, ensure_ascii=False))


def cmd_validate(args):
    path = find_dag_file(args.dag_file)
    dag = load_dag(path)
    errors = validate_dag(dag)
    if errors:
        print("VALIDATION FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)
    print(f"DAG is valid: {len(dag['nodes'])} nodes, {len(dag['edges'])} edges")


# ─── Analysis Helpers ────────────────────────────────────────

def build_adjacency(dag: dict, edge_type: str = "depends_on") -> dict[str, list[str]]:
    """Build adjacency list: node -> list of nodes it depends on."""
    adj: dict[str, list[str]] = defaultdict(list)
    for nid in dag["nodes"]:
        adj.setdefault(nid, [])
    for edge in dag["edges"]:
        if edge["type"] == edge_type:
            adj[edge["from"]].append(edge["to"])
    return dict(adj)


def detect_cycles(dag: dict) -> list[list[str]]:
    """Detect cycles in DAG using DFS. Returns list of cycle paths (deduplicated)."""
    adj = build_adjacency(dag)
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {nid: WHITE for nid in dag["nodes"]}
    parent: dict[str, str | None] = {nid: None for nid in dag["nodes"]}
    raw_cycles: list[list[str]] = []

    def dfs(u: str) -> None:
        color[u] = GRAY
        for v in adj.get(u, []):
            if v not in color:
                continue
            if color[v] == GRAY:
                # Back edge found — extract cycle by walking parent chain from u to v
                cycle = [u]
                cur = u
                while cur != v:
                    next_cur = parent.get(cur)
                    if next_cur is None:
                        break
                    cycle.append(next_cur)
                    cur = next_cur
                raw_cycles.append(list(reversed(cycle)))
            elif color[v] == WHITE:
                parent[v] = u
                dfs(v)
        color[u] = BLACK

    for nid in dag["nodes"]:
        if color.get(nid) == WHITE:
            dfs(nid)

    # Deduplicate: normalize each cycle to start from its smallest element
    seen: set[tuple[str, ...]] = set()
    cycles: list[list[str]] = []
    for cycle in raw_cycles:
        if not cycle:
            continue
        min_idx = cycle.index(min(cycle))
        normalized = tuple(cycle[min_idx:] + cycle[:min_idx])
        if normalized not in seen:
            seen.add(normalized)
            cycles.append(list(normalized))

    return cycles


def topological_sort(dag: dict) -> list[str]:
    """Kahn's algorithm for topological sort on depends_on edges.
    Returns sorted node IDs. Raises if cycle detected."""
    adj = build_adjacency(dag)
    in_degree: dict[str, int] = {nid: 0 for nid in dag["nodes"]}
    for edge in dag["edges"]:
        if edge["type"] == "depends_on" and edge["from"] in in_degree:
            # edge["from"] depends on edge["to"], so edge["from"] has an incoming dependency
            in_degree[edge["from"]] = in_degree.get(edge["from"], 0) + 1

    queue = deque([nid for nid, d in in_degree.items() if d == 0])
    result = []

    while queue:
        u = queue.popleft()
        result.append(u)
        # Find nodes that depend on u (u is in their deps)
        for edge in dag["edges"]:
            if edge["type"] == "depends_on" and edge["to"] == u:
                v = edge["from"]
                if v in in_degree:
                    in_degree[v] -= 1
                    if in_degree[v] == 0:
                        queue.append(v)

    if len(result) != len(dag["nodes"]):
        missing = set(dag["nodes"].keys()) - set(result)
        print(f"ERROR: Cycle detected. Nodes in cycle: {sorted(missing)}", file=sys.stderr)
        sys.exit(1)

    return result


def find_ready_issues(dag: dict) -> list[str]:
    """Find open issues whose all depends_on targets are closed."""
    adj = build_adjacency(dag)
    ready = []
    for nid, node in dag["nodes"].items():
        if node["status"] != "open":
            continue
        deps = adj.get(nid, [])
        if not deps:
            ready.append(nid)
            continue
        all_closed = all(
            dag["nodes"].get(dep, {}).get("status") == "closed"
            for dep in deps
        )
        if all_closed:
            ready.append(nid)
    return ready


def find_parallel_groups(dag: dict) -> list[list[str]]:
    """Find groups of ready issues that can be worked on simultaneously.
    Groups are formed by independent connected components among ready issues."""
    ready_set = set(find_ready_issues(dag))
    if not ready_set:
        return []

    # Build undirected adjacency among ready issues only
    undirected: dict[str, set[str]] = {nid: set() for nid in ready_set}
    for edge in dag["edges"]:
        if edge["from"] in ready_set and edge["to"] in ready_set:
            undirected[edge["from"]].add(edge["to"])
            undirected[edge["to"]].add(edge["from"])

    visited: set[str] = set()
    groups: list[list[str]] = []

    for nid in sorted(ready_set):
        if nid in visited:
            continue
        component: list[str] = []
        queue = deque([nid])
        while queue:
            u = queue.popleft()
            if u in visited:
                continue
            visited.add(u)
            component.append(u)
            for v in undirected.get(u, set()):
                if v not in visited:
                    queue.append(v)
        groups.append(sorted(component))

    return groups


def find_orphans(dag: dict) -> list[str]:
    """Find nodes that have no edges (neither from nor to)."""
    connected = set()
    for edge in dag["edges"]:
        connected.add(edge["from"])
        connected.add(edge["to"])
    return sorted(nid for nid in dag["nodes"] if nid not in connected)


def generate_mermaid(dag: dict) -> str:
    """Generate Mermaid diagram string."""
    lines = ["graph TD"]
    for nid, node in dag["nodes"].items():
        label = f'{node["title"]}'
        if node["status"] == "closed":
            lines.append(f'    {nid}["{nid}: {label} ✓"]:::closed')
        else:
            lines.append(f'    {nid}["{nid}: {label}"]')
    for edge in dag["edges"]:
        if edge["type"] == "depends_on":
            lines.append(f'    {edge["from"]} -->|depends_on| {edge["to"]}')
        elif edge["type"] == "duplicated_by":
            lines.append(f'    {edge["from"]} -.->|duplicated_by| {edge["to"]}')
    lines.append('    classDef closed fill:#9f9,stroke:#6a6')
    return "\n".join(lines)


# ─── Similarity & UL Helpers ─────────────────────────────────

UL_FILENAME = "ubiquitous-language.json"


def load_ul(dag_file_path: Path) -> dict:
    """Load UL dictionary from same directory as DAG file."""
    ul_path = dag_file_path.parent / UL_FILENAME
    if not ul_path.exists():
        return {"terms": []}
    with open(ul_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_ul(ul: dict, dag_file_path: Path) -> None:
    """Save UL dictionary to same directory as DAG file."""
    ul_path = dag_file_path.parent / UL_FILENAME
    with open(ul_path, "w", encoding="utf-8") as f:
        json.dump(ul, f, indent=2, ensure_ascii=False)
        f.write("\n")


def build_alias_map(ul: dict) -> dict[str, str]:
    """Build alias→canonical mapping from UL dictionary."""
    alias_map: dict[str, str] = {}
    for term in ul.get("terms", []):
        canonical = term["canonical"].lower()
        alias_map[canonical] = canonical
        for alias in term.get("aliases", []):
            alias_map[alias.lower()] = canonical
    return alias_map


def normalize_keywords(keywords: list[str], alias_map: dict[str, str]) -> set[str]:
    """Normalize keywords through UL alias mapping."""
    normalized = set()
    for kw in keywords:
        kw_lower = kw.lower().strip()
        if kw_lower in alias_map:
            normalized.add(alias_map[kw_lower])
        else:
            normalized.add(kw_lower)
    return normalized


def jaccard_similarity(set_a: set, set_b: set) -> float:
    """Compute Jaccard similarity between two sets."""
    if not set_a and not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0


def tokenize(text: str) -> set[str]:
    """Simple tokenization: split on non-alphanumeric, lowercase."""
    return set(re.findall(r'\w+', text.lower()))


def compute_similarity(
    query_keywords: set[str],
    query_paths: set[str],
    query_title_tokens: set[str],
    node: dict,
    alias_map: dict[str, str],
) -> float:
    """Compute composite similarity score between query and a DAG node."""
    # Keyword similarity (weight 0.5)
    node_keywords = normalize_keywords(node.get("keywords", []), alias_map)
    kw_sim = jaccard_similarity(query_keywords, node_keywords)

    # Path similarity (weight 0.3)
    node_paths = set(p.lower() for p in node.get("touched_paths", []))
    path_sim = jaccard_similarity(query_paths, node_paths)

    # Title token overlap (weight 0.2)
    node_title_tokens = tokenize(node.get("title", ""))
    title_sim = jaccard_similarity(query_title_tokens, node_title_tokens)

    return 0.5 * kw_sim + 0.3 * path_sim + 0.2 * title_sim


def find_similar(
    dag: dict,
    keywords: list[str],
    paths: list[str],
    title: str,
    alias_map: dict[str, str],
    threshold: float = 0.15,
) -> list[dict]:
    """Find nodes similar to the given query."""
    query_kw = normalize_keywords(keywords, alias_map)
    query_paths = set(p.lower() for p in paths)
    query_title_tokens = tokenize(title)

    results = []
    for nid, node in dag["nodes"].items():
        score = compute_similarity(query_kw, query_paths, query_title_tokens, node, alias_map)
        if score >= threshold:
            results.append({
                "id": nid,
                "title": node["title"],
                "status": node["status"],
                "score": round(score, 3),
                "keywords": node.get("keywords", []),
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


# ─── Import Helpers ──────────────────────────────────────────

STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "as", "be", "was", "are",
    "this", "that", "not", "no", "do", "if", "so", "we", "my", "i",
    "add", "fix", "update", "create", "implement", "remove", "delete",
    "should", "can", "will", "need", "use", "make", "get", "set",
})

DEFAULT_LABEL_TYPE_MAP = {
    "story": "story",
    "task": "task",
    "bug": "bug",
    "feature": "story",
    "enhancement": "story",
    "defect": "bug",
}


def classify_issue_type(labels: list[str], label_type_map: dict[str, str]) -> str:
    """Classify issue type from labels. Falls back to 'task' if no match."""
    for label in labels:
        label_lower = label.lower().strip()
        if label_lower in label_type_map:
            return label_type_map[label_lower]
    return "task"


def extract_paths_from_body(body: str) -> list[str]:
    """Extract file/directory paths from issue body.

    Matches:
    - Paths inside backticks: `src/auth/login.py`
    - Paths matching common source directories: src/, lib/, app/, pkg/, internal/
    """
    if not body:
        return []
    paths: set[str] = set()
    # Paths inside backticks
    for m in re.finditer(r'`([^`\s]+/[^`\s]+)`', body):
        paths.add(m.group(1))
    # Paths matching common directory patterns (not inside backticks)
    path_re = re.compile(r'(?:^|\s)((?:src|lib|app|pkg|internal)/[\w./*-]+)', re.MULTILINE)
    for m in path_re.finditer(body):
        paths.add(m.group(1))
    return sorted(paths)


def extract_keywords(title: str, body: str, labels: list[str], type_labels: set[str] | None = None) -> list[str]:
    """Extract keywords from title tokens, labels (excluding type labels), and body code paths.

    - Title: tokenized, stopwords filtered
    - Labels: included except known type labels
    - Body: code paths extracted and added as keywords
    """
    if type_labels is None:
        type_labels = set(DEFAULT_LABEL_TYPE_MAP.keys())

    keywords: set[str] = set()
    # Title tokens
    for token in re.findall(r'\w+', title.lower()):
        if token not in STOPWORDS and len(token) > 1:
            keywords.add(token)
    # Labels (excluding type labels)
    for label in labels:
        if label.lower().strip() not in type_labels:
            keywords.add(label.lower().strip())
    # Code paths from body
    for p in extract_paths_from_body(body):
        keywords.add(p.lower())
    return sorted(keywords)


def parse_dependencies(body: str) -> list[dict]:
    """Parse dependency references from issue body text.

    Supported patterns (case-insensitive):
    - 'depends on #N' / 'blocked by #N' / 'requires #N' / 'after #N' → depends_on
    - 'blocks #N' → depends_on (reverse: #N depends on current)
    - 'duplicate of #N' → duplicated_by
    - 'duplicated by #N' → duplicated_by (reverse: #N is dup of current)

    Multiple refs supported: 'depends on #1, #2, #3'
    Returns list of {ref, type, direction} dicts (deduplicated).
    """
    if not body:
        return []

    # Remove existing dag section to avoid double-parsing
    cleaned = re.sub(
        r'<!-- issue-dag:begin -->.*?<!-- issue-dag:end -->',
        '', body, flags=re.DOTALL
    )

    results: list[tuple[str, str, str]] = []

    # Forward dependency patterns: current depends on #N
    forward_dep_re = re.compile(
        r'(?:depends\s+on|blocked\s+by|requires|after)\s+(#\d+(?:\s*,\s*#\d+)*)',
        re.IGNORECASE,
    )
    for m in forward_dep_re.finditer(cleaned):
        for ref in re.findall(r'#(\d+)', m.group(1)):
            results.append((ref, "depends_on", "forward"))

    # Reverse dependency pattern: current blocks #N → #N depends on current
    blocks_re = re.compile(
        r'blocks\s+(#\d+(?:\s*,\s*#\d+)*)',
        re.IGNORECASE,
    )
    for m in blocks_re.finditer(cleaned):
        for ref in re.findall(r'#(\d+)', m.group(1)):
            results.append((ref, "depends_on", "reverse"))

    # Forward duplicate pattern: current is duplicate of #N
    dup_of_re = re.compile(
        r'duplicate\s+of\s+(#\d+(?:\s*,\s*#\d+)*)',
        re.IGNORECASE,
    )
    for m in dup_of_re.finditer(cleaned):
        for ref in re.findall(r'#(\d+)', m.group(1)):
            results.append((ref, "duplicated_by", "forward"))

    # Reverse duplicate pattern: current is duplicated by #N
    dup_by_re = re.compile(
        r'duplicated\s+by\s+(#\d+(?:\s*,\s*#\d+)*)',
        re.IGNORECASE,
    )
    for m in dup_by_re.finditer(cleaned):
        for ref in re.findall(r'#(\d+)', m.group(1)):
            results.append((ref, "duplicated_by", "reverse"))

    # Deduplicate
    seen: set[tuple[str, str, str]] = set()
    deduped: list[dict] = []
    for ref, etype, direction in results:
        key = (ref, etype, direction)
        if key not in seen:
            seen.add(key)
            deduped.append({"ref": ref, "type": etype, "direction": direction})
    return deduped


# ─── Import Command ─────────────────────────────────────────

def cmd_import_issues(args):
    """Import issues from stdin JSON into the DAG.

    3-pass processing:
    1. Add/update nodes
    2. Parse dependencies → add edges (with cycle check)
    3. Detect duplicates
    """
    path = find_dag_file(args.dag_file)
    dag = load_dag(path)
    ul = load_ul(path)
    alias_map = build_alias_map(ul)

    # Parse label map
    label_type_map = dict(DEFAULT_LABEL_TYPE_MAP)
    if args.label_map:
        for pair in args.label_map.split(","):
            if ":" in pair:
                k, v = pair.split(":", 1)
                label_type_map[k.strip().lower()] = v.strip().lower()

    dup_threshold = args.dup_threshold

    # Read issues from stdin
    try:
        issues = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON on stdin: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(issues, list):
        print("ERROR: stdin must be a JSON array", file=sys.stderr)
        sys.exit(1)

    report = {
        "nodes_added": [],
        "nodes_skipped": [],
        "nodes_updated": [],
        "edges_added": [],
        "edges_skipped": [],
        "cycles_detected": [],
        "duplicates_detected": [],
        "label_map_failures": [],
    }

    type_labels = set(label_type_map.keys())

    # ── Pass 1: Add/update nodes ──
    for issue in issues:
        nid = str(issue.get("id", ""))
        if not nid:
            continue

        title = issue.get("title", "")
        labels = issue.get("labels", [])
        body = issue.get("body", "") or ""
        status = issue.get("status", "open")

        issue_type = classify_issue_type(labels, label_type_map)
        keywords = extract_keywords(title, body, labels, type_labels)
        paths = extract_paths_from_body(body)

        # Track label map failures (no type label matched, fell back to 'task')
        matched_any = any(
            l.lower().strip() in label_type_map for l in labels
        )
        if labels and not matched_any:
            report["label_map_failures"].append({
                "id": nid, "title": title, "labels": labels,
            })

        if nid in dag["nodes"]:
            # Update existing node if anything changed
            node = dag["nodes"][nid]
            changed = False
            if node.get("title") != title:
                node["title"] = title
                changed = True
            if node.get("status") != status:
                node["status"] = status
                changed = True
            if sorted(node.get("keywords", [])) != sorted(keywords):
                node["keywords"] = keywords
                changed = True
            if sorted(node.get("touched_paths", [])) != sorted(paths):
                node["touched_paths"] = paths
                changed = True
            if changed:
                report["nodes_updated"].append(nid)
            else:
                report["nodes_skipped"].append(nid)
        else:
            dag["nodes"][nid] = {
                "title": title,
                "type": issue_type,
                "status": status,
                "keywords": keywords,
                "touched_paths": paths,
                "created_at": now_iso(),
            }
            report["nodes_added"].append(nid)

    # ── Pass 2: Parse dependencies → add edges ──
    for issue in issues:
        nid = str(issue.get("id", ""))
        if not nid or nid not in dag["nodes"]:
            continue

        body = issue.get("body", "") or ""
        deps = parse_dependencies(body)

        for dep in deps:
            ref = dep["ref"]
            etype = dep["type"]
            direction = dep["direction"]

            # Self-reference: skip
            if ref == nid:
                continue

            # Determine edge direction
            if direction == "forward":
                src, dst = nid, ref
            else:
                src, dst = ref, nid

            # Both nodes must exist in DAG
            if src not in dag["nodes"] or dst not in dag["nodes"]:
                report["edges_skipped"].append({
                    "from": src, "to": dst, "type": etype,
                    "reason": "node_not_found",
                })
                continue

            # Check duplicate edge
            edge_exists = any(
                e["from"] == src and e["to"] == dst and e["type"] == etype
                for e in dag["edges"]
            )
            if edge_exists:
                report["edges_skipped"].append({
                    "from": src, "to": dst, "type": etype,
                    "reason": "duplicate",
                })
                continue

            # Add edge
            dag["edges"].append({"from": src, "to": dst, "type": etype})

            # Cycle check for depends_on edges
            if etype == "depends_on":
                cycles = detect_cycles(dag)
                if cycles:
                    # Rollback
                    dag["edges"].pop()
                    report["cycles_detected"].append({
                        "attempted_edge": {"from": src, "to": dst, "type": etype},
                        "cycle": cycles[0],
                    })
                    continue

            report["edges_added"].append({"from": src, "to": dst, "type": etype})

    # ── Pass 3: Duplicate detection ──
    node_ids = sorted(dag["nodes"].keys())
    for i, nid_a in enumerate(node_ids):
        node_a = dag["nodes"][nid_a]
        kw_a = normalize_keywords(node_a.get("keywords", []), alias_map)
        paths_a = set(p.lower() for p in node_a.get("touched_paths", []))
        title_tokens_a = tokenize(node_a.get("title", ""))
        for nid_b in node_ids[i + 1:]:
            node_b = dag["nodes"][nid_b]
            score = compute_similarity(kw_a, paths_a, title_tokens_a, node_b, alias_map)
            if score >= dup_threshold:
                report["duplicates_detected"].append({
                    "a": {"id": nid_a, "title": node_a.get("title", "")},
                    "b": {"id": nid_b, "title": node_b.get("title", "")},
                    "score": round(score, 3),
                })

    save_dag(dag, path)
    print(json.dumps(report, indent=2, ensure_ascii=False))


# ─── Analysis Commands ───────────────────────────────────────

def cmd_topo_sort(args):
    path = find_dag_file(args.dag_file)
    dag = load_dag(path)
    order = topological_sort(dag)
    result = []
    for nid in order:
        node = dag["nodes"][nid]
        result.append({"id": nid, "title": node["title"], "status": node["status"]})
    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_ready(args):
    path = find_dag_file(args.dag_file)
    dag = load_dag(path)
    ready_ids = find_ready_issues(dag)
    result = []
    for nid in ready_ids:
        node = dag["nodes"][nid]
        result.append({"id": nid, "title": node["title"], "type": node["type"]})
    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_parallel(args):
    path = find_dag_file(args.dag_file)
    dag = load_dag(path)
    groups = find_parallel_groups(dag)
    result = []
    for group in groups:
        items = []
        for nid in group:
            node = dag["nodes"][nid]
            items.append({"id": nid, "title": node["title"]})
        result.append(items)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_check(args):
    path = find_dag_file(args.dag_file)
    dag = load_dag(path)
    nid = str(args.id)

    if nid not in dag["nodes"]:
        print(f"ERROR: Node {nid} not found", file=sys.stderr)
        sys.exit(1)

    node = dag["nodes"][nid]
    adj = build_adjacency(dag)
    deps = adj.get(nid, [])

    blockers = []
    for dep_id in deps:
        dep_node = dag["nodes"].get(dep_id)
        if dep_node and dep_node["status"] == "open":
            blockers.append({"id": dep_id, "title": dep_node["title"], "status": "open"})

    dependents = [
        e["from"] for e in dag["edges"]
        if e["to"] == nid and e["type"] == "depends_on"
    ]

    is_ready = len(blockers) == 0 and node["status"] == "open"

    result = {
        "id": nid,
        "title": node["title"],
        "status": node["status"],
        "is_ready": is_ready,
        "blockers": blockers,
        "total_deps": len(deps),
        "open_blockers": len(blockers),
        "dependents": dependents,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_detect_cycle(args):
    path = find_dag_file(args.dag_file)
    dag = load_dag(path)
    cycles = detect_cycles(dag)
    if cycles:
        print(f"CYCLES DETECTED: {len(cycles)}", file=sys.stderr)
        for i, cycle in enumerate(cycles):
            print(f"  Cycle {i+1}: {' -> '.join(cycle)}", file=sys.stderr)
        sys.exit(1)
    print("No cycles detected")


def cmd_orphans(args):
    path = find_dag_file(args.dag_file)
    dag = load_dag(path)
    orphan_ids = find_orphans(dag)
    result = []
    for nid in orphan_ids:
        node = dag["nodes"][nid]
        result.append({"id": nid, "title": node["title"], "status": node["status"]})
    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_viz(args):
    path = find_dag_file(args.dag_file)
    dag = load_dag(path)
    print(generate_mermaid(dag))


# ─── Dep Section Commands ────────────────────────────────────


MARKER_BEGIN = "<!-- issue-dag:begin -->"
MARKER_END = "<!-- issue-dag:end -->"


def compute_issue_deps(dag: dict) -> dict[str, dict[str, list[str]]]:
    """Compute dependency info for all issues with edges."""
    deps: dict[str, dict[str, list[str]]] = {}
    for nid in dag.get("nodes", {}):
        deps[nid] = {"depends_on": [], "blocks": [], "duplicate_of": [], "duplicated_by_from": []}
    for edge in dag.get("edges", []):
        src, tgt, etype = edge["from"], edge["to"], edge["type"]
        for nid in [src, tgt]:
            if nid not in deps:
                deps[nid] = {"depends_on": [], "blocks": [], "duplicate_of": [], "duplicated_by_from": []}
        if etype == "depends_on":
            deps[src]["depends_on"].append(tgt)
            deps[tgt]["blocks"].append(src)
        elif etype == "duplicated_by":
            deps[src]["duplicate_of"].append(tgt)
            deps[tgt]["duplicated_by_from"].append(src)
    return deps


def build_dep_section(info: dict[str, list[str]]) -> str:
    """Build the markdown dependency section for an issue."""
    lines = [MARKER_BEGIN, "## Dependencies (auto-managed by issue-dag)", ""]
    if info["depends_on"]:
        refs = ", ".join(f"#{x}" for x in sorted(info["depends_on"], key=int))
        lines.append(f"- **Depends on**: {refs}")
    if info["blocks"]:
        refs = ", ".join(f"#{x}" for x in sorted(info["blocks"], key=int))
        lines.append(f"- **Blocks**: {refs}")
    if info["duplicate_of"]:
        refs = ", ".join(f"#{x}" for x in sorted(info["duplicate_of"], key=int))
        lines.append(f"- **Duplicate of**: {refs}")
    if info["duplicated_by_from"]:
        refs = ", ".join(f"#{x}" for x in sorted(info["duplicated_by_from"], key=int))
        lines.append(f"- **Duplicated by**: {refs}")
    lines.append("")
    lines.append(MARKER_END)
    return "\n".join(lines)


def cmd_dep_section(args):
    """Output the dependency section markdown for given issue(s)."""
    path = find_dag_file(args.dag_file)
    dag = load_dag(path)
    all_deps = compute_issue_deps(dag)

    target_ids: list[str] = []
    if args.id == "all":
        target_ids = [k for k, v in all_deps.items()
                      if v["depends_on"] or v["blocks"] or v["duplicate_of"] or v["duplicated_by_from"]]
    else:
        target_ids = [x.strip().lstrip("#") for x in args.id.split(",")]

    result = {}
    for nid in sorted(target_ids, key=int):
        info = all_deps.get(nid)
        if info and (info["depends_on"] or info["blocks"] or info["duplicate_of"] or info["duplicated_by_from"]):
            result[nid] = build_dep_section(info)
        else:
            result[nid] = ""  # No edges — section should be removed
    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_affected_issues(args):
    """List issue IDs affected by an edge between two nodes."""
    path = find_dag_file(args.dag_file)
    dag = load_dag(path)
    all_deps = compute_issue_deps(dag)

    src = str(getattr(args, "from"))
    dst = str(args.to)

    affected = set()
    for nid in [src, dst]:
        info = all_deps.get(nid, {})
        if any(info.get(k) for k in ["depends_on", "blocks", "duplicate_of", "duplicated_by_from"]):
            affected.add(nid)
    print(json.dumps(sorted(affected, key=int), ensure_ascii=False))


# ─── Similarity & UL Commands ────────────────────────────────

def cmd_similar(args):
    path = find_dag_file(args.dag_file)
    dag = load_dag(path)
    ul = load_ul(path)
    alias_map = build_alias_map(ul)

    keywords = [k.strip() for k in args.keywords.split(",")] if args.keywords else []
    paths = [p.strip() for p in args.paths.split(",")] if args.paths else []
    title = args.title or ""
    threshold = args.threshold

    results = find_similar(dag, keywords, paths, title, alias_map, threshold)
    print(json.dumps(results, indent=2, ensure_ascii=False))


def cmd_ul_lookup(args):
    path = find_dag_file(args.dag_file)
    ul = load_ul(path)
    alias_map = build_alias_map(ul)

    term = args.term.lower().strip()
    canonical = alias_map.get(term)
    if canonical:
        # Find full term entry
        for entry in ul.get("terms", []):
            if entry["canonical"].lower() == canonical:
                print(json.dumps(entry, indent=2, ensure_ascii=False))
                return
    print(json.dumps({"canonical": None, "message": f"Term '{args.term}' not found in UL"}, indent=2))


def cmd_ul_add(args):
    path = find_dag_file(args.dag_file)
    ul = load_ul(path)

    canonical = args.canonical.strip()
    aliases = [a.strip() for a in args.aliases.split(",")] if args.aliases else []
    domain = args.domain or ""

    # Check if canonical already exists
    for term in ul.get("terms", []):
        if term["canonical"].lower() == canonical.lower():
            # Merge aliases
            existing = set(a.lower() for a in term.get("aliases", []))
            new_aliases = [a for a in aliases if a.lower() not in existing]
            term["aliases"].extend(new_aliases)
            save_ul(ul, path)
            print(f"Updated term '{canonical}': added {len(new_aliases)} new aliases")
            return

    new_term = {"canonical": canonical, "aliases": aliases}
    if domain:
        new_term["domain"] = domain
    ul.setdefault("terms", []).append(new_term)
    save_ul(ul, path)
    print(f"Added term '{canonical}' with {len(aliases)} aliases")


def cmd_ul_scan(args):
    """Scan project for domain terms. Outputs candidates for UL addition."""
    scan_dir = Path(args.dir) if args.dir else Path.cwd()

    candidates = []

    # 1. Check .claude/ubiquitous-language.yaml
    ul_yaml = scan_dir / ".claude" / "ubiquitous-language.yaml"
    if ul_yaml.exists():
        # Simple YAML-like parsing (no external deps)
        with open(ul_yaml, "r", encoding="utf-8") as f:
            content = f.read()
        print(f"Found project UL at {ul_yaml}")
        print(content)
        return

    # 2. Check docs/glossary*
    docs_dir = scan_dir / "docs"
    if docs_dir.exists():
        for p in docs_dir.iterdir():
            if p.name.lower().startswith("glossary") or p.name.lower().startswith("domain"):
                candidates.append({"source": str(p), "type": "glossary_file"})

    # 3. Scan for domain model classes
    src_patterns = [scan_dir / "src", scan_dir / "lib", scan_dir / "app"]
    domain_re = re.compile(r'class\s+(\w+)\s*\(.*(?:Entity|AggregateRoot|ValueObject|BaseModel).*\)')
    for src in src_patterns:
        if not src.exists():
            continue
        for py_file in src.rglob("*.py"):
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    for line in f:
                        m = domain_re.search(line)
                        if m:
                            candidates.append({
                                "term": m.group(1),
                                "source": str(py_file),
                                "type": "domain_class",
                            })
            except (UnicodeDecodeError, PermissionError):
                continue

    print(json.dumps(candidates, indent=2, ensure_ascii=False))


# ─── Argument Parser ─────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Issue DAG analysis and CRUD tool")
    parser.add_argument("--dag-file", help="Path to DAG JSON file")

    sub = parser.add_subparsers(dest="command", required=True)

    # init
    p = sub.add_parser("init", help="Initialize empty DAG")
    p.add_argument("--repo", required=True, help="owner/repo")
    p.add_argument("--force", action="store_true")

    # add-node
    p = sub.add_parser("add-node", help="Add a node")
    p.add_argument("--id", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--type", required=True, choices=["story", "task", "bug"])
    p.add_argument("--status", default="open", choices=["open", "closed"])
    p.add_argument("--keywords", default="")
    p.add_argument("--paths", default="")

    # add-edge
    p = sub.add_parser("add-edge", help="Add an edge")
    p.add_argument("--from", required=True, dest="from")
    p.add_argument("--to", required=True)
    p.add_argument("--type", required=True, choices=["depends_on", "duplicated_by"])

    # remove-node
    p = sub.add_parser("remove-node", help="Remove a node and its edges")
    p.add_argument("--id", required=True)

    # remove-edge
    p = sub.add_parser("remove-edge", help="Remove an edge")
    p.add_argument("--from", required=True, dest="from")
    p.add_argument("--to", required=True)

    # get-node
    p = sub.add_parser("get-node", help="Get node details")
    p.add_argument("--id", required=True)

    # update-node
    p = sub.add_parser("update-node", help="Update a node")
    p.add_argument("--id", required=True)
    p.add_argument("--status", choices=["open", "closed"])
    p.add_argument("--title")
    p.add_argument("--keywords")
    p.add_argument("--paths")

    # list-nodes
    p = sub.add_parser("list-nodes", help="List all nodes")
    p.add_argument("--status", choices=["open", "closed"])

    # list-edges
    sub.add_parser("list-edges", help="List all edges")

    # validate
    sub.add_parser("validate", help="Validate DAG structure")

    # topo-sort
    sub.add_parser("topo-sort", help="Topological sort of nodes")

    # ready
    sub.add_parser("ready", help="List issues ready to work on")

    # parallel
    sub.add_parser("parallel", help="List parallel-workable issue groups")

    # check
    p = sub.add_parser("check", help="Check blocker status for a node")
    p.add_argument("--id", required=True)

    # detect-cycle
    sub.add_parser("detect-cycle", help="Detect cycles in the DAG")

    # orphans
    sub.add_parser("orphans", help="Find orphan nodes with no edges")

    # viz
    sub.add_parser("viz", help="Generate Mermaid diagram")

    # similar
    p = sub.add_parser("similar", help="Find similar issues by keywords/paths/title")
    p.add_argument("--keywords", default="")
    p.add_argument("--paths", default="")
    p.add_argument("--title", default="")
    p.add_argument("--threshold", type=float, default=0.15)

    # ul-lookup
    p = sub.add_parser("ul-lookup", help="Look up a term in UL dictionary")
    p.add_argument("--term", required=True)

    # ul-add
    p = sub.add_parser("ul-add", help="Add a term to UL dictionary")
    p.add_argument("--canonical", required=True)
    p.add_argument("--aliases", default="")
    p.add_argument("--domain", default="")

    # ul-scan
    p = sub.add_parser("ul-scan", help="Scan project for domain terms")
    p.add_argument("--dir", default="")

    # import-issues
    p = sub.add_parser("import-issues", help="Bulk import issues from stdin JSON into DAG")
    p.add_argument("--label-map", default="", help="label:type pairs, e.g. story:story,bug:bug")
    p.add_argument("--dup-threshold", type=float, default=0.3, help="Duplicate detection threshold")

    # dep-section
    p = sub.add_parser("dep-section", help="Output dependency markdown section for issue(s)")
    p.add_argument("--id", required=True, help="Issue ID, comma-separated IDs, or 'all'")

    # affected-issues
    p = sub.add_parser("affected-issues", help="List issues affected by an edge")
    p.add_argument("--from", required=True, dest="from")
    p.add_argument("--to", required=True)

    return parser


COMMANDS = {
    "init": cmd_init,
    "add-node": cmd_add_node,
    "add-edge": cmd_add_edge,
    "remove-node": cmd_remove_node,
    "remove-edge": cmd_remove_edge,
    "get-node": cmd_get_node,
    "update-node": cmd_update_node,
    "list-nodes": cmd_list_nodes,
    "list-edges": cmd_list_edges,
    "validate": cmd_validate,
    "topo-sort": cmd_topo_sort,
    "ready": cmd_ready,
    "parallel": cmd_parallel,
    "check": cmd_check,
    "detect-cycle": cmd_detect_cycle,
    "orphans": cmd_orphans,
    "viz": cmd_viz,
    "similar": cmd_similar,
    "ul-lookup": cmd_ul_lookup,
    "ul-add": cmd_ul_add,
    "ul-scan": cmd_ul_scan,
    "dep-section": cmd_dep_section,
    "affected-issues": cmd_affected_issues,
    "import-issues": cmd_import_issues,
}


def main():
    parser = build_parser()
    args = parser.parse_args()
    COMMANDS[args.command](args)


if __name__ == "__main__":
    main()
