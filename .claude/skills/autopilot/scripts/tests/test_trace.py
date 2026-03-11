"""Unit tests for trace.py tracing engine."""

import json
import shutil
import tempfile
import time
import uuid
from pathlib import Path
from unittest import mock

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import trace as trace_mod


@pytest.fixture(autouse=True)
def tmp_project(tmp_path, monkeypatch):
    """Set up a temporary project directory for each test."""
    traces_dir = tmp_path / ".claude" / "autopilot-traces"
    traces_dir.mkdir(parents=True)

    # Patch _git_root to return tmp_path
    monkeypatch.setattr(trace_mod, "_git_root", lambda: tmp_path)
    return tmp_path


class TestInit:
    """Test 1.4: init — session initialization."""

    def test_creates_trace_file(self, tmp_project):
        result = trace_mod.cmd_init("test-001")
        path = tmp_project / ".claude" / "autopilot-traces" / "test-001.json"
        assert path.exists()

    def test_creates_session_root_span(self, tmp_project):
        result = trace_mod.cmd_init("test-001")
        assert len(result["spans"]) == 1
        root = result["spans"][0]
        assert root["kind"] == "session"
        assert root["parent_id"] is None
        assert root["name"] == "test-001"

    def test_root_span_has_required_fields(self, tmp_project):
        result = trace_mod.cmd_init("test-001")
        root = result["spans"][0]
        assert "id" in root
        assert "parent_id" in root
        assert "name" in root
        assert "kind" in root
        assert "status" in root
        assert "start_time_ms" in root
        assert root["status"] == "ok"

    def test_idempotent_init(self, tmp_project):
        r1 = trace_mod.cmd_init("test-001")
        r2 = trace_mod.cmd_init("test-001")
        assert r1["session_id"] == r2["session_id"]

    def test_meta_issue_stored(self, tmp_project):
        result = trace_mod.cmd_init("test-001", meta_issue_number=42,
                                     meta_issue_url="https://github.com/repo/issues/42")
        assert result["meta_issue"]["number"] == 42
        assert result["meta_issue"]["url"] == "https://github.com/repo/issues/42"

    def test_directory_auto_creation(self, tmp_project):
        # Remove traces dir
        traces_dir = tmp_project / ".claude" / "autopilot-traces"
        shutil.rmtree(traces_dir)
        result = trace_mod.cmd_init("test-001")
        assert (tmp_project / ".claude" / "autopilot-traces" / "test-001.json").exists()


class TestStartSpan:
    """Test 1.5: start-span — new span creation."""

    def test_generates_uuid(self, tmp_project):
        trace_mod.cmd_init("s1")
        span_id = trace_mod.cmd_start_span("s1", "CLASSIFY", "step")
        # Verify it's a valid UUID
        uuid.UUID(span_id)

    def test_parent_id_linked(self, tmp_project):
        trace_mod.cmd_init("s1")
        span_id = trace_mod.cmd_start_span("s1", "CLASSIFY", "step")
        trace = trace_mod._load_trace("s1")
        child = trace_mod._find_span(trace, span_id)
        root = trace["spans"][0]
        assert child["parent_id"] == root["id"]

    def test_start_time_recorded(self, tmp_project):
        trace_mod.cmd_init("s1")
        before = int(time.time() * 1000)
        span_id = trace_mod.cmd_start_span("s1", "CLASSIFY", "step")
        after = int(time.time() * 1000)
        trace = trace_mod._load_trace("s1")
        span = trace_mod._find_span(trace, span_id)
        assert before <= span["start_time_ms"] <= after

    def test_kind_validation(self, tmp_project):
        trace_mod.cmd_init("s1")
        for kind in ("session", "step", "issue", "sub_step"):
            span_id = trace_mod.cmd_start_span("s1", f"test-{kind}", kind)
            assert span_id  # Valid kinds work

    def test_invalid_kind_raises(self, tmp_project):
        trace_mod.cmd_init("s1")
        with pytest.raises(ValueError, match="Invalid kind"):
            trace_mod.cmd_start_span("s1", "test", "invalid_kind")

    def test_attr_parsing(self, tmp_project):
        trace_mod.cmd_init("s1")
        span_id = trace_mod.cmd_start_span("s1", "IMPL", "step",
                                            attrs={"model_requested": "sonnet", "total_tokens": 45230})
        trace = trace_mod._load_trace("s1")
        span = trace_mod._find_span(trace, span_id)
        assert span["attributes"]["model_requested"] == "sonnet"
        assert span["attributes"]["total_tokens"] == 45230


