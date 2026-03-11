#!/usr/bin/env python3
"""Unit tests for ambiguity check logic (Step 3.5).

Tests the heuristic that determines whether brainstorming should be triggered.
This is a standalone module that can be imported by the /issue orchestrator.
"""

import re
import unittest


# ---------------------------------------------------------------------------
# Ambiguity check logic (extracted for testability)
# ---------------------------------------------------------------------------

# Indicators for each issue type (from SKILL.md)
STORY_INDICATORS = [
    "사용자가", "as a user", "i want to", "feature", "기능", "할 수 있도록",
]
TASK_INDICATORS = [
    "설정", "구성", "마이그레이션", "configure", "setup", "migrate",
    "refactor", "update", "upgrade", "create", "integrate",
]
BUG_INDICATORS = [
    "버그", "에러", "오류", "안됨", "깨짐", "bug", "error", "broken",
    "crash", "fix", "not working", "regression", "fails", "unexpected",
    "500", "404", "exception", "traceback",
]

# Patterns that indicate clear, specific requirements
CLEAR_PATTERNS = [
    r"재현\s*단계",           # reproduction steps (Korean)
    r"steps?\s+to\s+reproduce",
    r"expected\s+behavior",
    r"actual\s+behavior",
    r"acceptance\s+criteria",
    r"수락\s*기준",
    r"done\s+criteria",
    r"완료\s*기준",
    r"given\s+.*when\s+.*then",
]


def needs_brainstorming(
    user_input: str,
    issue_type: str | None = None,
    flags: dict | None = None,
) -> bool:
    """Determine if brainstorming should be triggered.

    Args:
        user_input: Raw user input text.
        issue_type: Detected or explicit type ('story', 'task', 'bug', None).
        flags: Dict of flags (e.g., {'no_brainstorm': True}).

    Returns:
        True if brainstorming should be triggered.
    """
    flags = flags or {}

    # --no-brainstorm flag always skips
    if flags.get("no_brainstorm"):
        return False

    text = user_input.strip().lower()

    # Empty or extremely short input → brainstorm
    if len(text) < 10:
        return True

    # Bug with reproduction steps → skip
    if issue_type == "bug":
        for pattern in CLEAR_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return False
        # Bug indicators present but no clear structure → still might need brainstorming
        bug_count = sum(1 for ind in BUG_INDICATORS if ind in text)
        if bug_count >= 2:
            return False  # Multiple bug indicators = reasonably clear

    # Clear task with specific scope → skip
    if issue_type == "task":
        task_count = sum(1 for ind in TASK_INDICATORS if ind in text)
        if task_count >= 1 and len(text) > 30:
            return False  # Task with some specificity

    # Check for clear requirements patterns (any type)
    for pattern in CLEAR_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return False

    # Story type with vague description → brainstorm
    if issue_type == "story":
        # Check if acceptance criteria are present
        has_ac = any(
            re.search(p, text, re.IGNORECASE)
            for p in [r"acceptance", r"수락", r"given.*when.*then"]
        )
        if not has_ac:
            return True

    # General heuristic: short input with no clear structure → brainstorm
    word_count = len(text.split())
    if word_count < 8:
        return True

    # Multi-sentence with specific terms → probably clear enough
    # Filter out URL-like patterns before counting sentences to avoid inflation
    text_no_urls = re.sub(r'https?://\S+|[\w.-]+\.\w{2,}/\S*', '', text)
    sentence_count = len([s for s in re.split(r'[.!?\n]', text_no_urls) if s.strip()])
    if sentence_count >= 3 and word_count > 20:
        return False

    # Default: brainstorm for safety
    return True


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAmbiguityCheck(unittest.TestCase):
    """Test the needs_brainstorming heuristic."""

    def test_empty_input_triggers(self):
        self.assertTrue(needs_brainstorming(""))

    def test_short_vague_input_triggers(self):
        self.assertTrue(needs_brainstorming("로그인"))
        self.assertTrue(needs_brainstorming("auth"))
        self.assertTrue(needs_brainstorming("결제 기능"))

    def test_no_brainstorm_flag_skips(self):
        self.assertFalse(needs_brainstorming("뭔가", flags={"no_brainstorm": True}))

    def test_bug_with_reproduction_steps_skips(self):
        self.assertFalse(needs_brainstorming(
            "로그인 시 500 에러 발생. Steps to reproduce: 1. Go to login page 2. Enter credentials 3. Click submit",
            issue_type="bug",
        ))

    def test_bug_with_multiple_indicators_skips(self):
        self.assertFalse(needs_brainstorming(
            "로그인 페이지에서 500 에러가 발생하고 crash가 남. error log 확인 필요.",
            issue_type="bug",
        ))

    def test_vague_story_triggers(self):
        self.assertTrue(needs_brainstorming(
            "사용자가 로그인할 수 있도록",
            issue_type="story",
        ))

    def test_story_with_acceptance_criteria_skips(self):
        self.assertFalse(needs_brainstorming(
            "사용자가 소셜 로그인할 수 있도록. Acceptance criteria: Given 사용자가 로그인 페이지에 있을 때, When Google 로그인 버튼 클릭, Then OAuth 플로우 시작",
            issue_type="story",
        ))

    def test_clear_task_skips(self):
        self.assertFalse(needs_brainstorming(
            "Configure CI/CD pipeline with GitHub Actions for automated testing and deployment",
            issue_type="task",
        ))

    def test_short_task_still_triggers(self):
        self.assertTrue(needs_brainstorming(
            "설정",
            issue_type="task",
        ))

    def test_detailed_multisentence_skips(self):
        self.assertFalse(needs_brainstorming(
            "결제 시스템에 Stripe 연동을 추가해야 합니다. 현재 PayPal만 지원하고 있어 Stripe webhook 처리와 결제 확인 로직이 필요합니다. 테스트 환경에서 먼저 검증한 후 프로덕션에 배포할 예정입니다.",
        ))

    def test_given_when_then_skips(self):
        self.assertFalse(needs_brainstorming(
            "Given 사용자가 장바구니에 상품을 담았을 때, When 결제 버튼을 클릭하면, Then 결제 페이지로 이동한다",
        ))


class TestAmbiguityEdgeCases(unittest.TestCase):
    """Edge cases for the ambiguity check."""

    def test_korean_bug_indicators(self):
        self.assertFalse(needs_brainstorming(
            "메인 페이지에서 버그 발생. 에러 메시지: TypeError. 콘솔에 오류가 표시됨.",
            issue_type="bug",
        ))

    def test_english_bug_with_traceback(self):
        self.assertFalse(needs_brainstorming(
            "Login endpoint returns 500 error with traceback: KeyError 'user_id'",
            issue_type="bug",
        ))

    def test_type_none_short_input_triggers(self):
        """When type is not yet determined, short vague input still triggers."""
        self.assertTrue(needs_brainstorming("검색 기능"))

    def test_type_none_detailed_skips(self):
        """Detailed input without type should not trigger if clear patterns found."""
        self.assertFalse(needs_brainstorming(
            "검색 기능 구현. Done criteria: 1. 전체 텍스트 검색 가능 2. 결과 페이지네이션 3. 필터 적용",
        ))


if __name__ == "__main__":
    unittest.main()
