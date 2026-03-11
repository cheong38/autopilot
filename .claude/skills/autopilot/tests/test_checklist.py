#!/usr/bin/env python3
"""Tests for checklist.py — checklist CRUD operations."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import importlib
checklist_mod = importlib.import_module("checklist")


class TestChecklistSimple(unittest.TestCase):
    """Test autopilot-simple checklist operations."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self._patcher = patch.object(
            checklist_mod, "CHECKLIST_DIR", Path(self.tmp_dir),
        )
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_create_simple_checklist_has_6_steps(self):
        """Test 1.5: create_checklist(skill='autopilot-simple') creates 6-step checklist."""
        result = checklist_mod.create_checklist("autopilot-simple", "99")
        self.assertIn("Created:", result)
        path = checklist_mod.checklist_path("autopilot-simple", "99")
        self.assertTrue(path.exists())
        content = path.read_text()
        # Count top-level unchecked items (not indented)
        items = [l for l in content.splitlines() if l.startswith("- [ ]")]
        self.assertEqual(len(items), 6)

    def test_simple_checklist_contains_all_steps(self):
        """Test 1.6: generated checklist contains all 6 steps."""
        checklist_mod.create_checklist("autopilot-simple", "99")
        content = checklist_mod.read_checklist("autopilot-simple", "99")
        for step_name in ["CLASSIFY", "WHY-CONTEXT", "ISSUE", "IMPL", "VERIFY", "REPORT"]:
            self.assertIn(step_name, content, f"Missing step: {step_name}")

    def test_update_simple_checklist_step(self):
        """Test 1.7: update_step for autopilot-simple works."""
        checklist_mod.create_checklist("autopilot-simple", "99")
        result = checklist_mod.update_step("autopilot-simple", "99", "1", "done")
        self.assertIn("done", result)
        content = checklist_mod.read_checklist("autopilot-simple", "99")
        self.assertIn("- [x] 1.", content)

    def test_existing_autopilot_checklist_unchanged(self):
        """Test 1.8: existing autopilot checklist behavior unchanged (regression)."""
        checklist_mod.create_checklist("autopilot", "50")
        content = checklist_mod.read_checklist("autopilot", "50")
        # Should have 21 top-level steps
        items = [l for l in content.splitlines() if l.startswith("- [ ]")]
        self.assertEqual(len(items), 21)
        # Should contain original step names
        self.assertIn("META-ISSUE (Step 0)", content)
        self.assertIn("REPORT (Step 12)", content)
        # Update should work
        result = checklist_mod.update_step("autopilot", "50", "1", "done")
        self.assertIn("done", result)
        content = checklist_mod.read_checklist("autopilot", "50")
        self.assertIn("- [x] 1.", content)

    def test_checklist_path_uses_skill_prefix(self):
        """checklist_path includes skill name in filename."""
        path_a = checklist_mod.checklist_path("autopilot", "10")
        path_s = checklist_mod.checklist_path("autopilot-simple", "10")
        self.assertIn("autopilot-10", path_a.name)
        self.assertIn("autopilot-simple-10", path_s.name)
        self.assertNotEqual(path_a, path_s)

    def test_duplicate_create_returns_already_exists(self):
        """Duplicate create_checklist returns 'already exists' message."""
        checklist_mod.create_checklist("autopilot-simple", "99")
        result = checklist_mod.create_checklist("autopilot-simple", "99")
        self.assertIn("already exists", result)

    def test_update_step_failed_status(self):
        """update_step with status='failed' marks step with [!]."""
        checklist_mod.create_checklist("autopilot-simple", "99")
        checklist_mod.update_step("autopilot-simple", "99", "1", "failed")
        content = checklist_mod.read_checklist("autopilot-simple", "99")
        self.assertIn("- [!] 1.", content)

    def test_update_step_pending_resets_done(self):
        """update_step with status='pending' resets [x] back to [ ]."""
        checklist_mod.create_checklist("autopilot-simple", "99")
        checklist_mod.update_step("autopilot-simple", "99", "1", "done")
        content = checklist_mod.read_checklist("autopilot-simple", "99")
        self.assertIn("- [x] 1.", content)
        checklist_mod.update_step("autopilot-simple", "99", "1", "pending")
        content = checklist_mod.read_checklist("autopilot-simple", "99")
        self.assertIn("- [ ] 1.", content)

    def test_update_step_pending_resets_failed(self):
        """update_step with status='pending' resets [!] back to [ ]."""
        checklist_mod.create_checklist("autopilot-simple", "99")
        checklist_mod.update_step("autopilot-simple", "99", "1", "failed")
        checklist_mod.update_step("autopilot-simple", "99", "1", "pending")
        content = checklist_mod.read_checklist("autopilot-simple", "99")
        self.assertIn("- [ ] 1.", content)

    def test_update_step_done_recovers_from_failed(self):
        """update_step with status='done' can recover a [!] step to [x]."""
        checklist_mod.create_checklist("autopilot-simple", "99")
        checklist_mod.update_step("autopilot-simple", "99", "1", "failed")
        checklist_mod.update_step("autopilot-simple", "99", "1", "done")
        content = checklist_mod.read_checklist("autopilot-simple", "99")
        self.assertIn("- [x] 1.", content)

    def test_read_nonexistent_checklist(self):
        """read_checklist for nonexistent file returns 'not found'."""
        result = checklist_mod.read_checklist("autopilot-simple", "999")
        self.assertIn("not found", result)

    def test_update_nonexistent_checklist(self):
        """update_step for nonexistent file returns 'not found'."""
        result = checklist_mod.update_step("autopilot-simple", "999", "1", "done")
        self.assertIn("not found", result)


