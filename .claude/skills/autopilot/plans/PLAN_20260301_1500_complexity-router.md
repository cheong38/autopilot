# Implementation Plan: Autopilot Complexity Router

**설계 문서**: `docs/plans/2026-03-01-complexity-router-design.md`
**접근법**: Complexity Router — Step 0.3 CLASSIFY로 simple/complex 자동 분류

---

## 핵심 제약

- **SKILL.md 497줄** → 500줄 한계. 줄 수 예산 아래 명시.
- **test_prompts.py**가 모든 Step 0~12, 구조화 마커, UIP, 500줄 제한을 검증 중 → 변경과 동시에 테스트 업데이트.
- **기존 complex 경로 변경 없음** — 모든 기존 테스트가 그대로 통과해야 함.

---

## SKILL.md 줄 수 예산

현재: **497줄**. 한계: **500줄**. 여유: **3줄**.

### 추가 항목 (+22줄)

| 위치 | 내용 | 줄 수 |
|------|------|-------|
| Frontmatter (L4~11) | trigger/keyword 확장 | +2 |
| Orchestration Flow (L70~91) | `0.3 CLASSIFY` + simple 분기 주석 | +3 |
| Step 0~0.5 사이 | Step 0.3: CLASSIFY 섹션 (신규) | +15 |
| Status Footer (L54~67) | `Mode: simple \| complex` 줄 | +1 |
| Configuration (L45~52) | `classify_confidence` 행 | +1 |
| **합계** | | **+22** |

### 삭제/압축 항목 (-24줄)

| 위치 | 방법 | 줄 수 |
|------|------|-------|
| Error Recovery (L461~473) | `references/error-recovery.md`로 추출, 1줄 참조로 대체 | -13 |
| "Update checklist:" 반복 (L128,140,165,189,213,234,317) | Step-by-Step Detail 서두에 1회 일반 규칙 명시, 개별 라인 7개 삭제 | -6 |
| Self-Review Protocol (L475~479) | 5줄 → 3줄로 압축 | -2 |
| Status Command (L451~453) | Usage 섹션에 통합 | -3 |
| **합계** | | **-24** |

### 결과: 497 + 22 - 24 = **495줄** (여유 5줄)

---

## Checklist 생성 시점

**문제**: Step 0 (META-ISSUE)에서 `checklist.py create autopilot <meta-issue>`를 호출하지만, 이 시점에는 아직 complexity를 모른다.

**해결**: Step 0은 기존대로 `autopilot` 체크리스트를 생성한다 (complex 경로 하위호환). Step 0.3 CLASSIFY가 simple로 판정하면, **추가로** `autopilot-simple` 체크리스트를 생성한다. 이후 simple 경로는 `autopilot-simple` 체크리스트만 업데이트한다.

- Complex → `autopilot-{issue}.md` 사용 (기존 그대로)
- Simple → `autopilot-simple-{issue}.md` 생성 후 사용

`checklist_path()`를 `checklist_path(skill, issue)` 시그니처로 변경하여 skill별 파일명 분기. 기존 호출(`skill="autopilot"`)은 동일 경로 반환 → 하위호환.

---

## Simple 체크리스트 스텝 정의

**6단계** (숫자 기반, `update_step()` regex 호환):

```python
AUTOPILOT_SIMPLE_STEPS = [
    "CLASSIFY (Step 0.3)",       # step 1
    "WHY-CONTEXT (Step 0.5)",    # step 2
    "ISSUE (Step S1)",           # step 3
    "IMPL (Step S2)",            # step 4
    "VERIFY (Step S3)",          # step 5
    "REPORT (Step S4)",          # step 6
]
```

`update_step()`은 정수 step 번호로 regex 매칭(`r"- \[ \] {step_num}\."`)하므로, simple 체크리스트도 `- [ ] 1. CLASSIFY (Step 0.3)` 형식으로 생성되어 기존 함수와 호환된다.

---

## Phase 1: Simple 경로 수직 슬라이스

**목표**: autopilot이 단순 작업을 simple로 분류하고, 이슈 생성 → 구현 → 코드리뷰 → 검증 → 보고까지 완료
**가치**: "이 버그 고쳐줘"를 autopilot에 넣으면 거부 없이 전체 워크플로우 수행

### Integration Test (스크립트 체인)
- [x] **IT 1.1**: `state create` → `state update complexity simple` → `checklist create autopilot-simple` → `checklist update autopilot-simple <issue> 1 done` 체인 성공
- [x] **IT 1.2**: SKILL.md에 "Step 0.3: CLASSIFY" 존재 + simple-path.md 참조 존재
- [x] **IT 1.3**: SKILL.md ≤ 500줄
- [x] **IT 1.4**: `test_prompts.py`, `test_skill_structure.py` 전체 통과

