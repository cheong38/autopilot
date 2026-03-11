#!/usr/bin/env python3
"""State management CRUD for the autopilot skill.

Manages a JSON state file at <git-root>/.claude/autopilot-state.json.
Used by the autopilot orchestrator to persist session state across
context compactions and resume scenarios.

Usage:
    autopilot-state.py create --meta-issue <N> --meta-url <URL> --provider <p> --source <src>
    autopilot-state.py read
    autopilot-state.py update --field <key> --value <val>
    autopilot-state.py add-requirement --id <R-NNN> --text <text> [--confidence <N>] \
        [--verification-method <method>] [--verification-status <status>]
    autopilot-state.py add-issue --id <N> --url <URL> --type <type> --title <title> \
        [--requirement-ids <r1,r2>] [--verification-methods <m1,m2>]
    autopilot-state.py update-issue --id <N> [--status <status>] [--verified <bool>]
    autopilot-state.py query [--ready] [--open] [--verified] [--unverified] [--type <type>]
    autopilot-state.py query --field <key>
    autopilot-state.py add-lesson --step <step> --category <cat> --summary <text> \
        [--detail <text>] [--evidence <refs>]
"""

import argparse
import json
import subprocess
import sys
import uuid
from pathlib import Path

# Valid current_step values for the autopilot orchestrator
VALID_STEPS = {
    "META-ISSUE", "CLASSIFY", "WHY-CONTEXT",
    "INGEST", "VERIFY-PLAN", "UL-CHECK", "CLARIFY",
    "DECOMPOSE", "CONFIRM", "CREATE", "RECONCILE",
    "DAG-BUILD", "DAG-CONFIRM", "VERIFY-INFRA-CHECK",
    "IMPL-LOOP", "PRE-DEPLOY-VERIFY", "DEPLOY-DETECT", "DEPLOY-VERIFY",
    "TRIAGE", "CHECKPOINT", "FOLLOWUP", "FINAL-VERIFY", "REPORT",
}

# Valid current_step values for the simple path
VALID_SIMPLE_STEPS = {
    "CLASSIFY", "WHY-CONTEXT", "ISSUE", "IMPL", "VERIFY", "REPORT",
}

# Ordered step sequences for transition validation
COMPLEX_STEP_ORDER = [
    "META-ISSUE", "CLASSIFY", "WHY-CONTEXT",
    "INGEST", "VERIFY-PLAN", "UL-CHECK", "CLARIFY",
    "DECOMPOSE", "CONFIRM", "CREATE", "RECONCILE",
    "DAG-BUILD", "DAG-CONFIRM", "VERIFY-INFRA-CHECK",
    "IMPL-LOOP", "PRE-DEPLOY-VERIFY", "DEPLOY-DETECT", "DEPLOY-VERIFY",
    "TRIAGE", "CHECKPOINT", "FOLLOWUP", "FINAL-VERIFY", "REPORT",
]
SIMPLE_STEP_ORDER = [
    "CLASSIFY", "WHY-CONTEXT", "ISSUE", "IMPL", "VERIFY", "REPORT",
]
LOOP_BACK_ALLOWED = {"IMPL-LOOP", "FOLLOWUP", "IMPL"}


def _validate_step_transition(current: str, target: str, complexity: str | None) -> None:
    """Reject backward step jumps (except allowed loop-backs)."""
    order = SIMPLE_STEP_ORDER if complexity == "simple" else COMPLEX_STEP_ORDER
    if current not in order or target not in order:
        return  # Unknown steps validated elsewhere by name check
    cur_idx, tgt_idx = order.index(current), order.index(target)
    if tgt_idx >= cur_idx:
        return  # Forward or same — always allowed
    if target in LOOP_BACK_ALLOWED:
        return  # Allowed loop-back targets
    raise ValueError(
        f"Invalid step transition: {current!r} → {target!r}. "
        f"Forward only, or loop back to {sorted(LOOP_BACK_ALLOWED)}."
    )


def _git_root() -> Path:
    """Resolve the git repository root."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return Path(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return Path.cwd()


def state_file_path() -> Path:
    """Return the canonical state file path."""
    return _git_root() / ".claude" / "autopilot-state.json"


def _load(path: Path) -> dict:
    """Load state from file. Raises FileNotFoundError if missing."""
    if not path.exists():
        raise FileNotFoundError(f"No autopilot session found at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _save(path: Path, state: dict) -> None:
    """Save state to file, creating parent dirs if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def create_state(meta_issue: int, meta_url: str, provider: str, source: str) -> dict:
    """Create a new autopilot state file."""
    path = state_file_path()
    if path.exists():
        existing = _load(path)
        if existing.get("status") == "in_progress":
            raise FileExistsError(f"Active session exists: {path}")
        # Non-active session (complete/aborted) — overwrite allowed

    state = {
        "session_id": str(uuid.uuid4()),
        "state_file_path": str(path),
        "git_root": str(_git_root()),
        "meta_issue": {"number": meta_issue, "url": meta_url},
        "provider": provider,
        "source": source,
        "status": "in_progress",
        "current_step": "META-ISSUE",
        "current_issue": None,
        "followup_round": 0,
        "requirements": [],
        "issues": [],
        "lessons": [],
        "complexity": None,
        "dag_file": None,
        "trace_session_id": None,
    }
    _save(path, state)

    # Remove gate lock (Step 0 complete — open the gate)
    lock = path.parent / "autopilot-gate.lock"
    lock.unlink(missing_ok=True)

    return state


