#!/usr/bin/env python3
"""Unit tests for DAG readiness check logic.

Tests the decision logic used by Step 1.3 (DAG Readiness Check) in issue-impl.
This validates the pure logic, not the LLM orchestration.
"""

import json
import unittest


def check_readiness(issue_id: str, dag_data: dict | None) -> dict:
    """Check if an issue is ready to implement based on DAG dependencies.

    Args:
        issue_id: The issue number/key to check.
        dag_data: Parsed DAG JSON, or None if DAG is unavailable.

    Returns:
        dict with keys:
            - ready: bool — True if issue can proceed
            - blockers: list[dict] — open blocker issues [{id, title, status}]
            - warnings: list[str] — non-blocking warnings
            - skip_reason: str | None — reason DAG check was skipped
    """
    # DAG unavailable → graceful skip
    if dag_data is None:
        return {
            "ready": True,
            "blockers": [],
            "warnings": ["DAG unavailable — skipping readiness check"],
            "skip_reason": "dag_unavailable",
        }

    nodes = dag_data.get("nodes", {})
    edges = dag_data.get("edges", [])

    # Issue not in DAG → no dependency info, proceed
    if str(issue_id) not in nodes:
        return {
            "ready": True,
            "blockers": [],
            "warnings": [f"Issue #{issue_id} not found in DAG — no dependency info"],
            "skip_reason": "not_in_dag",
        }

    # Find all depends_on edges where this issue is the dependent (from)
    blocker_ids = [
        e["to"] for e in edges
        if e["from"] == str(issue_id) and e["type"] == "depends_on"
    ]

    # Check which blockers are still open
    open_blockers = []
    for bid in blocker_ids:
        node = nodes.get(str(bid))
        if node and node.get("status") != "closed":
            open_blockers.append({
                "id": bid,
                "title": node.get("title", "Unknown"),
                "status": node.get("status", "unknown"),
            })

    if open_blockers:
        return {
            "ready": False,
            "blockers": open_blockers,
            "warnings": [],
            "skip_reason": None,
        }

    return {
        "ready": True,
        "blockers": [],
        "warnings": [],
        "skip_reason": None,
    }


