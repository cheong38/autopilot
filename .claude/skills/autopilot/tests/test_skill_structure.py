#!/usr/bin/env python3
"""Structural validation tests for the autopilot skill."""

import re
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"

REQUIRED_REFERENCES = [
    "ingest-formats.md",
    "verification-matrix.md",
    "self-review-criteria.md",
    "self-review-prompt-template.md",
    "agent-delegation.md",
    "resume-protocol.md",
    "simple-path.md",
    "error-recovery.md",
]

REQUIRED_SCRIPTS = [
    "autopilot-state.py",
    "checklist.py",
    "test_prompts.py",
]


class TestSkillStructure(unittest.TestCase):
    """Validate autopilot skill directory structure and SKILL.md content."""

    def test_skill_md_exists(self):
        """SKILL.md file exists."""
        self.assertTrue(SKILL_MD.exists(), f"SKILL.md not found at {SKILL_MD}")

    def test_yaml_frontmatter(self):
        """SKILL.md has valid YAML frontmatter with required fields."""
        text = SKILL_MD.read_text()
        fm_match = re.match(r"^---\s*\n(.*?)^---", text, re.MULTILINE | re.DOTALL)
        self.assertIsNotNone(fm_match, "YAML frontmatter not found")
        fm = fm_match.group(1)
        self.assertIn("name:", fm, "Missing 'name' in frontmatter")
        self.assertIn("description:", fm, "Missing 'description' in frontmatter")
        # Verify name is 'autopilot'
        name_match = re.search(r"^name:\s*(\S+)", fm, re.MULTILINE)
        self.assertIsNotNone(name_match)
        self.assertEqual(name_match.group(1), "autopilot")

    def test_required_sections(self):
        """SKILL.md contains all required top-level sections."""
        text = SKILL_MD.read_text()
        required_sections = [
            "## Usage",
            "## Prerequisites",
            "## Configuration",
            "## Dependencies & References",
            "## Maintenance",
        ]
        for section in required_sections:
            self.assertIn(section, text, f"Missing section: {section}")

    def test_reference_files_exist(self):
        """All reference files exist in references/ directory."""
        refs_dir = SKILL_DIR / "references"
        self.assertTrue(refs_dir.is_dir(), "references/ directory not found")
        for ref_file in REQUIRED_REFERENCES:
            path = refs_dir / ref_file
            self.assertTrue(path.exists(), f"Missing reference: {ref_file}")

    def test_script_files_exist(self):
        """All script files exist in scripts/ directory."""
        scripts_dir = SKILL_DIR / "scripts"
        self.assertTrue(scripts_dir.is_dir(), "scripts/ directory not found")
        for script_file in REQUIRED_SCRIPTS:
            path = scripts_dir / script_file
            self.assertTrue(path.exists(), f"Missing script: {script_file}")

    def test_tests_directory_exists(self):
        """tests/ directory exists."""
        tests_dir = SKILL_DIR / "tests"
        self.assertTrue(tests_dir.is_dir(), "tests/ directory not found")

    def test_skill_md_line_count(self):
        """SKILL.md is under 550 lines (progressive disclosure)."""
        text = SKILL_MD.read_text()
        line_count = len(text.splitlines())
        self.assertLessEqual(
            line_count, 550,
            f"SKILL.md has {line_count} lines, exceeds 550-line limit",
        )

    def test_trigger_in_frontmatter(self):
        """Frontmatter includes trigger and keywords."""
        text = SKILL_MD.read_text()
        fm_match = re.match(r"^---\s*\n(.*?)^---", text, re.MULTILINE | re.DOTALL)
        fm = fm_match.group(1)
        self.assertIn("Trigger:", fm, "Missing 'Trigger' in frontmatter description")
        self.assertIn("Keywords:", fm, "Missing 'Keywords' in frontmatter description")


if __name__ == "__main__":
    unittest.main()
