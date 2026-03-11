"""Test 5.8: autopilot-state.py prereq-infra issue support.

Tests that add_issue() accepts type="prereq-infra" and
query_issues() filters by issue type correctly.
"""

import importlib.util
from pathlib import Path

import pytest

# Load autopilot-state.py module (hyphenated name requires importlib)
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "autopilot_state", SCRIPTS_DIR / "autopilot-state.py"
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

create_state = _mod.create_state
add_issue = _mod.add_issue
query_issues = _mod.query_issues
update_issue = _mod.update_issue
state_file_path = _mod.state_file_path


@pytest.fixture
def state_env(tmp_path, monkeypatch):
    """Set up a state environment with a fresh state file."""
    monkeypatch.setattr(_mod, "_git_root", lambda: tmp_path)
    create_state(
        meta_issue=100,
        meta_url="https://github.com/test/repo/issues/100",
        provider="github",
        source="test",
    )
    return tmp_path


class TestPrereqInfraIssue:
    """Test prereq-infra issue type support."""

    def test_add_prereq_infra_issue(self, state_env):
        """add_issue() with type='prereq-infra' succeeds."""
        state = add_issue(
            issue_id=201,
            url="https://github.com/test/repo/issues/201",
            issue_type="prereq-infra",
            title="Set up CI pipeline",
        )
        issues = state["issues"]
        assert len(issues) == 1
        assert issues[0]["type"] == "prereq-infra"
        assert issues[0]["title"] == "Set up CI pipeline"
        assert issues[0]["status"] == "open"
        assert issues[0]["verified"] is False

    def test_add_multiple_prereq_infra_issues(self, state_env):
        """Multiple prereq-infra issues can be added."""
        add_issue(201, "https://example.com/201", "prereq-infra", "Set up CI pipeline")
        add_issue(202, "https://example.com/202", "prereq-infra", "Configure Playwright")
        add_issue(203, "https://example.com/203", "task", "Implement login feature")

        issues = query_issues()
        assert len(issues) == 3

    def test_query_by_type_prereq_infra(self, state_env):
        """query_issues(issue_type='prereq-infra') returns only prereq-infra issues."""
        add_issue(201, "https://example.com/201", "prereq-infra", "Set up CI pipeline")
        add_issue(202, "https://example.com/202", "prereq-infra", "Configure Playwright")
        add_issue(203, "https://example.com/203", "task", "Implement login feature")

        prereqs = query_issues(issue_type="prereq-infra")
        assert len(prereqs) == 2
        assert all(i["type"] == "prereq-infra" for i in prereqs)

    def test_query_by_type_task(self, state_env):
        """query_issues(issue_type='task') returns only task issues."""
        add_issue(201, "https://example.com/201", "prereq-infra", "Set up CI pipeline")
        add_issue(203, "https://example.com/203", "task", "Implement login feature")

        tasks = query_issues(issue_type="task")
        assert len(tasks) == 1
        assert tasks[0]["type"] == "task"

    def test_query_by_type_none_returns_all(self, state_env):
        """query_issues() without type filter returns all issues."""
        add_issue(201, "https://example.com/201", "prereq-infra", "Set up CI pipeline")
        add_issue(203, "https://example.com/203", "task", "Implement login feature")

        all_issues = query_issues()
        assert len(all_issues) == 2

    def test_query_type_combined_with_open(self, state_env):
        """query_issues(open_only=True, issue_type='prereq-infra') combines filters."""
        add_issue(201, "https://example.com/201", "prereq-infra", "Set up CI pipeline")
        add_issue(202, "https://example.com/202", "prereq-infra", "Configure Playwright")
        add_issue(203, "https://example.com/203", "task", "Implement login feature")

        # Close one prereq issue
        update_issue(201, status="closed")

        open_prereqs = query_issues(open_only=True, issue_type="prereq-infra")
        assert len(open_prereqs) == 1
        assert open_prereqs[0]["id"] == 202

    def test_query_nonexistent_type_returns_empty(self, state_env):
        """query_issues(issue_type='nonexistent') returns empty list."""
        add_issue(201, "https://example.com/201", "prereq-infra", "Set up CI pipeline")

        result = query_issues(issue_type="nonexistent")
        assert result == []

    def test_prereq_infra_with_verification_methods(self, state_env):
        """prereq-infra issues can have verification methods."""
        state = add_issue(
            issue_id=201,
            url="https://example.com/201",
            issue_type="prereq-infra",
            title="Set up CI pipeline",
            verification_methods=["cli"],
        )
        assert state["issues"][0]["verification_methods"] == ["cli"]

    def test_update_nonexistent_issue_raises(self, state_env):
        """update_issue with nonexistent id raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            update_issue(999, status="closed")

    def test_update_issue_verified_flag(self, state_env):
        """update_issue can set verified=True."""
        add_issue(201, "https://example.com/201", "task", "Task A")
        state = update_issue(201, verified=True)
        assert state["issues"][0]["verified"] is True

    def test_query_verified_filter(self, state_env):
        """query_issues(verified=True) returns only verified issues."""
        add_issue(201, "https://example.com/201", "task", "Task A")
        add_issue(202, "https://example.com/202", "task", "Task B")
        update_issue(201, verified=True)

        result = query_issues(verified=True)
        assert len(result) == 1
        assert result[0]["id"] == 201

    def test_query_unverified_filter(self, state_env):
        """query_issues(unverified=True) returns only unverified issues."""
        add_issue(201, "https://example.com/201", "task", "Task A")
        add_issue(202, "https://example.com/202", "task", "Task B")
        update_issue(201, verified=True)

        result = query_issues(unverified=True)
        assert len(result) == 1
        assert result[0]["id"] == 202