def read_state() -> dict:
    """Read and return the current state."""
    return _load(state_file_path())


def update_field(field: str, value: str) -> dict:
    """Update a top-level field in the state."""
    path = state_file_path()
    state = _load(path)

    # Validate current_step against known steps
    if field == "current_step":
        all_steps = VALID_STEPS | VALID_SIMPLE_STEPS
        if value not in all_steps:
            raise ValueError(f"Invalid step: {value!r}. Valid: {sorted(all_steps)}")
        _validate_step_transition(
            current=state.get("current_step", "META-ISSUE"),
            target=value,
            complexity=state.get("complexity"),
        )

    # Type coercion for known fields
    coerced: str | int | bool | None = value
    if field in ("current_issue", "followup_round"):
        try:
            coerced = int(value)
        except ValueError:
            if value.lower() in ("null", "none"):
                coerced = None
    elif value.lower() == "true":
        coerced = True
    elif value.lower() == "false":
        coerced = False
    elif value.lower() in ("null", "none"):
        coerced = None

    state[field] = coerced
    _save(path, state)
    return state


def add_requirement(
    req_id: str, text: str, confidence: int = 0,
    verification_method: str = "", verification_status: str = "pending",
) -> dict:
    """Add a requirement to the state."""
    path = state_file_path()
    state = _load(path)

    req = {
        "id": req_id,
        "text": text,
        "confidence": confidence,
        "verification_method": verification_method,
        "verification_status": verification_status,
    }
    state["requirements"].append(req)
    _save(path, state)
    return state


def add_issue(
    issue_id: int, url: str, issue_type: str, title: str,
    requirement_ids: list[str] | None = None,
    verification_methods: list[str] | None = None,
) -> dict:
    """Add an issue to the state."""
    path = state_file_path()
    state = _load(path)

    issue = {
        "id": issue_id,
        "url": url,
        "type": issue_type,
        "title": title,
        "status": "open",
        "verified": False,
        "requirement_ids": requirement_ids or [],
        "verification_methods": verification_methods or [],
    }
    state["issues"].append(issue)
    _save(path, state)
    return state


def update_issue(issue_id: int, status: str | None = None, verified: bool | None = None) -> dict:
    """Update an issue's status or verified flag."""
    path = state_file_path()
    state = _load(path)

    for issue in state["issues"]:
        if issue["id"] == issue_id:
            if status is not None:
                issue["status"] = status
            if verified is not None:
                issue["verified"] = verified
            break
    else:
        raise ValueError(f"Issue {issue_id} not found in state")

    _save(path, state)
    return state


VALID_LESSON_CATEGORIES = {"verification", "diagnosis", "scope", "protocol"}


def add_lesson(
    step: str, category: str, summary: str,
    detail: str = "", evidence: str = "",
) -> tuple[dict, bool]:
    """Add a lesson learned to the state. Returns (state, added).

    Returns (state, False) if a lesson with the same summary already exists.
    """
    if category not in VALID_LESSON_CATEGORIES:
        raise ValueError(
            f"Invalid category: {category!r}. "
            f"Valid: {sorted(VALID_LESSON_CATEGORIES)}"
        )

    path = state_file_path()
    state = _load(path)

    lessons = state.setdefault("lessons", [])

    # Deduplicate by summary
    for existing in lessons:
        if existing["summary"] == summary:
            return state, False

    lesson = {
        "step": step,
        "category": category,
        "summary": summary,
        "detail": detail,
        "evidence": evidence,
    }
    lessons.append(lesson)
    _save(path, state)
    return state, True


def query_field(field: str):
    """Query an arbitrary top-level field from state."""
    state = _load(state_file_path())
    if field not in state:
        raise ValueError(f"Field {field!r} not found in state")
    return state[field]


