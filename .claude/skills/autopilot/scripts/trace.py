#!/usr/bin/env python3
"""Tracing engine for autopilot sessions.

Records execution spans (session → step → issue → sub_step) as JSON.
OTEL-compatible schema for future migration.

Usage:
    trace.py init --session-id <SID> [--meta-issue-number <N>] [--meta-issue-url <URL>]
    trace.py start-span --session <SID> --name <NAME> --kind <KIND> [--attr key=val ...]
    trace.py end-span --session <SID> --span-id <ID> [--status ok|error|skipped] [--attr key=val ...]
    trace.py add-event --session <SID> --span-id <ID> --event <NAME> [--attr key=val ...]
    trace.py add-notes --session <SID> --span-id <ID> --notes <TEXT>
    trace.py finalize --session <SID> [--attr key=val ...]
"""

import argparse
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path

VALID_KINDS = {"session", "step", "issue", "sub_step"}
VALID_STATUSES = {"ok", "error", "skipped"}
DEFAULT_RETENTION_COUNT = 50


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


def _trace_path(session_id: str) -> Path:
    return _traces_dir() / f"{session_id}.json"


def _index_path() -> Path:
    return _traces_dir() / "index.json"


def _load_trace(session_id: str) -> dict:
    path = _trace_path(session_id)
    if not path.exists():
        raise FileNotFoundError(f"Trace not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _save_trace(session_id: str, data: dict) -> None:
    path = _trace_path(session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _load_index() -> dict:
    path = _index_path()
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"sessions": []}


def _save_index(index: dict) -> None:
    path = _index_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _now_ms() -> int:
    return int(time.time() * 1000)


def _parse_attrs(attr_list: list[str] | None) -> dict:
    """Parse key=value attribute pairs."""
    attrs = {}
    if not attr_list:
        return attrs
    for item in attr_list:
        if "=" not in item:
            continue
        key, val = item.split("=", 1)
        # Try numeric coercion
        try:
            val = int(val)
        except ValueError:
            try:
                val = float(val)
            except ValueError:
                if val.lower() == "true":
                    val = True
                elif val.lower() == "false":
                    val = False
                elif val.lower() in ("null", "none"):
                    val = None
        attrs[key] = val
    return attrs


def parse_usage_tag(text: str) -> dict:
    """Parse <usage>...</usage> block from Agent tool result.

    Returns dict with keys: total_tokens, tool_uses, duration_ms.
    Missing or unparseable values are None. Never raises.
    """
    import re
    result: dict = {"total_tokens": None, "tool_uses": None, "duration_ms": None}
    match = re.search(r"<usage>(.*?)</usage>", text, re.DOTALL)
    if not match:
        return result
    block = match.group(1)
    for line in block.strip().splitlines():
        line = line.strip()
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip()
        if key in result:
            try:
                result[key] = int(val)
            except ValueError:
                pass  # leave as None
    return result


def _find_span(trace: dict, span_id: str) -> dict | None:
    for span in trace["spans"]:
        if span["id"] == span_id:
            return span
    return None


def _get_retention_count() -> int:
    """Load retention count from autopilot.yaml if available."""
    try:
        yaml_path = _git_root() / ".claude" / "autopilot.yaml"
        if yaml_path.exists():
            content = yaml_path.read_text(encoding="utf-8")
            for line in content.splitlines():
                if "trace_retention_count" in line:
                    _, val = line.split(":", 1)
                    return int(val.strip())
    except (ValueError, OSError):
        pass
    return DEFAULT_RETENTION_COUNT


# --- Commands ---

def cmd_init(session_id: str, meta_issue_number: int | None = None,
             meta_issue_url: str | None = None) -> dict:
    """Initialize a new trace session."""
    path = _trace_path(session_id)
    if path.exists():
        # Idempotent: return existing trace
        return _load_trace(session_id)

    now = _now_ms()
    root_span = {
        "id": str(uuid.uuid4()),
        "parent_id": None,
        "name": session_id,
        "kind": "session",
        "status": "ok",
        "start_time_ms": now,
        "end_time_ms": None,
        "duration_ms": None,
        "attributes": {},
        "events": [],
        "notes": None,
    }

    trace = {
        "session_id": session_id,
        "meta_issue": {
            "number": meta_issue_number,
            "url": meta_issue_url,
        },
        "created_at_ms": now,
        "spans": [root_span],
    }

    _save_trace(session_id, trace)
    return trace


def cmd_start_span(session_id: str, name: str, kind: str,
                   attrs: dict | None = None) -> str:
    """Start a new span. Returns span_id."""
    if kind not in VALID_KINDS:
        raise ValueError(f"Invalid kind '{kind}'. Must be one of: {VALID_KINDS}")

    trace = _load_trace(session_id)

    # Find parent: the last span in the list that hasn't ended (deepest active)
    active = [s for s in trace["spans"] if s.get("end_time_ms") is None]
    if not active:
        raise ValueError("No active parent span found")
    parent = active[-1]

    span_id = str(uuid.uuid4())
    span = {
        "id": span_id,
        "parent_id": parent["id"],
        "name": name,
        "kind": kind,
        "status": "ok",
        "start_time_ms": _now_ms(),
        "end_time_ms": None,
        "duration_ms": None,
        "attributes": attrs or {},
        "events": [],
        "notes": None,
    }

    trace["spans"].append(span)
    _save_trace(session_id, trace)
    return span_id


def cmd_end_span(session_id: str, span_id: str,
                 status: str = "ok", attrs: dict | None = None) -> dict:
    """End a span."""
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{status}'. Must be one of: {VALID_STATUSES}")

    trace = _load_trace(session_id)
    span = _find_span(trace, span_id)
    if span is None:
        raise ValueError(f"Span not found: {span_id}")

    now = _now_ms()
    span["end_time_ms"] = now
    span["duration_ms"] = now - span["start_time_ms"]
    span["status"] = status
    if attrs:
        span["attributes"].update(attrs)

    _save_trace(session_id, trace)
    return span


def cmd_add_event(session_id: str, span_id: str, event_name: str,
                  attrs: dict | None = None) -> dict:
    """Add an event to a span."""
    trace = _load_trace(session_id)
    span = _find_span(trace, span_id)
    if span is None:
        raise ValueError(f"Span not found: {span_id}")

    event = {
        "name": event_name,
        "timestamp_ms": _now_ms(),
        "attributes": attrs or {},
    }
    span["events"].append(event)
    _save_trace(session_id, trace)
    return event


def cmd_add_notes(session_id: str, span_id: str, notes: str) -> dict:
    """Add/replace notes on a span."""
    trace = _load_trace(session_id)
    span = _find_span(trace, span_id)
    if span is None:
        raise ValueError(f"Span not found: {span_id}")

    span["notes"] = notes
    _save_trace(session_id, trace)
    return span


def cmd_finalize(session_id: str, attrs: dict | None = None) -> dict:
    """Finalize a trace session: close root span, update index, apply retention."""
    trace = _load_trace(session_id)

    # Close any unclosed spans (root last)
    now = _now_ms()
    unclosed = [s for s in trace["spans"] if s.get("end_time_ms") is None]
    # Sort by depth (children first): reverse start_time order
    unclosed.sort(key=lambda s: s["start_time_ms"], reverse=True)
    for span in unclosed:
        span["end_time_ms"] = now
        span["duration_ms"] = now - span["start_time_ms"]

    # Apply attrs to root span
    root = trace["spans"][0]
    if attrs:
        root["attributes"].update(attrs)

    _save_trace(session_id, trace)

    # Update index
    index = _load_index()

    # Aggregate metrics from spans
    total_tokens = root["attributes"].get("total_tokens")
    total_tool_uses = root["attributes"].get("total_tool_uses")
    issue_count = len([s for s in trace["spans"] if s["kind"] == "issue"])

    session_entry = {
        "session_id": session_id,
        "meta_issue": trace.get("meta_issue", {"number": None, "url": None}),
        "started_at_ms": root["start_time_ms"],
        "ended_at_ms": root["end_time_ms"],
        "duration_ms": root["duration_ms"],
        "total_tokens": total_tokens,
        "total_tool_uses": total_tool_uses,
        "issue_count": issue_count,
        "status": root["status"],
        "complexity": root["attributes"].get("complexity"),
        "provider": root["attributes"].get("provider"),
        "file_available": True,
    }

    # Update or append
    existing_idx = None
    for i, entry in enumerate(index["sessions"]):
        if entry["session_id"] == session_id:
            existing_idx = i
            break
    if existing_idx is not None:
        index["sessions"][existing_idx] = session_entry
    else:
        index["sessions"].append(session_entry)

    # Apply retention policy
    retention = _get_retention_count()
    available = [e for e in index["sessions"] if e.get("file_available", True)]
    if len(available) > retention:
        # Sort by started_at_ms, remove oldest
        available.sort(key=lambda e: e["started_at_ms"])
        to_remove = available[:len(available) - retention]
        for entry in to_remove:
            trace_file = _trace_path(entry["session_id"])
            if trace_file.exists():
                trace_file.unlink()
            entry["file_available"] = False

    _save_index(index)
    return trace


def main() -> int:
    parser = argparse.ArgumentParser(description="Autopilot trace manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # init
    p_init = subparsers.add_parser("init", help="Initialize trace session")
    p_init.add_argument("--session-id", required=True)
    p_init.add_argument("--meta-issue-number", type=int, default=None)
    p_init.add_argument("--meta-issue-url", default=None)

    # start-span
    p_start = subparsers.add_parser("start-span", help="Start a new span")
    p_start.add_argument("--session", required=True)
    p_start.add_argument("--name", required=True)
    p_start.add_argument("--kind", required=True, choices=sorted(VALID_KINDS))
    p_start.add_argument("--attr", action="append", default=[])

    # end-span
    p_end = subparsers.add_parser("end-span", help="End a span")
    p_end.add_argument("--session", required=True)
    p_end.add_argument("--span-id", required=True)
    p_end.add_argument("--status", default="ok", choices=sorted(VALID_STATUSES))
    p_end.add_argument("--attr", action="append", default=[])

    # add-event
    p_event = subparsers.add_parser("add-event", help="Add event to span")
    p_event.add_argument("--session", required=True)
    p_event.add_argument("--span-id", required=True)
    p_event.add_argument("--event", required=True)
    p_event.add_argument("--attr", action="append", default=[])

    # add-notes
    p_notes = subparsers.add_parser("add-notes", help="Add notes to span")
    p_notes.add_argument("--session", required=True)
    p_notes.add_argument("--span-id", required=True)
    p_notes.add_argument("--notes", required=True)

    # finalize
    p_final = subparsers.add_parser("finalize", help="Finalize trace session")
    p_final.add_argument("--session", required=True)
    p_final.add_argument("--attr", action="append", default=[])

    args = parser.parse_args()

    try:
        if args.command == "init":
            result = cmd_init(args.session_id, args.meta_issue_number, args.meta_issue_url)
            print(json.dumps(result, indent=2, ensure_ascii=False))

        elif args.command == "start-span":
            attrs = _parse_attrs(args.attr)
            span_id = cmd_start_span(args.session, args.name, args.kind, attrs)
            print(span_id)

        elif args.command == "end-span":
            attrs = _parse_attrs(args.attr)
            result = cmd_end_span(args.session, args.span_id, args.status, attrs)
            print(json.dumps(result, indent=2, ensure_ascii=False))

        elif args.command == "add-event":
            attrs = _parse_attrs(args.attr)
            result = cmd_add_event(args.session, args.span_id, args.event, attrs)
            print(json.dumps(result, indent=2, ensure_ascii=False))

        elif args.command == "add-notes":
            result = cmd_add_notes(args.session, args.span_id, args.notes)
            print(json.dumps(result, indent=2, ensure_ascii=False))

        elif args.command == "finalize":
            attrs = _parse_attrs(args.attr)
            result = cmd_finalize(args.session, attrs)
            print(json.dumps(result, indent=2, ensure_ascii=False))

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
