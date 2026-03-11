# Implementation Plan: Autopilot 트레이싱 & Deploy-Verify

**Status**: 📋 Planning (Rev.2 — 리뷰 피드백 반영)
**Started**: 2026-03-02 23:00 KST
**Last Updated**: 2026-03-03 00:30 KST
**Approach**: Vertical Slices + E2E-First TDD
**Design Doc**: `docs/plans/2026-03-02-tracing-and-deploy-verify-design.md`

---

**⚠️ CRITICAL INSTRUCTIONS**:

**이 프로젝트는 CLI 스크립트 + 스킬 프롬프트로 구성됩니다.**
- Python 스크립트(trace.py, trace-report.py): pytest로 TDD
- 스킬 문서(SKILL.md, references/): 통합 테스트 (실 autopilot 실행)
- 각 Phase는 독립적으로 가치를 제공하며, 의존성은 아래 다이어그램 참조

---

## 📋 Overview

### Feature Description

autopilot 스킬에 실행 추적(observability) 시스템을 추가하고, post-deploy 검증과 verification-first 선행 이슈 생성 로직을 도입한다.

### Delivery Strategy & Dependencies

**Phase 의존성 다이어그램:**
```
Phase 0 (SKILL.md 리팩토링)
    │
    ├──→ Phase 1 (trace.py 코어)
    │        │
    │        ├──→ Phase 2 (autopilot 트레이싱 통합)
    │        │        │
    │        │        └──→ Phase 3 (trace-report.py 리포트)
    │        │
    │        └──→ Phase 4 (deploy-verify) ← Phase 1 필수
    │
    └──→ Phase 5 (verify-infra-check) ← Phase 0만 필요
```

**Phase별 가치:**
```
Phase 0: SKILL.md 줄 확보           → "후속 Phase의 SKILL.md 수정 가능"
Phase 1: trace.py 코어 엔진         → "세션 트레이스 JSON 기록/관리 가능"
Phase 2: autopilot 트레이싱 통합     → "autopilot 실행 시 자동 트레이스 기록"
Phase 3: trace-report.py 리포트     → "세션 요약, 병목 분석, 이슈 코멘트 자동 생성"
Phase 4: deploy-verify 워크플로우    → "merge 후 실환경에서 자동 검증"
Phase 5: verify-infra-check        → "검증 인프라 없으면 선행 이슈 자동 생성"
```

### Step 번호 전략

기존 autopilot 단계에 새 단계를 삽입할 때, **gap 방식** 사용 (기존 번호 유지):
- 기존: ... → 5.5 (DAG-CONFIRM) → 6 (IMPL-LOOP) → 6.5 (VERIFY) → 7 (TRIAGE) → ...
- 변경: ... → 5.5 (DAG-CONFIRM) → **5.7 (VERIFY-INFRA-CHECK)** → 6 (IMPL-LOOP) → **6.5 (PRE-DEPLOY-VERIFY, 개명)** → **6.6 (DEPLOY-DETECT)** → **6.7 (DEPLOY-VERIFY)** → 7 (TRIAGE) → ...

이유: 기존 Step 6+ 번호를 재배정하면 모든 참조(체크리스트, 로그, 코멘트)를 수정해야 함. gap 방식은 기존 참조를 유지하면서 새 단계를 삽입 가능.

### Success Criteria (Per Phase)

**Phase 0**: SKILL.md가 ~450줄 이하로 축소되어 ~50줄의 여유 확보
**Phase 1**: trace.py로 span 생성/종료/이벤트/finalize가 가능하고, JSON이 스키마의 모든 필수 필드를 포함
**Phase 2**: autopilot 실행 후 트레이스 JSON에 모든 단계(simple/complex path)가 기록됨
**Phase 3**: `trace-report.py summary`가 마크다운 요약 + 인사이트를 생성하고, `gh issue comment`로 게시됨
**Phase 4**: issue-impl merge 후 deploy-verify가 fallback chain으로 실행되고 트레이스에 기록됨
**Phase 5**: 검증 인프라 부재 시 선행 이슈가 DAG blocker로 생성됨

---

## 🏗️ Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| 별도 트레이스 파일 (Approach B) | autopilot-state.json과 관심사 분리. 세션별 파일로 히스토리 비교 용이 |
| OTEL 마이그레이션 가능한 스키마 | id/parent_id/timestamps/flat attributes로 기계적 OTEL 변환 가능 |
| `<usage>` 태그 파싱으로 토큰 측정 | Agent 도구 반환값의 total_tokens가 가장 정확한 소스 |
| reference 파일 분리 | SKILL.md 500줄 제약. Phase 0에서 ~54줄 회수 후 여유 확보 |
| Step 번호 gap 방식 | 기존 참조 유지. 5.7, 6.6, 6.7을 gap으로 삽입 |
| 프로젝트 단위 infra check | 이슈별 반복 검사는 비효율. 한 번 체크 후 전체 적용 |
| 선행 이슈 재귀 방지 | prereq-infra 태그로 VERIFY-INFRA-CHECK 스킵. depth=0 강제 |
| 코멘트 게시는 gh/glab CLI | 기존 autopilot이 사용하는 provider CLI 그대로 활용 |

---

## 🚀 Implementation Phases

---

### Phase 0: SKILL.md 줄 확보 리팩토링
**Goal**: 후속 Phase에서 SKILL.md에 새 지시문을 삽입할 줄 여유 확보
**Value**: "SKILL.md를 ~450줄로 축소하여 ~50줄의 삽입 여유 확보"
**Depends on**: 없음 (첫 번째 Phase)
**Status**: ⏳ Pending

#### 🟢 Implement

