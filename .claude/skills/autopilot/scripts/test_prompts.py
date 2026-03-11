#!/usr/bin/env python3
"""
Prompt Golden Tests for the Autopilot Skill.

Validates SKILL.md structural integrity:
  1. Required sections present
  2. All orchestration steps exist (Steps 0–12)
  3. Structured output markers present (AUTOPILOT_*_BEGIN/END)
  4. UIP tables validated (Other row, correct UIP numbers)
  5. Provider CLI commands present (gh, glab, Jira MCP)
  6. Progressive disclosure: SKILL.md < 500 lines
  7. Forbidden patterns check
  8. Reference file content validation (non-placeholder)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"

FORBIDDEN_PATTERNS = [
    "AskUser" + "Question",
    "EnterPlan" + "Mode",
    "ExitPlan" + "Mode",
]

REQUIRED_SECTIONS = [
    "## Language Matching",
    "## Usage",
    "## Prerequisites",
    "## Configuration",
    "## Status Footer",
    "## Orchestration Flow",
    "## Step-by-Step Detail",
    "## Dependencies & References",
    "## Maintenance",
]

REQUIRED_STEPS = [
    "Step 0: META-ISSUE",
    "Step 0.3: CLASSIFY",
    "Step 0.5: WHY-CONTEXT",
    "Step 1: INGEST",
    "Step 1.5: VERIFY-PLAN",
    "Step 2: UL-CHECK",
    "Step 2.5: CLARIFY",
    "Step 3: DECOMPOSE",
    "Step 3.5: CONFIRM",
    "Step 4: CREATE",
    "Step 4.5: RECONCILE",
    "Step 5: DAG-BUILD",
    "Step 5.5: DAG-CONFIRM",
    "Step 5.7: VERIFY-INFRA-CHECK",
    "Step 6: IMPL-LOOP",
    "Step 6.5: PRE-DEPLOY-VERIFY",
    "Step 6.6: DEPLOY-DETECT",
    "Step 6.7: DEPLOY-VERIFY",
    "Step 7: TRIAGE",
    "Step 8: CHECKPOINT",
    "Step 9: LOOP",
    "Step 10: FOLLOWUP",
    "Step 11: FINAL-VERIFY",
    "Step 12: REPORT",
]

STRUCTURED_MARKERS = [
    "AUTOPILOT_META_BEGIN",
    "AUTOPILOT_META_END",
    "AUTOPILOT_INGEST_BEGIN",
    "AUTOPILOT_INGEST_END",
    "AUTOPILOT_DECOMPOSE_BEGIN",
    "AUTOPILOT_DECOMPOSE_END",
    "AUTOPILOT_CHECKPOINT_BEGIN",
    "AUTOPILOT_CHECKPOINT_END",
    "AUTOPILOT_RESULT_BEGIN",
    "AUTOPILOT_RESULT_END",
    "AUTOPILOT_ABORT_BEGIN",
    "AUTOPILOT_ABORT_END",
]

UIP_NUMBERS = ["UIP-17", "UIP-18", "UIP-19", "UIP-20", "UIP-21", "UIP-22", "UIP-24", "UIP-25", "UIP-26", "UIP-27", "UIP-28"]

REFERENCE_FILES = [
    "references/ingest-formats.md",
    "references/verification-matrix.md",
    "references/self-review-criteria.md",
    "references/self-review-prompt-template.md",
    "references/agent-delegation.md",
    "references/resume-protocol.md",
    "references/simple-path.md",
    "references/error-recovery.md",
]

def check_sections(content: str, errors: list[str]) -> None:
    for section in REQUIRED_SECTIONS:
        if section not in content:
            errors.append(f"Missing section: {section}")


def check_steps(content: str, errors: list[str]) -> None:
    for step in REQUIRED_STEPS:
        if step not in content:
            errors.append(f"Missing step: {step}")


def check_structured_markers(content: str, errors: list[str]) -> None:
    # Markers may be in SKILL.md or in reference files (extracted for line budget)
    refs_dir = SKILL_DIR / "references"
    ref_content = ""
    if refs_dir.is_dir():
        for ref_file in refs_dir.glob("*.md"):
            ref_content += ref_file.read_text()
    combined = content + ref_content
    for marker in STRUCTURED_MARKERS:
        if marker not in combined:
            errors.append(f"Missing structured marker: {marker}")


def check_uip_tables(content: str, errors: list[str]) -> None:
    for uip in UIP_NUMBERS:
        if uip not in content:
            errors.append(f"Missing UIP reference: {uip}")

    # Check that UIP tables have "Other" row
    uip_pattern = re.compile(r"UIP-\d+\).*?\n((?:\|.*\n)+)", re.MULTILINE)
    for match in uip_pattern.finditer(content):
        table = match.group(1)
        if "Other" not in table:
            errors.append(f"UIP table near '{match.group(0)[:40]}...' missing 'Other' row")


def check_provider_commands(content: str, errors: list[str]) -> None:
    providers = {
        "GitHub": "gh issue create",
        "GitLab": "glab issue create",
        "Jira": "Jira MCP",
    }
    for provider, cmd in providers.items():
        if cmd not in content:
            errors.append(f"Missing {provider} command: {cmd}")


def check_line_count(content: str, errors: list[str], warnings: list[str]) -> None:
    lines = content.count("\n") + 1
    if lines > 500:
        errors.append(f"SKILL.md is {lines} lines (max 500)")
    elif lines > 480:
        warnings.append(f"SKILL.md is {lines} lines (close to 500 limit)")


def check_forbidden_patterns(content: str, errors: list[str]) -> None:
    for pattern in FORBIDDEN_PATTERNS:
        if pattern in content:
            errors.append(f"Forbidden pattern found: {pattern}")


def check_reference_files(errors: list[str]) -> None:
    for ref in REFERENCE_FILES:
        path = SKILL_DIR / ref
        if not path.exists():
            errors.append(f"Missing reference file: {ref}")
            continue
        text = path.read_text()
        if len(text.strip().split("\n")) < 5:
            errors.append(f"Reference file appears to be placeholder: {ref}")


def main() -> int:
    if not SKILL_MD.exists():
        print("ERROR: SKILL.md not found")
        return 1

    content = SKILL_MD.read_text()
    errors: list[str] = []
    warnings: list[str] = []

    check_sections(content, errors)
    check_steps(content, errors)
    check_structured_markers(content, errors)
    check_uip_tables(content, errors)
    check_provider_commands(content, errors)
    check_line_count(content, errors, warnings)
    check_forbidden_patterns(content, errors)
    check_reference_files(errors)

    print(f"=== Autopilot Prompt Tests ===\n")

    if errors:
        for e in errors:
            print(f"  ERROR: {e}")
    if warnings:
        for w in warnings:
            print(f"  WARN: {w}")

    total = (
        len(REQUIRED_SECTIONS)
        + len(REQUIRED_STEPS)
        + len(STRUCTURED_MARKERS)
        + len(UIP_NUMBERS)
        + 3  # provider, line count, forbidden
        + len(REFERENCE_FILES)
    )
    passed = total - len(errors)
    print(f"\n  Result: {passed}/{total} checks passed, {len(errors)} errors, {len(warnings)} warnings")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
