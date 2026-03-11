#!/usr/bin/env python3
"""Unit and integration tests for import-issues feature.

Tests parse_dependencies, extract_keywords, extract_paths_from_body helpers
and the import-issues subcommand end-to-end.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Import helpers directly for unit tests
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from importlib import import_module

dag_mod = import_module("dag-analyze")
parse_dependencies = dag_mod.parse_dependencies
extract_keywords = dag_mod.extract_keywords
extract_paths_from_body = dag_mod.extract_paths_from_body
classify_issue_type = dag_mod.classify_issue_type

SCRIPT = str(Path(__file__).parent.parent / "scripts" / "dag-analyze.py")


def run_cmd(*args, dag_file=None, stdin_data=None, expect_fail=False):
    """Run dag-analyze.py with arguments and return (returncode, stdout, stderr)."""
    cmd = [sys.executable, SCRIPT]
    if dag_file:
        cmd.extend(["--dag-file", str(dag_file)])
    cmd.extend(args)
    result = subprocess.run(
        cmd, capture_output=True, text=True,
        input=stdin_data,
    )
    if not expect_fail and result.returncode != 0:
        raise AssertionError(
            f"Command failed: {' '.join(cmd)}\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return result.returncode, result.stdout, result.stderr


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


# ─── parse_dependencies unit tests ──────────────────────────


class TestParseDependencies(unittest.TestCase):
    """Unit tests for parse_dependencies."""

    def test_depends_on_single(self):
        deps = parse_dependencies("This depends on #42")
        self.assertEqual(len(deps), 1)
        self.assertEqual(deps[0]["ref"], "42")
        self.assertEqual(deps[0]["type"], "depends_on")
        self.assertEqual(deps[0]["direction"], "forward")

    def test_depends_on_multiple(self):
        deps = parse_dependencies("depends on #1, #2, #3")
        refs = [d["ref"] for d in deps]
        self.assertEqual(sorted(refs), ["1", "2", "3"])
        for d in deps:
            self.assertEqual(d["type"], "depends_on")

    def test_blocked_by(self):
        deps = parse_dependencies("blocked by #10")
        self.assertEqual(len(deps), 1)
        self.assertEqual(deps[0]["ref"], "10")
        self.assertEqual(deps[0]["type"], "depends_on")
        self.assertEqual(deps[0]["direction"], "forward")

    def test_blocks_reverse(self):
        deps = parse_dependencies("blocks #20")
        self.assertEqual(len(deps), 1)
        self.assertEqual(deps[0]["ref"], "20")
        self.assertEqual(deps[0]["type"], "depends_on")
        self.assertEqual(deps[0]["direction"], "reverse")

    def test_requires(self):
        deps = parse_dependencies("requires #5")
        self.assertEqual(len(deps), 1)
        self.assertEqual(deps[0]["ref"], "5")
        self.assertEqual(deps[0]["type"], "depends_on")

    def test_after(self):
        deps = parse_dependencies("after #7")
        self.assertEqual(len(deps), 1)
        self.assertEqual(deps[0]["ref"], "7")
        self.assertEqual(deps[0]["type"], "depends_on")

    def test_duplicate_of(self):
        deps = parse_dependencies("duplicate of #99")
        self.assertEqual(len(deps), 1)
        self.assertEqual(deps[0]["ref"], "99")
        self.assertEqual(deps[0]["type"], "duplicated_by")
        self.assertEqual(deps[0]["direction"], "forward")

    def test_duplicated_by_reverse(self):
        deps = parse_dependencies("duplicated by #88")
        self.assertEqual(len(deps), 1)
        self.assertEqual(deps[0]["ref"], "88")
        self.assertEqual(deps[0]["type"], "duplicated_by")
        self.assertEqual(deps[0]["direction"], "reverse")

    def test_case_insensitive(self):
        deps = parse_dependencies("DEPENDS ON #1")
        self.assertEqual(len(deps), 1)
        self.assertEqual(deps[0]["ref"], "1")

    def test_dag_section_ignored(self):
        body = (
            "Some text depends on #1\n"
            "<!-- issue-dag:begin -->\n"
            "depends on #999\n"
            "<!-- issue-dag:end -->\n"
            "more text"
        )
        deps = parse_dependencies(body)
        refs = [d["ref"] for d in deps]
        self.assertIn("1", refs)
        self.assertNotIn("999", refs)

    def test_empty_body(self):
        self.assertEqual(parse_dependencies(""), [])
        self.assertEqual(parse_dependencies(None), [])

    def test_deduplication(self):
        body = "depends on #5, depends on #5"
        deps = parse_dependencies(body)
        refs = [d["ref"] for d in deps]
        self.assertEqual(refs.count("5"), 1)


# ─── extract_keywords / extract_paths unit tests ────────────


class TestExtractPaths(unittest.TestCase):
    """Unit tests for extract_paths_from_body."""

    def test_backtick_paths(self):
        body = "Check `src/auth/login.py` and `lib/utils/helper.ts`"
        paths = extract_paths_from_body(body)
        self.assertIn("src/auth/login.py", paths)
        self.assertIn("lib/utils/helper.ts", paths)

    def test_bare_src_paths(self):
        body = "Look at src/components/Button.tsx for reference"
        paths = extract_paths_from_body(body)
        self.assertIn("src/components/Button.tsx", paths)

    def test_empty_body(self):
        self.assertEqual(extract_paths_from_body(""), [])
        self.assertEqual(extract_paths_from_body(None), [])


class TestExtractKeywords(unittest.TestCase):
    """Unit tests for extract_keywords."""

    def test_title_tokens(self):
        kw = extract_keywords("Auth login system", "", [], None)
        self.assertIn("auth", kw)
        self.assertIn("login", kw)
        self.assertIn("system", kw)

    def test_stopwords_filtered(self):
        kw = extract_keywords("Add the login feature", "", [], None)
        self.assertNotIn("the", kw)
        self.assertNotIn("add", kw)
        self.assertIn("login", kw)
        self.assertIn("feature", kw)

    def test_labels_included(self):
        kw = extract_keywords("Test", "", ["frontend", "priority-high"], None)
        self.assertIn("frontend", kw)
        self.assertIn("priority-high", kw)

    def test_type_labels_excluded(self):
        kw = extract_keywords("Test", "", ["bug", "frontend"], None)
        self.assertNotIn("bug", kw)
        self.assertIn("frontend", kw)

    def test_body_paths_extracted(self):
        kw = extract_keywords("Test", "Check `src/auth/login.py`", [], None)
        self.assertIn("src/auth/login.py", kw)


class TestClassifyIssueType(unittest.TestCase):
    """Unit tests for classify_issue_type."""

    def test_bug_label(self):
        self.assertEqual(classify_issue_type(["bug"], {"bug": "bug"}), "bug")

    def test_no_match_fallback(self):
        self.assertEqual(classify_issue_type(["unknown"], {"bug": "bug"}), "task")

    def test_empty_labels(self):
        self.assertEqual(classify_issue_type([], {"bug": "bug"}), "task")


# ─── import-issues integration tests ────────────────────────


class ImportSetup(unittest.TestCase):
    """Base class that sets up an empty DAG for import tests."""

    def setUp(self):
        self.tmpfile = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.path = self.tmpfile.name
        self.tmpfile.close()
        os.unlink(self.path)
        run_cmd("init", "--repo", "test/repo", "--force", dag_file=self.path)

    def tearDown(self):
        if os.path.exists(self.path):
            os.unlink(self.path)

    def do_import(self, issues, extra_args=None, expect_fail=False):
        args = ["import-issues"]
        if extra_args:
            args.extend(extra_args)
        stdin_data = json.dumps(issues)
        return run_cmd(*args, dag_file=self.path, stdin_data=stdin_data,
                        expect_fail=expect_fail)


class TestImportBasic(ImportSetup):
    """Basic import-issues integration tests."""

    def test_import_creates_nodes(self):
        issues = [
            {"id": "1", "title": "Auth backend", "labels": ["story"], "body": "", "status": "open"},
            {"id": "2", "title": "Login UI", "labels": ["task"], "body": "", "status": "open"},
        ]
        _, stdout, _ = self.do_import(issues)
        report = json.loads(stdout)
        self.assertEqual(sorted(report["nodes_added"]), ["1", "2"])
        dag = load_json(self.path)
        self.assertIn("1", dag["nodes"])
        self.assertIn("2", dag["nodes"])

    def test_import_dependency_edge(self):
        issues = [
            {"id": "1", "title": "Auth backend", "labels": ["story"], "body": "", "status": "open"},
            {"id": "2", "title": "Login UI", "labels": ["task"],
             "body": "depends on #1", "status": "open"},
        ]
        _, stdout, _ = self.do_import(issues)
        report = json.loads(stdout)
        self.assertEqual(len(report["edges_added"]), 1)
        self.assertEqual(report["edges_added"][0]["from"], "2")
        self.assertEqual(report["edges_added"][0]["to"], "1")

    def test_existing_node_skipped(self):
        # Pre-add node 1 with matching keywords that import would compute
        run_cmd("add-node", "--id", "1", "--title", "Auth backend",
                "--type", "story", "--keywords", "auth,backend",
                dag_file=self.path)
        issues = [
            {"id": "1", "title": "Auth backend", "labels": ["story"], "body": "", "status": "open"},
        ]
        _, stdout, _ = self.do_import(issues)
        report = json.loads(stdout)
        self.assertIn("1", report["nodes_skipped"])

    def test_existing_node_updated(self):
        run_cmd("add-node", "--id", "1", "--title", "Old title",
                "--type", "story", dag_file=self.path)
        issues = [
            {"id": "1", "title": "New title", "labels": ["story"], "body": "", "status": "open"},
        ]
        _, stdout, _ = self.do_import(issues)
        report = json.loads(stdout)
        self.assertIn("1", report["nodes_updated"])
        dag = load_json(self.path)
        self.assertEqual(dag["nodes"]["1"]["title"], "New title")

    def test_cycle_detected(self):
        issues = [
            {"id": "1", "title": "A", "labels": [], "body": "depends on #2", "status": "open"},
            {"id": "2", "title": "B", "labels": [], "body": "depends on #1", "status": "open"},
        ]
        _, stdout, _ = self.do_import(issues)
        report = json.loads(stdout)
        # One edge should be added, the other should create a cycle
        self.assertEqual(len(report["edges_added"]), 1)
        self.assertEqual(len(report["cycles_detected"]), 1)

    def test_duplicate_detected(self):
        issues = [
            {"id": "1", "title": "Auth login system", "labels": ["auth"],
             "body": "", "status": "open"},
            {"id": "2", "title": "Auth login system", "labels": ["auth"],
             "body": "", "status": "open"},
        ]
        _, stdout, _ = self.do_import(issues, ["--dup-threshold", "0.1"])
        report = json.loads(stdout)
        self.assertGreater(len(report["duplicates_detected"]), 0)

    def test_duplicate_edge_skipped(self):
        # Pre-add nodes and edge
        run_cmd("add-node", "--id", "1", "--title", "A", "--type", "story", dag_file=self.path)
        run_cmd("add-node", "--id", "2", "--title", "B", "--type", "task", dag_file=self.path)
        run_cmd("add-edge", "--from", "2", "--to", "1", "--type", "depends_on", dag_file=self.path)
        issues = [
            {"id": "1", "title": "A", "labels": ["story"], "body": "", "status": "open"},
            {"id": "2", "title": "B", "labels": ["task"],
             "body": "depends on #1", "status": "open"},
        ]
        _, stdout, _ = self.do_import(issues)
        report = json.loads(stdout)
        self.assertEqual(len(report["edges_added"]), 0)
        dup_skips = [e for e in report["edges_skipped"] if e.get("reason") == "duplicate"]
        self.assertGreater(len(dup_skips), 0)

    def test_ref_not_in_dag_skipped(self):
        issues = [
            {"id": "1", "title": "A", "labels": [], "body": "depends on #999", "status": "open"},
        ]
        _, stdout, _ = self.do_import(issues)
        report = json.loads(stdout)
        self.assertEqual(len(report["edges_added"]), 0)
        not_found = [e for e in report["edges_skipped"] if e.get("reason") == "node_not_found"]
        self.assertGreater(len(not_found), 0)

    def test_custom_label_map(self):
        issues = [
            {"id": "1", "title": "A", "labels": ["epic"], "body": "", "status": "open"},
        ]
        _, stdout, _ = self.do_import(issues, ["--label-map", "epic:story"])
        report = json.loads(stdout)
        dag = load_json(self.path)
        self.assertEqual(dag["nodes"]["1"]["type"], "story")

    def test_label_map_failure_reported(self):
        issues = [
            {"id": "1", "title": "A", "labels": ["unknown-label"], "body": "", "status": "open"},
        ]
        _, stdout, _ = self.do_import(issues)
        report = json.loads(stdout)
        self.assertEqual(len(report["label_map_failures"]), 1)
        self.assertEqual(report["label_map_failures"][0]["id"], "1")

    def test_empty_list_import(self):
        _, stdout, _ = self.do_import([])
        report = json.loads(stdout)
        self.assertEqual(report["nodes_added"], [])
        self.assertEqual(report["edges_added"], [])

    def test_blocks_reverse_edge(self):
        issues = [
            {"id": "1", "title": "A", "labels": [], "body": "blocks #2", "status": "open"},
            {"id": "2", "title": "B", "labels": [], "body": "", "status": "open"},
        ]
        _, stdout, _ = self.do_import(issues)
        report = json.loads(stdout)
        # "1 blocks 2" means 2 depends_on 1 → edge from=2, to=1
        edges = report["edges_added"]
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]["from"], "2")
        self.assertEqual(edges[0]["to"], "1")

    def test_self_reference_ignored(self):
        issues = [
            {"id": "1", "title": "A", "labels": [], "body": "depends on #1", "status": "open"},
        ]
        _, stdout, _ = self.do_import(issues)
        report = json.loads(stdout)
        self.assertEqual(len(report["edges_added"]), 0)


if __name__ == "__main__":
    unittest.main()