- [ ] **Impl 0.1**: state block 포맷들을 `references/state-block-formats.md`로 추출
  - File: `SKILL.md` → `references/state-block-formats.md` (신규)
  - 이동 대상 (총 45줄):
    - Lines 127-134 (8줄): `AUTOPILOT_META_BEGIN/END` 블록
    - Lines 169-175 (7줄): `AUTOPILOT_INGEST_BEGIN/END` 블록
    - Lines 255-261 (7줄): `AUTOPILOT_DECOMPOSE_BEGIN/END` 블록
    - Lines 382-385 (4줄): `AUTOPILOT_CHECKPOINT_BEGIN/END` 블록
    - Lines 418-428 (11줄): `AUTOPILOT_RESULT_BEGIN/END` 블록
    - Lines 447-454 (8줄): `AUTOPILOT_ABORT_BEGIN/END` 블록
  - 각 위치에 1줄 참조 포인터 삽입: `→ See references/state-block-formats.md`
  - 순회수: 45줄 제거 - 6줄 포인터 추가 = **39줄 회수**

- [ ] **Impl 0.2**: provider-specific 이슈 생성 커맨드를 `references/meta-issue-creation-cmds.md`로 추출
  - File: `SKILL.md` Lines 112-120 → `references/meta-issue-creation-cmds.md` (신규)
  - 순회수: 9줄 제거 - 1줄 포인터 = **8줄 회수**

- [ ] **Impl 0.3**: 줄 수 검증
  - 변경 전: 497줄
  - 예상 변경 후: 497 - 39 - 8 = **450줄** (~50줄 여유)
  - 실제 줄 수 확인: `wc -l SKILL.md`

#### Quality Gate ✋

- [ ] SKILL.md ≤ 460줄 (50줄 이상 여유)
- [ ] 추출된 references/ 파일이 원본 내용과 동일
- [ ] 기존 autopilot 기능에 regression 없음 (참조 포인터가 정확)

---

### Phase 1: trace.py 트레이싱 엔진 코어
**Goal**: CLI로 세션 트레이스를 기록/관리하는 핵심 엔진
**Value**: "trace.py 커맨드로 span 생성/종료/이벤트/finalize를 실행하면, 스키마를 따르는 JSON 생성"
**Depends on**: Phase 0
**Status**: ⏳ Pending

#### Span 스키마: 필수/조건부/선택 분류

| 분류 | 필드 | 설명 |
|------|------|------|
| **필수** (모든 span) | `id`, `parent_id`, `name`, `kind`, `status`, `start_time_ms` | 생성 시 자동 설정 |
| **필수** (종료된 span) | `end_time_ms`, `duration_ms` | end-span 시 자동 계산 |
| **조건부** (step/issue) | `attributes.model_requested`, `attributes.total_tokens`, `attributes.tool_uses` | Agent 실행 시에만 |
| **조건부** (sub_step) | `attributes.attempt`, `attributes.verdict` | 리뷰 span에만 |
| **조건부** (issue) | `attributes.issue_number`, `attributes.skill_invoked` | 이슈 span에만 |
| **선택** (모든 span) | `notes`, `events[]`, `attributes.error_message`, `attributes.error_category`, `attributes.decision_points`, `attributes.dag_ready_set`, `attributes.context_compaction_count`, `attributes.wip_buffer_flushes` | 있으면 기록, 없으면 null/[] |
| **예약** (미사용) | `attributes.input_tokens`, `attributes.output_tokens` | 향후 Claude Code 지원 시 |

#### 🎯 E2E Acceptance Test (Write First)

- [ ] **E2E 1.1**: 전체 트레이싱 라이프사이클 + 스키마 검증
  - File: `scripts/tests/test_trace_e2e.py`
  - Given: 빈 `.claude/autopilot-traces/` 디렉토리
  - When: init → start-span(session) → start-span(step, --attr model_requested=sonnet) → start-span(issue, --attr issue_number=42) → start-span(sub_step, --attr attempt=1 --attr verdict=APPROVE) → add-event(retry) → add-notes("관찰 노트") → end-span(sub_step) → end-span(issue) → end-span(step, --attr total_tokens=45230) → end-span(session) → finalize
  - Then: `{session-id}.json` 생성됨
  - Then: **필수 필드 검증** — 모든 span에 id, parent_id, name, kind, status, start_time_ms 존재
  - Then: **종료 필드 검증** — 종료된 span에 end_time_ms, duration_ms 존재하고 duration = end - start
  - Then: **조건부 필드 검증** — step span에 model_requested, issue span에 issue_number, sub_step에 attempt+verdict 존재
  - Then: **선택 필드 검증** — notes 필드에 "관찰 노트", events에 retry 이벤트 존재
  - Then: **index.json 검증** — 세션 엔트리에 11개 필드 모두 존재:
    `session_id, meta_issue, started_at_ms, ended_at_ms, duration_ms, total_tokens, total_tool_uses, issue_count, status, complexity, provider`

- [ ] **E2E 1.2**: 4레벨 계층 트레이싱 테스트
  - Given: init된 세션
  - When: session(root) → step → issue → sub_step 4레벨 span 생성 후 역순 종료
  - Then: parent_id 체인: sub_step.parent_id == issue.id, issue.parent_id == step.id, step.parent_id == session.id
  - Then: kind 값: session, step, issue, sub_step 각각 정확

- [ ] **E2E 1.3**: 보존 정책 테스트
  - Given: 51개의 기존 트레이스 파일 (trace_retention_count=50)
  - When: finalize 실행
  - Then: 가장 오래된 파일 1개 삭제됨
  - Then: index.json에서 해당 세션 엔트리에 `file_available: false` 설정됨 (메트릭은 유지)

#### 🔴 RED: Write Failing Tests

**Span 관리 테스트**:
- [ ] **Test 1.4**: `init` — 세션 초기화
  - File: `scripts/tests/test_trace.py`
  - Tests: 디렉토리 생성, 빈 spans 배열로 JSON 생성, session root span 자동 생성 (kind=session)

- [ ] **Test 1.5**: `start-span` — 새 span 시작
  - Tests: UUID v4 생성, parent_id 연결, start_time_ms epoch ms 기록, kind 검증(4종), --attr key=val 파싱

- [ ] **Test 1.6**: `end-span` — span 종료
  - Tests: end_time_ms 기록, duration_ms = end - start 계산, status 설정(ok/error/skipped), --attr 병합

- [ ] **Test 1.7**: `add-event` — 이벤트 추가
  - Tests: span의 events[] 배열에 추가, timestamp_ms 기록, event attributes 파싱

