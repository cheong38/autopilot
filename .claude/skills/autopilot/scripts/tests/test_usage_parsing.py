"""Test 2.11: <usage> tag parsing unit tests.

Tests the parse_usage_tag() function in trace.py for:
- Normal parsing
- Tag absent (→ null)
- Parse failure (→ null)
- Partial data (only some fields present)
"""

import importlib.util
import sys
from pathlib import Path

# Add scripts dir to path
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

# Import trace.py (shadowed name, use importlib)
_spec = importlib.util.spec_from_file_location(
    "trace_module", SCRIPTS_DIR / "trace.py"
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
parse_usage_tag = _mod.parse_usage_tag


class TestUsageParsing:
    """Test <usage> tag parsing from Agent tool results."""

    def test_normal_parsing(self):
        """Parse complete <usage> block with all fields."""
        text = """Some result text here.
<usage>
total_tokens: 45230
tool_uses: 12
duration_ms: 120000
</usage>
More text after."""
        result = parse_usage_tag(text)
        assert result["total_tokens"] == 45230
        assert result["tool_uses"] == 12
        assert result["duration_ms"] == 120000

    def test_tag_absent(self):
        """No <usage> tag → all values null."""
        text = "Agent completed successfully. No usage block."
        result = parse_usage_tag(text)
        assert result["total_tokens"] is None
        assert result["tool_uses"] is None
        assert result["duration_ms"] is None

    def test_parse_failure_non_numeric(self):
        """Non-numeric values → null for those fields."""
        text = "<usage>\ntotal_tokens: not_a_number\ntool_uses: 5\n</usage>"
        result = parse_usage_tag(text)
        assert result["total_tokens"] is None
        assert result["tool_uses"] == 5
        assert result["duration_ms"] is None

    def test_partial_data_total_tokens_only(self):
        """Only total_tokens present → others null."""
        text = "<usage>\ntotal_tokens: 30000\n</usage>"
        result = parse_usage_tag(text)
        assert result["total_tokens"] == 30000
        assert result["tool_uses"] is None
        assert result["duration_ms"] is None

    def test_partial_data_tool_uses_only(self):
        """Only tool_uses present → others null."""
        text = "<usage>\ntool_uses: 8\n</usage>"
        result = parse_usage_tag(text)
        assert result["total_tokens"] is None
        assert result["tool_uses"] == 8
        assert result["duration_ms"] is None

    def test_empty_usage_block(self):
        """Empty <usage></usage> → all null."""
        text = "<usage></usage>"
        result = parse_usage_tag(text)
        assert result["total_tokens"] is None
        assert result["tool_uses"] is None
        assert result["duration_ms"] is None

    def test_whitespace_handling(self):
        """Extra whitespace around values is handled."""
        text = "<usage>\n  total_tokens:  45230  \n  tool_uses:  12  \n</usage>"
        result = parse_usage_tag(text)
        assert result["total_tokens"] == 45230
        assert result["tool_uses"] == 12

    def test_unknown_keys_ignored(self):
        """Unknown keys in <usage> block are ignored."""
        text = "<usage>\ntotal_tokens: 100\nunknown_field: abc\ntool_uses: 5\n</usage>"
        result = parse_usage_tag(text)
        assert result["total_tokens"] == 100
        assert result["tool_uses"] == 5
        assert "unknown_field" not in result

    def test_multiline_result_with_usage(self):
        """Usage tag embedded in complex Agent result."""
        text = """ISSUE_IMPL_RESULT_BEGIN
STATUS=complete
PR=42
ISSUE_IMPL_RESULT_END

<usage>
total_tokens: 88000
tool_uses: 35
duration_ms: 300000
</usage>"""
        result = parse_usage_tag(text)
        assert result["total_tokens"] == 88000
        assert result["tool_uses"] == 35
        assert result["duration_ms"] == 300000

    def test_return_type_is_dict(self):
        """Always returns a dict with the expected keys."""
        result = parse_usage_tag("")
        assert isinstance(result, dict)
        assert set(result.keys()) == {"total_tokens", "tool_uses", "duration_ms"}
