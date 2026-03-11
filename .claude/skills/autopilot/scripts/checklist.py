#!/usr/bin/env python3
"""Checklist CRUD for the autopilot skill.

Extends the shared checklist pattern from issue/issue-impl skills.
Manages markdown checklist files at /tmp/skill-checklists/.

Usage:
    checklist.py create autopilot <meta-issue> [--title <title>]
    checklist.py create autopilot-simple <meta-issue> [--title <title>]
    checklist.py update autopilot <meta-issue> <step> <status>
    checklist.py update autopilot-simple <meta-issue> <step> <status>
    checklist.py check-step autopilot <meta-issue> <step_num>
    checklist.py ready-subtasks autopilot <meta-issue> <step_num>
    checklist.py read autopilot <meta-issue>
    checklist.py read autopilot-simple <meta-issue>
"""

import argparse
import hashlib
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

CHECKLIST_DIR = Path("/tmp/skill-checklists")

AUTOPILOT_STEPS = [
    "META-ISSUE (Step 0)",
    "INGEST (Step 1)",
    "VERIFY-PLAN (Step 1.5)",
    "UL-CHECK (Step 2)",
    "CLARIFY (Step 2.5)",
    "DECOMPOSE (Step 3)",
    "CONFIRM (Step 3.5)",
    "CREATE (Step 4)",
    "RECONCILE (Step 4.5)",
    "DAG-BUILD (Step 5)",
    "DAG-CONFIRM (Step 5.5)",
    "VERIFY-INFRA-CHECK (Step 5.7)",
    "IMPL-LOOP (Step 6)",
    "PRE-DEPLOY-VERIFY (Step 6.5)",
    "DEPLOY-DETECT (Step 6.6)",
    "DEPLOY-VERIFY (Step 6.7)",
    "TRIAGE (Step 7)",
    "CHECKPOINT (Step 8)",
    "FOLLOWUP (Step 10)",
    "FINAL-VERIFY (Step 11)",
    "REPORT (Step 12)",
]

AUTOPILOT_SIMPLE_STEPS = [
    "CLASSIFY (Step 0.3)",
    "WHY-CONTEXT (Step 0.5)",
    "ISSUE (Step S1)",
    "IMPL (Step S2)",
    "VERIFY (Step S3)",
    "REPORT (Step S4)",
]

