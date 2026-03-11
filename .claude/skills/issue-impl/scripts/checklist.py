#!/usr/bin/env python3
"""Checklist CRUD operations for skill orchestration.

Manages markdown checklist files at /tmp/skill-checklists/.
Used by both `issue` and `issue-impl` skills to track progress,
agent IDs, and review history.

Usage:
    checklist.py create <skill> <issue> [--title <title>] [--type <type>]
    checklist.py update <skill> <issue> <step> <status>
    checklist.py add-agent <skill> <issue> <role> <agent-id>
    checklist.py add-review <skill> <issue> <iteration> <verdict> <summary>
    checklist.py read <skill> <issue>
"""

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

CHECKLIST_DIR = Path("/tmp/skill-checklists")

ISSUE_STEPS = [
    "Parse requirements",
    "Determine issue type",
    "Detect provider",
    "Guided discovery",
    "Create issue draft",
    "Create/post issue",
    "Review issue (iteration 1)",
    "Address feedback (if needed)",
    "Final approval",
]

ISSUE_IMPL_STEPS = [
    "Fetch issue",
    "Setup worktree",
    "Create plan",
    "Post plan to tracker",
    "Review plan (iteration 1)",
    "Plan approved",
    "Implement (phase by phase)",
    "Create PR/MR",
    "Code review (iteration 1)",
    "Code review approved",
    "Merge PR/MR",
    "Deploy & verify",
    "Cleanup worktree",
]

ISSUE_AGENTS = ["creator", "reviewer"]
ISSUE_IMPL_AGENTS = ["planner", "plan-reviewer", "implementer", "code-reviewer"]


def checklist_path(skill: str, issue: str) -> Path:
    """Return the checklist file path for a skill/issue combination."""
    return CHECKLIST_DIR / f"{skill}-{issue}.md"


def create_checklist(skill: str, issue: str, title: str = "", issue_type: str = "") -> str:
    """Create a new checklist file."""
    CHECKLIST_DIR.mkdir(parents=True, exist_ok=True)
    path = checklist_path(skill, issue)

    if path.exists():
        return f"Checklist already exists: {path}"

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if skill == "issue":
        steps = ISSUE_STEPS
        agents = ISSUE_AGENTS
        review_header = "| Iteration | Verdict | Findings Summary |"
        review_sep = "|-----------|---------|------------------|"
    elif skill == "issue-impl":
        steps = ISSUE_IMPL_STEPS
        agents = ISSUE_IMPL_AGENTS
        review_header = "| Phase | Iteration | Verdict | Findings Summary |"
        review_sep = "|-------|-----------|---------|------------------|"
    else:
        return f"Unknown skill: {skill}. Use 'issue' or 'issue-impl'."

    steps_md = "\n".join(f"- [ ] {i + 1}. {s}" for i, s in enumerate(steps))
    agents_md = "\n".join(f"| {a} | - | pending |" for a in agents)

    type_line = f"\nType: {issue_type}" if issue_type else ""

    content = f"""# {skill.replace('-', ' ').title()} Checklist: #{issue}

Created: {now}
Issue: #{issue}{type_line}
Title: {title or "(untitled)"}
Status: IN_PROGRESS

## Progress
{steps_md}

## Agent Registry
| Role | Agent ID | Status |
|------|----------|--------|
{agents_md}

## Review History
{review_header}
{review_sep}
"""

    path.write_text(content)
    return f"Created: {path}"


def update_step(skill: str, issue: str, step: str, status: str) -> str:
    """Update a step's status in the checklist."""
    path = checklist_path(skill, issue)
    if not path.exists():
        return f"Checklist not found: {path}"

    content = path.read_text()
    step_num = step if step.isdigit() else None

    if status == "done":
        # Replace - [ ] N. with - [x] N.
        if step_num:
            content = re.sub(
                rf"- \[ \] {step_num}\.",
                f"- [x] {step_num}.",
                content,
            )
        else:
            content = content.replace(f"- [ ] {step}", f"- [x] {step}")
    elif status == "failed":
        if step_num:
            content = re.sub(
                rf"- \[[ x]\] {step_num}\.",
                f"- [!] {step_num}.",
                content,
            )
        else:
            content = content.replace(f"- [ ] {step}", f"- [!] {step}")
            content = content.replace(f"- [x] {step}", f"- [!] {step}")
    elif status == "pending":
        if step_num:
            content = re.sub(
                rf"- \[[x!]\] {step_num}\.",
                f"- [ ] {step_num}.",
                content,
            )

    path.write_text(content)
    return f"Updated step {step} → {status}"


