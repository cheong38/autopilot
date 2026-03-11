#!/usr/bin/env python3
"""SKILL.md integrity linter for issue and issue-impl skills.

Validates three categories:
  1. Step number continuity against checklist.py definitions
  2. Provider matrix completeness (GitHub/GitLab/Jira coverage)
  3. Structured block field completeness (*_RESULT_BEGIN/*_RESULT_END)

Usage:
    python3 lint_skill.py /path/to/skill/directory
    python3 lint_skill.py /path/to/issue/skill /path/to/issue-impl/skill

Exit code: 0 if no errors, 1 if any errors found.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Checklist step definitions (mirrored from checklist.py)
# ---------------------------------------------------------------------------

ISSUE_STEPS: dict[int, str] = {
    1: "Parse requirements",
    2: "Determine issue type",
    3: "Detect provider",
    4: "Guided discovery",
    5: "Create issue draft",
    6: "Create/post issue",
    7: "Review issue (iteration 1)",
    8: "Address feedback (if needed)",
    9: "Final approval",
}

ISSUE_IMPL_STEPS: dict[int, str] = {
    1: "Fetch issue",
    2: "Setup worktree",
    3: "Create plan",
    4: "Post plan to tracker",
    5: "Review plan (iteration 1)",
    6: "Plan approved",
    7: "Implement (phase by phase)",
    8: "Create PR/MR",
    9: "Code review (iteration 1)",
    10: "Code review approved",
    11: "Merge PR/MR",
    12: "Deploy & verify",
    13: "Cleanup worktree",
}

# ---------------------------------------------------------------------------
# Expected structured block fields
# ---------------------------------------------------------------------------

# issue skill blocks
ISSUE_BLOCKS: dict[str, dict[str, list[str]]] = {
    "ISSUE_RESULT_BEGIN:create:github": {
        "required": ["ISSUE_NUMBER", "ISSUE_URL", "TITLE", "TYPE", "STATUS", "PROVIDER"],
    },
    "ISSUE_RESULT_BEGIN:create:gitlab": {
        "required": ["ISSUE_NUMBER", "ISSUE_URL", "TITLE", "TYPE", "STATUS", "PROVIDER"],
    },
    "ISSUE_RESULT_BEGIN:create:jira": {
        "required": ["ISSUE_KEY", "ISSUE_URL", "TITLE", "TYPE", "STATUS", "PROVIDER"],
    },
    "ISSUE_RESULT_BEGIN:address": {
        "required": ["ISSUE", "ISSUE_URL", "TYPE", "CHANGES_MADE", "CHANGES_DECLINED", "STATUS", "PROVIDER"],
    },
    "REVIEW_RESULT_BEGIN": {
        "required": [
            "ISSUE", "TYPE", "VERDICT", "CRITICAL_COUNT",
            "MAJOR_COUNT", "MINOR_COUNT", "SUGGESTION_COUNT",
            "SUMMARY", "PROVIDER",
        ],
    },
}

# issue-impl skill blocks
ISSUE_IMPL_BLOCKS: dict[str, dict[str, list[str]]] = {
    "PLAN_RESULT_BEGIN": {
        "required": ["PLAN_FILE", "TOTAL_PHASES", "STATUS"],
    },
    "PLAN_REVIEW_RESULT_BEGIN": {
        "required": ["VERDICT", "CRITICAL_COUNT", "MAJOR_COUNT", "MINOR_COUNT", "SUMMARY"],
        "optional": ["REVIEW_MODE"],
    },
    "IMPL_RESULT_BEGIN": {
        "required": ["PHASES_COMPLETED", "TOTAL_PHASES", "FINAL_COMMIT", "STATUS", "SUMMARY"],
    },
    "CODE_REVIEW_RESULT_BEGIN": {
        "required": ["PR_MR_NUMBER", "VERDICT", "CRITICAL_COUNT", "MAJOR_COUNT", "MINOR_COUNT", "SUMMARY"],
        "optional": ["DONE_CRITERIA_TOTAL", "DONE_CRITERIA_CHECKED"],
    },
}

# ---------------------------------------------------------------------------
# Provider matrix expectations
# ---------------------------------------------------------------------------

# Steps that must mention specific providers, and which providers apply.
ISSUE_PROVIDER_STEPS: dict[str, list[str]] = {
    "Create Issue": ["GitHub", "GitLab", "Jira"],
    "Review Issue": ["GitHub", "GitLab", "Jira"],
    "Address Feedback": ["GitHub", "GitLab", "Jira"],
}

ISSUE_IMPL_PROVIDER_STEPS: dict[str, list[str]] = {
    "Fetch Issue": ["GitHub", "GitLab", "Jira"],
    "Post Plan": ["GitHub", "GitLab", "Jira"],
    "Implement (update issue)": ["GitHub", "GitLab", "Jira"],
    "Create PR/MR": ["GitHub", "GitLab", "Jira"],
    "Code Review": ["GitHub", "GitLab"],
    "Merge": ["GitHub", "GitLab"],
}


# ---------------------------------------------------------------------------
# Diagnostic types
# ---------------------------------------------------------------------------

@dataclass
class Diagnostic:
    level: str  # "error" or "warning"
    category: str
    message: str
    line: Optional[int] = None

    def __str__(self) -> str:
        loc = f"Line {self.line}: " if self.line else ""
        prefix = "\u274c" if self.level == "error" else "\u26a0\ufe0f"
        return f"  {prefix} {loc}{self.message}"


@dataclass
class LintResult:
    skill_name: str
    diagnostics: list[Diagnostic] = field(default_factory=list)

    @property
    def errors(self) -> list[Diagnostic]:
        return [d for d in self.diagnostics if d.level == "error"]

    @property
    def warnings(self) -> list[Diagnostic]:
        return [d for d in self.diagnostics if d.level == "warning"]


# ---------------------------------------------------------------------------
# 1. Step Number Continuity
# ---------------------------------------------------------------------------

def check_step_numbers(lines: list[str], skill_name: str) -> list[Diagnostic]:
    """Parse SKILL.md for checklist.py update references and validate step numbers."""
    diagnostics: list[Diagnostic] = []
    steps = ISSUE_STEPS if skill_name == "issue" else ISSUE_IMPL_STEPS
    max_step = max(steps.keys())

    # Pattern: checklist.py update <skill> <issue> <step_number> done|failed|pending
    pattern = re.compile(
        r"checklist\.py\s+update\s+(?:issue-impl|issue)\s+\S+\s+(\d+)\s+(?:done|failed|pending)"
    )

    found_steps: list[tuple[int, int]] = []  # (line_number, step_number)

    for i, line in enumerate(lines, start=1):
        for match in pattern.finditer(line):
            step_num = int(match.group(1))
            found_steps.append((i, step_num))

            if step_num < 1 or step_num > max_step:
                diagnostics.append(Diagnostic(
                    level="error",
                    category="STEP NUMBERS",
                    message=(
                        f"references step {step_num}, but checklist only has "
                        f"steps 1-{max_step}"
                    ),
                    line=i,
                ))

    # Check for out-of-sequence references
    if len(found_steps) >= 2:
        prev_step = found_steps[0][1]
        for line_num, step_num in found_steps[1:]:
            if step_num < prev_step:
                diagnostics.append(Diagnostic(
                    level="warning",
                    category="STEP NUMBERS",
                    message=(
                        f"references step {step_num} after step {prev_step}, "
                        f"appears out of sequence"
                    ),
                    line=line_num,
                ))
            prev_step = step_num

    if not diagnostics:
        diagnostics.append(Diagnostic(
            level="info",
            category="STEP NUMBERS",
            message=f"All step references valid ({len(found_steps)} checked)",
        ))

    return diagnostics


# ---------------------------------------------------------------------------
# 2. Provider Matrix Completeness
# ---------------------------------------------------------------------------

def _find_section_range(
    lines: list[str], start_pattern: str, end_patterns: list[str]
) -> tuple[int, int]:
    """Find the line range of a markdown section starting with start_pattern."""
    start = -1
    for i, line in enumerate(lines):
        if start_pattern in line:
            start = i
            break
    if start == -1:
        return (-1, -1)

    end = len(lines)
    for i in range(start + 1, len(lines)):
        for ep in end_patterns:
            if ep in lines[i]:
                return (start, i)
    return (start, end)


def _provider_mentioned(text: str, provider: str) -> bool:
    """Check if a provider is mentioned via various indicators."""
    provider_lower = provider.lower()
    indicators: dict[str, list[str]] = {
        "github": ["github", "gh issue", "gh pr", "gh run", "`gh`", "GitHub"],
        "gitlab": ["gitlab", "glab issue", "glab mr", "glab ci", "`glab`", "GitLab"],
        "jira": ["jira", "mcp__jira", "ISSUE_KEY", "Jira"],
    }
    for indicator in indicators.get(provider_lower, []):
        if indicator.lower() in text.lower():
            return True
    return False


def check_provider_matrix_issue(lines: list[str]) -> list[Diagnostic]:
    """Check provider coverage for the issue skill."""
    diagnostics: list[Diagnostic] = []
    # --- Step 6: Create Issue ---
    # Extract Step 6 section text
    step6_text = ""
    in_step6 = False
    for line in lines:
        if "### Step 6:" in line:
            in_step6 = True
            continue
        if in_step6 and line.startswith("### Step 7:"):
            break
        if in_step6:
            step6_text += line + "\n"

    for provider in ["GitHub", "GitLab", "Jira"]:
        if not _provider_mentioned(step6_text, provider):
            diagnostics.append(Diagnostic(
                level="warning",
                category="PROVIDER MATRIX",
                message=f'Step "Create Issue": missing {provider} handling',
            ))

    # --- Step 7: Review Issue ---
    review_section_text = ""
    in_review = False
    for line in lines:
        if "### Step 7:" in line or "Review Issue" in line and "###" in line:
            in_review = True
            continue
        if in_review and line.startswith("### Step 8:"):
            break
        if in_review:
            review_section_text += line + "\n"

    for provider in ["GitHub", "GitLab", "Jira"]:
        if not _provider_mentioned(review_section_text, provider):
            diagnostics.append(Diagnostic(
                level="warning",
                category="PROVIDER MATRIX",
                message=f'Step "Review Issue": missing {provider} handling',
            ))

    # --- Step 8: Address Feedback ---
    address_section_text = ""
    in_address = False
    for line in lines:
        if "### Step 8:" in line or "Address Feedback" in line and "###" in line:
            in_address = True
            continue
        if in_address and line.startswith("### Step 9:"):
            break
        if in_address:
            address_section_text += line + "\n"

    for provider in ["GitHub", "GitLab", "Jira"]:
        if not _provider_mentioned(address_section_text, provider):
            diagnostics.append(Diagnostic(
                level="warning",
                category="PROVIDER MATRIX",
                message=f'Step "Address Feedback": missing {provider} handling',
            ))

    if not diagnostics:
        diagnostics.append(Diagnostic(
            level="info",
            category="PROVIDER MATRIX",
            message="All provider coverage complete",
        ))

    return diagnostics


def check_provider_matrix_issue_impl(lines: list[str]) -> list[Diagnostic]:
    """Check provider coverage for the issue-impl skill."""
    diagnostics: list[Diagnostic] = []

    # Build sections keyed by step header
    sections: dict[str, str] = {}
    current_key: Optional[str] = None
    current_lines: list[str] = []

    for line in lines:
        if line.startswith("### Step"):
            if current_key is not None:
                sections[current_key] = "\n".join(current_lines)
            current_key = line.strip()
            current_lines = []
        elif current_key is not None:
            current_lines.append(line)
    if current_key is not None:
        sections[current_key] = "\n".join(current_lines)

    # Step checks with expected providers
    step_checks: list[tuple[str, str, list[str]]] = [
        ("Step 1", "Fetch Issue", ["GitHub", "GitLab", "Jira"]),
        ("Step 4a", "Post Plan", ["GitHub", "GitLab", "Jira"]),
        ("Step 6", "Implement", ["GitHub", "GitLab", "Jira"]),
        ("Step 7", "Create PR/MR", ["GitHub", "GitLab", "Jira"]),
        ("Step 8", "Code Review", ["GitHub", "GitLab"]),
        ("Step 9", "Merge", ["GitHub", "GitLab"]),
    ]

    for step_id, step_label, providers in step_checks:
        # Find matching section using a priority-based approach:
        # 1. Exact step ID match (e.g., "Step 6" or "Step 4a")
        # 2. Broader step number match
        # 3. Label-based match (word boundary) as last resort
        section_text = ""

        # Extract step number/id for matching (e.g., "6", "4a")
        step_suffix = step_id.split(maxsplit=1)[1] if " " in step_id else step_id

        # Priority 1: Exact step ID in section header
        for key, text in sections.items():
            # Match "### Step 6:" or "### Step 4a:" patterns
            if re.search(rf"Step\s+{re.escape(step_suffix)}\b", key):
                section_text = text
                break

        # Priority 2: Label-based match with word boundary
        if not section_text:
            label_pattern = re.compile(
                rf"\b{re.escape(step_label)}\b", re.IGNORECASE
            )
            for key, text in sections.items():
                if label_pattern.search(key):
                    section_text = text
                    break

        for provider in providers:
            if not _provider_mentioned(section_text, provider):
                # Check if this is a known N/A case
                na_cases = {
                    ("Code Review", "Jira"),
                    ("Merge", "Jira"),
                }
                if (step_label, provider) in na_cases:
                    continue
                diagnostics.append(Diagnostic(
                    level="warning",
                    category="PROVIDER MATRIX",
                    message=f'Step "{step_label}": missing {provider} handling',
                ))

    if not diagnostics:
        diagnostics.append(Diagnostic(
            level="info",
            category="PROVIDER MATRIX",
            message="All provider coverage complete",
        ))

    return diagnostics


# ---------------------------------------------------------------------------
# 3. Structured Block Field Completeness
# ---------------------------------------------------------------------------

@dataclass
class ParsedBlock:
    """A parsed BEGIN/END block from SKILL.md."""
    block_type: str  # e.g. "ISSUE_RESULT_BEGIN"
    start_line: int
    end_line: int
    fields: list[str]  # field names found
    context: str  # surrounding text for disambiguation


def parse_blocks(lines: list[str]) -> list[ParsedBlock]:
    """Parse all *_RESULT_BEGIN / *_RESULT_END blocks."""
    blocks: list[ParsedBlock] = []
    begin_pattern = re.compile(r"(\w+_RESULT_BEGIN)\b")
    end_pattern = re.compile(r"(\w+_RESULT_END)\b")
    field_pattern = re.compile(r"^\s*([A-Z][A-Z0-9_]+)=")

    i = 0
    while i < len(lines):
        begin_match = begin_pattern.search(lines[i])
        if begin_match:
            block_type = begin_match.group(1)
            start_line = i + 1  # 1-indexed
            fields: list[str] = []

            # Grab context: 20 lines before the block start
            context_start = max(0, i - 20)
            context = "\n".join(lines[context_start:i])

            j = i + 1
            while j < len(lines):
                if end_pattern.search(lines[j]):
                    break
                fm = field_pattern.search(lines[j])
                if fm:
                    fields.append(fm.group(1))
                j += 1

            blocks.append(ParsedBlock(
                block_type=block_type,
                start_line=start_line,
                end_line=j + 1,
                fields=fields,
                context=context,
            ))
            i = j + 1
        else:
            i += 1

    return blocks


def _classify_issue_block(block: ParsedBlock) -> Optional[str]:
    """Classify an ISSUE_RESULT_BEGIN block by its context (create vs address, provider)."""
    ctx_lower = block.context.lower()

    # Check if this is an address/update block
    address_indicators = ["address", "update", "changes_made", "resume"]
    is_address = any(ind in ctx_lower for ind in address_indicators)
    # Also check the fields themselves
    if "CHANGES_MADE" in block.fields or "CHANGES_DECLINED" in block.fields:
        is_address = True

    if is_address:
        return "ISSUE_RESULT_BEGIN:address"

    # It's a create block; determine provider
    if "jira" in ctx_lower or "ISSUE_KEY" in block.fields:
        return "ISSUE_RESULT_BEGIN:create:jira"
    elif "gitlab" in ctx_lower:
        return "ISSUE_RESULT_BEGIN:create:gitlab"
    else:
        return "ISSUE_RESULT_BEGIN:create:github"


def check_structured_blocks(lines: list[str], skill_name: str) -> list[Diagnostic]:
    """Validate structured block fields against expected definitions."""
    diagnostics: list[Diagnostic] = []
    blocks = parse_blocks(lines)
    expected_defs = ISSUE_BLOCKS if skill_name == "issue" else ISSUE_IMPL_BLOCKS

    blocks_checked = 0

    for block in blocks:
        # Determine which expected definition to compare against
        if skill_name == "issue" and block.block_type == "ISSUE_RESULT_BEGIN":
            def_key = _classify_issue_block(block)
        elif block.block_type == "REVIEW_RESULT_BEGIN":
            def_key = "REVIEW_RESULT_BEGIN"
        else:
            def_key = block.block_type

        if def_key is None:
            diagnostics.append(Diagnostic(
                level="warning",
                category="STRUCTURED BLOCKS",
                message=f"{block.block_type} (line {block.start_line}): could not classify block context",
                line=block.start_line,
            ))
            continue

        expected = expected_defs.get(def_key)
        if expected is None:
            # Not a known block for this skill - might be from the other skill
            # referenced in examples. Skip silently.
            continue

        blocks_checked += 1
        required_fields = set(expected["required"])
        actual_fields = set(block.fields)

        # Missing required fields
        missing = required_fields - actual_fields
        for f in sorted(missing):
            diagnostics.append(Diagnostic(
                level="error",
                category="STRUCTURED BLOCKS",
                message=f"{def_key} (line {block.start_line}): missing field {f}",
                line=block.start_line,
            ))

        # Unexpected fields (warning only)
        optional_fields = set(expected.get("optional", []))
        unexpected = actual_fields - required_fields - optional_fields
        for f in sorted(unexpected):
            diagnostics.append(Diagnostic(
                level="warning",
                category="STRUCTURED BLOCKS",
                message=f"{def_key} (line {block.start_line}): unexpected field {f}",
                line=block.start_line,
            ))

    if not any(d.level in ("error", "warning") for d in diagnostics):
        diagnostics.append(Diagnostic(
            level="info",
            category="STRUCTURED BLOCKS",
            message=f"All structured blocks valid ({blocks_checked} blocks checked)",
        ))

    return diagnostics


# ---------------------------------------------------------------------------
# Main lint orchestration
# ---------------------------------------------------------------------------

def lint_skill(skill_dir: Path) -> LintResult:
    """Run all lint checks on a skill directory."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        result = LintResult(skill_name=skill_dir.name)
        result.diagnostics.append(Diagnostic(
            level="error",
            category="SETUP",
            message=f"SKILL.md not found at {skill_md}",
        ))
        return result

    # Determine skill name from directory or SKILL.md frontmatter
    skill_name = _detect_skill_name(skill_dir, skill_md)
    result = LintResult(skill_name=skill_name)

    text = skill_md.read_text()
    lines = text.split("\n")

    # 1. Step number continuity
    result.diagnostics.extend(check_step_numbers(lines, skill_name))

    # 2. Provider matrix completeness
    if skill_name == "issue":
        result.diagnostics.extend(check_provider_matrix_issue(lines))
    elif skill_name == "issue-impl":
        result.diagnostics.extend(check_provider_matrix_issue_impl(lines))

    # 3. Structured block field completeness
    result.diagnostics.extend(check_structured_blocks(lines, skill_name))

    return result


