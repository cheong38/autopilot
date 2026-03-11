"""E2E 4.2: Deploy-verify tracing simulation test.

Simulates a deploy-verify scenario using trace.py calls and verifies
the resulting trace JSON has correct span hierarchy and attributes.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

# Load trace.py module
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "trace_module", SCRIPTS_DIR / "trace.py"
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

cmd_init = _mod.cmd_init
cmd_start_span = _mod.cmd_start_span
cmd_end_span = _mod.cmd_end_span
cmd_add_event = _mod.cmd_add_event
cmd_finalize = _mod.cmd_finalize
_load_trace = _mod._load_trace


@pytest.fixture
def trace_session(tmp_path, monkeypatch):
    """Set up a trace session for testing."""
    monkeypatch.setattr(_mod, "_git_root", lambda: tmp_path)
    session_id = "deploy-verify-test"
    cmd_init(session_id, meta_issue_number=100)

    # Create session → step (IMPL-LOOP) → issue hierarchy
    impl_span = cmd_start_span(session_id, "IMPL-LOOP", "step")
    issue_span = cmd_start_span(session_id, "issue-101", "issue",
                                 {"issue_number": 101, "skill_invoked": "issue-impl"})

    return {
        "session_id": session_id,
        "impl_span": impl_span,
        "issue_span": issue_span,
        "tmp_path": tmp_path,
    }


class TestDeployVerifyTrace:
    """Test deploy-verify tracing simulation."""

    def test_deploy_detect_span(self, trace_session):
        """Deploy-detect creates sub_step span with env attributes."""
        sid = trace_session["session_id"]

        detect_span = cmd_start_span(sid, "deploy-detect", "sub_step")
        cmd_end_span(sid, detect_span, attrs={
            "env": "vercel",
            "deploy_url": "https://my-app.vercel.app",
        })

        trace = _load_trace(sid)
        span = next(s for s in trace["spans"] if s["id"] == detect_span)
        assert span["kind"] == "sub_step"
        assert span["name"] == "deploy-detect"
        assert span["attributes"]["env"] == "vercel"
        assert span["attributes"]["deploy_url"] == "https://my-app.vercel.app"
        assert span["status"] == "ok"

    def test_test_data_setup_span(self, trace_session):
        """Test data setup creates sub_step span."""
        sid = trace_session["session_id"]

        setup_span = cmd_start_span(sid, "test-data-setup", "sub_step")
        cmd_end_span(sid, setup_span, status="ok")

        trace = _load_trace(sid)
        span = next(s for s in trace["spans"] if s["id"] == setup_span)
        assert span["kind"] == "sub_step"
        assert span["status"] == "ok"

    def test_verify_automated_span(self, trace_session):
        """Verify-automated creates sub_step with method and result."""
        sid = trace_session["session_id"]

        verify_span = cmd_start_span(sid, "verify-automated", "sub_step",
                                      {"method": "playwright"})
        cmd_end_span(sid, verify_span, attrs={"verification_result": True})

        trace = _load_trace(sid)
        span = next(s for s in trace["spans"] if s["id"] == verify_span)
        assert span["attributes"]["method"] == "playwright"
        assert span["attributes"]["verification_result"] is True

    def test_auth_handoff_event(self, trace_session):
        """Auth handoff recorded as event on verify span."""
        sid = trace_session["session_id"]

        verify_span = cmd_start_span(sid, "verify-automated", "sub_step",
                                      {"method": "playwright"})
        event = cmd_add_event(sid, verify_span, "auth-handoff", {
            "auth_type": "web_login",
            "resolved": True,
        })
        cmd_end_span(sid, verify_span, attrs={"verification_result": True})

        trace = _load_trace(sid)
        span = next(s for s in trace["spans"] if s["id"] == verify_span)
        assert len(span["events"]) == 1
        assert span["events"][0]["name"] == "auth-handoff"
        assert span["events"][0]["attributes"]["auth_type"] == "web_login"
        assert span["events"][0]["attributes"]["resolved"] is True

    def test_full_deploy_verify_hierarchy(self, trace_session):
        """Full deploy-verify flow produces correct span hierarchy."""
        sid = trace_session["session_id"]
        issue_span_id = trace_session["issue_span"]

        # Deploy detect
        detect = cmd_start_span(sid, "deploy-detect", "sub_step")
        cmd_end_span(sid, detect, attrs={"env": "docker"})

        # Test data setup
        setup = cmd_start_span(sid, "test-data-setup", "sub_step")
        cmd_end_span(sid, setup)

        # Verify automated with auth handoff
        verify = cmd_start_span(sid, "verify-automated", "sub_step",
                                 {"method": "cli"})
        cmd_add_event(sid, verify, "auth-handoff",
                       {"auth_type": "api_token", "resolved": True})
        cmd_end_span(sid, verify, attrs={"verification_result": True})

        # Close issue and impl spans
        cmd_end_span(sid, issue_span_id, attrs={"total_tokens": 15000})
        cmd_end_span(sid, trace_session["impl_span"])

        trace = _load_trace(sid)

        # Verify hierarchy: all sub_steps are children of issue span
        sub_steps = [s for s in trace["spans"] if s["kind"] == "sub_step"]
        assert len(sub_steps) == 3  # detect, setup, verify
        for ss in sub_steps:
            assert ss["parent_id"] == issue_span_id

        # Verify all spans are closed
        for span in trace["spans"]:
            if span["kind"] != "session":  # session stays open until finalize
                assert span["end_time_ms"] is not None

    def test_deploy_verify_failure_trace(self, trace_session):
        """Deploy verify failure recorded correctly."""
        sid = trace_session["session_id"]

        verify = cmd_start_span(sid, "verify-automated", "sub_step",
                                 {"method": "playwright"})
        cmd_end_span(sid, verify, status="error", attrs={
            "verification_result": False,
            "error_message": "Expected element not found",
            "error_category": "test_failure",
        })

        trace = _load_trace(sid)
        span = next(s for s in trace["spans"] if s["id"] == verify)
        assert span["status"] == "error"
        assert span["attributes"]["verification_result"] is False
        assert span["attributes"]["error_category"] == "test_failure"
