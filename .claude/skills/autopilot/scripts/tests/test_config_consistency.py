"""Test 2.10: checklist.py & autopilot-state.py consistency tests.

Verifies that step names in AUTOPILOT_STEPS match the valid steps
defined in autopilot-state.py, and that new steps exist in both.
"""

import importlib.util
import re
import sys
from pathlib import Path

# Add scripts dir to path
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from checklist import AUTOPILOT_STEPS, AUTOPILOT_SIMPLE_STEPS

# Import autopilot-state.py (hyphenated module name)
_spec = importlib.util.spec_from_file_location(
    "autopilot_state", SCRIPTS_DIR / "autopilot-state.py"
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
VALID_STEPS = _mod.VALID_STEPS
VALID_SIMPLE_STEPS = _mod.VALID_SIMPLE_STEPS


def _extract_step_name(entry: str) -> str:
    """Extract step name from checklist entry like 'VERIFY (Step 6.5)' → 'VERIFY'."""
    match = re.match(r"^([A-Z][A-Z0-9-]*)", entry)
    assert match, f"Could not extract step name from: {entry}"
    return match.group(1)


class TestStepConsistency:
    """Verify checklist steps match autopilot-state valid steps."""

    def test_all_autopilot_steps_in_valid_steps(self):
        """Every step in AUTOPILOT_STEPS must be in VALID_STEPS."""
        for entry in AUTOPILOT_STEPS:
            name = _extract_step_name(entry)
            assert name in VALID_STEPS, (
                f"Step '{name}' from checklist not found in VALID_STEPS"
            )

    def test_all_simple_steps_in_valid_simple_steps(self):
        """Every step in AUTOPILOT_SIMPLE_STEPS must be in VALID_SIMPLE_STEPS."""
        for entry in AUTOPILOT_SIMPLE_STEPS:
            name = _extract_step_name(entry)
            assert name in VALID_SIMPLE_STEPS, (
                f"Step '{name}' from simple checklist not found in VALID_SIMPLE_STEPS"
            )

    def test_new_steps_in_autopilot_steps(self):
        """New steps (Phase 2/4/5) must exist in AUTOPILOT_STEPS."""
        new_steps = {
            "VERIFY-INFRA-CHECK",
            "PRE-DEPLOY-VERIFY",
            "DEPLOY-DETECT",
            "DEPLOY-VERIFY",
        }
        checklist_names = {_extract_step_name(e) for e in AUTOPILOT_STEPS}
        for step in new_steps:
            assert step in checklist_names, (
                f"New step '{step}' missing from AUTOPILOT_STEPS"
            )

    def test_new_steps_in_valid_steps(self):
        """New steps must exist in VALID_STEPS."""
        new_steps = {
            "VERIFY-INFRA-CHECK",
            "PRE-DEPLOY-VERIFY",
            "DEPLOY-DETECT",
            "DEPLOY-VERIFY",
        }
        for step in new_steps:
            assert step in VALID_STEPS, (
                f"New step '{step}' missing from VALID_STEPS"
            )

    def test_step_order_in_checklist(self):
        """Verify the new steps appear in correct order in the checklist."""
        names = [_extract_step_name(e) for e in AUTOPILOT_STEPS]
        dag_confirm_idx = names.index("DAG-CONFIRM")
        verify_infra_idx = names.index("VERIFY-INFRA-CHECK")
        impl_loop_idx = names.index("IMPL-LOOP")
        pre_deploy_idx = names.index("PRE-DEPLOY-VERIFY")
        deploy_detect_idx = names.index("DEPLOY-DETECT")
        deploy_verify_idx = names.index("DEPLOY-VERIFY")
        triage_idx = names.index("TRIAGE")

        assert dag_confirm_idx < verify_infra_idx < impl_loop_idx
        assert impl_loop_idx < pre_deploy_idx < deploy_detect_idx < deploy_verify_idx < triage_idx

    def test_no_duplicate_step_names(self):
        """No duplicate step names in either checklist."""
        autopilot_names = [_extract_step_name(e) for e in AUTOPILOT_STEPS]
        assert len(autopilot_names) == len(set(autopilot_names)), "Duplicate in AUTOPILOT_STEPS"

        simple_names = [_extract_step_name(e) for e in AUTOPILOT_SIMPLE_STEPS]
        assert len(simple_names) == len(set(simple_names)), "Duplicate in AUTOPILOT_SIMPLE_STEPS"

    def test_old_verify_step_renamed(self):
        """Old 'VERIFY (Step 6.5)' should be renamed to PRE-DEPLOY-VERIFY."""
        entries_with_6_5 = [e for e in AUTOPILOT_STEPS if "Step 6.5" in e]
        assert len(entries_with_6_5) == 1
        assert entries_with_6_5[0].startswith("PRE-DEPLOY-VERIFY")