- [ ] **Test 1.8**: `add-notes` — 자연어 관찰 노트
  - Tests: span의 notes 필드 업데이트, 기존 notes 덮어쓰기

- [ ] **Test 1.9**: `finalize` — 세션 종료
  - Tests: session root span 자동 종료, index.json 업데이트, 보존 정책 적용

**Index 관리 테스트**:
- [ ] **Test 1.10**: index.json CRUD
  - Tests: 세션 추가 시 11개 필드 모두 기록 (`session_id, meta_issue{number,url}, started_at_ms, ended_at_ms, duration_ms, total_tokens, total_tool_uses, issue_count, status, complexity, provider`)
  - Tests: 세션 목록 조회, 메트릭 집계

**보존 정책 테스트**:
- [ ] **Test 1.11**: 파일 개수 초과 시 정리
  - Tests: 50개 초과 시 가장 오래된 파일 삭제, index 엔트리에 `file_available: false` 표시 (메트릭은 유지)

**스키마 검증 테스트**:
- [ ] **Test 1.12**: span 스키마 무결성
  - Tests: 필수 필드 누락 시 에러, kind가 4종 외 값이면 에러, status가 3종 외 값이면 에러
  - Tests: 조건부 필드 — step span에 issue_number 넣어도 에러 아님 (허용), sub_step span에 attempt 없어도 에러 아님 (선택적)

**에러 핸들링 테스트**:
- [ ] **Test 1.13**: 엣지 케이스
  - Tests: 존재하지 않는 span_id로 end-span → 에러, 중복 init → 기존 세션 유지, 디렉토리 미존재 → 자동 생성

#### 🟢 GREEN: Implement to Pass

- [ ] **Impl 1.14**: `trace.py` 스크립트 구현
  - File: `scripts/trace.py`
  - CLI: argparse 서브커맨드 (init, start-span, end-span, add-event, add-notes, finalize)
  - 스키마: 위 필수/조건부/선택 테이블 기반. 스키마 검증 함수 포함
  - 저장 경로: `.claude/autopilot-traces/{session-id}.json` (프로젝트 상대경로)
  - UUID: `uuid.uuid4()`, 시간: `int(time.time() * 1000)` (epoch ms)
  - start-span stdout으로 span_id 반환 (후속 호출에서 사용)

- [ ] **Impl 1.15**: index.json 관리 로직
  - 세션 추가: 11개 필드 전체 기록 (design doc Section 4.1)
  - 필드 출처:
    - trace.py가 채우는 필드: `session_id, started_at_ms, ended_at_ms, duration_ms, status`
    - 호출자(SKILL.md)가 --attr로 전달: `total_tokens, total_tool_uses, issue_count, complexity, provider`
    - meta_issue: init 시 --meta-issue-number, --meta-issue-url 파라미터로 전달
  - 보존 정책: `trace_retention_count` (기본값 50, autopilot.yaml으로 override 가능)
  - 아카이브: 파일 삭제 시 index 엔트리에 `file_available: false` 표시 (메트릭 유지)

- [ ] **Impl 1.16**: autopilot-state.py에 `trace_session_id` 필드 추가
  - File: `scripts/autopilot-state.py`
  - `create_state()`에 `trace_session_id` 필드 추가 (session_id와 동일 값)
  - `update_field()`에서 해당 필드 지원

#### 🔵 REFACTOR: Clean Up

- [ ] **Refactor 1.17**: 코드 정리
  - 중복 제거, 네이밍 개선
  - autopilot-state.py와 trace.py 간 공유 유틸리티 추출 (필요 시)

#### Quality Gate ✋

- [ ] `python -m pytest scripts/tests/test_trace*.py -v` 전체 통과
- [ ] E2E 1.1 스키마 검증 — 필수 필드 100% 존재
- [ ] 기존 autopilot-state.py 기능 깨지지 않음

**Validation Commands**:
```bash
cd ~/.claude/skills/autopilot && python -m pytest scripts/tests/ -v

# 수동 E2E
cd /tmp/test-project && mkdir -p .claude
python ~/.claude/skills/autopilot/scripts/trace.py init --session-id test-001
python ~/.claude/skills/autopilot/scripts/trace.py start-span --session test-001 --name "TEST" --kind step
python ~/.claude/skills/autopilot/scripts/trace.py finalize --session test-001
cat .claude/autopilot-traces/test-001.json | python -m json.tool
cat .claude/autopilot-traces/index.json | python -m json.tool
```

---

### Phase 2: Autopilot 트레이싱 통합
**Goal**: autopilot SKILL.md와 참조 문서를 수정해서 실행 시 자동 트레이싱
**Value**: "autopilot 실행 후 트레이스 JSON에 전체 실행 히스토리가 기록됨"
**Depends on**: Phase 0 (줄 여유), Phase 1 (trace.py)
**Status**: ⏳ Pending

#### 🎯 E2E Acceptance Test (Write First)

- [ ] **E2E 2.1**: autopilot simple path 트레이싱
  - Given: 간단한 요구사항이 있는 테스트 프로젝트
  - When: autopilot simple path 실행
  - Then: 트레이스 JSON에 **6개 step span** 존재: CLASSIFY, WHY-CONTEXT, ISSUE, IMPL, VERIFY, REPORT
  - Then: IMPL span 아래에 **issue span** 존재 (kind=issue)
  - Then: issue span 아래에 **sub_step span** 존재: plan, implement, code-review 등
  - Then: 각 span에 start_time_ms, end_time_ms, duration_ms 기록됨
  - Verification: `python -c "import json; d=json.load(open('.claude/autopilot-traces/*.json')); kinds=set(s['kind'] for s in d['spans']); assert kinds == {'session','step','issue','sub_step'}"`

- [ ] **E2E 2.2**: `<usage>` 태그 파싱 검증
  - Given: Agent 도구가 `<usage>total_tokens: 45230\ntool_uses: 12\nduration_ms: 120000</usage>` 반환
  - When: IMPL-LOOP에서 /issue-impl 서브에이전트 실행 후 트레이스 기록
  - Then: 해당 issue span의 attributes에 `total_tokens: 45230`, `tool_uses: 12` 기록됨