def _detect_skill_name(skill_dir: Path, skill_md: Path) -> str:
    """Detect skill name from the SKILL.md frontmatter or directory name."""
    text = skill_md.read_text()
    # Check frontmatter for name field
    fm_match = re.search(r"^---\s*\n.*?^name:\s*(\S+).*?^---", text, re.MULTILINE | re.DOTALL)
    if fm_match:
        return fm_match.group(1).strip()
    # Fall back to directory name
    return skill_dir.name


def format_results(result: LintResult) -> str:
    """Format lint results for display."""
    output_lines: list[str] = []
    output_lines.append(f"=== SKILL.md Integrity Lint: {result.skill_name} ===")
    output_lines.append("")

    # Group diagnostics by category
    categories = ["STEP NUMBERS", "PROVIDER MATRIX", "STRUCTURED BLOCKS"]
    for cat in categories:
        cat_diags = [d for d in result.diagnostics if d.category == cat]
        output_lines.append(f"[{cat}]")

        info_diags = [d for d in cat_diags if d.level == "info"]
        error_diags = [d for d in cat_diags if d.level == "error"]
        warning_diags = [d for d in cat_diags if d.level == "warning"]

        if not error_diags and not warning_diags:
            for d in info_diags:
                output_lines.append(f"\u2705 {d.message}")
        else:
            if error_diags:
                for d in error_diags:
                    output_lines.append(str(d))
            if warning_diags:
                for d in warning_diags:
                    output_lines.append(str(d))
        output_lines.append("")

    # Non-standard category diagnostics (e.g., SETUP errors)
    other_diags = [d for d in result.diagnostics if d.category not in categories]
    if other_diags:
        for d in other_diags:
            output_lines.append(str(d))
        output_lines.append("")

    error_count = len(result.errors)
    warning_count = len(result.warnings)
    output_lines.append(f"Summary: {error_count} errors, {warning_count} warnings")

    return "\n".join(output_lines)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python3 lint_skill.py /path/to/skill/directory [...]", file=sys.stderr)
        print("", file=sys.stderr)
        print("Validates SKILL.md integrity for issue and issue-impl skills.", file=sys.stderr)
        print("Provide one or more skill directories as arguments.", file=sys.stderr)
        return 2

    has_errors = False
    results: list[LintResult] = []

    for arg in sys.argv[1:]:
        skill_dir = Path(arg).resolve()
        if not skill_dir.is_dir():
            print(f"Error: {arg} is not a directory", file=sys.stderr)
            has_errors = True
            continue

        result = lint_skill(skill_dir)
        results.append(result)

    for i, result in enumerate(results):
        if i > 0:
            print("")
            print("=" * 60)
            print("")
        print(format_results(result))
        if result.errors:
            has_errors = True

    return 1 if has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