def add_agent(skill: str, issue: str, role: str, agent_id: str) -> str:
    """Register an agent ID for a role."""
    path = checklist_path(skill, issue)
    if not path.exists():
        return f"Checklist not found: {path}"

    content = path.read_text()
    # Replace the row for this role
    content = re.sub(
        rf"\| {re.escape(role)} \| [^|]+ \| [^|]+ \|",
        f"| {role} | {agent_id} | active |",
        content,
    )
    path.write_text(content)
    return f"Registered agent {role} → {agent_id}"


def add_review(
    skill: str, issue: str, iteration: str, verdict: str, summary: str, phase: str = ""
) -> str:
    """Add a review record to the history."""
    path = checklist_path(skill, issue)
    if not path.exists():
        return f"Checklist not found: {path}"

    content = path.read_text()

    # Escape pipe characters in summary to prevent markdown table breakage
    safe_summary = summary.replace("|", "\\|")

    if skill == "issue-impl" and phase:
        row = f"| {phase} | {iteration} | {verdict} | {safe_summary} |"
    else:
        row = f"| {iteration} | {verdict} | {safe_summary} |"

    # Append row after the last line of the Review History table
    lines = content.split("\n")
    insert_idx = None
    in_review = False
    for i, line in enumerate(lines):
        if "## Review History" in line:
            in_review = True
        elif in_review and line.startswith("|"):
            insert_idx = i + 1
        elif in_review and not line.startswith("|") and line.strip() == "":
            if insert_idx is None:
                insert_idx = i
            break

    if insert_idx is not None:
        lines.insert(insert_idx, row)
        content = "\n".join(lines)
        path.write_text(content)
        return f"Added review: iteration {iteration} → {verdict}"

    return "Could not find Review History table"


def read_checklist(skill: str, issue: str) -> str:
    """Read and return the checklist contents."""
    path = checklist_path(skill, issue)
    if not path.exists():
        return f"Checklist not found: {path}"
    return path.read_text()


def main() -> int:
    parser = argparse.ArgumentParser(description="Skill checklist manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create
    p_create = subparsers.add_parser("create", help="Create a new checklist")
    p_create.add_argument("skill", choices=["issue", "issue-impl"])
    p_create.add_argument("issue", help="Issue key (e.g., 123, KIH-456)")
    p_create.add_argument("--title", default="", help="Issue title")
    p_create.add_argument("--type", default="", dest="issue_type", help="Issue type (story/task/bug)")

    # update
    p_update = subparsers.add_parser("update", help="Update a step status")
    p_update.add_argument("skill", choices=["issue", "issue-impl"])
    p_update.add_argument("issue")
    p_update.add_argument("step", help="Step number or text")
    p_update.add_argument("status", choices=["pending", "done", "failed"])

    # add-agent
    p_agent = subparsers.add_parser("add-agent", help="Register an agent ID")
    p_agent.add_argument("skill", choices=["issue", "issue-impl"])
    p_agent.add_argument("issue")
    p_agent.add_argument("role", help="Agent role name")
    p_agent.add_argument("agent_id", help="Agent ID from Task tool")

    # add-review
    p_review = subparsers.add_parser("add-review", help="Add review record")
    p_review.add_argument("skill", choices=["issue", "issue-impl"])
    p_review.add_argument("issue")
    p_review.add_argument("iteration", help="Review iteration number")
    p_review.add_argument("verdict", choices=["APPROVE", "NEEDS_WORK", "REQUEST_CHANGES"])
    p_review.add_argument("summary", help="One-line findings summary")
    p_review.add_argument("--phase", default="", help="Phase name (issue-impl only)")

    # read
    p_read = subparsers.add_parser("read", help="Read checklist contents")
    p_read.add_argument("skill", choices=["issue", "issue-impl"])
    p_read.add_argument("issue")

    args = parser.parse_args()

    if args.command == "create":
        print(create_checklist(args.skill, args.issue, args.title, args.issue_type))
    elif args.command == "update":
        print(update_step(args.skill, args.issue, args.step, args.status))
    elif args.command == "add-agent":
        print(add_agent(args.skill, args.issue, args.role, args.agent_id))
    elif args.command == "add-review":
        print(
            add_review(
                args.skill,
                args.issue,
                args.iteration,
                args.verdict,
                args.summary,
                getattr(args, "phase", ""),
            )
        )
    elif args.command == "read":
        print(read_checklist(args.skill, args.issue))

    return 0


if __name__ == "__main__":
    sys.exit(main())