- [ ] **E2E 2.3**: `<usage>` 태그 누락 시 graceful degradation
  - Given: Agent 도구가 `<usage>` 태그 없이 결과만 반환
  - When: 트레이스 기록
  - Then: span 생성됨, `total_tokens: null`, `tool_uses: null` (에러 없음, status=ok 유지)

- [ ] **E2E 2.4**: 하위 호환성 — 트레이싱 없는 세션
  - Given: autopilot-state.json에 `trace_session_id` 필드 없음
  - When: 기존 autopilot 실행
  - Then: 정상 완료, 트레이스 파일 생성 안 됨, 에러 없음

#### 🟢 GREEN: Implement

- [ ] **Impl 2.5**: `references/tracing-protocol.md` 작성
  - File: `references/tracing-protocol.md`
  - 내용:
    - 트레이싱 초기화: Step 0 META-ISSUE 직후, `trace.py init --session-id $SESSION_ID`
    - 각 단계별 span 생성/종료 규칙 (step 이름 매핑 테이블)
    - `<usage>` 태그 파싱 규칙:
      ```
      Agent 결과에서 <usage>...</usage> 블록 검색
      - 존재: total_tokens, tool_uses, duration_ms 추출 → end-span --attr로 전달
      - 부재: total_tokens=null, tool_uses=null로 기록 (에러 아님)
      - 파싱 실패: total_tokens=null, 경고 notes 추가
      ```
    - 이상 패턴 감지 규칙 (디자인 문서 Section 5.4)
    - 자연어 notes 작성 규칙 (수치→원인→액션 3단)
    - 인사이트 도출 규칙 (confidence ≥ 90% 설정 업데이트 제안)
    - simple path vs complex path 트레이싱 span 매핑
    - 에러 시 span 처리: status=error, error_message 기록, error_category 분류

- [ ] **Impl 2.6**: SKILL.md 트레이싱 지시문 삽입
  - File: `SKILL.md`
  - 변경사항 (~8줄 추가, Phase 0에서 ~47줄 회수했으므로 여유 충분):
    - Step 0 (META-ISSUE) 끝: `trace.py init --session-id $SESSION_ID` 호출
    - 전역 규칙 1줄: "각 단계 시작/종료 시 trace.py 호출. See references/tracing-protocol.md"
    - Step 6 (IMPL-LOOP) 1줄: "Agent 결과에서 <usage> 파싱 후 end-span --attr 전달"
    - Step 8 (CHECKPOINT) 1줄: "트레이스 파일도 디스크에 저장됨 (자동)"
    - Step 12 (REPORT) 2줄: "trace.py finalize 호출. trace-report.py summary 실행 후 코멘트 게시"
    - 기존 Step 6.5 VERIFY → PRE-DEPLOY-VERIFY 개명 (1줄 수정)

- [ ] **Impl 2.7**: `references/simple-path.md` 업데이트
  - File: `references/simple-path.md`
  - 변경: simple path 단계별 트레이싱 span 이름 매핑 추가

- [ ] **Impl 2.8**: checklist.py 단계 목록 업데이트
  - File: `scripts/checklist.py`
  - 변경: `AUTOPILOT_STEPS`에 새 단계 추가:
    - "VERIFY-INFRA-CHECK (Step 5.7)" (DAG-CONFIRM 뒤)
    - "PRE-DEPLOY-VERIFY (Step 6.5)" (기존 VERIFY 개명)
    - "DEPLOY-DETECT (Step 6.6)" (PRE-DEPLOY-VERIFY 뒤)
    - "DEPLOY-VERIFY (Step 6.7)" (DEPLOY-DETECT 뒤)

- [ ] **Impl 2.9**: autopilot-state.py 단계 목록 업데이트
  - File: `scripts/autopilot-state.py`
  - 변경: `current_step` 유효값에 VERIFY-INFRA-CHECK, PRE-DEPLOY-VERIFY, DEPLOY-DETECT, DEPLOY-VERIFY 추가

#### 🔴 RED + 🟢 GREEN: Configuration Tests

- [ ] **Test 2.10**: checklist.py & autopilot-state.py 정합성
  - File: `scripts/tests/test_config_consistency.py`
  - Tests: AUTOPILOT_STEPS의 단계 이름이 autopilot-state.py의 current_step 유효값에 모두 포함되는지 검증
  - Tests: AUTOPILOT_SIMPLE_STEPS도 동일하게 검증
  - Tests: 새 단계 4개가 양쪽 모두에 존재

- [ ] **Test 2.11**: `<usage>` 태그 파싱 유닛 테스트
  - File: `scripts/tests/test_usage_parsing.py`
  - Tests: 정상 파싱, 태그 누락(→null), 파싱 실패(→null+경고), 부분 데이터(total_tokens만 있음)

#### Quality Gate ✋

- [ ] SKILL.md ≤ 500줄 (Phase 0 회수분 내에서 추가)
- [ ] tracing-protocol.md가 디자인 문서의 모든 트레이싱 규칙을 포함
- [ ] `python -m pytest scripts/tests/test_config_consistency.py -v` 통과
- [ ] `python -m pytest scripts/tests/test_usage_parsing.py -v` 통과
- [ ] 하위 호환성: trace_session_id 없는 세션이 정상 동작 (E2E 2.4)

---

### Phase 3: trace-report.py 리포트 생성기
**Goal**: 트레이스 데이터 → 마크다운 요약/인사이트 → 이슈 코멘트 게시
**Value**: "세션 종료 시 메타 이슈에 타임라인 + 인사이트 + 설정 업데이트 제안이 자동 게시됨"
**Depends on**: Phase 1 (trace.py, JSON 포맷)
**Status**: ⏳ Pending

#### 코멘트 게시 메커니즘

SKILL.md Step 12 (REPORT)에서:
1. `python trace-report.py summary --session $SID --format markdown > /tmp/trace-summary.md`
2. provider별 코멘트 게시:
   - GitHub: `gh issue comment $META_ISSUE --body-file /tmp/trace-summary.md`
   - GitLab: `glab issue note $META_ISSUE --message "$(cat /tmp/trace-summary.md)"`
   - Jira: `mcp__jira__add_comment` (기존 autopilot의 provider detection 활용)