AUTOPILOT_SUBTASKS = {
    1: [  # META-ISSUE (Step 0)
        {"id": "1.1", "name": "Detect provider", "deps": []},
        {"id": "1.2", "name": "Ensure labels exist", "deps": ["1.1"]},
        {"id": "1.3", "name": "Create meta-issue", "deps": ["1.2"]},
        {"id": "1.4", "name": "Acquire session lock", "deps": ["1.3"]},
        {"id": "1.5", "name": "Initialize checklist", "deps": ["1.3"]},
        {"id": "1.6", "name": "Store in state", "deps": ["1.3"]},
        {"id": "1.7", "name": "Initialize tracing", "deps": ["1.3"]},
    ],
    2: [  # INGEST (Step 1)
        {"id": "2.1", "name": "Detect input format", "deps": []},
        {"id": "2.2", "name": "Extract requirements", "deps": ["2.1"]},
        {"id": "2.3", "name": "Self-review", "deps": ["2.2"]},
    ],
    3: [  # VERIFY-PLAN (Step 1.5)
        {"id": "3.1", "name": "Classify verification per requirement", "deps": []},
        {"id": "3.2", "name": "Resolve unclear (UIP-18)", "deps": ["3.1"]},
        {"id": "3.3", "name": "Self-review", "deps": ["3.2"]},
    ],
    4: [  # UL-CHECK (Step 2)
        {"id": "4.1", "name": "Sync DAG", "deps": []},
        {"id": "4.2", "name": "Load UL dictionary", "deps": ["4.1"]},
        {"id": "4.3", "name": "Scan for new terms", "deps": ["4.1"]},
        {"id": "4.4", "name": "Register new terms (UIP-19)", "deps": ["4.2", "4.3"]},
        {"id": "4.5", "name": "Self-review", "deps": ["4.4"]},
    ],
    5: [  # CLARIFY (Step 2.5)
        {"id": "5.1", "name": "Identify low-confidence requirements", "deps": []},
        {"id": "5.2", "name": "Ask UIP-17 per requirement", "deps": ["5.1"]},
        {"id": "5.3", "name": "Confirm all >= threshold", "deps": ["5.2"]},
    ],
    6: [  # DECOMPOSE (Step 3)
        {"id": "6.1", "name": "Map requirements to issues", "deps": []},
        {"id": "6.2", "name": "Identify dependencies", "deps": ["6.1"]},
        {"id": "6.3", "name": "Self-review", "deps": ["6.2"]},
    ],
    7: [  # CONFIRM (Step 3.5)
        {"id": "7.1", "name": "Evaluate confidence", "deps": []},
        {"id": "7.2", "name": "Present UIP-20 if needed", "deps": ["7.1"]},
    ],
    8: [  # CREATE (Step 4)
        {"id": "8.1", "name": "Invoke /issue per spec", "deps": []},
        {"id": "8.2", "name": "Store in state", "deps": ["8.1"]},
        {"id": "8.3", "name": "Include context", "deps": ["8.1"]},
        {"id": "8.4", "name": "Self-review", "deps": ["8.2", "8.3"]},
    ],
    9: [  # RECONCILE (Step 4.5)
        {"id": "9.1", "name": "Check all issues in DAG", "deps": []},
        {"id": "9.2", "name": "Register missing nodes", "deps": ["9.1"]},
    ],
    10: [  # DAG-BUILD (Step 5)
        {"id": "10.1", "name": "Add dependency edges", "deps": []},
        {"id": "10.2", "name": "Validate no cycles", "deps": ["10.1"]},
        {"id": "10.3", "name": "Push DAG", "deps": ["10.2"]},
    ],
    11: [  # DAG-CONFIRM (Step 5.5)
        {"id": "11.1", "name": "Evaluate threshold", "deps": []},
        {"id": "11.2", "name": "Present UIP-21 if needed", "deps": ["11.1"]},
    ],
    12: [  # VERIFY-INFRA-CHECK (Step 5.7)
        {"id": "12.1", "name": "Check verification infra", "deps": []},
        {"id": "12.2", "name": "Create prereq issues if missing", "deps": ["12.1"]},
    ],
    13: [  # IMPL-LOOP (Step 6)
        {"id": "13.1", "name": "Query ready issues", "deps": []},
        {"id": "13.2", "name": "Select next issue", "deps": ["13.1"]},
        {"id": "13.3", "name": "Execute /issue-impl", "deps": ["13.2"]},
        {"id": "13.4", "name": "Self-review", "deps": ["13.3"]},
        {"id": "13.5", "name": "Proceed to verify", "deps": ["13.4"]},
    ],
    14: [  # PRE-DEPLOY-VERIFY (Step 6.5)
        {"id": "14.1", "name": "Run verification (priority chain)", "deps": []},
        {"id": "14.2", "name": "Handle credentials (UIP-22)", "deps": ["14.1"]},
        {"id": "14.3", "name": "Mark result", "deps": ["14.2"]},
    ],
    15: [  # DEPLOY-DETECT (Step 6.6)
        {"id": "15.1", "name": "Detect deployment indicators", "deps": []},
        {"id": "15.2", "name": "Extract deploy URL", "deps": ["15.1"]},
        {"id": "15.3", "name": "Ask user if not detected (UIP-27)", "deps": ["15.2"]},
    ],
    16: [  # DEPLOY-VERIFY (Step 6.7)
        {"id": "16.1", "name": "Test data setup (6.7.1)", "deps": []},
        {"id": "16.2", "name": "Verify attempt — fallback chain (6.7.2)", "deps": ["16.1"]},
        {"id": "16.3", "name": "Auth handoff if needed (6.7.3)", "deps": ["16.2"]},
        {"id": "16.4", "name": "Cleanup test data (6.7.4)", "deps": ["16.3"]},
    ],
    17: [  # TRIAGE (Step 7)
        {"id": "17.1", "name": "Check dependents", "deps": []},
        {"id": "17.2", "name": "Classify blocking vs non-blocking", "deps": ["17.1"]},
        {"id": "17.3", "name": "Create bug / defer", "deps": ["17.2"]},
    ],
    18: [  # CHECKPOINT (Step 8)
        {"id": "18.1", "name": "Update DAG node status", "deps": []},
        {"id": "18.2", "name": "Query next ready", "deps": ["18.1"]},
        {"id": "18.3", "name": "Save state", "deps": ["18.2"]},
        {"id": "18.4", "name": "Post progress comment", "deps": ["18.2"]},
        {"id": "18.5", "name": "Push DAG", "deps": ["18.3", "18.4"]},
    ],
    19: [  # FOLLOWUP (Step 10)
        {"id": "19.1", "name": "Collect follow-ups", "deps": []},
        {"id": "19.2", "name": "Create new issues", "deps": ["19.1"]},
        {"id": "19.3", "name": "Re-enter IMPL-LOOP", "deps": ["19.2"]},
    ],
    20: [  # FINAL-VERIFY (Step 11)
        {"id": "20.1", "name": "Full test suite", "deps": []},
        {"id": "20.2", "name": "E2E / integration tests", "deps": ["20.1"]},
        {"id": "20.3", "name": "Handle failures", "deps": ["20.2"]},
    ],
    21: [  # REPORT (Step 12)
        {"id": "21.1", "name": "Update session status", "deps": []},
        {"id": "21.2", "name": "Finalize tracing", "deps": ["21.1"]},
        {"id": "21.3", "name": "Post final report", "deps": ["21.2"]},
        {"id": "21.4", "name": "Close meta-issue", "deps": ["21.3"]},
        {"id": "21.5", "name": "Release session lock", "deps": ["21.4"]},
    ],
}