class TestSubtasks(unittest.TestCase):
    """Test sub-task checklist features (Phase 3)."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self._patcher = patch.object(
            checklist_mod, "CHECKLIST_DIR", Path(self.tmp_dir),
        )
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    # 3.1: sub-task count for complex checklist
    def test_complex_checklist_has_subtasks(self):
        """Complex checklist includes indented sub-tasks for each step."""
        checklist_mod.create_checklist("autopilot", "100")
        content = checklist_mod.read_checklist("autopilot", "100")
        # Count indented sub-task items
        subtask_lines = [l for l in content.splitlines() if l.startswith("  - [ ]")]
        # Total sub-tasks across all 21 steps
        expected = sum(len(v) for v in checklist_mod.AUTOPILOT_SUBTASKS.values())
        self.assertEqual(len(subtask_lines), expected)
        self.assertGreater(expected, 0)

    # 3.2: sub-task count for simple checklist
    def test_simple_checklist_has_subtasks(self):
        """Simple checklist includes indented sub-tasks for each step."""
        checklist_mod.create_checklist("autopilot-simple", "100")
        content = checklist_mod.read_checklist("autopilot-simple", "100")
        subtask_lines = [l for l in content.splitlines() if l.startswith("  - [ ]")]
        expected = sum(len(v) for v in checklist_mod.AUTOPILOT_SIMPLE_SUBTASKS.values())
        self.assertEqual(len(subtask_lines), expected)
        self.assertGreater(expected, 0)

    # 3.3: sub-task update
    def test_subtask_update_marks_done(self):
        """update_step('1.3', 'done') marks the sub-task [x]."""
        checklist_mod.create_checklist("autopilot", "100")
        checklist_mod.update_step("autopilot", "100", "1.3", "done")
        content = checklist_mod.read_checklist("autopilot", "100")
        self.assertIn("  - [x] 1.3 ", content)
        # Other sub-tasks remain unchecked
        self.assertIn("  - [ ] 1.1 ", content)
        self.assertIn("  - [ ] 1.2 ", content)

    # 3.4: check_step COMPLETE
    def test_check_step_complete(self):
        """check_step returns COMPLETE when all sub-tasks are done."""
        checklist_mod.create_checklist("autopilot", "100")
        subtasks = checklist_mod.AUTOPILOT_SUBTASKS[1]
        for j in range(1, len(subtasks) + 1):
            checklist_mod.update_step("autopilot", "100", f"1.{j}", "done")
        result = checklist_mod.check_step("autopilot", "100", 1)
        self.assertEqual(result, "COMPLETE")

    # 3.5: check_step INCOMPLETE
    def test_check_step_incomplete(self):
        """check_step returns INCOMPLETE with count when some sub-tasks remain."""
        checklist_mod.create_checklist("autopilot", "100")
        checklist_mod.update_step("autopilot", "100", "1.1", "done")
        checklist_mod.update_step("autopilot", "100", "1.2", "done")
        result = checklist_mod.check_step("autopilot", "100", 1)
        total = len(checklist_mod.AUTOPILOT_SUBTASKS[1])
        self.assertIn("INCOMPLETE", result)
        self.assertIn(f"2/{total}", result)

    # 3.6: top-level step update backward compat
    def test_toplevel_step_update_backward_compat(self):
        """Top-level step update('1', 'done') still works with sub-tasks present."""
        checklist_mod.create_checklist("autopilot", "100")
        result = checklist_mod.update_step("autopilot", "100", "1", "done")
        self.assertIn("done", result)
        content = checklist_mod.read_checklist("autopilot", "100")
        self.assertIn("- [x] 1.", content)
        # Sub-tasks should remain unchanged (unchecked)
        self.assertIn("  - [ ] 1.1 ", content)

    # 3.7: sub-task failed/pending state transitions
    def test_subtask_failed_pending_transitions(self):
        """Sub-task supports failed and pending state transitions."""
        checklist_mod.create_checklist("autopilot", "100")
        # Mark failed
        checklist_mod.update_step("autopilot", "100", "1.3", "failed")
        content = checklist_mod.read_checklist("autopilot", "100")
        self.assertIn("  - [!] 1.3 ", content)
        # Reset to pending
        checklist_mod.update_step("autopilot", "100", "1.3", "pending")
        content = checklist_mod.read_checklist("autopilot", "100")
        self.assertIn("  - [ ] 1.3 ", content)
        # Mark done from pending
        checklist_mod.update_step("autopilot", "100", "1.3", "done")
        content = checklist_mod.read_checklist("autopilot", "100")
        self.assertIn("  - [x] 1.3 ", content)
        # Mark failed from done
        checklist_mod.update_step("autopilot", "100", "1.3", "failed")
        content = checklist_mod.read_checklist("autopilot", "100")
        self.assertIn("  - [!] 1.3 ", content)
        # Recover done from failed
        checklist_mod.update_step("autopilot", "100", "1.3", "done")
        content = checklist_mod.read_checklist("autopilot", "100")
        self.assertIn("  - [x] 1.3 ", content)

    def test_check_step_incomplete_with_failed(self):
        """check_step reports failed count when sub-tasks are [!]."""
        checklist_mod.create_checklist("autopilot", "100")
        checklist_mod.update_step("autopilot", "100", "1.1", "done")
        checklist_mod.update_step("autopilot", "100", "1.2", "done")
        checklist_mod.update_step("autopilot", "100", "1.3", "failed")
        result = checklist_mod.check_step("autopilot", "100", 1)
        total = len(checklist_mod.AUTOPILOT_SUBTASKS[1])
        self.assertIn("INCOMPLETE", result)
        self.assertIn(f"2/{total} done", result)
        self.assertIn("1 failed", result)

    def test_check_step_incomplete_without_failed(self):
        """check_step omits failed count when no sub-tasks are [!]."""
        checklist_mod.create_checklist("autopilot", "100")
        checklist_mod.update_step("autopilot", "100", "1.1", "done")
        result = checklist_mod.check_step("autopilot", "100", 1)
        self.assertIn("INCOMPLETE", result)
        self.assertNotIn("failed", result)

    def test_check_step_nonexistent_checklist(self):
        """check_step on nonexistent checklist returns 'not found'."""
        result = checklist_mod.check_step("autopilot", "999", 1)
        self.assertIn("not found", result)

    def test_check_step_no_subtasks_defined(self):
        """check_step for step with no sub-tasks returns appropriate message."""
        checklist_mod.create_checklist("autopilot", "100")
        result = checklist_mod.check_step("autopilot", "100", 99)
        self.assertIn("No sub-tasks defined", result)

    def test_simple_subtask_update(self):
        """Sub-task update works for autopilot-simple."""
        checklist_mod.create_checklist("autopilot-simple", "100")
        checklist_mod.update_step("autopilot-simple", "100", "1.1", "done")
        content = checklist_mod.read_checklist("autopilot-simple", "100")
        self.assertIn("  - [x] 1.1 ", content)

    def test_simple_check_step_complete(self):
        """check_step works for autopilot-simple."""
        checklist_mod.create_checklist("autopilot-simple", "100")
        subtasks = checklist_mod.AUTOPILOT_SIMPLE_SUBTASKS[1]
        for j in range(1, len(subtasks) + 1):
            checklist_mod.update_step("autopilot-simple", "100", f"1.{j}", "done")
        result = checklist_mod.check_step("autopilot-simple", "100", 1)
        self.assertEqual(result, "COMPLETE")


class TestReadySubtasks(unittest.TestCase):
    """Test ready_subtasks() dependency graph queries."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self._patcher = patch.object(
            checklist_mod, "CHECKLIST_DIR", Path(self.tmp_dir),
        )
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_ready_subtasks_returns_entry_points(self):
        """ready_subtasks returns deps=[] sub-tasks when nothing is done."""
        checklist_mod.create_checklist("autopilot", "200")
        result = checklist_mod.ready_subtasks("autopilot", "200", 1)
        # Step 1: only 1.1 has deps=[]
        self.assertEqual(result, ["1.1"])

    def test_ready_subtasks_after_partial_done(self):
        """After marking some done, next unblocked sub-tasks are returned."""
        checklist_mod.create_checklist("autopilot", "200")
        checklist_mod.update_step("autopilot", "200", "1.1", "done")
        result = checklist_mod.ready_subtasks("autopilot", "200", 1)
        # 1.2 depends on 1.1 (done) → ready
        self.assertEqual(result, ["1.2"])

    def test_ready_subtasks_parallel(self):
        """After 1.3 done, 1.4/1.5/1.6/1.7 are all ready (parallel)."""
        checklist_mod.create_checklist("autopilot", "200")
        for sub_id in ["1.1", "1.2", "1.3"]:
            checklist_mod.update_step("autopilot", "200", sub_id, "done")
        result = checklist_mod.ready_subtasks("autopilot", "200", 1)
        self.assertEqual(sorted(result), ["1.4", "1.5", "1.6", "1.7"])

    def test_ready_subtasks_blocked_by_failed(self):
        """Failed dep blocks downstream — sub-task is NOT ready."""
        checklist_mod.create_checklist("autopilot", "200")
        checklist_mod.update_step("autopilot", "200", "1.1", "failed")
        result = checklist_mod.ready_subtasks("autopilot", "200", 1)
        # 1.1 is failed (not pending), 1.2 depends on 1.1 which is not done
        self.assertEqual(result, [])

    def test_ready_subtasks_all_done(self):
        """When all sub-tasks are done, returns empty list."""
        checklist_mod.create_checklist("autopilot", "200")
        subtasks = checklist_mod.AUTOPILOT_SUBTASKS[1]
        for sub in subtasks:
            checklist_mod.update_step("autopilot", "200", sub["id"], "done")
        result = checklist_mod.ready_subtasks("autopilot", "200", 1)
        self.assertEqual(result, [])

    def test_ready_subtasks_nonexistent_checklist(self):
        """Nonexistent checklist returns empty list."""
        result = checklist_mod.ready_subtasks("autopilot", "999", 1)
        self.assertEqual(result, [])

    def test_ready_subtasks_simple_path(self):
        """ready_subtasks works for autopilot-simple skill."""
        checklist_mod.create_checklist("autopilot-simple", "200")
        result = checklist_mod.ready_subtasks("autopilot-simple", "200", 1)
        # Step 1 of simple: 1.1 has deps=[]
        self.assertEqual(result, ["1.1"])
        # Mark 1.1 done → 1.2 ready
        checklist_mod.update_step("autopilot-simple", "200", "1.1", "done")
        result = checklist_mod.ready_subtasks("autopilot-simple", "200", 1)
        self.assertEqual(result, ["1.2"])

    def test_ready_subtasks_multi_dep_join(self):
        """Sub-task with multiple deps is only ready when ALL deps are done."""
        # Step 8 (CREATE): 8.4 depends on ["8.2", "8.3"]
        checklist_mod.create_checklist("autopilot", "200")
        checklist_mod.update_step("autopilot", "200", "8.1", "done")
        # 8.2 and 8.3 are now ready (both depend on 8.1)
        result = checklist_mod.ready_subtasks("autopilot", "200", 8)
        self.assertIn("8.2", result)
        self.assertIn("8.3", result)
        self.assertNotIn("8.4", result)  # blocked: 8.3 still pending
        # Mark only 8.2 done — 8.4 still blocked (8.3 not done)
        checklist_mod.update_step("autopilot", "200", "8.2", "done")
        result = checklist_mod.ready_subtasks("autopilot", "200", 8)
        self.assertNotIn("8.4", result)
        self.assertIn("8.3", result)
        # Mark 8.3 done — now 8.4 is ready (all deps satisfied)
        checklist_mod.update_step("autopilot", "200", "8.3", "done")
        result = checklist_mod.ready_subtasks("autopilot", "200", 8)
        self.assertEqual(result, ["8.4"])

    def test_ready_subtasks_undefined_step(self):
        """Undefined step_num returns empty list."""
        checklist_mod.create_checklist("autopilot", "200")
        result = checklist_mod.ready_subtasks("autopilot", "200", 99)
        self.assertEqual(result, [])


