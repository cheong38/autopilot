"""Tests for trace-report.py: summary, compare, bottleneck, review-stats, list.

Tests cover:
- Summary command with timeline, insights, and suggested updates
- Anomaly detection (5 patterns)
- Confidence-based suggestion filtering
- Compare command with delta calculation
- Bottleneck command with top-N token consumers
- Review stats aggregation
- List command formatting
- Null token handling (no crash)
"""

import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

# Load trace-report.py module (hyphenated name)
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "trace_report", SCRIPTS_DIR / "trace-report.py"
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

cmd_summary = _mod.cmd_summary
cmd_compare = _mod.cmd_compare
cmd_bottleneck = _mod.cmd_bottleneck
cmd_review_stats = _mod.cmd_review_stats
cmd_list = _mod.cmd_list
_detect_anomalies = _mod._detect_anomalies
_generate_suggested_updates = _mod._generate_suggested_updates
_format_duration = _mod._format_duration
_format_tokens = _mod._format_tokens

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def traces_dir(tmp_path, monkeypatch):
    """Set up a temporary traces directory with fixture files."""
    traces = tmp_path / ".claude" / "autopilot-traces"
    traces.mkdir(parents=True)

    # Copy fixtures using session_id as filename
    for fixture in FIXTURES_DIR.glob("*.json"):
        data = json.loads(fixture.read_text())
        sid = data.get("session_id", fixture.stem)
        target = traces / f"{sid}.json"
        shutil.copy(fixture, target)

    # Create index.json
    index = {"sessions": []}
    for fixture in FIXTURES_DIR.glob("*.json"):
        data = json.loads(fixture.read_text())
        root = data["spans"][0]
        issue_count = len([s for s in data["spans"] if s["kind"] == "issue"])
        index["sessions"].append({
            "session_id": data["session_id"],
            "meta_issue": data.get("meta_issue", {}),
            "started_at_ms": root["start_time_ms"],
            "ended_at_ms": root.get("end_time_ms"),
            "duration_ms": root.get("duration_ms"),
            "total_tokens": root["attributes"].get("total_tokens"),
            "total_tool_uses": root["attributes"].get("total_tool_uses"),
            "issue_count": issue_count,
            "status": root["status"],
            "complexity": root["attributes"].get("complexity"),
            "provider": root["attributes"].get("provider"),
            "file_available": True,
        })
    (traces / "index.json").write_text(json.dumps(index, indent=2))

    monkeypatch.setattr(_mod, "_git_root", lambda: tmp_path)
    return traces


class TestFormatters:
    """Test formatting utilities."""

    def test_format_duration_seconds(self):
        assert _format_duration(5000) == "5s"

    def test_format_duration_minutes(self):
        assert _format_duration(125000) == "2m 5s"

    def test_format_duration_hours(self):
        assert _format_duration(3725000) == "1h 2m"

    def test_format_duration_none(self):
        assert _format_duration(None) == "N/A"

    def test_format_tokens(self):
        assert _format_tokens(45230) == "45,230"

    def test_format_tokens_none(self):
        assert _format_tokens(None) == "N/A"


class TestSummary:
    """Test summary command."""

    def test_summary_has_required_sections(self, traces_dir):
        result = cmd_summary("normal-001")
        assert "## Autopilot Trace Summary" in result
        assert "### Execution Timeline" in result
        assert "### Insights" in result
        assert "### Suggested Updates" in result

    def test_summary_timeline_has_step_spans(self, traces_dir):
        result = cmd_summary("normal-001")
        assert "CLASSIFY" in result
        assert "INGEST" in result
        assert "IMPL-LOOP" in result
        assert "REPORT" in result

    def test_summary_shows_metrics(self, traces_dir):
        result = cmd_summary("normal-001")
        assert "50,000" in result  # total tokens
        assert "10m" in result  # duration ~600s

    def test_summary_json_format(self, traces_dir):
        result = cmd_summary("normal-001", fmt="json")
        data = json.loads(result)
        assert data["session_id"] == "normal-001"
        assert data["total_tokens"] == 50000
        assert data["issue_count"] == 2

    def test_summary_null_tokens_no_crash(self, traces_dir):
        """Null tokens session should not crash."""
        result = cmd_summary("null-001")
        assert "## Autopilot Trace Summary" in result
        assert "N/A" in result