class TestDagReadiness(unittest.TestCase):
    """Test DAG readiness check logic."""

    def setUp(self):
        """Create a sample DAG with dependencies."""
        self.dag = {
            "version": 1,
            "repo": "test/repo",
            "updated_at": "2026-02-28T10:00:00Z",
            "nodes": {
                "42": {
                    "title": "Auth system",
                    "type": "story",
                    "status": "open",
                    "keywords": ["auth"],
                    "touched_paths": [],
                    "created_at": "2026-02-28T10:00:00Z",
                },
                "43": {
                    "title": "Login UI",
                    "type": "task",
                    "status": "open",
                    "keywords": ["login"],
                    "touched_paths": [],
                    "created_at": "2026-02-28T10:00:00Z",
                },
                "44": {
                    "title": "Session management",
                    "type": "task",
                    "status": "open",
                    "keywords": ["session"],
                    "touched_paths": [],
                    "created_at": "2026-02-28T10:00:00Z",
                },
                "45": {
                    "title": "Standalone feature",
                    "type": "task",
                    "status": "open",
                    "keywords": ["standalone"],
                    "touched_paths": [],
                    "created_at": "2026-02-28T10:00:00Z",
                },
            },
            "edges": [
                {"from": "43", "to": "42", "type": "depends_on"},
                {"from": "44", "to": "42", "type": "depends_on"},
            ],
        }

    def test_ready_no_blockers(self):
        """Issue with no dependencies is ready."""
        result = check_readiness("42", self.dag)
        self.assertTrue(result["ready"])
        self.assertEqual(result["blockers"], [])

    def test_blocked_by_open_dependency(self):
        """Issue with open dependency is blocked."""
        result = check_readiness("43", self.dag)
        self.assertFalse(result["ready"])
        self.assertEqual(len(result["blockers"]), 1)
        self.assertEqual(result["blockers"][0]["id"], "42")
        self.assertEqual(result["blockers"][0]["title"], "Auth system")

    def test_ready_after_dependency_closed(self):
        """Issue becomes ready when all dependencies are closed."""
        self.dag["nodes"]["42"]["status"] = "closed"
        result = check_readiness("43", self.dag)
        self.assertTrue(result["ready"])
        self.assertEqual(result["blockers"], [])

    def test_standalone_issue_ready(self):
        """Issue with no dependency edges is ready."""
        result = check_readiness("45", self.dag)
        self.assertTrue(result["ready"])

    def test_not_in_dag_proceeds(self):
        """Issue not present in DAG proceeds with warning."""
        result = check_readiness("999", self.dag)
        self.assertTrue(result["ready"])
        self.assertEqual(result["skip_reason"], "not_in_dag")
        self.assertTrue(len(result["warnings"]) > 0)

    def test_dag_unavailable_graceful_skip(self):
        """When DAG data is None, gracefully skip and proceed."""
        result = check_readiness("43", None)
        self.assertTrue(result["ready"])
        self.assertEqual(result["skip_reason"], "dag_unavailable")
        self.assertTrue(len(result["warnings"]) > 0)

    def test_multiple_blockers(self):
        """Issue blocked by multiple open dependencies."""
        # Add another dependency for issue 44
        self.dag["edges"].append(
            {"from": "44", "to": "43", "type": "depends_on"}
        )
        result = check_readiness("44", self.dag)
        self.assertFalse(result["ready"])
        self.assertEqual(len(result["blockers"]), 2)
        blocker_ids = {b["id"] for b in result["blockers"]}
        self.assertEqual(blocker_ids, {"42", "43"})

    def test_partial_blockers_resolved(self):
        """Issue blocked by one of two dependencies (one closed, one open)."""
        self.dag["edges"].append(
            {"from": "44", "to": "43", "type": "depends_on"}
        )
        self.dag["nodes"]["42"]["status"] = "closed"
        result = check_readiness("44", self.dag)
        self.assertFalse(result["ready"])
        self.assertEqual(len(result["blockers"]), 1)
        self.assertEqual(result["blockers"][0]["id"], "43")

    def test_duplicated_by_edge_ignored(self):
        """duplicated_by edges should not affect readiness."""
        self.dag["edges"].append(
            {"from": "45", "to": "42", "type": "duplicated_by"}
        )
        result = check_readiness("45", self.dag)
        self.assertTrue(result["ready"])
        self.assertEqual(result["blockers"], [])

    def test_empty_dag(self):
        """Empty DAG — issue not found, proceeds with warning."""
        empty_dag = {"version": 1, "repo": "test/repo", "nodes": {}, "edges": []}
        result = check_readiness("42", empty_dag)
        self.assertTrue(result["ready"])
        self.assertEqual(result["skip_reason"], "not_in_dag")

    def test_blocker_info_includes_title_and_status(self):
        """Blocker entries must include id, title, and status."""
        result = check_readiness("43", self.dag)
        self.assertFalse(result["ready"])
        blocker = result["blockers"][0]
        self.assertIn("id", blocker)
        self.assertIn("title", blocker)
        self.assertIn("status", blocker)


class TestReadinessOutputFormat(unittest.TestCase):
    """Test output format of readiness check."""

    def test_ready_result_format(self):
        """Ready result has expected keys."""
        result = check_readiness("1", None)
        self.assertIn("ready", result)
        self.assertIn("blockers", result)
        self.assertIn("warnings", result)
        self.assertIn("skip_reason", result)

    def test_result_is_json_serializable(self):
        """Result must be JSON-serializable."""
        dag = {
            "nodes": {"1": {"title": "Test", "status": "open"}},
            "edges": [],
        }
        result = check_readiness("1", dag)
        json.dumps(result)  # Should not raise


if __name__ == "__main__":
    unittest.main()