#### Confidence 점수 산출 알고리즘

```
패턴 반복 횟수를 최근 N개 세션에서 집계:
- confidence = (패턴 발생 세션 수 / 조사 세션 수) × 100
- 최소 조사 세션: 3개 (3개 미만이면 제안 안 함)
- 임계값: 90% 이상만 제안
- 예시: 최근 5세션 중 5회 발생 → 100% → 제안
- 예시: 최근 5세션 중 4회 발생 → 80% → 미제안
- 예시: 최근 3세션 중 3회 발생 → 100% → 제안
```

#### 🎯 E2E Acceptance Test (Write First)

- [ ] **E2E 3.1**: 마크다운 요약 생성 테스트
  - File: `scripts/tests/test_trace_report_e2e.py`
  - Given: 샘플 트레이스 JSON (fixtures/에서 로드, 다양한 span 유형/이벤트/notes 포함)
  - When: `python trace-report.py summary --session $SID --format markdown`
  - Then: 출력에 **3개 필수 섹션** 존재:
    - `## Autopilot Trace Summary` (헤더 + 메트릭)
    - `### Execution Timeline` (테이블, 모든 step span 포함)
    - `### Insights` (최소 1개 이상의 이상 패턴 분석)
  - Then: Insights에 이상 패턴이 **수치 → 원인 → 액션** 3단 구조를 따름
  - Then: `### Suggested Updates` 섹션이 confidence ≥ 90% 항목만 포함

- [ ] **E2E 3.2**: 세션 비교 테스트
  - Given: 2개의 트레이스 JSON (하나는 높은 토큰 사용 + retry 다수, 하나는 정상)
  - When: `python trace-report.py compare --sessions $S1 $S2`
  - Then: 출력에 Duration, Total Tokens, Avg Tokens/Issue, Review Retries, CI Failures 비교 테이블
  - Then: Notable Differences에 구체적 차이점 기술

- [ ] **E2E 3.3**: 코멘트 게시 통합 테스트
  - Given: trace-report.py summary 출력이 /tmp/trace-summary.md에 저장됨
  - When: `gh issue comment $META_ISSUE --body-file /tmp/trace-summary.md` 실행
  - Then: 메타 이슈에 트레이스 요약 코멘트 게시됨
  - Note: 이 테스트는 실 GitHub 리포가 있는 환경에서만 실행

#### 🔴 RED: Write Failing Tests

- [ ] **Test 3.4**: `summary` 커맨드 — 타임라인 생성
  - File: `scripts/tests/test_trace_report.py`
  - Tests: step span → 타임라인 row 변환, duration 포맷팅 (ms → Xm Ys), 토큰 포맷팅 (천 단위 구분)

- [ ] **Test 3.5**: `summary` 커맨드 — 인사이트 도출
  - Tests: 5가지 이상 패턴 각각 감지 (fixture 기반):
    - 긴 시간+적은 토큰 → "외부 대기" 감지
    - 짧은 시간+많은 토큰 → "과도한 컨텍스트" 감지
    - 높은 retry → "프롬프트 품질" 감지
    - 세션 간 급증 → "회귀/비효율" 감지
    - 과다 tool_uses → "탐색 비효율" 감지

- [ ] **Test 3.6**: `summary` 커맨드 — 설정 업데이트 제안
  - Tests: confidence 계산 (반복 횟수/세션 수 × 100)
  - Tests: confidence < 90% → 필터링됨
  - Tests: 조사 세션 < 3 → 제안 안 함
  - Tests: null total_tokens 포함 세션 → 토큰 메트릭 스킵, 시간/retry 메트릭은 정상 출력

- [ ] **Test 3.7**: `compare` 커맨드
  - Tests: 두 세션 메트릭 비교, 델타 계산 (절대값 + %), Notable Differences 생성

- [ ] **Test 3.8**: `bottleneck` 커맨드
  - Tests: top-N 토큰 소비 span 추출, 비율 계산, 정렬

- [ ] **Test 3.9**: `review-stats` 커맨드
  - Tests: N개 세션에서 리뷰 attempt 평균, 빈출 피드백 집계

- [ ] **Test 3.10**: `list` 커맨드
  - Tests: index.json에서 세션 목록 출력, 요약 메트릭 포맷팅

#### 🟢 GREEN: Implement to Pass

- [ ] **Impl 3.11**: `trace-report.py` 스크립트 구현
  - File: `scripts/trace-report.py`
  - 서브커맨드: summary, compare, bottleneck, review-stats, list
  - 이상 패턴 감지 엔진 (5가지 규칙, 디자인 문서 Section 5.4)
  - 인사이트 생성기 (수치 → 원인 → 액션 3단)
  - 설정 업데이트 제안 (confidence 알고리즘 위 참조)
  - null 토큰 처리: 토큰 관련 메트릭 스킵, 시간/retry 기반 인사이트는 정상 생성

- [ ] **Impl 3.12**: SKILL.md Step 12 (REPORT)에 코멘트 게시 지시 추가
  - File: `SKILL.md`
  - 변경 (~2줄):
    ```
    trace-report.py summary 실행 → /tmp/trace-summary.md
    provider별 CLI로 메타 이슈에 코멘트 게시 (gh/glab/jira)
    ```

- [ ] **Impl 3.13**: 테스트 픽스처 생성
  - File: `scripts/tests/fixtures/` 디렉토리
  - Phase 1 E2E 테스트에서 생성된 JSON을 기반으로 시나리오별 픽스처:
    - `normal_session.json` — 정상 세션
    - `high_retry_session.json` — retry 다수
    - `high_token_session.json` — 토큰 급증
    - `error_session.json` — 에러 포함
    - `null_tokens_session.json` — `<usage>` 태그 누락 세션

#### Quality Gate ✋

- [ ] `python -m pytest scripts/tests/test_trace_report*.py -v` 전체 통과
- [ ] summary 출력에 3개 필수 섹션 존재 (Timeline, Insights, Suggested Updates)
- [ ] 이상 패턴 5가지 모두 감지 테스트 통과
- [ ] confidence < 90% 필터링 테스트 통과
- [ ] null 토큰 세션에서 크래시 없음

