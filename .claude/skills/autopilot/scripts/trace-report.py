#!/usr/bin/env python3
"""Report generator for autopilot trace data.

Reads trace JSON files and generates markdown summaries, comparisons,
bottleneck analysis, review statistics, and session listings.

Usage:
    trace-report.py summary --session <SID> [--format markdown|json]
    trace-report.py compare --sessions <S1> <S2>
    trace-report.py bottleneck --session <SID> [--top <N>]
    trace-report.py review-stats [--sessions <S1> <S2> ...] [--last <N>]
    trace-report.py list [--last <N>]
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def _git_root() -> Path:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return Path(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return Path.cwd()


def _traces_dir() -> Path:
    return _git_root() / ".claude" / "autopilot-traces"


def _load_trace(session_id: str) -> dict:
    path = _traces_dir() / f"{session_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Trace not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_index() -> dict:
    path = _traces_dir() / "index.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"sessions": []}


def _format_duration(ms: int | None) -> str:
    """Format milliseconds as human-readable duration."""
    if ms is None:
        return "N/A"
    seconds = ms // 1000
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    remaining = seconds % 60
    if minutes < 60:
        return f"{minutes}m {remaining}s"
    hours = minutes // 60
    remaining_m = minutes % 60
    return f"{hours}h {remaining_m}m"


def _format_tokens(tokens: int | None) -> str:
    """Format token count with thousand separators."""
    if tokens is None:
        return "N/A"
    return f"{tokens:,}"


# --- Anomaly Detection ---

def _detect_anomalies(trace: dict) -> list[dict]:
    """Detect anomaly patterns in trace spans.

    Returns list of dicts with keys: metric, cause, action.
    """
    anomalies = []
    root = trace["spans"][0]
    root_tokens = root["attributes"].get("total_tokens")
    root_duration = root.get("duration_ms")

    issue_spans = [s for s in trace["spans"] if s["kind"] == "issue"]
    step_spans = [s for s in trace["spans"] if s["kind"] == "step"]
    sub_step_spans = [s for s in trace["spans"] if s["kind"] == "sub_step"]

    # 1. Long duration + few tokens → external wait
    if root_duration and root_tokens:
        tokens_per_second = root_tokens / (root_duration / 1000) if root_duration > 0 else 0
        if root_duration > 300000 and tokens_per_second < 50:
            anomalies.append({
                "metric": f"duration={_format_duration(root_duration)}, tokens/s={tokens_per_second:.0f}",
                "cause": "Possible external wait (CI, deploy, user input)",
                "action": "Check for blocking steps; consider async patterns",
            })

    # 2. Short duration + many tokens → excessive context loading
    if root_duration and root_tokens:
        if root_duration < 120000 and root_tokens > 100000:
            anomalies.append({
                "metric": f"duration={_format_duration(root_duration)}, tokens={_format_tokens(root_tokens)}",
                "cause": "Excessive context loading relative to duration",
                "action": "Review context window usage; consider targeted reads",
            })

    # 3. High retry count (>3 attempts per issue)
    for issue_span in issue_spans:
        reviews = [s for s in sub_step_spans
                   if s["parent_id"] == issue_span["id"]
                   and s["name"] == "code-review"]
        if len(reviews) > 3:
            issue_num = issue_span["attributes"].get("issue_number", issue_span["name"])
            anomalies.append({
                "metric": f"retries={len(reviews)} for issue #{issue_num}",
                "cause": "Prompt quality or persistent review issues",
                "action": "Review code-review criteria; consider prompt improvements",
            })

    # 4. Excessive tool_uses (>50 per issue)
    for issue_span in issue_spans:
        tool_uses = issue_span["attributes"].get("tool_uses")
        if tool_uses and tool_uses > 50:
            issue_num = issue_span["attributes"].get("issue_number", issue_span["name"])
            anomalies.append({
                "metric": f"tool_uses={tool_uses} for issue #{issue_num}",
                "cause": "Exploration inefficiency",
                "action": "Improve issue description or provide better context",
            })

    # 5. Token spike vs session average
    if len(issue_spans) > 1:
        tokens_list = [s["attributes"].get("total_tokens") for s in issue_spans
                       if s["attributes"].get("total_tokens") is not None]
        if len(tokens_list) > 1:
            avg = sum(tokens_list) / len(tokens_list)
            for issue_span in issue_spans:
                t = issue_span["attributes"].get("total_tokens")
                if t and avg > 0 and t > avg * 2:
                    issue_num = issue_span["attributes"].get("issue_number", issue_span["name"])
                    anomalies.append({
                        "metric": f"tokens={_format_tokens(t)} vs avg={_format_tokens(int(avg))} for issue #{issue_num}",
                        "cause": "Token spike — possible regression or inefficiency",
                        "action": "Investigate issue complexity; check for unnecessary context",
                    })

    return anomalies


def _generate_suggested_updates(sessions: list[dict]) -> list[dict]:
    """Generate configuration update suggestions based on cross-session patterns.

    Only suggests when confidence >= 90% across >= 3 sessions.
    Returns list of dicts with keys: suggestion, confidence, evidence.
    """
    suggestions = []
    if len(sessions) < 3:
        return suggestions

    # Check retry pattern across sessions
    high_retry_count = 0
    for trace in sessions:
        sub_steps = [s for s in trace["spans"] if s["kind"] == "sub_step"]
        issue_spans = [s for s in trace["spans"] if s["kind"] == "issue"]
        for issue in issue_spans:
            reviews = [s for s in sub_steps
                       if s["parent_id"] == issue["id"]
                       and s["name"] == "code-review"]
            if len(reviews) > 3:
                high_retry_count += 1
                break  # count session once

    confidence = (high_retry_count / len(sessions)) * 100
    if confidence >= 90:
        suggestions.append({
            "suggestion": "Increase max_retries or improve review criteria",
            "confidence": confidence,
            "evidence": f"High retry count in {high_retry_count}/{len(sessions)} sessions",
        })

    # Check excessive tool usage pattern
    high_tool_count = 0
    for trace in sessions:
        for span in trace["spans"]:
            if span["kind"] == "issue":
                tool_uses = span["attributes"].get("tool_uses")
                if tool_uses and tool_uses > 50:
                    high_tool_count += 1
                    break

    confidence = (high_tool_count / len(sessions)) * 100
    if confidence >= 90:
        suggestions.append({
            "suggestion": "Improve issue descriptions to reduce exploration",
            "confidence": confidence,
            "evidence": f"Excessive tool_uses in {high_tool_count}/{len(sessions)} sessions",
        })

    return suggestions


# --- Commands ---

def cmd_summary(session_id: str, fmt: str = "markdown") -> str:
    """Generate session summary."""
    trace = _load_trace(session_id)
    root = trace["spans"][0]
    step_spans = [s for s in trace["spans"] if s["kind"] == "step"]
    issue_spans = [s for s in trace["spans"] if s["kind"] == "issue"]

    total_tokens = root["attributes"].get("total_tokens")
    total_tool_uses = root["attributes"].get("total_tool_uses")
    duration = root.get("duration_ms")
    meta = trace.get("meta_issue", {})

    anomalies = _detect_anomalies(trace)

    # Try loading other sessions for suggested updates
    index = _load_index()
    other_traces = []
    for entry in index.get("sessions", []):
        if entry["session_id"] != session_id and entry.get("file_available", True):
            try:
                other_traces.append(_load_trace(entry["session_id"]))
            except FileNotFoundError:
                pass
    all_traces = other_traces + [trace]
    suggestions = _generate_suggested_updates(all_traces)

    if fmt == "json":
        return json.dumps({
            "session_id": session_id,
            "duration_ms": duration,
            "total_tokens": total_tokens,
            "total_tool_uses": total_tool_uses,
            "issue_count": len(issue_spans),
            "step_count": len(step_spans),
            "anomalies": anomalies,
            "suggestions": suggestions,
        }, indent=2)

    # Markdown format
    lines = []
    lines.append("## Autopilot Trace Summary")
    lines.append("")
    lines.append(f"**Session**: `{session_id}`")
    if meta.get("number"):
        lines.append(f"**Meta-Issue**: #{meta['number']}")
    lines.append(f"**Duration**: {_format_duration(duration)}")
    lines.append(f"**Total Tokens**: {_format_tokens(total_tokens)}")
    lines.append(f"**Tool Uses**: {_format_tokens(total_tool_uses)}")
    lines.append(f"**Issues**: {len(issue_spans)}")
    lines.append(f"**Status**: {root['status']}")
    lines.append("")

    # Execution Timeline
    lines.append("### Execution Timeline")
    lines.append("")
    lines.append("| Step | Duration | Tokens | Status |")
    lines.append("|------|----------|--------|--------|")
    for span in step_spans:
        tokens = span["attributes"].get("total_tokens")
        lines.append(
            f"| {span['name']} | {_format_duration(span.get('duration_ms'))} "
            f"| {_format_tokens(tokens)} | {span['status']} |"
        )
    lines.append("")

    # Insights
    lines.append("### Insights")
    lines.append("")
    if anomalies:
        for a in anomalies:
            lines.append(f"- **{a['metric']}** | {a['cause']} | {a['action']}")
    else:
        lines.append("No anomalies detected.")
    lines.append("")

    # Suggested Updates
    lines.append("### Suggested Updates")
    lines.append("")
    if suggestions:
        for s in suggestions:
            lines.append(f"- [{s['confidence']:.0f}%] {s['suggestion']} ({s['evidence']})")
    else:
        lines.append("No suggestions (insufficient data or no recurring patterns).")
    lines.append("")

    return "\n".join(lines)


def cmd_compare(session_ids: list[str]) -> str:
    """Compare two sessions side-by-side."""
    if len(session_ids) != 2:
        raise ValueError("Compare requires exactly 2 session IDs")

    traces = [_load_trace(sid) for sid in session_ids]
    roots = [t["spans"][0] for t in traces]

    def _get_metric(root: dict, key: str):
        if key == "duration_ms":
            return root.get("duration_ms")
        return root["attributes"].get(key)

    metrics = [
        ("Duration", "duration_ms", _format_duration),
        ("Total Tokens", "total_tokens", _format_tokens),
        ("Tool Uses", "total_tool_uses", _format_tokens),
    ]

    lines = []
    lines.append("## Session Comparison")
    lines.append("")
    lines.append(f"| Metric | `{session_ids[0]}` | `{session_ids[1]}` | Delta |")
    lines.append("|--------|---|---|-------|")

    for label, key, formatter in metrics:
        v1 = _get_metric(roots[0], key)
        v2 = _get_metric(roots[1], key)
        if v1 is not None and v2 is not None:
            delta = v2 - v1
            pct = (delta / v1 * 100) if v1 != 0 else 0
            delta_str = f"{'+' if delta > 0 else ''}{formatter(delta)} ({pct:+.0f}%)"
        else:
            delta_str = "N/A"
        lines.append(f"| {label} | {formatter(v1)} | {formatter(v2)} | {delta_str} |")

    # Issue counts
    ic1 = len([s for s in traces[0]["spans"] if s["kind"] == "issue"])
    ic2 = len([s for s in traces[1]["spans"] if s["kind"] == "issue"])
    delta = ic2 - ic1
    lines.append(f"| Issues | {ic1} | {ic2} | {'+' if delta > 0 else ''}{delta} |")

    # Review retries
    r1 = len([s for s in traces[0]["spans"] if s["kind"] == "sub_step" and s["name"] == "code-review"])
    r2 = len([s for s in traces[1]["spans"] if s["kind"] == "sub_step" and s["name"] == "code-review"])
    delta = r2 - r1
    lines.append(f"| Review Retries | {r1} | {r2} | {'+' if delta > 0 else ''}{delta} |")

    lines.append("")

    # Notable differences
    lines.append("### Notable Differences")
    lines.append("")
    differences = []
    t1 = _get_metric(roots[0], "total_tokens")
    t2 = _get_metric(roots[1], "total_tokens")
    if t1 and t2 and abs(t2 - t1) / max(t1, 1) > 0.5:
        if t2 > t1:
            differences.append(f"Session `{session_ids[1]}` used {((t2-t1)/t1*100):.0f}% more tokens")
        else:
            differences.append(f"Session `{session_ids[0]}` used {((t1-t2)/t2*100):.0f}% more tokens")

    d1 = _get_metric(roots[0], "duration_ms")
    d2 = _get_metric(roots[1], "duration_ms")
    if d1 and d2 and abs(d2 - d1) / max(d1, 1) > 0.5:
        if d2 > d1:
            differences.append(f"Session `{session_ids[1]}` took {((d2-d1)/d1*100):.0f}% longer")
        else:
            differences.append(f"Session `{session_ids[0]}` took {((d1-d2)/d2*100):.0f}% longer")

    if r2 > r1 + 2:
        differences.append(f"Session `{session_ids[1]}` had {r2-r1} more review retries")
    elif r1 > r2 + 2:
        differences.append(f"Session `{session_ids[0]}` had {r1-r2} more review retries")

    if differences:
        for d in differences:
            lines.append(f"- {d}")
    else:
        lines.append("No notable differences detected.")
    lines.append("")

    return "\n".join(lines)


def cmd_bottleneck(session_id: str, top_n: int = 5) -> str:
    """Find top-N token-consuming spans."""
    trace = _load_trace(session_id)
    spans_with_tokens = []
    for span in trace["spans"]:
        tokens = span["attributes"].get("total_tokens")
        if tokens is not None and span["kind"] != "session":
            spans_with_tokens.append((span, tokens))

    spans_with_tokens.sort(key=lambda x: x[1], reverse=True)
    top = spans_with_tokens[:top_n]

    root_tokens = trace["spans"][0]["attributes"].get("total_tokens")

    lines = []
    lines.append("## Bottleneck Analysis")
    lines.append("")
    lines.append(f"**Session**: `{session_id}`")
    lines.append(f"**Total Tokens**: {_format_tokens(root_tokens)}")
    lines.append("")
    lines.append("| Rank | Span | Kind | Tokens | % of Total | Duration |")
    lines.append("|------|------|------|--------|------------|----------|")

    for i, (span, tokens) in enumerate(top, 1):
        pct = (tokens / root_tokens * 100) if root_tokens else 0
        lines.append(
            f"| {i} | {span['name']} | {span['kind']} "
            f"| {_format_tokens(tokens)} | {pct:.1f}% "
            f"| {_format_duration(span.get('duration_ms'))} |"
        )
    lines.append("")

    return "\n".join(lines)


def cmd_review_stats(session_ids: list[str] | None = None, last_n: int | None = None) -> str:
    """Aggregate review statistics across sessions."""
    if session_ids:
        traces = [_load_trace(sid) for sid in session_ids]
    else:
        index = _load_index()
        available = [e for e in index.get("sessions", []) if e.get("file_available", True)]
        available.sort(key=lambda e: e["started_at_ms"], reverse=True)
        if last_n:
            available = available[:last_n]
        traces = []
        for entry in available:
            try:
                traces.append(_load_trace(entry["session_id"]))
            except FileNotFoundError:
                pass

    if not traces:
        return "No sessions found."

    total_reviews = 0
    total_attempts = 0
    verdict_counts: dict[str, int] = {}

    for trace in traces:
        reviews = [s for s in trace["spans"]
                   if s["kind"] == "sub_step" and s["name"] == "code-review"]
        total_reviews += len(reviews)
        for r in reviews:
            attempt = r["attributes"].get("attempt", 1)
            total_attempts = max(total_attempts, attempt)
            verdict = r["attributes"].get("verdict", "UNKNOWN")
            verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1

    avg_attempts = total_reviews / len(traces) if traces else 0

    lines = []
    lines.append("## Review Statistics")
    lines.append("")
    lines.append(f"**Sessions Analyzed**: {len(traces)}")
    lines.append(f"**Total Reviews**: {total_reviews}")
    lines.append(f"**Avg Reviews/Session**: {avg_attempts:.1f}")
    lines.append("")
    lines.append("### Verdict Distribution")
    lines.append("")
    lines.append("| Verdict | Count | % |")
    lines.append("|---------|-------|---|")
    for verdict, count in sorted(verdict_counts.items(), key=lambda x: -x[1]):
        pct = (count / total_reviews * 100) if total_reviews else 0
        lines.append(f"| {verdict} | {count} | {pct:.0f}% |")
    lines.append("")

    return "\n".join(lines)


def cmd_list(last_n: int | None = None) -> str:
    """List sessions from index."""
    index = _load_index()
    sessions = index.get("sessions", [])
    sessions.sort(key=lambda e: e.get("started_at_ms", 0), reverse=True)
    if last_n:
        sessions = sessions[:last_n]

    if not sessions:
        return "No sessions found."

    lines = []
    lines.append("## Session List")
    lines.append("")
    lines.append("| Session | Meta-Issue | Duration | Tokens | Issues | Status |")
    lines.append("|---------|-----------|----------|--------|--------|--------|")

    for entry in sessions:
        meta = entry.get("meta_issue", {})
        meta_num = meta.get("number", "N/A")
        lines.append(
            f"| `{entry['session_id'][:12]}...` "
            f"| #{meta_num} "
            f"| {_format_duration(entry.get('duration_ms'))} "
            f"| {_format_tokens(entry.get('total_tokens'))} "
            f"| {entry.get('issue_count', 0)} "
            f"| {entry.get('status', 'N/A')} |"
        )
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Autopilot trace report generator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # summary
    p_summary = subparsers.add_parser("summary", help="Generate session summary")
    p_summary.add_argument("--session", required=True)
    p_summary.add_argument("--format", default="markdown", choices=["markdown", "json"])

    # compare
    p_compare = subparsers.add_parser("compare", help="Compare two sessions")
    p_compare.add_argument("--sessions", nargs=2, required=True)

    # bottleneck
    p_bottleneck = subparsers.add_parser("bottleneck", help="Find token bottlenecks")
    p_bottleneck.add_argument("--session", required=True)
    p_bottleneck.add_argument("--top", type=int, default=5)

    # review-stats
    p_review = subparsers.add_parser("review-stats", help="Review statistics")
    p_review.add_argument("--sessions", nargs="*", default=None)
    p_review.add_argument("--last", type=int, default=None)

    # list
    p_list = subparsers.add_parser("list", help="List sessions")
    p_list.add_argument("--last", type=int, default=None)

    args = parser.parse_args()

    try:
        if args.command == "summary":
            print(cmd_summary(args.session, args.format))
        elif args.command == "compare":
            print(cmd_compare(args.sessions))
        elif args.command == "bottleneck":
            print(cmd_bottleneck(args.session, args.top))
        elif args.command == "review-stats":
            print(cmd_review_stats(args.sessions, args.last))
        elif args.command == "list":
            print(cmd_list(args.last))
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