### 1A. scripts/autopilot-state.py (TDD)
- [x] **🔴 Test 1.1**: `create_state`에 `complexity: null` 포함 확인
- [x] **🔴 Test 1.2**: `update_field("complexity", "simple")` → `"simple"` 저장 확인
- [x] **🔴 Test 1.3**: `update_field("complexity", "complex")` → `"complex"` 저장 확인
- [x] **🟢 Impl 1.4**: `create_state()`의 초기 state dict에 `"complexity": None` 추가 (1줄)

### 1B. scripts/checklist.py (TDD)
- [x] **🔴 Test 1.5**: `create_checklist(skill="autopilot-simple")` 시 6단계 체크리스트 생성 확인
- [x] **🔴 Test 1.6**: 생성된 체크리스트에 6단계 (CLASSIFY, WHY-CONTEXT, ISSUE, IMPL, VERIFY, REPORT) 포함 확인
- [x] **🔴 Test 1.7**: `update_step(skill="autopilot-simple", issue="99", step="1", status="done")` 성공 확인
- [x] **🔴 Test 1.8**: 기존 `autopilot` 체크리스트 동작 변경 없음 확인 (회귀 테스트)
- [x] **🟢 Impl 1.9**: `AUTOPILOT_SIMPLE_STEPS` 상수 추가 (위 6단계)
- [x] **🟢 Impl 1.10**: `STEPS` dict 구조화 — `{"autopilot": AUTOPILOT_STEPS, "autopilot-simple": AUTOPILOT_SIMPLE_STEPS}`
- [x] **🟢 Impl 1.11**: `checklist_path(skill, issue)` → `CHECKLIST_DIR / f"{skill}-{issue}.md"` (시그니처 변경)
- [x] **🟢 Impl 1.12**: `create_checklist()`, `update_step()`, `read_checklist()` — `skill` 파라미터로 step 목록/경로 분기
- [x] **🟢 Impl 1.13**: argparse `choices`에 `"autopilot-simple"` 추가

### 1C. references/simple-path.md (신규)
- [x] **🟢 Impl 1.14**: Simple path 전체 상세 작성:
  - Step S1: ISSUE — `/issue` 호출 (review cycle 포함), `autopilot-state.py add-issue` 로 state 저장
  - Step S2: IMPL — `/issue-impl <issue_number>` 호출, 코드리뷰는 issue-impl 내부 Step 8에 포함
  - Step S3: VERIFY — Playwright/CLI/테스트 검증, [Verification Matrix](references/verification-matrix.md) 참조
  - Step S4: REPORT — 결과 보고, 메타이슈 닫기, 세션 잠금 해제
  - Simple 경로 status footer 형식 (`Mode: simple`, `Progress` 생략)
  - Simple 경로 `AUTOPILOT_RESULT` 형식 (`MODE=simple`, `ISSUE=<N>`, `PR=<N>`)
  - 에러 복구: `/issue` 실패 → 직접 생성 fallback, `/issue-impl` 실패 → UIP-26 참조
  - Checklist 업데이트 규칙: 각 step 완료 시 `checklist.py update autopilot-simple <meta-issue> <N> done`

### 1D. references/error-recovery.md (추출)
- [x] **🟢 Impl 1.15**: 기존 SKILL.md Error Recovery 테이블을 `references/error-recovery.md`로 추출
  - 내용 그대로 이동, SKILL.md에는 `See [Error Recovery](references/error-recovery.md).` 1줄로 대체

### 1E. SKILL.md 수정
- [x] **🟢 Impl 1.16**: Frontmatter description & triggers 확장 (+2줄)
  - description: "End-to-end implementation orchestrator. Handles PRDs, requirements, bug fixes, and simple tasks."
  - Trigger에 "이 이슈 해결해줘", "이 버그 고쳐" 추가
  - Keywords에 "bug fix", "simple task", "단순 작업" 추가
- [x] **🟢 Impl 1.17**: Orchestration Flow 다이어그램 수정 (+3줄)
  - `0.3 CLASSIFY` 행 삽입
  - simple 분기 주석: `    └─ simple → See references/simple-path.md`
- [x] **🟢 Impl 1.18**: Step 0.3: CLASSIFY 섹션 추가 (+15줄, Step 0과 Step 0.5 사이)
  - 분류 기준 5가지 (이슈 1개, 요구사항 명확, 의존성 없음, NFR 없음, 다중 도메인 아님)
  - confidence < 90% → complex fallback
  - State 업데이트: `autopilot-state.py update --field complexity --value <simple|complex>`
  - Simple → `checklist.py create autopilot-simple <meta-issue>` 후 [Simple Path](references/simple-path.md) 진입
  - Complex → 기존 Step 0.5부터 계속