---

### Phase 4: Deploy-Verify 워크플로우
**Goal**: issue-impl에서 merge 후 실환경 검증을 자동화
**Value**: "merge 후 배포된 환경에서 Playwright/CLI/수동 가이드로 검증하고, 인증 핸드오프로 로그인 장벽도 해결"
**Depends on**: Phase 0 (SKILL.md 줄 여유), Phase 1 (trace.py — deploy-verify 결과를 트레이스에 기록)
**Status**: ⏳ Pending

#### issue-impl SKILL.md 삽입 지점 (사전 검증 완료)

- 파일: `~/.claude/skills/issue-impl/SKILL.md` (609줄, 줄 제한 없음)
- Step 번호 포맷: `### Step N:` (markdown H3)
- 삽입 위치: **Line 486** (Step 11 끝, Step 11a 앞)
- 참조 파일: `~/.claude/skills/issue-impl/references/` 디렉토리 존재 (8개 파일)
- deploy-verify.md는 `~/.claude/skills/autopilot/references/`에 생성하되, issue-impl에서 참조

#### 🎯 E2E Acceptance Test (Write First)

- [ ] **E2E 4.1**: deploy-verify reference 문서 완결성 검증 (문서 기반)
  - Given: `references/deploy-verify.md` 작성 완료
  - When: 디자인 문서 Section 6의 모든 항목과 대조
  - Then: Section 6.1 (기존 Step 관계), 6.2 (4개 sub-step), 6.3 (SKILL.md 통합), 6.4 (fallback chain) 모두 커버됨
  - Verification: 체크리스트 기반 수동 대조

- [ ] **E2E 4.2**: deploy-verify 트레이싱 통합 시뮬레이션 테스트
  - File: `scripts/tests/test_deploy_verify_trace.py`
  - Given: trace.py init된 세션
  - When: deploy-verify 시나리오를 trace.py 호출로 시뮬레이션:
    ```python
    start_span("deploy-detect", kind="sub_step")
    end_span(attrs={"env": "dev", "deploy_url": "https://..."})
    start_span("test-data-setup", kind="sub_step")
    end_span(status="ok")
    start_span("verify-automated", kind="sub_step", attrs={"method": "playwright"})
    add_event("auth-handoff", attrs={"auth_type": "web_login", "resolved": True})
    end_span(status="ok", attrs={"verification_result": True})
    ```
  - Then: 트레이스 JSON에 deploy-verify 관련 span들이 올바른 계층으로 기록됨
  - Then: auth-handoff 이벤트가 적절한 attributes와 함께 기록됨

- [ ] **E2E 4.3**: 수동 가이드 생성 시뮬레이션
  - Given: deploy URL 접근 불가, CLI도 불가한 상황
  - When: fallback chain에서 Priority 3 (수동 가이드) 도달
  - Then: 프롬프트 기반으로 사용자에게 step-by-step 검증 가이드 제시 (LLM이 컨텍스트에 맞게 생성)
  - Note: 수동 가이드는 **프롬프트 기반** — LLM이 배포 컨텍스트(URL, 기능, 테스트 계정)를 바탕으로 맞춤형 가이드 생성

#### 🟢 GREEN: Implement

- [ ] **Impl 4.4**: `references/deploy-verify.md` 작성
  - File: `references/deploy-verify.md`
  - 내용:
    - Step 6.5 PRE-DEPLOY-VERIFY (기존 VERIFY 개명) — 로컬/CI 수준 검증
    - Step 6.6 DEPLOY-DETECT — 배포 환경 감지:
      - Vercel: `vercel ls`, deploy URL 패턴
      - Docker: `docker ps`, compose 설정
      - 수동: 사용자에게 URL 질의 (UIP)
    - Step 6.7 DEPLOY-VERIFY 상세:
      - 6.7.1 TEST-DATA-SETUP: 테스트 계정/데이터 준비 (prod 격리, 크리덴셜 .env.test→.gitignore)
      - 6.7.2 VERIFY-ATTEMPT: fallback chain (Playwright → CLI/API → 수동 가이드)
        - **수동 가이드**: 프롬프트 기반. LLM이 배포 컨텍스트를 참고해 맞춤형 step-by-step 가이드 생성. 사용자가 각 단계 확인 후 결과 입력.
      - 6.7.3 AUTH-HANDOFF: 인증 위임 프로토콜 (크리덴셜 미저장, trace에 auth_type/wait_duration/resolved만 기록)
      - 6.7.4 CLEANUP: 테스트 데이터 정리 (선택적)
    - 트레이스 기록: 각 sub-step별 span 생성 규칙 + `DEPLOY_VERIFY_RESULT_BEGIN/END` 구조화 출력

- [ ] **Impl 4.5**: issue-impl SKILL.md 수정
  - File: `~/.claude/skills/issue-impl/SKILL.md`
  - 삽입 위치: Line 486 (Step 11 끝, Step 11a 앞)
  - 변경사항 (~10줄):
    ```
    ### Step 11.1: DEPLOY-DETECT
    배포 환경 감지. See autopilot/references/deploy-verify.md Section 6.6

    ### Step 11.2: DEPLOY-VERIFY
    배포 후 실환경 검증. Fallback: Playwright → CLI → 수동 가이드.
    See autopilot/references/deploy-verify.md Section 6.7

    DEPLOY_VERIFY_RESULT_BEGIN
    METHOD=playwright|cli|api|manual
    STATUS=pass|fail
    AUTH_HANDOFF=true|false
    DEPLOY_VERIFY_RESULT_END
    ```

- [ ] **Impl 4.6**: `references/verification-matrix.md` 업데이트
  - File: `references/verification-matrix.md`
  - 변경: pre-deploy(6.5) vs post-deploy(6.7) 검증 구분 추가

- [ ] **Impl 4.7**: autopilot SKILL.md에 Step 6.6, 6.7 참조 추가
  - File: `SKILL.md`
  - 변경 (~3줄): Step 6.5 PRE-DEPLOY-VERIFY 뒤에 6.6, 6.7 참조 포인터

#### Quality Gate ✋

