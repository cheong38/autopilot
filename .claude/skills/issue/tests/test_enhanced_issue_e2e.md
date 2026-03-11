# Enhanced Issue E2E Test Scenarios

Manual verification scenarios for `/issue` with brainstorming + DAG integration.

## Scenario A: Vague Input + Similar Issue Exists

**Preconditions**:
- DAG contains "인증 시스템 구현" issue with keywords: ["인증", "로그인", "auth"]
- UL dictionary has `인증 = [auth, authentication, 로그인 인증]`

**Steps**:
1. Run `/issue 로그인 기능 추가`
2. Verify ambiguity check triggers brainstorming
3. Answer clarifying questions
4. Verify DAG analysis runs and finds "인증 시스템 구현" as similar
5. Verify user confirmation gate presents options
6. Choose "Create anyway"
7. Verify issue is created and added to DAG

**Expected**: Brainstorming → DAG analysis → similar issue presented → user confirmation → create + DAG register

| Date | Result | Notes |
|------|--------|-------|
| | | |

---

## Scenario B: Clear Bug Report

**Preconditions**:
- Any DAG state

**Steps**:
1. Run `/issue --bug 로그인 시 500 에러 발생. Steps to reproduce: 1. Go to login 2. Submit form 3. See 500`
2. Verify brainstorming is SKIPPED
3. Verify DAG analysis still runs
4. Verify issue is created and added to DAG

**Expected**: No brainstorming → DAG analysis → create + DAG register

| Date | Result | Notes |
|------|--------|-------|
| | | |

---

## Scenario C: Create with Dependency

**Preconditions**:
- DAG contains issue #42 "인증 시스템 구현"

**Steps**:
1. Run `/issue 소셜 로그인 추가`
2. Answer brainstorming questions
3. DAG analysis finds #42 as similar
4. Choose "Create with dependency"
5. Verify issue body contains `blocked by #42`
6. Verify DAG has `depends_on` edge from new issue to #42

**Expected**: Create with `blocked by #42` in body + DAG edge

| Date | Result | Notes |
|------|--------|-------|
| | | |

---

## Scenario D: --no-brainstorm Flag

**Preconditions**: N/A

**Steps**:
1. Run `/issue --no-brainstorm 뭔가 구현`
2. Verify brainstorming is SKIPPED
3. Verify normal discovery flow continues

**Expected**: No brainstorming, straight to discovery

| Date | Result | Notes |
|------|--------|-------|
| | | |

---

## Scenario E: Non-GitHub Provider (Graceful Skip)

**Preconditions**:
- Repository uses GitLab as VCS provider

**Steps**:
1. Run `/issue 새로운 기능 추가`
2. Verify DAG analysis step is skipped with info message
3. Verify issue creation proceeds normally without DAG

**Expected**: DAG steps gracefully skipped, issue created normally

| Date | Result | Notes |
|------|--------|-------|
| | | |