- [x] **🟢 Impl 1.19**: Status Footer에 `Mode: simple | complex` 추가 (+1줄)
- [x] **🟢 Impl 1.20**: Configuration 테이블에 `classify_confidence | 90 | Minimum confidence % for simple classification` 추가 (+1줄)
- [x] **🟢 Impl 1.21**: 줄 수 압축 (-24줄)
  - Error Recovery → reference 추출 (-13줄)
  - "Update checklist:" 반복 7개 → Step-by-Step Detail 서두에 일반 규칙 1줄로 대체 (-6줄)
  - Self-Review Protocol 5→3줄 압축 (-2줄)
  - Status Command → Usage 섹션 통합 (-3줄)
- [x] **🟢 Impl 1.22**: Dependencies & References에 `[Simple Path](references/simple-path.md)`, `[Error Recovery](references/error-recovery.md)` 추가

### 1F. 테스트 업데이트 (변경과 동시)
- [x] **🟢 Impl 1.23**: `scripts/test_prompts.py` 수정
  - `REQUIRED_STEPS`에 `"Step 0.3: CLASSIFY"` 추가
  - `REFERENCE_FILES`에 `"references/simple-path.md"`, `"references/error-recovery.md"` 추가
- [x] **🟢 Impl 1.24**: `tests/test_skill_structure.py` 수정
  - `REQUIRED_REFERENCES`에 `"simple-path.md"`, `"error-recovery.md"` 추가

### Quality Gate ✋
- [x] `python3 ~/.claude/skills/autopilot/scripts/test_prompts.py` — 0 errors
- [x] `python3 -m unittest discover -s ~/.claude/skills/autopilot/tests -v` — 전체 통과
- [x] SKILL.md ≤ 500줄 (`wc -l` 확인)
- [x] `references/simple-path.md` 5줄 이상 (placeholder 아님)
- [x] `references/error-recovery.md` 5줄 이상 (placeholder 아님)
- [x] 기존 complex 경로 Step 0~12 전부 남아있음 확인
- [x] 기존 `autopilot` 체크리스트 회귀 없음

---

## Phase 2: Simple 경로 Resume 지원

**목표**: 중단된 simple 세션을 `/autopilot --resume`로 재개 가능
**가치**: simple 경로에서도 context compaction이나 세션 중단 시 이어서 작업 가능

### Integration Test
- [x] **IT 2.1**: resume-protocol.md에 simple 경로 재진입 로직 포함
- [x] **IT 2.2**: 전체 테스트 스위트 통과

### 2A. references/resume-protocol.md 수정
- [x] **🟢 Impl 2.1**: `## Simple Path Re-entry` 섹션 추가:
  - **CLASSIFY (Step 0.3)**: state의 `complexity` 필드 확인 → 값 있으면 스킵, null이면 재분류
  - **ISSUE (Step S1)**: state의 `issues` 배열 확인 → 이슈 존재하면 스킵, 없으면 생성
  - **IMPL (Step S2)**: issue-impl 자체 resume 메커니즘 활용 (`/issue-impl <issue_number>`)
  - **VERIFY (Step S3)**: 항상 재실행 (부분 검증 상태 신뢰 불가)
  - **REPORT (Step S4)**: 항상 재실행
  - 재진입 판단: `current_step` 필드 + `complexity == "simple"` → simple resume 경로

### Quality Gate ✋ (최종)
- [x] `python3 ~/.claude/skills/autopilot/scripts/test_prompts.py` — 0 errors
- [x] `python3 -m unittest discover -s ~/.claude/skills/autopilot/tests -v` — 전체 통과
- [x] resume-protocol.md에 Simple Path 섹션 존재

---

## 변경 파일 요약

| 파일 | Phase | 변경 내용 |
|------|-------|----------|
| `scripts/autopilot-state.py` | 1 | `complexity: null` 초기값 추가 |
| `scripts/checklist.py` | 1 | `autopilot-simple` 타입 추가, `checklist_path(skill, issue)` 시그니처 변경 |
| `tests/test_state_management.py` | 1 | complexity 필드 테스트 3개 추가 |
| `references/simple-path.md` | 1 | 신규 — simple 경로 S1~S4 상세 |
| `references/error-recovery.md` | 1 | 신규 — SKILL.md에서 추출한 에러 복구 테이블 |
| `SKILL.md` | 1 | CLASSIFY 단계, frontmatter, flow, footer, 줄 수 압축 |
| `scripts/test_prompts.py` | 1 | CLASSIFY step + simple-path.md + error-recovery.md 검증 |
| `tests/test_skill_structure.py` | 1 | simple-path.md, error-recovery.md 참조 추가 |
| `references/resume-protocol.md` | 2 | simple 경로 재진입 로직 |

## 미변경 파일

- `/issue`, `/issue-impl`, `/issue-dag` 스킬 전체
- `references/verification-matrix.md`, `agent-delegation.md`, `self-review-criteria.md`, `self-review-prompt-template.md`, `ingest-formats.md`
- 기존 complex 경로 Step 0.5~12 내용 (Step 0에서 checklist 생성하는 기존 코드도 유지)