- [ ] deploy-verify.md가 디자인 문서 Section 6 전체를 커버 (체크리스트 대조)
- [ ] issue-impl SKILL.md에 Step 11.1, 11.2 삽입됨
- [ ] E2E 4.2 트레이싱 시뮬레이션 통과
- [ ] 기존 issue-impl 기능에 regression 없음 (Step 11, 11a 동작 변경 없음)
- [ ] autopilot SKILL.md ≤ 500줄

---

### Phase 5: Verify-Infra-Check 선행 이슈 생성
**Goal**: 검증 인프라 부재 시 자동으로 선행 이슈를 생성하고 DAG blocker로 등록
**Value**: "검증할 수 없는 이슈를 구현하기 전에, 검증 인프라 세팅을 먼저 자동으로 해결"
**Depends on**: Phase 0 (SKILL.md 줄 여유)
**Status**: ⏳ Pending

#### 🎯 E2E Acceptance Test (Write First)

- [ ] **E2E 5.1**: 인프라 부재 시 선행 이슈 생성 (통합 테스트)
  - Given: CI 파이프라인과 Playwright가 없는 프로젝트에서 autopilot 실행
  - When: Step 5.7 VERIFY-INFRA-CHECK 도달
  - Then: "Set up CI pipeline" + "Configure Playwright" 이슈 2개 자동 생성
  - Then: DAG에 blocker로 등록, feature 이슈보다 먼저 구현됨
  - Verification: `dag-analyze.py ready` 실행 시 prereq 이슈가 먼저 나옴

- [ ] **E2E 5.2**: 재귀 방지 테스트 (통합 테스트)
  - Given: `type: prereq-infra` 태그가 있는 선행 이슈
  - When: 해당 이슈의 issue-impl 실행
  - Then: VERIFY-INFRA-CHECK 스킵됨 (재귀 없음)

- [ ] **E2E 5.3**: 인프라 존재 시 스킵 테스트 (통합 테스트)
  - Given: CI (.github/workflows/ 존재), Playwright (playwright.config.ts 존재) 모두 있는 프로젝트
  - When: Step 5.7 VERIFY-INFRA-CHECK 도달
  - Then: 선행 이슈 생성 없음, IMPL-LOOP로 바로 진행

#### 🟢 GREEN: Implement

- [ ] **Impl 5.4**: `references/verify-infra-check.md` 작성
  - File: `references/verify-infra-check.md`
  - 내용:
    - 프로젝트 단위 1회 인프라 체크 (이슈별 반복 아님)
    - 체크 항목 + 검출 방법:
      | 항목 | 검출 방법 |
      |------|----------|
      | CI | `.github/workflows/*.yml` 또는 `.gitlab-ci.yml` 존재 |
      | Playwright | `playwright.config.*` 존재 |
      | Deploy target | `vercel.json`, `Dockerfile`, deploy 스크립트 존재 |
      | Test data | `.env.test` 또는 test fixtures 디렉토리 존재 |
      | Auth | 테스트 크리덴셜 접근 가능 (환경변수/파일) |
    - 선행 이슈 생성 규칙: 카테고리별 이슈 제목/본문 템플릿
    - DAG blocker 등록: `dag-analyze.py add-edge --from prereq-N --to ALL_FEATURE_ISSUES`
    - 재귀 방지: `type: prereq-infra` 태그 → VERIFY-INFRA-CHECK 자동 스킵
    - prereq 이슈의 검증: 수동 검증 또는 간단한 CLI 체크 (VERIFY-INFRA-CHECK 재진입 안 함)
    - 트레이스 기록: VERIFY-INFRA-CHECK span 아래 check-*/prereq-create/prereq-impl sub-span

- [ ] **Impl 5.5**: SKILL.md에 Step 5.7 추가
  - File: `SKILL.md`
  - 변경 (~3줄): Step 5.5 (DAG-CONFIRM) 뒤에:
    ```
    ### Step 5.7: VERIFY-INFRA-CHECK
    프로젝트의 검증 인프라 존재 여부 확인. 부재 시 선행 이슈 생성.
    → See references/verify-infra-check.md
    ```

- [ ] **Impl 5.6**: checklist.py에 VERIFY-INFRA-CHECK 단계 추가
  - File: `scripts/checklist.py`
  - 변경: `AUTOPILOT_STEPS` 리스트에 "VERIFY-INFRA-CHECK (Step 5.7)" 항목 추가 (DAG-CONFIRM 뒤)
  - 주의: Phase 2 Impl 2.8에서 이미 추가했다면 스킵

- [ ] **Impl 5.7**: autopilot-state.py에 prereq 이슈 지원
  - File: `scripts/autopilot-state.py`
  - 변경: `add_issue()`에서 `type` 파라미터에 `prereq-infra` 값 허용
  - 변경: `query_issues()`에서 `type` 필터 지원

#### 🔴 RED + 🟢 GREEN: Configuration Tests

- [ ] **Test 5.8**: autopilot-state.py prereq-infra 이슈 지원
  - File: `scripts/tests/test_state_prereq.py`
  - Tests: `add_issue(type="prereq-infra")` 성공
  - Tests: `query_issues(type="prereq-infra")` 필터링 정상

#### Quality Gate ✋

- [ ] verify-infra-check.md가 디자인 문서 Section 7 전체를 커버
- [ ] 재귀 방지 로직이 명확히 문서화됨 (prereq-infra 태그)
- [ ] SKILL.md ≤ 500줄
- [ ] `python -m pytest scripts/tests/test_state_prereq.py -v` 통과
- [ ] checklist.py/autopilot-state.py 정합성 테스트 통과 (Phase 2 Test 2.10 재실행)

---

