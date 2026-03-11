"""Tests for step sequence validation and create_state overwrite/lock behavior."""

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
update_field = _mod.update_field
state_file_path = _mod.state_file_path
_validate_step_transition = _mod._validate_step_transition


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


# --- Step transition tests (9) ---


class TestStepTransitionValidation:
    """Test _validate_step_transition logic."""

    def test_forward_transition_allowed(self):
        """Forward transitions are always allowed."""
        _validate_step_transition("META-ISSUE", "CLASSIFY", complexity=None)
        _validate_step_transition("CLASSIFY", "REPORT", complexity=None)

    def test_backward_transition_blocked(self):
        """Backward transitions to non-loop-back targets are blocked."""
        with pytest.raises(ValueError, match="Invalid step transition"):
            _validate_step_transition("REPORT", "CLASSIFY", complexity=None)

    def test_same_step_allowed(self):
        """Same step re-entry is allowed (tgt_idx >= cur_idx)."""
        _validate_step_transition("IMPL-LOOP", "IMPL-LOOP", complexity=None)

    def test_loop_back_impl_loop_allowed(self):
        """IMPL-LOOP is an allowed loop-back target."""
        _validate_step_transition("CHECKPOINT", "IMPL-LOOP", complexity=None)

    def test_loop_back_followup_allowed(self):
        """FOLLOWUP is an allowed loop-back target."""
        _validate_step_transition("REPORT", "FOLLOWUP", complexity=None)

    def test_loop_back_impl_allowed_simple(self):
        """IMPL is an allowed loop-back target in simple path."""
        _validate_step_transition("VERIFY", "IMPL", complexity="simple")

    def test_backward_to_non_loop_blocked_simple(self):
        """Backward to non-loop-back in simple path is blocked."""
        with pytest.raises(ValueError, match="Invalid step transition"):
            _validate_step_transition("REPORT", "ISSUE", complexity="simple")

    def test_unknown_step_passes_through(self):
        """Unknown steps are not validated (name check is elsewhere)."""
        _validate_step_transition("UNKNOWN", "CLASSIFY", complexity=None)
        _validate_step_transition("CLASSIFY", "UNKNOWN", complexity=None)

    def test_forward_skip_allowed(self):
        """Forward skips (non-adjacent) are allowed."""
        _validate_step_transition("META-ISSUE", "IMPL-LOOP", complexity=None)


class TestStepTransitionIntegration:
    """Test step transition via update_field."""

    def test_update_field_forward_allowed(self, state_env):
        """update_field allows forward step transitions."""
        update_field("current_step", "CLASSIFY")

    def test_update_field_backward_blocked(self, state_env):
        """update_field blocks backward step transitions."""
        update_field("current_step", "IMPL-LOOP")
        with pytest.raises(ValueError, match="Invalid step transition"):
            update_field("current_step", "CLASSIFY")


# --- create_state overwrite + lock tests (3) ---


class TestCreateStateOverwrite:
    """Test create_state overwrite and lock removal behavior."""

    def test_overwrite_complete_session(self, state_env):
        """Non-active (complete) session can be overwritten."""
        update_field("status", "complete")
        state = create_state(
            meta_issue=200,
            meta_url="https://github.com/test/repo/issues/200",
            provider="github",
            source="test2",
        )
        assert state["meta_issue"]["number"] == 200

    def test_overwrite_aborted_session(self, state_env):
        """Non-active (aborted) session can be overwritten."""
        update_field("status", "aborted")
        state = create_state(
            meta_issue=201,
            meta_url="https://github.com/test/repo/issues/201",
            provider="github",
            source="test3",
        )
        assert state["meta_issue"]["number"] == 201

    def test_active_session_raises(self, state_env):
        """Active (in_progress) session raises FileExistsError."""
        with pytest.raises(FileExistsError, match="Active session exists"):
            create_state(
                meta_issue=202,
                meta_url="https://github.com/test/repo/issues/202",
                provider="github",
                source="test4",
            )

    def test_create_removes_gate_lock(self, tmp_path, monkeypatch):
        """create_state removes autopilot-gate.lock after creating state."""
        monkeypatch.setattr(_mod, "_git_root", lambda: tmp_path)
        lock = tmp_path / ".claude" / "autopilot-gate.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.touch()
        assert lock.exists()

        create_state(
            meta_issue=300,
            meta_url="https://github.com/test/repo/issues/300",
            provider="github",
            source="test",
        )
        assert not lock.exists()