AUTOPILOT_SIMPLE_SUBTASKS = {
    1: [  # CLASSIFY (Step 0.3)
        {"id": "1.1", "name": "Evaluate simple criteria", "deps": []},
        {"id": "1.2", "name": "Update state complexity", "deps": ["1.1"]},
    ],
    2: [  # WHY-CONTEXT (Step 0.5)
        {"id": "2.1", "name": "Explore project context", "deps": []},
        {"id": "2.2", "name": "Extract user_problem and decision_context", "deps": ["2.1"]},
        {"id": "2.3", "name": "Ask UIP-27/28 if needed", "deps": ["2.2"]},
        {"id": "2.4", "name": "Generate narrative", "deps": ["2.3"]},
        {"id": "2.5", "name": "Propagate context", "deps": ["2.4"]},
    ],
    3: [  # ISSUE (Step S1)
        {"id": "3.1", "name": "Invoke /issue", "deps": []},
        {"id": "3.2", "name": "Store in state", "deps": ["3.1"]},
        {"id": "3.3", "name": "Include context", "deps": ["3.1"]},
    ],
    4: [  # IMPL (Step S2)
        {"id": "4.1", "name": "Execute /issue-impl", "deps": []},
        {"id": "4.2", "name": "Wait for completion", "deps": ["4.1"]},
    ],
    5: [  # VERIFY (Step S3)
        {"id": "5.1", "name": "Run verification", "deps": []},
        {"id": "5.2", "name": "Handle pass/fail", "deps": ["5.1"]},
    ],
    6: [  # REPORT (Step S4)
        {"id": "6.1", "name": "Update session status", "deps": []},
        {"id": "6.2", "name": "Post summary", "deps": ["6.1"]},
        {"id": "6.3", "name": "Close meta-issue", "deps": ["6.2"]},
        {"id": "6.4", "name": "Release session lock", "deps": ["6.3"]},
    ],
}

STEPS = {
    "autopilot": AUTOPILOT_STEPS,
    "autopilot-simple": AUTOPILOT_SIMPLE_STEPS,
}

SUBTASKS = {
    "autopilot": AUTOPILOT_SUBTASKS,
    "autopilot-simple": AUTOPILOT_SIMPLE_SUBTASKS,
}