## ⚠️ Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| SKILL.md 500줄 초과 | Low (Phase 0 해결) | High | Phase 0에서 ~47줄 회수. 추가분 ~16줄. 예상 잔여 ~31줄 여유 |
| `<usage>` 태그 포맷 변경 | Medium | Medium | graceful degradation: 누락→null, 파싱실패→null+경고. trace-report는 null 안전 처리 |
| 기존 autopilot regression | Medium | High | E2E 2.4 하위 호환성 테스트. trace_session_id 없으면 트레이싱 스킵 |
| deploy-verify 환경 다양성 | High | Medium | 3단계 fallback chain. 최종: LLM이 맞춤형 수동 가이드 생성 |
| 선행 이슈 과다 생성 | Low | Medium | 프로젝트 단위 1회. 기존 인프라 있으면 스킵 |
| index.json 동시 접근 | Low | Low | autopilot은 단일 세션. 동시 실행 시 file lock 고려 (Phase 1 trace.py) |
| confidence 산출 데이터 부족 | Medium | Low | 최소 3세션 미만이면 제안 안 함. 초기에는 인사이트만 출력 |
| Phase 0 reference 추출 시 참조 누락 | Low | High | 추출 후 autopilot dry-run으로 참조 포인터 검증 |

---

## 🔄 Rollback Strategy

각 Phase는 독립적으로 롤백 가능. 의존 Phase가 있으면 역순 롤백.

- **Phase 0**: `references/state-block-formats.md`, `references/meta-issue-creation-cmds.md` 삭제. SKILL.md에 원본 내용 복원 (git revert)
- **Phase 1**: `scripts/trace.py`, `scripts/tests/test_trace*.py` 삭제. autopilot-state.py에서 trace_session_id 필드 제거. `.claude/autopilot-traces/` 디렉토리는 수동 정리
- **Phase 2**: SKILL.md 트레이싱 지시문 제거(~8줄), Step 6.5 개명 복원, `references/tracing-protocol.md` 삭제. checklist.py/autopilot-state.py에서 새 단계 제거. **Phase 3이 설치되어 있다면 Phase 3 먼저 롤백**
- **Phase 3**: `scripts/trace-report.py`, 테스트, 픽스처 삭제. SKILL.md Step 12에서 리포트/코멘트 호출 제거(~2줄)
- **Phase 4**: `references/deploy-verify.md` 삭제, issue-impl SKILL.md에서 Step 11.1/11.2 제거(~10줄), autopilot SKILL.md에서 6.6/6.7 참조 제거(~3줄), verification-matrix.md 복원
- **Phase 5**: `references/verify-infra-check.md` 삭제, SKILL.md에서 Step 5.7 제거(~3줄), autopilot-state.py에서 prereq-infra 타입 지원 제거

---

## 📊 Progress Tracking

| Phase | Tasks | Depends On | Status |
|-------|-------|------------|--------|
| Phase 0: SKILL.md 리팩토링 | 3 | — | ⏳ Pending |
| Phase 1: trace.py 코어 엔진 | 17 | Phase 0 | ⏳ Pending |
| Phase 2: autopilot 트레이싱 통합 | 11 | Phase 0, 1 | ⏳ Pending |
| Phase 3: trace-report.py 리포트 | 13 | Phase 1 | ⏳ Pending |
| Phase 4: deploy-verify 워크플로우 | 7 | Phase 0, 1 | ⏳ Pending |
| Phase 5: verify-infra-check | 8 | Phase 0 | ⏳ Pending |
| **Total** | **59** | | |

---

## 📁 File Structure (변경/신규 파일)

```
~/.claude/skills/autopilot/
├── SKILL.md                                    (수정: Phase 0 축소 + Phase 2,3,4,5 추가)
├── scripts/
│   ├── autopilot-state.py                      (수정: trace_session_id + prereq-infra)
│   ├── checklist.py                            (수정: 새 단계 4개 추가)
│   ├── trace.py                                (신규: 트레이싱 엔진)
│   ├── trace-report.py                         (신규: 리포트 생성기)
│   └── tests/
│       ├── test_trace.py                       (신규: trace.py 유닛)
│       ├── test_trace_e2e.py                   (신규: 트레이스 E2E)
│       ├── test_trace_report.py                (신규: 리포트 유닛)
│       ├── test_trace_report_e2e.py            (신규: 리포트 E2E)
│       ├── test_config_consistency.py          (신규: checklist/state 정합성)
│       ├── test_usage_parsing.py               (신규: <usage> 파싱)
│       ├── test_deploy_verify_trace.py         (신규: deploy-verify 트레이싱 시뮬레이션)
│       ├── test_state_prereq.py                (신규: prereq-infra 이슈 지원)
│       └── fixtures/                           (신규: 테스트용 트레이스 JSON)
├── references/
│   ├── state-block-formats.md                  (신규: Phase 0에서 추출)
│   ├── meta-issue-creation-cmds.md             (신규: Phase 0에서 추출)
│   ├── tracing-protocol.md                     (신규: 트레이싱 규칙)
│   ├── deploy-verify.md                        (신규: 배포 후 검증)
│   ├── verify-infra-check.md                   (신규: 검증 인프라 선행 이슈)
│   ├── verification-matrix.md                  (수정: deploy-verify 추가)
│   └── simple-path.md                          (수정: 트레이싱 매핑)

~/.claude/skills/issue-impl/
└── SKILL.md                                    (수정: Line 486에 Step 11.1/11.2 삽입)
```

---

## ✅ Final Checklist

- [ ] Phase 0: SKILL.md ≤ 460줄 (여유 확보)
- [ ] Phase 1: trace.py 스키마 — 필수/조건부/선택 필드 모두 지원, pytest 전체 통과
- [ ] Phase 2: autopilot 실행 시 트레이스 자동 기록, 하위 호환성 유지
- [ ] Phase 3: 세션 요약 + 인사이트 + 설정 제안 → 이슈 코멘트 게시 (gh/glab/jira)
- [ ] Phase 4: merge 후 deploy-verify fallback chain, 트레이스 기록
- [ ] Phase 5: 검증 인프라 부재 → 선행 이슈 자동 생성, 재귀 방지
- [ ] SKILL.md ≤ 500줄 (모든 Phase 완료 후)
- [ ] 기존 autopilot/issue-impl regression 없음
- [ ] 모든 Python 테스트 통과

---

**Plan Status**: 📋 Ready for Approval (Rev.2)
**Review Fixes Applied**: C1-C5 (Critical 5개), M1-M7 (Medium 7개) 전부 반영
**Next Action**: Phase 0 — SKILL.md 줄 확보 리팩토링