class TestEndSpan:
    """Test 1.6: end-span — span termination."""

    def test_end_time_recorded(self, tmp_project):
        trace_mod.cmd_init("s1")
        span_id = trace_mod.cmd_start_span("s1", "CLASSIFY", "step")
        result = trace_mod.cmd_end_span("s1", span_id)
        assert result["end_time_ms"] is not None

    def test_duration_calculated(self, tmp_project):
        trace_mod.cmd_init("s1")
        span_id = trace_mod.cmd_start_span("s1", "CLASSIFY", "step")
        result = trace_mod.cmd_end_span("s1", span_id)
        assert result["duration_ms"] == result["end_time_ms"] - result["start_time_ms"]

    def test_status_set(self, tmp_project):
        trace_mod.cmd_init("s1")
        for status in ("ok", "error", "skipped"):
            span_id = trace_mod.cmd_start_span("s1", f"test-{status}", "step")
            result = trace_mod.cmd_end_span("s1", span_id, status=status)
            assert result["status"] == status

    def test_invalid_status_raises(self, tmp_project):
        trace_mod.cmd_init("s1")
        span_id = trace_mod.cmd_start_span("s1", "test", "step")
        with pytest.raises(ValueError, match="Invalid status"):
            trace_mod.cmd_end_span("s1", span_id, status="invalid")

    def test_attr_merged(self, tmp_project):
        trace_mod.cmd_init("s1")
        span_id = trace_mod.cmd_start_span("s1", "IMPL", "step",
                                            attrs={"model_requested": "sonnet"})
        result = trace_mod.cmd_end_span("s1", span_id, attrs={"total_tokens": 45230})
        assert result["attributes"]["model_requested"] == "sonnet"
        assert result["attributes"]["total_tokens"] == 45230

    def test_nonexistent_span_raises(self, tmp_project):
        trace_mod.cmd_init("s1")
        with pytest.raises(ValueError, match="Span not found"):
            trace_mod.cmd_end_span("s1", "nonexistent-id")


class TestAddEvent:
    """Test 1.7: add-event — event recording."""

    def test_event_added_to_span(self, tmp_project):
        trace_mod.cmd_init("s1")
        span_id = trace_mod.cmd_start_span("s1", "IMPL", "step")
        event = trace_mod.cmd_add_event("s1", span_id, "retry")
        assert event["name"] == "retry"

    def test_event_has_timestamp(self, tmp_project):
        trace_mod.cmd_init("s1")
        span_id = trace_mod.cmd_start_span("s1", "IMPL", "step")
        before = int(time.time() * 1000)
        event = trace_mod.cmd_add_event("s1", span_id, "retry")
        assert event["timestamp_ms"] >= before

    def test_event_attributes(self, tmp_project):
        trace_mod.cmd_init("s1")
        span_id = trace_mod.cmd_start_span("s1", "IMPL", "step")
        event = trace_mod.cmd_add_event("s1", span_id, "ci-failure",
                                         attrs={"run_id": 12345})
        assert event["attributes"]["run_id"] == 12345

    def test_multiple_events(self, tmp_project):
        trace_mod.cmd_init("s1")
        span_id = trace_mod.cmd_start_span("s1", "IMPL", "step")
        trace_mod.cmd_add_event("s1", span_id, "retry1")
        trace_mod.cmd_add_event("s1", span_id, "retry2")
        trace = trace_mod._load_trace("s1")
        span = trace_mod._find_span(trace, span_id)
        assert len(span["events"]) == 2