class TestAnomalyDetection:
    """Test anomaly pattern detection."""

    def test_high_retry_detected(self, traces_dir):
        trace = json.loads((FIXTURES_DIR / "high_retry_session.json").read_text())
        anomalies = _detect_anomalies(trace)
        retry_anomalies = [a for a in anomalies if "retries=" in a["metric"]]
        assert len(retry_anomalies) >= 1
        assert "4" in retry_anomalies[0]["metric"]

    def test_excessive_context_detected(self, traces_dir):
        trace = json.loads((FIXTURES_DIR / "high_token_session.json").read_text())
        anomalies = _detect_anomalies(trace)
        context_anomalies = [a for a in anomalies if "context" in a["cause"].lower()]
        assert len(context_anomalies) >= 1

    def test_excessive_tool_uses_detected(self, traces_dir):
        trace = json.loads((FIXTURES_DIR / "high_retry_session.json").read_text())
        anomalies = _detect_anomalies(trace)
        tool_anomalies = [a for a in anomalies if "tool_uses=" in a["metric"]]
        assert len(tool_anomalies) >= 1

    def test_normal_session_no_major_anomalies(self, traces_dir):
        trace = json.loads((FIXTURES_DIR / "normal_session.json").read_text())
        anomalies = _detect_anomalies(trace)
        # Normal session should have no retry or tool_uses anomalies
        retry_anomalies = [a for a in anomalies if "retries=" in a["metric"]]
        assert len(retry_anomalies) == 0

    def test_null_tokens_no_crash(self, traces_dir):
        trace = json.loads((FIXTURES_DIR / "null_tokens_session.json").read_text())
        anomalies = _detect_anomalies(trace)
        # Should not crash; may have no anomalies
        assert isinstance(anomalies, list)

    def test_anomaly_three_part_structure(self, traces_dir):
        """Each anomaly must have metric, cause, action keys."""
        trace = json.loads((FIXTURES_DIR / "high_retry_session.json").read_text())
        anomalies = _detect_anomalies(trace)
        for a in anomalies:
            assert "metric" in a
            assert "cause" in a
            assert "action" in a


class TestSuggestedUpdates:
    """Test configuration update suggestions."""

    def test_insufficient_sessions_no_suggestions(self):
        """Fewer than 3 sessions → no suggestions."""
        traces = [json.loads((FIXTURES_DIR / "normal_session.json").read_text())]
        suggestions = _generate_suggested_updates(traces)
        assert len(suggestions) == 0

    def test_below_threshold_no_suggestion(self):
        """Pattern in 2/5 sessions (40%) → no suggestion."""
        normal = json.loads((FIXTURES_DIR / "normal_session.json").read_text())
        retry = json.loads((FIXTURES_DIR / "high_retry_session.json").read_text())
        # 1 retry + 4 normal = 20% < 90%
        traces = [retry, normal, normal, normal, normal]
        suggestions = _generate_suggested_updates(traces)
        retry_suggestions = [s for s in suggestions if "retry" in s["suggestion"].lower()]
        assert len(retry_suggestions) == 0


class TestCompare:
    """Test compare command."""

    def test_compare_has_table(self, traces_dir):
        result = cmd_compare(["normal-001", "retry-001"])
        assert "## Session Comparison" in result
        assert "|" in result

    def test_compare_two_sessions(self, traces_dir):
        result = cmd_compare(["normal-001", "retry-001"])
        assert "## Session Comparison" in result
        assert "Duration" in result
        assert "Total Tokens" in result
        assert "Tool Uses" in result
        assert "Delta" in result

    def test_compare_notable_differences(self, traces_dir):
        result = cmd_compare(["normal-001", "retry-001"])
        assert "### Notable Differences" in result

    def test_compare_shows_review_retries(self, traces_dir):
        result = cmd_compare(["normal-001", "retry-001"])
        assert "Review Retries" in result

    def test_compare_requires_two_sessions(self, traces_dir):
        with pytest.raises(ValueError, match="exactly 2"):
            cmd_compare(["normal-001"])


class TestBottleneck:
    """Test bottleneck command."""

    def test_bottleneck_shows_top_spans(self, traces_dir):
        result = cmd_bottleneck("normal-001", top_n=3)
        assert "## Bottleneck Analysis" in result
        assert "Rank" in result
        assert "Tokens" in result

    def test_bottleneck_sorted_by_tokens(self, traces_dir):
        result = cmd_bottleneck("normal-001", top_n=5)
        assert "IMPL-LOOP" in result  # highest token consumer

    def test_bottleneck_shows_percentage(self, traces_dir):
        result = cmd_bottleneck("normal-001", top_n=3)
        assert "%" in result


class TestReviewStats:
    """Test review-stats command."""

    def test_review_stats_from_sessions(self, traces_dir):
        result = cmd_review_stats(session_ids=["normal-001", "retry-001"])
        assert "## Review Statistics" in result
        assert "Sessions Analyzed" in result
        assert "Total Reviews" in result
        assert "APPROVE" in result

    def test_review_stats_verdict_distribution(self, traces_dir):
        result = cmd_review_stats(session_ids=["retry-001"])
        assert "REQUEST_CHANGES" in result
        assert "APPROVE" in result


class TestList:
    """Test list command."""

    def test_list_shows_sessions(self, traces_dir):
        result = cmd_list()
        assert "## Session List" in result
        assert "Session" in result
        assert "Duration" in result

    def test_list_last_n(self, traces_dir):
        result = cmd_list(last_n=2)
        assert "## Session List" in result
        # Should show at most 2 rows (plus header)
        lines = [l for l in result.split("\n") if l.startswith("| `")]
        assert len(lines) <= 2
