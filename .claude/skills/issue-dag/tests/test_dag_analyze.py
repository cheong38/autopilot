#!/usr/bin/env python3
"""Unit tests for dag-analyze.py CRUD operations.

Uses only Python standard library unittest. No external packages.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = str(Path(__file__).parent.parent / "scripts" / "dag-analyze.py")


def run_cmd(*args, dag_file=None, expect_fail=False):
    """Run dag-analyze.py with arguments and return (returncode, stdout, stderr)."""
    cmd = [sys.executable, SCRIPT]
    if dag_file:
        cmd.extend(["--dag-file", str(dag_file)])
    cmd.extend(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if not expect_fail and result.returncode != 0:
        raise AssertionError(
            f"Command failed: {' '.join(cmd)}\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return result.returncode, result.stdout, result.stderr


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


class TestInit(unittest.TestCase):
    def test_init_creates_valid_dag(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        os.unlink(path)  # remove so init can create it
        try:
            run_cmd("init", "--repo", "owner/repo", "--force", dag_file=path)
            dag = load_json(path)
            self.assertEqual(dag["version"], 1)
            self.assertEqual(dag["repo"], "owner/repo")
            self.assertIsInstance(dag["nodes"], dict)
            self.assertIsInstance(dag["edges"], list)
            self.assertEqual(len(dag["nodes"]), 0)
            self.assertEqual(len(dag["edges"]), 0)
        finally:
            os.unlink(path)

    def test_init_without_force_fails_on_existing(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump({"version": 1}, f)
            path = f.name
        try:
            rc, _, stderr = run_cmd("init", "--repo", "o/r", dag_file=path, expect_fail=True)
            self.assertNotEqual(rc, 0)
            self.assertIn("already exists", stderr)
        finally:
            os.unlink(path)


class TestAddNode(unittest.TestCase):
    def setUp(self):
        self.tmpfile = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.path = self.tmpfile.name
        self.tmpfile.close()
        os.unlink(self.path)
        run_cmd("init", "--repo", "test/repo", "--force", dag_file=self.path)

    def tearDown(self):
        if os.path.exists(self.path):
            os.unlink(self.path)

    def test_add_node_basic(self):
        run_cmd("add-node", "--id", "42", "--title", "Test Issue",
                "--type", "story", dag_file=self.path)
        dag = load_json(self.path)
        self.assertIn("42", dag["nodes"])
        self.assertEqual(dag["nodes"]["42"]["title"], "Test Issue")
        self.assertEqual(dag["nodes"]["42"]["type"], "story")
        self.assertEqual(dag["nodes"]["42"]["status"], "open")

    def test_add_node_with_keywords_and_paths(self):
        run_cmd("add-node", "--id", "43", "--title", "Auth",
                "--type", "task", "--keywords", "auth,login",
                "--paths", "src/auth/*,src/middleware/*", dag_file=self.path)
        dag = load_json(self.path)
        node = dag["nodes"]["43"]
        self.assertEqual(node["keywords"], ["auth", "login"])
        self.assertEqual(node["touched_paths"], ["src/auth/*", "src/middleware/*"])

    def test_add_duplicate_node_fails(self):
        run_cmd("add-node", "--id", "42", "--title", "First",
                "--type", "story", dag_file=self.path)
        rc, _, stderr = run_cmd("add-node", "--id", "42", "--title", "Second",
                                "--type", "task", dag_file=self.path, expect_fail=True)
        self.assertNotEqual(rc, 0)
        self.assertIn("already exists", stderr)

    def test_add_node_invalid_type_fails(self):
        rc, _, _ = run_cmd("add-node", "--id", "1", "--title", "X",
                           "--type", "epic", dag_file=self.path, expect_fail=True)
        self.assertNotEqual(rc, 0)


class TestAddEdge(unittest.TestCase):
    def setUp(self):
        self.tmpfile = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.path = self.tmpfile.name
        self.tmpfile.close()
        os.unlink(self.path)
        run_cmd("init", "--repo", "test/repo", "--force", dag_file=self.path)
        run_cmd("add-node", "--id", "42", "--title", "A", "--type", "story", dag_file=self.path)
        run_cmd("add-node", "--id", "43", "--title", "B", "--type", "task", dag_file=self.path)

    def tearDown(self):
        if os.path.exists(self.path):
            os.unlink(self.path)

    def test_add_edge_depends_on(self):
        run_cmd("add-edge", "--from", "43", "--to", "42",
                "--type", "depends_on", dag_file=self.path)
        dag = load_json(self.path)
        self.assertEqual(len(dag["edges"]), 1)
        self.assertEqual(dag["edges"][0]["from"], "43")
        self.assertEqual(dag["edges"][0]["to"], "42")
        self.assertEqual(dag["edges"][0]["type"], "depends_on")

    def test_add_duplicate_edge_fails(self):
        run_cmd("add-edge", "--from", "43", "--to", "42",
                "--type", "depends_on", dag_file=self.path)
        rc, _, stderr = run_cmd("add-edge", "--from", "43", "--to", "42",
                                "--type", "depends_on", dag_file=self.path, expect_fail=True)
        self.assertNotEqual(rc, 0)
        self.assertIn("already exists", stderr)

    def test_add_edge_nonexistent_node_fails(self):
        rc, _, stderr = run_cmd("add-edge", "--from", "99", "--to", "42",
                                "--type", "depends_on", dag_file=self.path, expect_fail=True)
        self.assertNotEqual(rc, 0)
        self.assertIn("not found", stderr)


class TestRemoveNode(unittest.TestCase):
    def setUp(self):
        self.tmpfile = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.path = self.tmpfile.name
        self.tmpfile.close()
        os.unlink(self.path)
        run_cmd("init", "--repo", "test/repo", "--force", dag_file=self.path)
        run_cmd("add-node", "--id", "42", "--title", "A", "--type", "story", dag_file=self.path)
        run_cmd("add-node", "--id", "43", "--title", "B", "--type", "task", dag_file=self.path)
        run_cmd("add-edge", "--from", "43", "--to", "42",
                "--type", "depends_on", dag_file=self.path)

    def tearDown(self):
        if os.path.exists(self.path):
            os.unlink(self.path)

    def test_remove_node_and_edges(self):
        run_cmd("remove-node", "--id", "42", dag_file=self.path)
        dag = load_json(self.path)
        self.assertNotIn("42", dag["nodes"])
        self.assertEqual(len(dag["edges"]), 0)  # edge referencing 42 removed

    def test_remove_nonexistent_node_fails(self):
        rc, _, stderr = run_cmd("remove-node", "--id", "99",
                                dag_file=self.path, expect_fail=True)
        self.assertNotEqual(rc, 0)
        self.assertIn("not found", stderr)


class TestRemoveEdge(unittest.TestCase):
    def setUp(self):
        self.tmpfile = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.path = self.tmpfile.name
        self.tmpfile.close()
        os.unlink(self.path)
        run_cmd("init", "--repo", "test/repo", "--force", dag_file=self.path)
        run_cmd("add-node", "--id", "42", "--title", "A", "--type", "story", dag_file=self.path)
        run_cmd("add-node", "--id", "43", "--title", "B", "--type", "task", dag_file=self.path)
        run_cmd("add-edge", "--from", "43", "--to", "42",
                "--type", "depends_on", dag_file=self.path)

    def tearDown(self):
        if os.path.exists(self.path):
            os.unlink(self.path)

    def test_remove_edge(self):
        run_cmd("remove-edge", "--from", "43", "--to", "42", dag_file=self.path)
        dag = load_json(self.path)
        self.assertEqual(len(dag["edges"]), 0)

    def test_remove_nonexistent_edge_fails(self):
        rc, _, stderr = run_cmd("remove-edge", "--from", "42", "--to", "43",
                                dag_file=self.path, expect_fail=True)
        self.assertNotEqual(rc, 0)
        self.assertIn("not found", stderr)


class TestGetNode(unittest.TestCase):
    def setUp(self):
        self.tmpfile = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.path = self.tmpfile.name
        self.tmpfile.close()
        os.unlink(self.path)
        run_cmd("init", "--repo", "test/repo", "--force", dag_file=self.path)
        run_cmd("add-node", "--id", "42", "--title", "Auth", "--type", "story",
                "--keywords", "auth,login", dag_file=self.path)
        run_cmd("add-node", "--id", "43", "--title", "Login UI", "--type", "task", dag_file=self.path)
        run_cmd("add-edge", "--from", "43", "--to", "42",
                "--type", "depends_on", dag_file=self.path)

    def tearDown(self):
        if os.path.exists(self.path):
            os.unlink(self.path)

    def test_get_node_with_relations(self):
        _, stdout, _ = run_cmd("get-node", "--id", "42", dag_file=self.path)
        node = json.loads(stdout)
        self.assertEqual(node["id"], "42")
        self.assertEqual(node["title"], "Auth")
        self.assertEqual(node["blocked_by_this"], ["43"])  # 43 depends on 42
        self.assertEqual(node["depends_on"], [])

    def test_get_nonexistent_node_fails(self):
        rc, _, _ = run_cmd("get-node", "--id", "99",
                           dag_file=self.path, expect_fail=True)
        self.assertNotEqual(rc, 0)


class TestUpdateNode(unittest.TestCase):
    def setUp(self):
        self.tmpfile = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.path = self.tmpfile.name
        self.tmpfile.close()
        os.unlink(self.path)
        run_cmd("init", "--repo", "test/repo", "--force", dag_file=self.path)
        run_cmd("add-node", "--id", "42", "--title", "Auth", "--type", "story", dag_file=self.path)

    def tearDown(self):
        if os.path.exists(self.path):
            os.unlink(self.path)

    def test_update_status(self):
        run_cmd("update-node", "--id", "42", "--status", "closed", dag_file=self.path)
        dag = load_json(self.path)
        self.assertEqual(dag["nodes"]["42"]["status"], "closed")

    def test_update_keywords(self):
        run_cmd("update-node", "--id", "42", "--keywords", "auth,session,jwt", dag_file=self.path)
        dag = load_json(self.path)
        self.assertEqual(dag["nodes"]["42"]["keywords"], ["auth", "session", "jwt"])


class TestListNodes(unittest.TestCase):
    def setUp(self):
        self.tmpfile = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.path = self.tmpfile.name
        self.tmpfile.close()
        os.unlink(self.path)
        run_cmd("init", "--repo", "test/repo", "--force", dag_file=self.path)
        run_cmd("add-node", "--id", "42", "--title", "A", "--type", "story", dag_file=self.path)
        run_cmd("add-node", "--id", "43", "--title", "B", "--type", "task",
                "--status", "closed", dag_file=self.path)

    def tearDown(self):
        if os.path.exists(self.path):
            os.unlink(self.path)

    def test_list_all(self):
        _, stdout, _ = run_cmd("list-nodes", dag_file=self.path)
        nodes = json.loads(stdout)
        self.assertEqual(len(nodes), 2)

    def test_list_filtered_by_status(self):
        _, stdout, _ = run_cmd("list-nodes", "--status", "open", dag_file=self.path)
        nodes = json.loads(stdout)
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["id"], "42")


class TestValidate(unittest.TestCase):
    def test_valid_dag(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        os.unlink(path)
        try:
            run_cmd("init", "--repo", "test/repo", "--force", dag_file=path)
            run_cmd("add-node", "--id", "1", "--title", "T", "--type", "bug", dag_file=path)
            run_cmd("validate", dag_file=path)
        finally:
            os.unlink(path)

    def test_invalid_dag_detected(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump({"version": 2, "repo": "bad", "nodes": {}, "edges": []}, f)
            path = f.name
        try:
            rc, _, stderr = run_cmd("validate", dag_file=path, expect_fail=True)
            self.assertNotEqual(rc, 0)
            self.assertIn("VALIDATION FAILED", stderr)
        finally:
            os.unlink(path)


class AnalysisSetup(unittest.TestCase):
    """Base class with a complex DAG: A→B→D, A→C→D, E independent."""

    def setUp(self):
        self.tmpfile = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.path = self.tmpfile.name
        self.tmpfile.close()
        os.unlink(self.path)
        run_cmd("init", "--repo", "test/repo", "--force", dag_file=self.path)
        # A, B, C, D, E — A and E have no deps (ready), D blocked by B and C
        run_cmd("add-node", "--id", "A", "--title", "Task A", "--type", "story", dag_file=self.path)
        run_cmd("add-node", "--id", "B", "--title", "Task B", "--type", "task", dag_file=self.path)
        run_cmd("add-node", "--id", "C", "--title", "Task C", "--type", "task", dag_file=self.path)
        run_cmd("add-node", "--id", "D", "--title", "Task D", "--type", "story", dag_file=self.path)
        run_cmd("add-node", "--id", "E", "--title", "Task E", "--type", "bug", dag_file=self.path)
        # B depends_on A, C depends_on A, D depends_on B, D depends_on C
        run_cmd("add-edge", "--from", "B", "--to", "A", "--type", "depends_on", dag_file=self.path)
        run_cmd("add-edge", "--from", "C", "--to", "A", "--type", "depends_on", dag_file=self.path)
        run_cmd("add-edge", "--from", "D", "--to", "B", "--type", "depends_on", dag_file=self.path)
        run_cmd("add-edge", "--from", "D", "--to", "C", "--type", "depends_on", dag_file=self.path)

    def tearDown(self):
        if os.path.exists(self.path):
            os.unlink(self.path)


class TestTopoSort(AnalysisSetup):
    def test_topo_order(self):
        _, stdout, _ = run_cmd("topo-sort", dag_file=self.path)
        result = json.loads(stdout)
        ids = [r["id"] for r in result]
        # A and E must come before B, C. B, C must come before D.
        self.assertLess(ids.index("A"), ids.index("B"))
        self.assertLess(ids.index("A"), ids.index("C"))
        self.assertLess(ids.index("B"), ids.index("D"))
        self.assertLess(ids.index("C"), ids.index("D"))
        self.assertEqual(len(ids), 5)

    def test_topo_sort_empty(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        os.unlink(path)
        try:
            run_cmd("init", "--repo", "test/repo", "--force", dag_file=path)
            _, stdout, _ = run_cmd("topo-sort", dag_file=path)
            result = json.loads(stdout)
            self.assertEqual(result, [])
        finally:
            os.unlink(path)


class TestReady(AnalysisSetup):
    def test_ready_initial(self):
        """A and E have no open deps, so they are ready."""
        _, stdout, _ = run_cmd("ready", dag_file=self.path)
        result = json.loads(stdout)
        ids = sorted(r["id"] for r in result)
        self.assertEqual(ids, ["A", "E"])

    def test_ready_after_closing_a(self):
        """After closing A, B and C become ready."""
        run_cmd("update-node", "--id", "A", "--status", "closed", dag_file=self.path)
        _, stdout, _ = run_cmd("ready", dag_file=self.path)
        result = json.loads(stdout)
        ids = sorted(r["id"] for r in result)
        self.assertEqual(ids, ["B", "C", "E"])

    def test_ready_after_closing_a_b_c(self):
        """After closing A, B, C — D becomes ready."""
        for nid in ["A", "B", "C"]:
            run_cmd("update-node", "--id", nid, "--status", "closed", dag_file=self.path)
        _, stdout, _ = run_cmd("ready", dag_file=self.path)
        result = json.loads(stdout)
        ids = sorted(r["id"] for r in result)
        self.assertEqual(ids, ["D", "E"])


class TestParallel(AnalysisSetup):
    def test_parallel_initial(self):
        """A and E are ready and independent → each in their own group or together."""
        _, stdout, _ = run_cmd("parallel", dag_file=self.path)
        groups = json.loads(stdout)
        all_ids = set()
        for g in groups:
            for item in g:
                all_ids.add(item["id"])
        self.assertEqual(all_ids, {"A", "E"})

    def test_parallel_after_close_a(self):
        """After closing A, B, C, E are ready. B and C are independent of E."""
        run_cmd("update-node", "--id", "A", "--status", "closed", dag_file=self.path)
        _, stdout, _ = run_cmd("parallel", dag_file=self.path)
        groups = json.loads(stdout)
        all_ids = set()
        for g in groups:
            for item in g:
                all_ids.add(item["id"])
        self.assertEqual(all_ids, {"B", "C", "E"})


class TestCheck(AnalysisSetup):
    def test_check_blocked_node(self):
        _, stdout, _ = run_cmd("check", "--id", "D", dag_file=self.path)
        result = json.loads(stdout)
        self.assertEqual(result["id"], "D")
        self.assertFalse(result["is_ready"])
        self.assertEqual(result["open_blockers"], 2)
        blocker_ids = sorted(b["id"] for b in result["blockers"])
        self.assertEqual(blocker_ids, ["B", "C"])

    def test_check_ready_node(self):
        _, stdout, _ = run_cmd("check", "--id", "A", dag_file=self.path)
        result = json.loads(stdout)
        self.assertTrue(result["is_ready"])
        self.assertEqual(result["open_blockers"], 0)

    def test_check_dependents(self):
        _, stdout, _ = run_cmd("check", "--id", "A", dag_file=self.path)
        result = json.loads(stdout)
        self.assertEqual(sorted(result["dependents"]), ["B", "C"])

    def test_check_nonexistent(self):
        rc, _, _ = run_cmd("check", "--id", "Z", dag_file=self.path, expect_fail=True)
        self.assertNotEqual(rc, 0)


class TestDetectCycle(AnalysisSetup):
    def test_no_cycle(self):
        run_cmd("detect-cycle", dag_file=self.path)

    def test_cycle_detected(self):
        """Manually inject a cycle: A→B already, add B→A edge."""
        dag = load_json(self.path)
        dag["edges"].append({"from": "A", "to": "B", "type": "depends_on"})
        with open(self.path, "w") as f:
            json.dump(dag, f)
        rc, _, stderr = run_cmd("detect-cycle", dag_file=self.path, expect_fail=True)
        self.assertNotEqual(rc, 0)
        self.assertIn("CYCLES DETECTED", stderr)


class TestOrphans(AnalysisSetup):
    def test_no_orphans_in_connected_dag(self):
        """E is an orphan (no edges)."""
        _, stdout, _ = run_cmd("orphans", dag_file=self.path)
        result = json.loads(stdout)
        ids = [r["id"] for r in result]
        self.assertEqual(ids, ["E"])

    def test_all_connected(self):
        """Add edge involving E → no orphans."""
        run_cmd("add-edge", "--from", "E", "--to", "A", "--type", "depends_on", dag_file=self.path)
        _, stdout, _ = run_cmd("orphans", dag_file=self.path)
        result = json.loads(stdout)
        self.assertEqual(result, [])


class TestViz(AnalysisSetup):
    def test_viz_mermaid_format(self):
        _, stdout, _ = run_cmd("viz", dag_file=self.path)
        self.assertTrue(stdout.startswith("graph TD"))
        self.assertIn("depends_on", stdout)
        self.assertIn("A", stdout)
        self.assertIn("D", stdout)

    def test_viz_closed_node(self):
        run_cmd("update-node", "--id", "A", "--status", "closed", dag_file=self.path)
        _, stdout, _ = run_cmd("viz", dag_file=self.path)
        # Closed nodes should have a check mark
        self.assertIn("✓", stdout)


class DepSectionSetup(unittest.TestCase):
    """Base class with numeric IDs for dep-section/affected-issues tests.

    DAG: #43 depends_on #42, #44 depends_on #42, #45 duplicated_by #43
    """

    def setUp(self):
        self.tmpfile = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.path = self.tmpfile.name
        self.tmpfile.close()
        os.unlink(self.path)
        run_cmd("init", "--repo", "test/repo", "--force", dag_file=self.path)
        run_cmd("add-node", "--id", "42", "--title", "Auth backend", "--type", "story", dag_file=self.path)
        run_cmd("add-node", "--id", "43", "--title", "Login UI", "--type", "task", dag_file=self.path)
        run_cmd("add-node", "--id", "44", "--title", "Session mgmt", "--type", "task", dag_file=self.path)
        run_cmd("add-node", "--id", "45", "--title", "Login duplicate", "--type", "task", dag_file=self.path)
        # 43 depends_on 42, 44 depends_on 42
        run_cmd("add-edge", "--from", "43", "--to", "42", "--type", "depends_on", dag_file=self.path)
        run_cmd("add-edge", "--from", "44", "--to", "42", "--type", "depends_on", dag_file=self.path)
        # 45 duplicated_by 43
        run_cmd("add-edge", "--from", "45", "--to", "43", "--type", "duplicated_by", dag_file=self.path)

    def tearDown(self):
        if os.path.exists(self.path):
            os.unlink(self.path)


class TestDepSection(DepSectionSetup):
    """Test dep-section subcommand."""

    def test_single_issue(self):
        """dep-section for #42 should show blocks info."""
        _, stdout, _ = run_cmd("dep-section", "--id", "42", dag_file=self.path)
        result = json.loads(stdout)
        self.assertIn("42", result)
        section = result["42"]
        self.assertIn("<!-- issue-dag:begin -->", section)
        self.assertIn("<!-- issue-dag:end -->", section)
        self.assertIn("**Blocks**: #43, #44", section)

    def test_multiple_issues(self):
        """dep-section for comma-separated IDs."""
        _, stdout, _ = run_cmd("dep-section", "--id", "42,43", dag_file=self.path)
        result = json.loads(stdout)
        self.assertIn("42", result)
        self.assertIn("43", result)
        # 43 depends on 42 and is duplicated_by target of 45
        self.assertIn("**Depends on**: #42", result["43"])

    def test_all_issues(self):
        """dep-section --id all should return sections for all issues with edges."""
        _, stdout, _ = run_cmd("dep-section", "--id", "all", dag_file=self.path)
        result = json.loads(stdout)
        # 42, 43, 44, 45 all have edges
        self.assertEqual(len(result), 4)
        for nid in ["42", "43", "44", "45"]:
            self.assertIn(nid, result)

    def test_issue_with_no_edges_returns_empty(self):
        """An issue with no edges should return empty string."""
        run_cmd("add-node", "--id", "99", "--title", "Orphan", "--type", "bug", dag_file=self.path)
        _, stdout, _ = run_cmd("dep-section", "--id", "99", dag_file=self.path)
        result = json.loads(stdout)
        self.assertEqual(result["99"], "")

    def test_depends_on_section(self):
        """#43 depends on #42."""
        _, stdout, _ = run_cmd("dep-section", "--id", "43", dag_file=self.path)
        result = json.loads(stdout)
        self.assertIn("**Depends on**: #42", result["43"])

    def test_duplicated_by_section(self):
        """#43 has a duplicated_by relationship from #45."""
        _, stdout, _ = run_cmd("dep-section", "--id", "43", dag_file=self.path)
        result = json.loads(stdout)
        # 45 duplicated_by 43 → 43 should show "Duplicated by: #45"
        self.assertIn("**Duplicated by**: #45", result["43"])

    def test_duplicate_of_section(self):
        """#45 is duplicate of #43."""
        _, stdout, _ = run_cmd("dep-section", "--id", "45", dag_file=self.path)
        result = json.loads(stdout)
        self.assertIn("**Duplicate of**: #43", result["45"])

    def test_section_format_markers(self):
        """Section should have proper begin/end markers."""
        _, stdout, _ = run_cmd("dep-section", "--id", "42", dag_file=self.path)
        result = json.loads(stdout)
        section = result["42"]
        lines = section.split("\n")
        self.assertEqual(lines[0], "<!-- issue-dag:begin -->")
        self.assertEqual(lines[-1], "<!-- issue-dag:end -->")
        self.assertIn("## Dependencies (auto-managed by issue-dag)", section)


class TestAffectedIssues(DepSectionSetup):
    """Test affected-issues subcommand."""

    def test_affected_by_existing_edge(self):
        """Both endpoints of an edge should be affected."""
        _, stdout, _ = run_cmd("affected-issues", "--from", "43", "--to", "42", dag_file=self.path)
        result = json.loads(stdout)
        self.assertIn("42", result)
        self.assertIn("43", result)

    def test_affected_returns_sorted(self):
        """Result should be sorted by numeric ID."""
        _, stdout, _ = run_cmd("affected-issues", "--from", "44", "--to", "42", dag_file=self.path)
        result = json.loads(stdout)
        self.assertEqual(result, sorted(result, key=int))

    def test_affected_node_without_edges(self):
        """A node with no other edges should not be in affected list."""
        run_cmd("add-node", "--id", "99", "--title", "Orphan", "--type", "bug", dag_file=self.path)
        _, stdout, _ = run_cmd("affected-issues", "--from", "99", "--to", "42", dag_file=self.path)
        result = json.loads(stdout)
        # 42 has edges so it's affected, 99 has no edges so it's not
        self.assertIn("42", result)
        self.assertNotIn("99", result)


if __name__ == "__main__":
    unittest.main()
