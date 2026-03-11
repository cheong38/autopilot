# DAG Integration E2E Test Scenarios

Manual verification scenarios for `/issue-impl` DAG integration (Phase 5).
These validate LLM orchestration behavior that cannot be tested with unit tests.

## Scenario A — Blocker가 있는 이슈

**Given**: DAG에 #43 depends_on #42 (status: open)
**When**: `/issue-impl #43`
**Then**:
- [ ] Step 1.3에서 blocker 경고가 표시됨
- [ ] #42를 먼저 처리하라는 안내가 제시됨
- [ ] 사용자 선택지 3개 제시: "먼저 blocker 처리" / "무시하고 진행" / "중단"
- [ ] "중단" 선택 시 session lock 없이 종료됨

**Test Date**: _______________
**Result**: ☐ PASS / ☐ FAIL
**Notes**: _________________

---

## Scenario B — Ready 이슈 (모든 blocker resolved)

**Given**: DAG에 #43 depends_on #42 (status: closed)
**When**: `/issue-impl #43`
**Then**:
- [ ] Step 1.3에서 readiness 확인 통과
- [ ] 정상적으로 Session Lock(Step 1.5)으로 진행
- [ ] DAG 분석 결과가 간략히 표시됨 ("All blockers resolved")

**Test Date**: _______________
**Result**: ☐ PASS / ☐ FAIL
**Notes**: _________________

---

## Scenario C — 완료 후 DAG 업데이트 + 다음 작업 추천

**Given**: #42 구현 완료 상태, DAG에 #43 depends_on #42, #44 depends_on #42
**When**: Step 10 (Merge) 완료 후 Step 10.5 실행
**Then**:
- [ ] DAG에서 #42 status가 closed로 업데이트됨
- [ ] Wiki에 push됨 (또는 push 실패 시 경고 표시)
- [ ] 새로 Ready가 된 이슈 목록 표시: #43, #44
- [ ] Completion Summary에 "Next Ready Issues" 포함

**Test Date**: _______________
**Result**: ☐ PASS / ☐ FAIL
**Notes**: _________________

---

## Scenario D — Non-GitHub 환경 (GitLab)

**Given**: GitLab 프로젝트에서 실행
**When**: `/issue-impl #10`
**Then**:
- [ ] Step 1.3 DAG 체크 정상 실행 (GitLab Wiki 지원)
- [ ] GitLab Wiki 접근 실패 시 로컬 폴백으로 자동 전환
- [ ] 나머지 워크플로우 정상 진행

**Test Date**: _______________
**Result**: ☐ PASS / ☐ FAIL
**Notes**: _________________

---

## Scenario E — DAG Wiki 접근 불가 (네트워크 에러)

**Given**: GitHub 프로젝트, Wiki가 비활성화 또는 네트워크 장애
**When**: `/issue-impl #42`
**Then**:
- [ ] Step 1.3에서 DAG 접근 실패 감지
- [ ] 경고만 표시하고 정상 진행 (graceful degradation)
- [ ] Step 10.5에서도 DAG push 실패 시 경고 표시 + Deploy 진행 허용

**Test Date**: _______________
**Result**: ☐ PASS / ☐ FAIL
**Notes**: _________________