class TestAddNotes:
    """Test 1.8: add-notes — observation notes."""

    def test_notes_set(self, tmp_project):
        trace_mod.cmd_init("s1")
        span_id = trace_mod.cmd_start_span("s1", "IMPL", "step")
        result = trace_mod.cmd_add_notes("s1", span_id, "Observation note")
        assert result["notes"] == "Observation note"

    def test_notes_overwrite(self, tmp_project):
        trace_mod.cmd_init("s1")
        span_id = trace_mod.cmd_start_span("s1", "IMPL", "step")
        trace_mod.cmd_add_notes("s1", span_id, "First note")
        result = trace_mod.cmd_add_notes("s1", span_id, "Second note")
        assert result["notes"] == "Second note"


class TestFinalize:
    """Test 1.9: finalize — session finalization."""

    def test_root_span_closed(self, tmp_project):
        trace_mod.cmd_init("s1")
        result = trace_mod.cmd_finalize("s1")
        root = result["spans"][0]
        assert root["end_time_ms"] is not None
        assert root["duration_ms"] is not None

    def test_unclosed_spans_auto_closed(self, tmp_project):
        trace_mod.cmd_init("s1")
        trace_mod.cmd_start_span("s1", "IMPL", "step")
        result = trace_mod.cmd_finalize("s1")
        for span in result["spans"]:
            assert span["end_time_ms"] is not None

    def test_index_updated(self, tmp_project):
        trace_mod.cmd_init("s1")
        trace_mod.cmd_finalize("s1")
        index = trace_mod._load_index()
        assert len(index["sessions"]) == 1
        entry = index["sessions"][0]
        assert entry["session_id"] == "s1"

    def test_attrs_applied_to_root(self, tmp_project):
        trace_mod.cmd_init("s1")
        result = trace_mod.cmd_finalize("s1", attrs={"total_tokens": 50000, "provider": "github"})
        root = result["spans"][0]
        assert root["attributes"]["total_tokens"] == 50000
        assert root["attributes"]["provider"] == "github"


class TestIndexManagement:
    """Test 1.10: index.json CRUD."""

    def test_session_entry_fields(self, tmp_project):
        trace_mod.cmd_init("s1", meta_issue_number=42,
                           meta_issue_url="https://example.com/42")
        trace_mod.cmd_start_span("s1", "IMPL", "step")
        sid = trace_mod.cmd_start_span("s1", "issue-1", "issue")
        trace_mod.cmd_end_span("s1", sid)
        trace_mod.cmd_finalize("s1", attrs={
            "total_tokens": 50000,
            "total_tool_uses": 25,
            "complexity": "simple",
            "provider": "github",
        })

        index = trace_mod._load_index()
        entry = index["sessions"][0]

        required_fields = [
            "session_id", "meta_issue", "started_at_ms", "ended_at_ms",
            "duration_ms", "total_tokens", "total_tool_uses", "issue_count",
            "status", "complexity", "provider",
        ]
        for field in required_fields:
            assert field in entry, f"Missing field: {field}"

        assert entry["session_id"] == "s1"
        assert entry["meta_issue"]["number"] == 42
        assert entry["total_tokens"] == 50000
        assert entry["total_tool_uses"] == 25
        assert entry["issue_count"] == 1
        assert entry["complexity"] == "simple"
        assert entry["provider"] == "github"

    def test_multiple_sessions(self, tmp_project):
        trace_mod.cmd_init("s1")
        trace_mod.cmd_finalize("s1")
        trace_mod.cmd_init("s2")
        trace_mod.cmd_finalize("s2")

        index = trace_mod._load_index()
        assert len(index["sessions"]) == 2