def _repo_hash() -> str:
    """Short hash of git root path for repo-scoped checklist isolation."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        root = result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        root = str(Path.cwd())
    return hashlib.sha256(root.encode()).hexdigest()[:8]


def checklist_path(skill: str, issue: str) -> Path:
    repo_hash = _repo_hash()
    return CHECKLIST_DIR / f"{skill}-{issue}-{repo_hash}.md"


def create_checklist(skill: str, issue: str, title: str = "") -> str:
    CHECKLIST_DIR.mkdir(parents=True, exist_ok=True)
    path = checklist_path(skill, issue)
    if path.exists():
        return f"Checklist already exists: {path}"

    steps = STEPS[skill]
    subtasks = SUBTASKS.get(skill, {})
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = []
    for i, s in enumerate(steps):
        step_num = i + 1
        lines.append(f"- [ ] {step_num}. {s}")
        if step_num in subtasks:
            for sub in subtasks[step_num]:
                lines.append(f"  - [ ] {sub['id']} {sub['name']}")

    steps_md = "\n".join(lines)
    label = "Autopilot Simple" if skill == "autopilot-simple" else "Autopilot"

    content = f"""# {label} Checklist: #{issue}

Created: {now}
Meta-Issue: #{issue}
Title: {title or "(untitled)"}
Status: IN_PROGRESS