class TestDataStructureValidation(unittest.TestCase):
    """Validate sub-task data structure integrity."""

    def test_data_structure_has_required_keys(self):
        """Every node in AUTOPILOT_SUBTASKS has id, name, deps keys."""
        for step_num, subtasks in checklist_mod.AUTOPILOT_SUBTASKS.items():
            for sub in subtasks:
                self.assertIn("id", sub, f"Step {step_num}: missing 'id'")
                self.assertIn("name", sub, f"Step {step_num}: missing 'name'")
                self.assertIn("deps", sub, f"Step {step_num}: missing 'deps'")
                self.assertIsInstance(sub["deps"], list)

    def test_data_structure_simple_has_required_keys(self):
        """Every node in AUTOPILOT_SIMPLE_SUBTASKS has id, name, deps keys."""
        for step_num, subtasks in checklist_mod.AUTOPILOT_SIMPLE_SUBTASKS.items():
            for sub in subtasks:
                self.assertIn("id", sub, f"Step {step_num}: missing 'id'")
                self.assertIn("name", sub, f"Step {step_num}: missing 'name'")
                self.assertIn("deps", sub, f"Step {step_num}: missing 'deps'")
                self.assertIsInstance(sub["deps"], list)

    def test_deps_reference_valid_ids(self):
        """All deps reference existing IDs within the same step."""
        for step_num, subtasks in checklist_mod.AUTOPILOT_SUBTASKS.items():
            valid_ids = {sub["id"] for sub in subtasks}
            for sub in subtasks:
                for dep in sub["deps"]:
                    self.assertIn(
                        dep, valid_ids,
                        f"Step {step_num}, sub {sub['id']}: dep '{dep}' not in step",
                    )

    def test_deps_reference_valid_ids_simple(self):
        """All deps in simple subtasks reference existing IDs within same step."""
        for step_num, subtasks in checklist_mod.AUTOPILOT_SIMPLE_SUBTASKS.items():
            valid_ids = {sub["id"] for sub in subtasks}
            for sub in subtasks:
                for dep in sub["deps"]:
                    self.assertIn(
                        dep, valid_ids,
                        f"Step {step_num}, sub {sub['id']}: dep '{dep}' not in step",
                    )

    def test_no_self_deps(self):
        """No sub-task depends on itself."""
        for source in [checklist_mod.AUTOPILOT_SUBTASKS, checklist_mod.AUTOPILOT_SIMPLE_SUBTASKS]:
            for step_num, subtasks in source.items():
                for sub in subtasks:
                    self.assertNotIn(
                        sub["id"], sub["deps"],
                        f"Step {step_num}, sub {sub['id']}: self-dependency",
                    )

    def test_each_step_has_entry_point(self):
        """Each step has at least one sub-task with deps=[]."""
        for source in [checklist_mod.AUTOPILOT_SUBTASKS, checklist_mod.AUTOPILOT_SIMPLE_SUBTASKS]:
            for step_num, subtasks in source.items():
                entry_points = [s for s in subtasks if s["deps"] == []]
                self.assertGreater(
                    len(entry_points), 0,
                    f"Step {step_num}: no entry point (deps=[])",
                )


if __name__ == "__main__":
    unittest.main()
