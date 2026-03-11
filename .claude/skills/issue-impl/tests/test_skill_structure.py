#!/usr/bin/env python3
"""Structural validation tests for issue-impl/SKILL.md.

Verifies that required DAG integration steps exist in SKILL.md.
Phase 5: Step 1.3 (DAG Readiness Check) and Step 10.5 (Post-Merge DAG Update).
"""

import re
import sys
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"


class TestSkillStructure(unittest.TestCase):
    """Validate SKILL.md has all required DAG integration steps."""

    @classmethod
    def setUpClass(cls):
        cls.text = SKILL_MD.read_text()
        cls.lines = cls.text.split("\n")

    def test_skill_md_exists(self):
        self.assertTrue(SKILL_MD.exists(), "SKILL.md not found")

    def test_step_1_3_dag_readiness_check(self):
        """Step 1.3 (DAG Readiness Check) must exist between Step 1 and Step 1.5."""
        self.assertRegex(
            self.text,
            r"###\s+Step\s+1\.3.*DAG",
            "Step 1.3 (DAG Readiness Check) not found in SKILL.md",
        )

    def test_step_10_5_post_merge_dag_update(self):
        """Step 10.5 (Post-Merge DAG Update) must exist between Step 10 and Step 11."""
        self.assertRegex(
            self.text,
            r"###\s+Step\s+10\.5.*DAG",
            "Step 10.5 (Post-Merge DAG Update) not found in SKILL.md",
        )

    def test_step_order(self):
        """Steps must appear in correct order: 1 → 1.3 → 1.5 → ... → 10 → 10.5 → 11."""
        step_positions = {}
        for i, line in enumerate(self.lines):
            if re.match(r"###\s+Step\s+1:", line):
                step_positions["1"] = i
            elif re.match(r"###\s+Step\s+1\.3:", line):
                step_positions["1.3"] = i
            elif re.match(r"###\s+Step\s+1\.5:", line):
                step_positions["1.5"] = i
            elif re.match(r"###\s+Step\s+10:", line):
                step_positions["10"] = i
            elif re.match(r"###\s+Step\s+10\.5:", line):
                step_positions["10.5"] = i
            elif re.match(r"###\s+Step\s+11:", line):
                step_positions["11"] = i

        expected_order = ["1", "1.3", "1.5", "10", "10.5", "11"]
        present = [s for s in expected_order if s in step_positions]
        missing = [s for s in expected_order if s not in step_positions]
        self.assertEqual(missing, [], f"Steps missing from SKILL.md: {missing}")
        for a, b in zip(present, present[1:]):
            self.assertLess(
                step_positions[a],
                step_positions[b],
                f"Step {a} (line {step_positions[a]}) should appear before Step {b} (line {step_positions[b]})",
            )

    def test_dag_readiness_has_blocker_options(self):
        """Step 1.3 must document user choices when blockers exist."""
        step13_text = self._extract_step_text(r"###\s+Step\s+1\.3:")
        lower = step13_text.lower()
        self.assertTrue(
            "blocker" in lower or "block" in lower,
            "Step 1.3 missing blocker handling documentation",
        )
        self.assertTrue(
            "skip" in lower or "proceed" in lower or "진행" in lower or "ignore" in lower,
            "Step 1.3 missing 'proceed despite blockers' option",
        )

    def test_dag_readiness_graceful_degradation(self):
        """Step 1.3 must handle unsupported environments gracefully."""
        step13_text = self._extract_step_text(r"###\s+Step\s+1\.3:")
        lower = step13_text.lower()
        self.assertTrue(
            "graceful" in lower or "skip" in lower or "github" in lower
            or "status" in lower or "fallback" in lower,
            "Step 1.3 missing graceful degradation for unsupported environments",
        )

    def test_post_merge_updates_status(self):
        """Step 10.5 must update DAG node status to closed."""
        step105_text = self._extract_step_text(r"###\s+Step\s+10\.5:")
        lower = step105_text.lower()
        self.assertTrue(
            "closed" in lower or "status" in lower,
            "Step 10.5 missing node status update documentation",
        )

    def test_post_merge_shows_ready_issues(self):
        """Step 10.5 must identify newly unblocked/ready issues."""
        step105_text = self._extract_step_text(r"###\s+Step\s+10\.5:")
        lower = step105_text.lower()
        self.assertTrue(
            "ready" in lower or "unblock" in lower or "next" in lower,
            "Step 10.5 missing ready/unblocked issue identification",
        )

    def test_post_merge_best_effort(self):
        """Step 10.5 must not block deployment on DAG update failure."""
        step105_text = self._extract_step_text(r"###\s+Step\s+10\.5:")
        lower = step105_text.lower()
        self.assertTrue(
            "best effort" in lower or "best-effort" in lower
            or ("fail" in lower and ("warn" in lower or "proceed" in lower or "block" in lower)),
            "Step 10.5 missing best-effort failure handling",
        )

    def test_completion_summary_has_next_ready(self):
        """Completion Summary must include next ready issues."""
        # Find Completion Summary section
        summary_text = ""
        in_section = False
        for line in self.lines:
            if "Completion Summary" in line:
                in_section = True
                continue
            if in_section and line.startswith("## "):
                break
            if in_section:
                summary_text += line + "\n"
        lower = summary_text.lower()
        self.assertTrue(
            "next" in lower or "ready" in lower,
            "Completion Summary missing next ready issues",
        )

    def test_orchestration_flow_includes_new_steps(self):
        """Orchestration flow diagram must include Steps 1.3 and 10.5."""
        # Find the orchestration flow block
        flow_text = ""
        in_flow = False
        for line in self.lines:
            if "ISSUE-IMPL LIFECYCLE" in line:
                in_flow = True
            if in_flow:
                flow_text += line + "\n"
            if in_flow and line.strip().startswith("└"):
                break
        self.assertIn("1.3", flow_text, "Orchestration flow missing Step 1.3")
        self.assertIn("10.5", flow_text, "Orchestration flow missing Step 10.5")

    def test_issue_dag_referenced(self):
        """SKILL.md must reference /issue-dag for DAG operations."""
        self.assertIn(
            "issue-dag",
            self.text,
            "/issue-dag integration not referenced in SKILL.md",
        )

    def _extract_step_text(self, step_pattern):
        """Extract text content of a step section."""
        text = ""
        in_step = False
        for line in self.lines:
            if re.match(step_pattern, line):
                in_step = True
                continue
            if in_step and line.startswith("### Step"):
                break
            if in_step:
                text += line + "\n"
        return text


class TestLintSkillIntegration(unittest.TestCase):
    """Run lint_skill.py and verify it passes."""

    def test_lint_passes(self):
        """lint_skill.py should pass on the issue-impl skill without new errors."""
        lint_script = Path(__file__).parent.parent.parent / "issue" / "scripts" / "lint_skill.py"
        if not lint_script.exists():
            self.skipTest("lint_skill.py not found")

        # Known pre-existing lint issues (not introduced by Phase 5)
        KNOWN_ISSUES = {
            "ISSUE_RESULT_BEGIN:create:jira",
        }

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