## Progress
{steps_md}
"""
    path.write_text(content)
    return f"Created: {path}"


def _is_subtask_id(step: str) -> bool:
    """Check if step is a sub-task ID like '1.3' (digit.digit)."""
    return bool(re.match(r"^\d+\.\d+$", step))


def update_step(skill: str, issue: str, step: str, status: str) -> str:
    path = checklist_path(skill, issue)
    if not path.exists():
        return f"Checklist not found: {path}"

    content = path.read_text()

    if _is_subtask_id(step):
        # Sub-task update: match "  - [ ] 1.3 " (indented)
        escaped = re.escape(step)
        if status == "done":
            content = re.sub(
                rf"  - \[[ !]\] {escaped} ",
                f"  - [x] {step} ",
                content,
            )
        elif status == "failed":
            content = re.sub(
                rf"  - \[[ x]\] {escaped} ",
                f"  - [!] {step} ",
                content,
            )
        elif status == "pending":
            content = re.sub(
                rf"  - \[[x!]\] {escaped} ",
                f"  - [ ] {step} ",
                content,
            )
    else:
        step_num = step if step.isdigit() else None
        if status == "done":
            if step_num:
                content = re.sub(
                    rf"^- \[[ !]\] {step_num}\.",
                    f"- [x] {step_num}.",
                    content,
                    flags=re.MULTILINE,
                )
            else:
                content = content.replace(f"- [ ] {step}", f"- [x] {step}")
                content = content.replace(f"- [!] {step}", f"- [x] {step}")
        elif status == "failed":
            if step_num:
                content = re.sub(
                    rf"^- \[[ x]\] {step_num}\.",
                    f"- [!] {step_num}.",
                    content,
                    flags=re.MULTILINE,
                )
            else:
                content = content.replace(f"- [ ] {step}", f"- [!] {step}")
                content = content.replace(f"- [x] {step}", f"- [!] {step}")
        elif status == "pending":
            if step_num:
                content = re.sub(
                    rf"^- \[[x!]\] {step_num}\.",
                    f"- [ ] {step_num}.",
                    content,
                    flags=re.MULTILINE,
                )
            else:
                content = content.replace(f"- [x] {step}", f"- [ ] {step}")
                content = content.replace(f"- [!] {step}", f"- [ ] {step}")

    path.write_text(content)
    return f"Updated step {step} → {status}"


def check_step(skill: str, issue: str, step_num: int) -> str:
    """Check if all sub-tasks for a step are complete.

    Returns 'COMPLETE' if all sub-tasks are [x], otherwise
    'INCOMPLETE: N/M done'.
    """
    path = checklist_path(skill, issue)
    if not path.exists():
        return f"Checklist not found: {path}"

    subtasks = SUBTASKS.get(skill, {})
    if step_num not in subtasks:
        return f"No sub-tasks defined for step {step_num}"

    content = path.read_text()
    step_subtasks = subtasks[step_num]
    total = len(step_subtasks)
    done = 0
    failed = 0

    for sub in step_subtasks:
        sub_id = sub["id"]
        escaped = re.escape(sub_id)
        if re.search(rf"  - \[x\] {escaped} ", content):
            done += 1
        elif re.search(rf"  - \[!\] {escaped} ", content):
            failed += 1

    if done == total:
        return "COMPLETE"
    if failed:
        return f"INCOMPLETE: {done}/{total} done, {failed} failed"
    return f"INCOMPLETE: {done}/{total} done"


def read_checklist(skill: str, issue: str) -> str:
    path = checklist_path(skill, issue)
    if not path.exists():
        return f"Checklist not found: {path}"
    return path.read_text()


def ready_subtasks(skill: str, issue: str, step_num: int) -> list:
    """Return IDs of sub-tasks whose deps are all done and that are still pending.

    A sub-task is "ready" when:
    - It is pending ([ ])
    - All its deps are done ([x])

    Failed ([!]) deps do NOT satisfy the dependency — downstream stays blocked.
    Returns empty list if checklist doesn't exist or step_num is undefined.
    """
    path = checklist_path(skill, issue)
    if not path.exists():
        return []

    subtask_defs = SUBTASKS.get(skill, {})
    if step_num not in subtask_defs:
        return []

    content = path.read_text()
    step_subtasks = subtask_defs[step_num]

    # Parse status of each sub-task from checklist content
    statuses = {}  # id -> "done" | "failed" | "pending"
    for sub in step_subtasks:
        sub_id = sub["id"]
        escaped = re.escape(sub_id)
        if re.search(rf"  - \[x\] {escaped} ", content):
            statuses[sub_id] = "done"
        elif re.search(rf"  - \[!\] {escaped} ", content):
            statuses[sub_id] = "failed"
        else:
            statuses[sub_id] = "pending"

    # Find pending sub-tasks whose deps are all done
    ready = []
    for sub in step_subtasks:
        if statuses[sub["id"]] != "pending":
            continue
        if all(statuses.get(dep) == "done" for dep in sub["deps"]):
            ready.append(sub["id"])

    return ready


def main() -> int:
    parser = argparse.ArgumentParser(description="Autopilot checklist manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    skill_choices = ["autopilot", "autopilot-simple"]

    p_create = subparsers.add_parser("create")
    p_create.add_argument("skill", choices=skill_choices)
    p_create.add_argument("issue")
    p_create.add_argument("--title", default="")

    p_update = subparsers.add_parser("update")
    p_update.add_argument("skill", choices=skill_choices)
    p_update.add_argument("issue")
    p_update.add_argument("step")
    p_update.add_argument("status", choices=["pending", "done", "failed"])

    p_check = subparsers.add_parser("check-step")
    p_check.add_argument("skill", choices=skill_choices)
    p_check.add_argument("issue")
    p_check.add_argument("step_num", type=int)

    p_ready = subparsers.add_parser("ready-subtasks")
    p_ready.add_argument("skill", choices=skill_choices)
    p_ready.add_argument("issue")
    p_ready.add_argument("step_num", type=int)

    p_read = subparsers.add_parser("read")
    p_read.add_argument("skill", choices=skill_choices)
    p_read.add_argument("issue")

    args = parser.parse_args()

    if args.command == "create":
        print(create_checklist(args.skill, args.issue, args.title))
    elif args.command == "update":
        print(update_step(args.skill, args.issue, args.step, args.status))
    elif args.command == "check-step":
        print(check_step(args.skill, args.issue, args.step_num))
    elif args.command == "ready-subtasks":
        ids = ready_subtasks(args.skill, args.issue, args.step_num)
        print(" ".join(ids) if ids else "NONE")
    elif args.command == "read":
        print(read_checklist(args.skill, args.issue))

    return 0


if __name__ == "__main__":
    sys.exit(main())
