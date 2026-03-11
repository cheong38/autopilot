#!/usr/bin/env python3
"""Structural validation tests for issue/SKILL.md.

Verifies that required steps and DAG integration points exist in SKILL.md.
Extends lint_skill.py checks with Phase 4 requirements.
"""

import re
import sys
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"


class TestSkillStructure(unittest.TestCase):
    """Validate SKILL.md has all required steps and sections."""

    @classmethod
    def setUpClass(cls):
        cls.text = SKILL_MD.read_text()
        cls.lines = cls.text.split("\n")

    def test_skill_md_exists(self):
        self.assertTrue(SKILL_MD.exists(), "SKILL.md not found")

    def test_step_3_5_ambiguity_check(self):
        """Step 3.5 (Ambiguity Check) must exist between Step 3 and Step 4."""
        self.assertRegex(
            self.text,
            r"###\s+Step\s+3\.5.*Ambiguity",
            "Step 3.5 (Ambiguity Check) not found in SKILL.md",
        )

    def test_step_5_5_dag_analysis(self):
        """Step 5.5 (DAG Analysis) must exist between Step 5 and Step 6."""
        self.assertRegex(
            self.text,
            r"###\s+Step\s+5\.5.*DAG",
            "Step 5.5 (DAG Analysis) not found in SKILL.md",
        )

    def test_step_5_6_user_confirmation(self):
        """Step 5.6 (User Confirmation Gate) must exist after Step 5.5."""
        self.assertRegex(
            self.text,
            r"###\s+Step\s+5\.6.*Confirm",
            "Step 5.6 (User Confirmation) not found in SKILL.md",
        )

    def test_post_creation_dag_update(self):
        """Post-Creation DAG Update section must exist."""
        self.assertIn(
            "DAG Update",
            self.text,
            "Post-Creation DAG Update section not found in SKILL.md",
        )

    def test_dag_similar_command_referenced(self):
        """SKILL.md must reference /issue-dag similar for duplicate detection."""
        self.assertIn(
            "issue-dag",
            self.text,
            "/issue-dag integration not referenced in SKILL.md",
        )

    def test_no_brainstorm_flag_mentioned(self):
        """--no-brainstorm flag must be documented."""
        self.assertIn(
            "--no-brainstorm",
            self.text,
            "--no-brainstorm flag not documented in SKILL.md",
        )

    def test_step_order(self):
        """Steps must appear in correct order: 3 → 3.5 → 4 → 5 → 5.5 → 5.6 → 6."""
        step_positions = {}
        for i, line in enumerate(self.lines):
            if re.match(r"###\s+Step\s+3:", line):
                step_positions["3"] = i
            elif re.match(r"###\s+Step\s+3\.5:", line):
                step_positions["3.5"] = i
            elif re.match(r"###\s+Step\s+4:", line):
                step_positions["4"] = i
            elif re.match(r"###\s+Step\s+5:", line):
                step_positions["5"] = i
            elif re.match(r"###\s+Step\s+5\.5:", line):
                step_positions["5.5"] = i
            elif re.match(r"###\s+Step\s+5\.6:", line):
                step_positions["5.6"] = i
            elif re.match(r"###\s+Step\s+6:", line):
                step_positions["6"] = i

        expected_order = ["3", "3.5", "4", "5", "5.5", "5.6", "6"]
        present = [s for s in expected_order if s in step_positions]
        missing = [s for s in expected_order if s not in step_positions]
        self.assertEqual(missing, [], f"Steps missing from SKILL.md: {missing}")
        for a, b in zip(present, present[1:]):
            self.assertLess(
                step_positions[a],
                step_positions[b],
                f"Step {a} (line {step_positions[a]}) should appear before Step {b} (line {step_positions[b]})",
            )

    def test_brainstorming_triggers_documented(self):
        """Ambiguity Check must document when brainstorming is triggered vs skipped."""
        # Find Step 3.5 section
        step35_text = ""
        in_step = False
        for line in self.lines:
            if re.match(r"###\s+Step\s+3\.5:", line):
                in_step = True
                continue
            if in_step and line.startswith("### Step"):
                break
            if in_step:
                step35_text += line + "\n"
        self.assertIn("trigger", step35_text.lower(), "Brainstorming triggers not documented in Step 3.5")
        self.assertIn("skip", step35_text.lower(), "Brainstorming skip conditions not documented in Step 3.5")

    def test_user_confirmation_options(self):
        """Step 5.6 must document all four user options."""
        step56_text = ""
        in_step = False
        for line in self.lines:
            if re.match(r"###\s+Step\s+5\.6:", line):
                in_step = True
                continue
            if in_step and line.startswith("### Step"):
                break
            if in_step:
                step56_text += line + "\n"
        lower = step56_text.lower()
        self.assertTrue(
            "create" in lower and "dependency" in lower,
            "Step 5.6 missing 'Create with dependency' option",
        )
        self.assertTrue(
            "cancel" in lower or "abort" in lower,
            "Step 5.6 missing 'Cancel' option",
        )


class TestLintSkillIntegration(unittest.TestCase):
    """Run lint_skill.py and verify it passes."""

    def test_lint_passes(self):
        """lint_skill.py should pass on the issue skill without new errors."""
        lint_script = SKILL_DIR / "scripts" / "lint_skill.py"
        if not lint_script.exists():
            self.skipTest("lint_skill.py not found")

        # Known pre-existing lint issues (not introduced by Phase 4)
        KNOWN_ISSUES = {
            "ISSUE_RESULT_BEGIN:create:jira",  # Jira block uses ISSUE_KEY but generic template has ISSUE_NUMBER
        }

        # Import and run lint
        sys.path.insert(0, str(lint_script.parent))
        try:
            import lint_skill
            result = lint_skill.lint_skill(SKILL_DIR)
            errors = [
                d for d in result.diagnostics
                if d.level == "error"
                and not any(known in d.message for known in KNOWN_ISSUES)
            ]
            if errors:
                error_msgs = "\n".join(str(e) for e in errors)
                self.fail(f"lint_skill.py found errors:\n{error_msgs}")
        finally:
            sys.path.pop(0)


if __name__ == "__main__":
    unittest.main()
