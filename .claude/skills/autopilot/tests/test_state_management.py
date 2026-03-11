#!/usr/bin/env python3
"""Tests for autopilot-state.py — state file CRUD operations."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Add scripts directory to path
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import importlib
state_mod = importlib.import_module("autopilot-state")


class TestStateManagement(unittest.TestCase):
    """Test autopilot state CRUD operations."""

    def setUp(self):
        """Create a temporary directory for state files."""
        self.tmp_dir = tempfile.mkdtemp()
        self.state_path = Path(self.tmp_dir) / ".claude" / "autopilot-state.json"
        # Patch state_file_path to use temp dir
        self._patcher = patch.object(
            state_mod, "state_file_path", return_value=self.state_path,
        )
        self._patcher.start()

    def tearDown(self):
        """Clean up temporary files."""
        self._patcher.stop()
        if self.state_path.exists():
            self.state_path.unlink()
        # Remove parent dirs if empty
        for parent in [self.state_path.parent, Path(self.tmp_dir)]:
            try:
                parent.rmdir()
            except OSError:
                pass

    def test_create_state(self):
        """Create a new state file with required fields."""
        state = state_mod.create_state(
            meta_issue=100,
            meta_url="https://github.com/org/repo/issues/100",
            provider="github",
            source="prd.md",
        )
        self.assertTrue(self.state_path.exists())
        self.assertEqual(state["meta_issue"]["number"], 100)
        self.assertEqual(state["provider"], "github")
        self.assertEqual(state["source"], "prd.md")
        self.assertEqual(state["status"], "in_progress")
        self.assertEqual(state["current_step"], "META-ISSUE")
        self.assertIsNone(state["current_issue"])
        self.assertEqual(state["followup_round"], 0)
        self.assertEqual(state["requirements"], [])
        self.assertEqual(state["issues"], [])
        self.assertIsNotNone(state["session_id"])

    def test_create_state_already_exists(self):
        """Attempting to create when file exists raises FileExistsError."""
        state_mod.create_state(100, "url", "github", "src")
        with self.assertRaises(FileExistsError):
            state_mod.create_state(101, "url2", "github", "src2")

    def test_read_state(self):
        """Read an existing state file."""
        state_mod.create_state(100, "url", "github", "src")
        state = state_mod.read_state()
        self.assertEqual(state["meta_issue"]["number"], 100)
        self.assertEqual(state["provider"], "github")

    def test_read_missing_state_file(self):
        """Reading a non-existent state file raises FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            state_mod.read_state()

    def test_update_step(self):
        """Update current_step field."""
        state_mod.create_state(100, "url", "github", "src")
        state = state_mod.update_field("current_step", "INGEST")
        self.assertEqual(state["current_step"], "INGEST")

    def test_update_current_issue(self):
        """Update current_issue with integer coercion."""
        state_mod.create_state(100, "url", "github", "src")
        state = state_mod.update_field("current_issue", "42")
        self.assertEqual(state["current_issue"], 42)

    def test_update_null_value(self):
        """Update a field to null."""
        state_mod.create_state(100, "url", "github", "src")
        state_mod.update_field("current_issue", "42")
        state = state_mod.update_field("current_issue", "null")
        self.assertIsNone(state["current_issue"])

    def test_add_requirement(self):
        """Add a requirement to the requirements array."""
        state_mod.create_state(100, "url", "github", "src")
        state = state_mod.add_requirement(
            req_id="R-001",
            text="User can log in",
            confidence=95,
            verification_method="playwright",
            verification_status="pending",
        )
        self.assertEqual(len(state["requirements"]), 1)
        req = state["requirements"][0]
        self.assertEqual(req["id"], "R-001")
        self.assertEqual(req["text"], "User can log in")
        self.assertEqual(req["confidence"], 95)
        self.assertEqual(req["verification_method"], "playwright")

    def test_add_multiple_requirements(self):
        """Add multiple requirements."""
        state_mod.create_state(100, "url", "github", "src")
        state_mod.add_requirement("R-001", "Login")
        state = state_mod.add_requirement("R-002", "Signup")
        self.assertEqual(len(state["requirements"]), 2)

    def test_add_issue(self):
        """Add an issue to the issues array."""
        state_mod.create_state(100, "url", "github", "src")
        state = state_mod.add_issue(
            issue_id=42,
            url="https://github.com/org/repo/issues/42",
            issue_type="story",
            title="Login feature",
            requirement_ids=["R-001"],
            verification_methods=["playwright"],
        )
        self.assertEqual(len(state["issues"]), 1)
        issue = state["issues"][0]
        self.assertEqual(issue["id"], 42)
        self.assertEqual(issue["type"], "story")
        self.assertEqual(issue["status"], "open")
        self.assertFalse(issue["verified"])
        self.assertEqual(issue["requirement_ids"], ["R-001"])

    def test_update_issue_status(self):
        """Update an issue's status."""
        state_mod.create_state(100, "url", "github", "src")
        state_mod.add_issue(42, "url", "story", "Login")
        state = state_mod.update_issue(42, status="closed")
        self.assertEqual(state["issues"][0]["status"], "closed")

    def test_update_issue_verified(self):
        """Update an issue's verified flag."""
        state_mod.create_state(100, "url", "github", "src")
        state_mod.add_issue(42, "url", "story", "Login")
        state = state_mod.update_issue(42, verified=True)
        self.assertTrue(state["issues"][0]["verified"])

    def test_update_issue_not_found(self):
        """Updating a non-existent issue raises ValueError."""
        state_mod.create_state(100, "url", "github", "src")
        with self.assertRaises(ValueError):
            state_mod.update_issue(999, status="closed")

    def test_query_open_issues(self):
        """Query only open issues."""
        state_mod.create_state(100, "url", "github", "src")
        state_mod.add_issue(42, "url", "story", "Login")
        state_mod.add_issue(43, "url", "task", "Setup")
        state_mod.update_issue(42, status="closed")
        issues = state_mod.query_issues(open_only=True)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["id"], 43)

    def test_query_unverified_issues(self):
        """Query unverified issues."""
        state_mod.create_state(100, "url", "github", "src")
        state_mod.add_issue(42, "url", "story", "Login")
        state_mod.add_issue(43, "url", "task", "Setup")
        state_mod.update_issue(42, verified=True)
        issues = state_mod.query_issues(unverified=True)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["id"], 43)

    def test_query_verified_issues(self):
        """Query verified issues."""
        state_mod.create_state(100, "url", "github", "src")
        state_mod.add_issue(42, "url", "story", "Login")
        state_mod.update_issue(42, verified=True)
        issues = state_mod.query_issues(verified=True)
        self.assertEqual(len(issues), 1)

    def test_state_file_path_resolution(self):
        """State file path is absolute."""
        path = state_mod.state_file_path()
        self.assertTrue(path.is_absolute())
        self.assertTrue(str(path).endswith("autopilot-state.json"))

    def test_create_state_has_complexity_null(self):
        """Test 1.1: create_state includes complexity: null."""
        state = state_mod.create_state(100, "url", "github", "src")
        self.assertIn("complexity", state)
        self.assertIsNone(state["complexity"])

    def test_update_complexity_simple(self):
        """Test 1.2: update_field('complexity', 'simple') stores 'simple'."""
        state_mod.create_state(100, "url", "github", "src")
        state = state_mod.update_field("complexity", "simple")
        self.assertEqual(state["complexity"], "simple")

    def test_update_complexity_complex(self):
        """Test 1.3: update_field('complexity', 'complex') stores 'complex'."""
        state_mod.create_state(100, "url", "github", "src")
        state = state_mod.update_field("complexity", "complex")
        self.assertEqual(state["complexity"], "complex")

    def test_state_json_roundtrip(self):
        """State file is valid JSON after all operations."""
        state_mod.create_state(100, "url", "github", "src")
        state_mod.add_requirement("R-001", "Login")
        state_mod.add_issue(42, "url", "story", "Login")
        state_mod.update_issue(42, status="closed", verified=True)
        state_mod.update_field("current_step", "REPORT")

        raw = self.state_path.read_text()
        state = json.loads(raw)
        self.assertEqual(state["current_step"], "REPORT")
        self.assertEqual(state["issues"][0]["status"], "closed")


if __name__ == "__main__":
    unittest.main()
