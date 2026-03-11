#!/usr/bin/env python3
"""
Prompt Golden Tests for the Issue-Impl Skill (platform-agnostic format).

Validates execution step instructions in SKILL.md:
  1. Step 4: Plan           (sequential steps)
  2. Step 5: Plan Review    (sequential steps)
  3. Step 6: Implement      (sequential steps, all providers)
  4. Step 8: Code Review    (sequential steps, all VCS providers)

Checks performed per step:
  A. Required structural sections present
  B. Expected CLI commands per provider/stage
  C. Structured output markers (PLAN_RESULT_BEGIN, IMPL_RESULT_BEGIN, etc.)
  D. No platform-specific sub-agent patterns (Task tool:, subagent_type, AskUserQuestion)
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SKILL_MD = Path(__file__).resolve().parent.parent / "SKILL.md"

# Platform-specific patterns that should NOT appear outside the
# "Sub-Agent Dispatch" section. Note: subagent_type and Task tool
# references are ALLOWED inside the cross-platform dispatch section.
FORBIDDEN_PATTERNS = [
    "AskUser" + "Question",
    "EnterPlan" + "Mode",
    "ExitPlan" + "Mode",
]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class StepCheck:
    """Definition of what to validate for a single execution step."""

    name: str
    # Step heading pattern (regex) to locate the section
    heading_pattern: str
    # Substrings that MUST appear somewhere in the step section
    required_sections: list[str]
    # CLI commands that MUST appear
    required_commands: list[str]
    # CLI commands that MUST NOT appear
    forbidden_commands: list[str] = field(default_factory=list)


@dataclass
class StepResult:
    """Validation result for a single execution step."""

    name: str
    section_pass: bool
    missing_sections: list[str]
    command_pass: bool
    missing_commands: list[str]
    forbidden_found: list[str]
    step_found: bool = True

    @property
    def has_errors(self) -> bool:
        return (
            not self.step_found
            or not self.section_pass
            or not self.command_pass
            or len(self.forbidden_found) > 0
        )


# ---------------------------------------------------------------------------
# Section extraction
# ---------------------------------------------------------------------------


def load_skill_md() -> str:
    """Read the SKILL.md file and return its full text."""
    if not SKILL_MD.exists():
        print(f"ERROR: SKILL.md not found at {SKILL_MD}", file=sys.stderr)
        sys.exit(1)
    return SKILL_MD.read_text(encoding="utf-8")


def extract_step_sections(text: str) -> dict[str, str]:
    """Extract step sections keyed by their heading line.

    Returns a dict where key = heading text, value = full section text
    (from heading to next heading of same or higher level).
    """
    sections: dict[str, str] = {}
    lines = text.splitlines()
    step_pattern = re.compile(r"^### Step \d+")
    step_starts: list[tuple[int, str]] = []

    for idx, line in enumerate(lines):
        if step_pattern.match(line):
            step_starts.append((idx, line.strip()))

    for si, (start, heading) in enumerate(step_starts):
        end = step_starts[si + 1][0] if si + 1 < len(step_starts) else len(lines)
        sections[heading] = "\n".join(lines[start:end])

    return sections


def find_step_by_keywords(
    sections: dict[str, str], *keywords: str
) -> str | None:
    """Find a step section that contains ALL keywords in its heading."""
    for heading, text in sections.items():
        heading_lower = heading.lower()
        if all(kw.lower() in heading_lower for kw in keywords):
            return text
    return None


# ---------------------------------------------------------------------------
# Validation logic
# ---------------------------------------------------------------------------


def validate_step(
    section_text: str | None,
    check: StepCheck,
) -> StepResult:
    """Run all checks against a single step section."""
    if section_text is None:
        return StepResult(
            name=check.name,
            section_pass=False,
            missing_sections=check.required_sections[:],
            command_pass=False,
            missing_commands=check.required_commands[:],
            forbidden_found=[],
            step_found=False,
        )

    text_lower = section_text.lower()

    # Section checks (case-insensitive substring match)
    missing_sections = [
        s for s in check.required_sections if s.lower() not in text_lower
    ]

    # Command checks (case-sensitive -- CLI commands are exact)
    missing_commands = [c for c in check.required_commands if c not in section_text]

    # Forbidden command checks
    forbidden_found = [c for c in check.forbidden_commands if c in section_text]

    return StepResult(
        name=check.name,
        section_pass=len(missing_sections) == 0,
        missing_sections=missing_sections,
        command_pass=len(missing_commands) == 0,
        missing_commands=missing_commands,
        forbidden_found=forbidden_found,
    )


# ---------------------------------------------------------------------------
# Step definitions (platform-agnostic sequential steps)
# ---------------------------------------------------------------------------

# Step 4: Plan -------
PLAN = StepCheck(
    name="Step 4: Plan",
    heading_pattern=r"Step 4.*Plan",
    required_sections=[
        "Instructions",
        "plan-template.md",
        "tdd-workflow.md",
        "Structured Output",
        "PLAN_RESULT_BEGIN",
        "PLAN_RESULT_END",
    ],
    required_commands=[],  # Plan step does not invoke provider CLIs directly
)

# Step 5: Plan Review -------
PLAN_REVIEW = StepCheck(
    name="Step 5: Plan Review",
    heading_pattern=r"Step 5.*Plan Review",
    required_sections=[
        "Instructions",
        "plan-review-criteria.md",
        "Structured Output",
        "PLAN_REVIEW_RESULT_BEGIN",
        "PLAN_REVIEW_RESULT_END",
    ],
    required_commands=[],  # Plan review reads local files, no provider CLIs
)

# Step 6: Implement -------
IMPLEMENT = StepCheck(
    name="Step 6: Implement",
    heading_pattern=r"Step 6.*Implement",
    required_sections=[
        "Instructions",
        "tdd-workflow.md",
        "Structured Output",
        "IMPL_RESULT_BEGIN",
        "IMPL_RESULT_END",
    ],
    required_commands=[
        # Provider-specific issue update commands
        "gh issue view",
        "gh issue edit",
        "glab issue view",
        "glab issue edit",
        "mcp__jira__jira_post",
    ],
)

# Step 8: Code Review -------
CODE_REVIEW = StepCheck(
    name="Step 8: Code Review",
    heading_pattern=r"Step 8.*Code Review",
    required_sections=[
        "Instructions",
        "code-review-criteria.md",
        "Structured Output",
        "CODE_REVIEW_RESULT_BEGIN",
        "CODE_REVIEW_RESULT_END",
    ],
    required_commands=[
        "gh pr diff",
        "gh pr review",
        "glab mr diff",
        "glab mr note",
    ],
)


# ---------------------------------------------------------------------------
# Forbidden pattern check
# ---------------------------------------------------------------------------


def check_forbidden_patterns(text: str) -> list[str]:
    """Find platform-specific sub-agent patterns that should not appear."""
    found = []
    for pattern in FORBIDDEN_PATTERNS:
        if pattern in text:
            found.append(pattern)
    return found


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def print_result(r: StepResult) -> None:
    """Print human-readable validation result for one step."""
    print(f"\n  [{r.name}]")

    if not r.step_found:
        print("    STEP: NOT FOUND in SKILL.md")
        return

    # Required sections
    if r.section_pass:
        print("    Required sections: all present")
    else:
        for ms in r.missing_sections:
            print(f'    Required sections: MISSING "{ms}"')

    # CLI commands
    if r.command_pass:
        print("    CLI commands: all present")
    else:
        for mc in r.missing_commands:
            print(f'    CLI commands: MISSING "{mc}"')

    # Forbidden commands
    if r.forbidden_found:
        for fc in r.forbidden_found:
            print(f'    CLI commands: FORBIDDEN "{fc}" found')


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    text = load_skill_md()
    sections = extract_step_sections(text)

    # -- Locate each step section --
    step4 = find_step_by_keywords(sections, "step 4", "plan")
    step5 = find_step_by_keywords(sections, "step 5", "plan review")
    step6 = find_step_by_keywords(sections, "step 6", "implement")
    step8 = find_step_by_keywords(sections, "step 8", "code review")

    # -- Run checks --
    checks_and_sections = [
        (PLAN, step4),
        (PLAN_REVIEW, step5),
        (IMPLEMENT, step6),
        (CODE_REVIEW, step8),
    ]

    results: list[StepResult] = []
    for check, section in checks_and_sections:
        results.append(validate_step(section, check))

    # -- Check for forbidden patterns --
    forbidden = check_forbidden_patterns(text)

    # -- Report --
    print("=== Prompt Golden Tests: issue-impl (platform-agnostic) ===")

    error_count = 0
    warning_count = 0

    for r in results:
        print_result(r)
        if r.has_errors:
            error_count += 1

    if forbidden:
        print(f"\n  [Forbidden Patterns]")
        for pattern in forbidden:
            print(f'    FOUND: "{pattern}" — must be removed for platform neutrality')
            error_count += 1
    else:
        print("\n  [Forbidden Patterns]")
        print("    None found — platform-agnostic")

    print(
        f"\n  Summary: {len(results)} steps checked, {error_count} errors, {warning_count} warnings"
    )

    return 1 if error_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