class TestRetentionPolicy:
    """Test 1.11: file retention policy."""

    def test_retention_purge(self, tmp_project, monkeypatch):
        # Patch retention to 5 for faster test
        monkeypatch.setattr(trace_mod, "_get_retention_count", lambda: 5)

        # Create 6 sessions
        for i in range(6):
            sid = f"s{i:03d}"
            trace_mod.cmd_init(sid)
            # Manually set start_time for ordering
            trace = trace_mod._load_trace(sid)
            trace["spans"][0]["start_time_ms"] = 1000000 + i * 1000
            trace_mod._save_trace(sid, trace)
            trace_mod.cmd_finalize(sid)

        index = trace_mod._load_index()
        # Oldest session should have file_available=False
        oldest = [e for e in index["sessions"] if e["session_id"] == "s000"][0]
        assert oldest["file_available"] is False
        assert not (tmp_project / ".claude" / "autopilot-traces" / "s000.json").exists()

        # Other sessions should still have files
        for i in range(1, 6):
            sid = f"s{i:03d}"
            entry = [e for e in index["sessions"] if e["session_id"] == sid][0]
            assert entry.get("file_available", True) is True


class TestSchemaValidation:
    """Test 1.12: span schema integrity."""

    def test_required_fields_present(self, tmp_project):
        trace_mod.cmd_init("s1")
        span_id = trace_mod.cmd_start_span("s1", "TEST", "step")
        trace = trace_mod._load_trace("s1")
        span = trace_mod._find_span(trace, span_id)

        required = ["id", "parent_id", "name", "kind", "status", "start_time_ms"]
        for field in required:
            assert field in span, f"Missing required field: {field}"

    def test_closed_span_has_end_fields(self, tmp_project):
        trace_mod.cmd_init("s1")
        span_id = trace_mod.cmd_start_span("s1", "TEST", "step")
        trace_mod.cmd_end_span("s1", span_id)
        trace = trace_mod._load_trace("s1")
        span = trace_mod._find_span(trace, span_id)
        assert span["end_time_ms"] is not None
        assert span["duration_ms"] is not None

    def test_conditional_fields_allowed(self, tmp_project):
        """Step span can have issue_number (permissive, no error)."""
        trace_mod.cmd_init("s1")
        span_id = trace_mod.cmd_start_span("s1", "TEST", "step",
                                            attrs={"issue_number": 42})
        trace = trace_mod._load_trace("s1")
        span = trace_mod._find_span(trace, span_id)
        assert span["attributes"]["issue_number"] == 42


class TestEdgeCases:
    """Test 1.13: edge cases."""

    def test_end_nonexistent_span(self, tmp_project):
        trace_mod.cmd_init("s1")
        with pytest.raises(ValueError, match="Span not found"):
            trace_mod.cmd_end_span("s1", "does-not-exist")

    def test_nonexistent_session(self, tmp_project):
        with pytest.raises(FileNotFoundError):
            trace_mod.cmd_start_span("nonexistent", "X", "step")

    def test_auto_directory_creation(self, tmp_project):
        shutil.rmtree(tmp_project / ".claude" / "autopilot-traces")
        trace_mod.cmd_init("s1")
        assert (tmp_project / ".claude" / "autopilot-traces" / "s1.json").exists()


class TestParseAttrs:
    """Tests for _parse_attrs helper."""

    def test_string_value(self):
        result = trace_mod._parse_attrs(["key=value"])
        assert result == {"key": "value"}

    def test_int_value(self):
        result = trace_mod._parse_attrs(["count=42"])
        assert result == {"count": 42}

    def test_bool_values(self):
        result = trace_mod._parse_attrs(["a=true", "b=false"])
        assert result == {"a": True, "b": False}

    def test_null_value(self):
        result = trace_mod._parse_attrs(["x=null"])
        assert result == {"x": None}

    def test_empty_list(self):
        assert trace_mod._parse_attrs([]) == {}
        assert trace_mod._parse_attrs(None) == {}