def query_issues(
    ready: bool = False, open_only: bool = False,
    verified: bool = False, unverified: bool = False,
    issue_type: str | None = None,
) -> list[dict]:
    """Query issues by filter criteria."""
    state = _load(state_file_path())
    issues = state["issues"]

    if open_only or ready:
        issues = [i for i in issues if i["status"] == "open"]
    if verified:
        issues = [i for i in issues if i["verified"]]
    if unverified:
        issues = [i for i in issues if not i["verified"]]
    if issue_type is not None:
        issues = [i for i in issues if i.get("type") == issue_type]

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Autopilot state manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create
    p_create = subparsers.add_parser("create", help="Create new state")
    p_create.add_argument("--meta-issue", type=int, required=True)
    p_create.add_argument("--meta-url", required=True)
    p_create.add_argument("--provider", required=True, choices=["github", "gitlab", "jira"])
    p_create.add_argument("--source", required=True)

    # read
    subparsers.add_parser("read", help="Read current state")

    # update
    p_update = subparsers.add_parser("update", help="Update a field")
    p_update.add_argument("--field", required=True)
    p_update.add_argument("--value", required=True)

    # add-requirement
    p_req = subparsers.add_parser("add-requirement", help="Add a requirement")
    p_req.add_argument("--id", required=True, dest="req_id")
    p_req.add_argument("--text", required=True)
    p_req.add_argument("--confidence", type=int, default=0)
    p_req.add_argument("--verification-method", default="")
    p_req.add_argument("--verification-status", default="pending")

    # add-issue
    p_issue = subparsers.add_parser("add-issue", help="Add an issue")
    p_issue.add_argument("--id", type=int, required=True, dest="issue_id")
    p_issue.add_argument("--url", required=True)
    p_issue.add_argument("--type", required=True, dest="issue_type")
    p_issue.add_argument("--title", required=True)
    p_issue.add_argument("--requirement-ids", default="")
    p_issue.add_argument("--verification-methods", default="")

    # update-issue
    p_upd_issue = subparsers.add_parser("update-issue", help="Update an issue")
    p_upd_issue.add_argument("--id", type=int, required=True, dest="issue_id")
    p_upd_issue.add_argument("--status", default=None)
    p_upd_issue.add_argument("--verified", default=None, choices=["true", "false"])

    # add-lesson
    p_lesson = subparsers.add_parser("add-lesson", help="Add a lesson learned")
    p_lesson.add_argument("--step", required=True)
    p_lesson.add_argument("--category", required=True,
                          choices=sorted(VALID_LESSON_CATEGORIES))
    p_lesson.add_argument("--summary", required=True)
    p_lesson.add_argument("--detail", default="")
    p_lesson.add_argument("--evidence", default="")

    # query
    p_query = subparsers.add_parser("query", help="Query issues or state fields")
    p_query.add_argument("--field", default=None, help="Query a top-level state field (e.g., lessons)")
    p_query.add_argument("--ready", action="store_true")
    p_query.add_argument("--open", action="store_true", dest="open_only")
    p_query.add_argument("--verified", action="store_true")
    p_query.add_argument("--unverified", action="store_true")
    p_query.add_argument("--type", default=None, dest="issue_type")

    args = parser.parse_args()

    try:
        if args.command == "create":
            result = create_state(args.meta_issue, args.meta_url, args.provider, args.source)
            print(json.dumps(result, indent=2, ensure_ascii=False))

        elif args.command == "read":
            result = read_state()
            print(json.dumps(result, indent=2, ensure_ascii=False))

        elif args.command == "update":
            result = update_field(args.field, args.value)
            print(json.dumps(result, indent=2, ensure_ascii=False))

        elif args.command == "add-requirement":
            result = add_requirement(
                args.req_id, args.text, args.confidence,
                args.verification_method, args.verification_status,
            )
            print(f"Added requirement {args.req_id}")

        elif args.command == "add-issue":
            req_ids = [r.strip() for r in args.requirement_ids.split(",") if r.strip()]
            ver_methods = [m.strip() for m in args.verification_methods.split(",") if m.strip()]
            result = add_issue(
                args.issue_id, args.url, args.issue_type, args.title,
                req_ids, ver_methods,
            )
            print(f"Added issue #{args.issue_id}")

        elif args.command == "update-issue":
            verified = None
            if args.verified is not None:
                verified = args.verified.lower() == "true"
            result = update_issue(args.issue_id, args.status, verified)
            print(f"Updated issue #{args.issue_id}")

        elif args.command == "add-lesson":
            _, added = add_lesson(
                args.step, args.category, args.summary,
                args.detail, args.evidence,
            )
            if added:
                print(f"Added lesson: {args.summary}")
            else:
                print(f"Skipped (duplicate): {args.summary}")

        elif args.command == "query":
            if args.field:
                result = query_field(args.field)
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                issues = query_issues(args.ready, args.open_only, args.verified, args.unverified, args.issue_type)
                print(json.dumps(issues, indent=2, ensure_ascii=False))

    except FileNotFoundError as e:
        print(json.dumps({"error": str(e), "error_type": "FileNotFoundError"}))
        return 1
    except FileExistsError as e:
        print(json.dumps({"error": str(e), "error_type": "FileExistsError"}))
        return 1
    except ValueError as e:
        print(json.dumps({"error": str(e), "error_type": "ValueError"}))
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