class TestE2ELifecycle:
    """E2E 1.1: Full tracing lifecycle + schema validation."""

    def test_full_lifecycle(self, tmp_project):
        # init
        trace_mod.cmd_init("e2e-001")

        # session → step → issue → sub_step (4 levels)
        step_id = trace_mod.cmd_start_span("e2e-001", "IMPL-LOOP", "step",
                                           attrs={"model_requested": "sonnet"})
        issue_id = trace_mod.cmd_start_span("e2e-001", "issue-42", "issue",
                                            attrs={"issue_number": 42})
        sub_id = trace_mod.cmd_start_span("e2e-001", "code-review", "sub_step",
                                          attrs={"attempt": 1, "verdict": "APPROVE"})

        # add event + notes
        trace_mod.cmd_add_event("e2e-001", sub_id, "retry",
                                attrs={"reason": "lint-fail"})
        trace_mod.cmd_add_notes("e2e-001", sub_id, "Observation note")

        # end in reverse order
        trace_mod.cmd_end_span("e2e-001", sub_id)
        trace_mod.cmd_end_span("e2e-001", issue_id)
        trace_mod.cmd_end_span("e2e-001", step_id,
                               attrs={"total_tokens": 45230})

        # finalize
        result = trace_mod.cmd_finalize("e2e-001", attrs={
            "total_tokens": 45230,
            "total_tool_uses": 12,
            "complexity": "complex",
            "provider": "github",
        })

        # Verify all spans
        assert len(result["spans"]) == 4  # session + step + issue + sub_step

        # Required fields on all spans
        for span in result["spans"]:
            assert "id" in span
            assert "parent_id" in span or span["kind"] == "session"
            assert "name" in span
            assert "kind" in span
            assert "status" in span
            assert "start_time_ms" in span
            assert span["end_time_ms"] is not None
            assert span["duration_ms"] is not None
            assert span["duration_ms"] == span["end_time_ms"] - span["start_time_ms"]

        # Conditional fields
        step_span = [s for s in result["spans"] if s["kind"] == "step"][0]
        assert step_span["attributes"]["model_requested"] == "sonnet"
        assert step_span["attributes"]["total_tokens"] == 45230

        issue_span = [s for s in result["spans"] if s["kind"] == "issue"][0]
        assert issue_span["attributes"]["issue_number"] == 42

        sub_span = [s for s in result["spans"] if s["kind"] == "sub_step"][0]
        assert sub_span["attributes"]["attempt"] == 1
        assert sub_span["attributes"]["verdict"] == "APPROVE"

        # Optional fields
        assert sub_span["notes"] == "Observation note"
        assert len(sub_span["events"]) == 1
        assert sub_span["events"][0]["name"] == "retry"

        # Index
        index = trace_mod._load_index()
        entry = index["sessions"][0]
        required_index_fields = [
            "session_id", "meta_issue", "started_at_ms", "ended_at_ms",
            "duration_ms", "total_tokens", "total_tool_uses", "issue_count",
            "status", "complexity", "provider",
        ]
        for field in required_index_fields:
            assert field in entry, f"Missing index field: {field}"


class TestE2EHierarchy:
    """E2E 1.2: 4-level hierarchy test."""

    def test_parent_chain(self, tmp_project):
        trace_mod.cmd_init("h1")
        step_id = trace_mod.cmd_start_span("h1", "STEP", "step")
        issue_id = trace_mod.cmd_start_span("h1", "ISSUE", "issue")
        sub_id = trace_mod.cmd_start_span("h1", "SUB", "sub_step")

        trace = trace_mod._load_trace("h1")
        root = trace["spans"][0]
        step = trace_mod._find_span(trace, step_id)
        issue = trace_mod._find_span(trace, issue_id)
        sub = trace_mod._find_span(trace, sub_id)

        assert step["parent_id"] == root["id"]
        assert issue["parent_id"] == step_id
        assert sub["parent_id"] == issue_id

        assert root["kind"] == "session"
        assert step["kind"] == "step"
        assert issue["kind"] == "issue"
        assert sub["kind"] == "sub_step"
