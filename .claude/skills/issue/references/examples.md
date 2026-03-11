# Issue Examples

## Story Examples

### Good Story

```markdown
## User Story

**As a** admin user managing member records
**I want to** search members by phone number (last 4 digits)
**So that** I can quickly find a specific member during phone inquiries

## Value Delivered

Reduces member lookup time from manual scrolling to instant search.
Enables staff to assist callers efficiently during peak hours.

## Acceptance Criteria

- [ ] Given a member list page, when admin enters 4 digits in search,
      then members with matching phone last 4 digits are displayed
- [ ] Given a search with no matches, when admin searches,
      then "no results" message is shown
- [ ] Given mixed search input, when admin enters text vs digits,
      then system auto-detects search type (name vs phone)

## Non-Functional Requirements

- Performance: Search results within 500ms

## Task Outline

1. Phone search detection logic
2. Phone last-4 denormalization for Firestore
3. Search UI integration
4. Migration for existing member data

## Notes

- Firestore doesn't support LIKE queries; use denormalized phone_last4 field
- Need composite indexes for filtered phone search
```

### Bad Story (with issues)

```markdown
## User Story

**As a** user
**I want to** manage things
**So that** it works better

## Acceptance Criteria

- [ ] It should work
- [ ] It should be fast

## Task Outline

1. Create database schema with PostgreSQL
2. Build React component with useState hook
3. Add API endpoint POST /api/things
```

**What's Wrong:**
- **CRITICAL**: Vague user role ("user" - who specifically?)
- **CRITICAL**: Vague goal ("manage things" - what things? what actions?)
- **CRITICAL**: No business value ("works better" is not measurable)
- **MAJOR**: Acceptance criteria are untestable ("should work")
- **MAJOR**: Task outline contains implementation details (database, React, API)
- **MINOR**: No edge cases or error scenarios considered

---

## Task Examples

### Good Task

```markdown
## Task

**Title**: Migrate user avatar storage from local filesystem to S3

## Description

User avatar images are currently stored on the local filesystem at `/uploads/avatars/`.
This creates issues with horizontal scaling (each server has its own copy) and deployment
(uploads are lost on redeploy). Need to migrate to S3 for persistent, shared storage.

## Done Criteria

- [ ] All existing avatar images migrated to S3 bucket
- [ ] Upload endpoint writes to S3 instead of local filesystem
- [ ] Serving endpoint reads from S3 (or CloudFront CDN)
- [ ] Old local filesystem code removed
- [ ] No broken avatar images in staging environment after migration

## Dependencies

- Depends on #87 — AWS S3 bucket provisioned (DevOps)

## Blocks

> 이 Task를 완료해야 아래 이슈를 진행할 수 있습니다.

- Blocks #92 — User profile image display (needs S3 URLs)

## Constraints

- Backward compatible: existing avatar URLs must redirect to new location
- Migration must be zero-downtime (run in background)

## Task Outline

1. S3 client integration
2. Migration script for existing files
3. Update upload/serving endpoints
4. CDN configuration
5. Cleanup old filesystem code

## Notes

- ~15,000 existing avatars, total ~2GB
- Consider presigned URLs for upload to reduce server load
```

### Bad Task (with issues)

```markdown
## Task

**Title**: Fix things

## Description

Some stuff needs to be updated.

## Done Criteria

- [ ] It works
```

**What's Wrong:**
- **CRITICAL**: Vague title ("Fix things" - what things?)
- **CRITICAL**: No meaningful description (what needs updating and why?)
- **CRITICAL**: Done criteria is untestable ("It works" is not verifiable)

---

## Bug Examples

### Good Bug Report

```markdown
## Bug Report

**Title**: Login fails with "Invalid credentials" for users with + in email

## Environment

- Version/Branch: v2.3.1 / main
- Browser/OS: Chrome 120 / macOS 14.2
- Environment: Production

## Steps to Reproduce

1. Go to /login page
2. Enter email: user+test@example.com
3. Enter correct password
4. Click "Sign In"

## Expected Behavior

User should be logged in and redirected to dashboard.

## Actual Behavior

Error message "Invalid credentials" is displayed.
The same user can log in successfully if the email doesn't contain a + character.
Server logs show the email is being truncated at the + sign.

## Severity

High - Users with + in their email cannot log in at all, no workaround.

## Affected Code Paths

- `src/api/controllers/auth_controller.py:45` → `login()` 요청 파라미터 파싱 지점
- `src/api/services/auth_service.py:78` → `authenticate()` 이메일 조회 지점

## Action Items

- [ ] **1단계 (선행)**: `auth_controller.py:45`에서 email 파라미터의 URL decoding 방식 수정
  - `+` 문자가 space로 변환되지 않도록 `urllib.parse.unquote_plus` → `urllib.parse.unquote` 변경
- [ ] **2단계 (후행)**: 기존 `+` 포함 이메일 사용자 데이터 정합성 확인
  - DB에서 truncated email로 저장된 레코드가 있는지 조사 필요

## Unknowns

| Unknown | 확인 방법 | 판단 기준 |
|---------|----------|----------|
| truncated email 레코드 존재 여부 | `SELECT count(*) FROM users WHERE email LIKE '%+%'` | 0건이면 데이터 보정 불필요, 1건 이상이면 마이그레이션 필요 |

## Acceptance Criteria (Fix Verification)

- [ ] Users with + in email can log in successfully
- [ ] Email field preserves the full email including + and characters after it
- [ ] Existing users with + emails retain access to their accounts

## Notes

- Root cause hypothesis: URL encoding is stripping the + sign in the login API request
- Affects approximately 150 users based on database query
- Related: similar issue was fixed for registration in PR #234
```

### Bad Bug Report (with issues)

```markdown
## Bug Report

**Title**: Login broken

## Steps to Reproduce

1. Try to log in

## Expected Behavior

Should work

## Actual Behavior

Doesn't work
```

**What's Wrong:**
- **CRITICAL**: Steps to reproduce are too vague to follow
- **CRITICAL**: Expected/actual behavior don't describe anything specific
- **MAJOR**: No environment information
- **MAJOR**: No severity assessment
- **MAJOR**: No fix verification criteria

---

## Korean Examples

### Story (Korean)

```markdown
## User Story

**As a** 학원 관리자
**I want to** 수강생의 결제 내역을 조회
**So that** 미납 현황을 파악하고 수납 관리를 효율적으로 할 수 있음

## Value Delivered

미납 수강생을 즉시 파악하여 수납률을 높이고,
결제 이력 기반의 정확한 매출 현황 파악이 가능해짐.

## Acceptance Criteria

- [ ] 결제 목록 페이지에서 카테고리별(멤버십/코스/기타) 필터링 가능
- [ ] 결제 내역에 회원명, 금액, 결제일, 환불 여부가 표시됨
- [ ] 날짜 범위로 결제 내역 검색 가능
- [ ] 환불 처리 시 환불일과 사유가 기록됨

## Task Outline

1. 결제 목록 조회 기능
2. 카테고리별 필터링
3. 환불 처리 기능
4. 결제 현황 요약

## Notes

- 기존 멤버십 결제와 코스 수강료 결제를 통합 관리
- 분납 결제의 경우 개별 납부 건으로 기록
```

### Task (Korean)

```markdown
## Task

**Title**: Firebase Authentication에서 Custom Claims 기반 역할 관리로 전환

## Description

현재 사용자 역할(admin, instructor, member)이 Firestore users 컬렉션에 저장되어 있어
매 API 요청마다 DB 조회가 필요함. Firebase Custom Claims로 전환하면
토큰에 역할이 포함되어 DB 조회 없이 권한 검증이 가능해짐.

## Done Criteria

- [ ] Custom Claims에 role 필드가 설정됨 (admin/instructor/member)
- [ ] API 미들웨어가 Custom Claims에서 역할을 확인함
- [ ] 기존 사용자 전체에 Custom Claims가 마이그레이션됨
- [ ] Firestore Security Rules가 Custom Claims 기반으로 업데이트됨

## Dependencies

- Depends on #45 — Firebase Admin SDK 설정 완료 필요

## Blocks

> 이 Task를 완료해야 아래 이슈를 진행할 수 있습니다.

- Blocks #52 — API 권한 검증 미들웨어 (Custom Claims 기반)
- Blocks #53 — 관리자 전용 페이지 접근 제어

## Task Outline

1. Custom Claims 설정 함수 구현
2. 기존 사용자 마이그레이션 스크립트
3. API 미들웨어 수정
4. Security Rules 업데이트

## Notes

- Custom Claims는 최대 1000 bytes 제한
- Claims 변경 후 토큰 갱신까지 최대 1시간 소요
```

### Bug (Korean)

```markdown
## Bug Report

**Title**: 회원 목록에서 전화번호 검색 시 결과가 표시되지 않음

## Environment

- Version/Branch: v1.2.0 / main
- Browser/OS: Chrome 120 / Windows 11
- Environment: Production

## Steps to Reproduce

1. 관리자 계정으로 로그인
2. 회원 관리 > 회원 목록 페이지로 이동
3. 검색창에 전화번호 뒷 4자리 "1234" 입력
4. Enter 또는 검색 버튼 클릭

## Expected Behavior

전화번호 뒷 4자리가 "1234"인 회원들이 목록에 표시됨.

## Actual Behavior

"검색 결과가 없습니다" 메시지가 표시됨.
이름으로 검색하면 정상 작동함.

## Severity

High - 전화 문의 시 회원 조회가 불가능하여 업무에 큰 지장

## Acceptance Criteria (Fix Verification)

- [ ] 전화번호 뒷 4자리로 검색하면 해당 회원이 표시됨
- [ ] 이름 검색과 전화번호 검색이 모두 정상 작동함
- [ ] 검색어가 숫자인 경우 전화번호 검색으로 자동 전환됨

## Notes

- Firestore composite index가 누락된 것으로 추정
- 개발 환경에서는 데이터 수가 적어 발생하지 않을 수 있음
```

---

## Agent Pipeline Bug Examples

### Good Agent Pipeline Bug (RCA-generated, Korean)

```markdown
## Bug Report

**Title**: GCS signed URL 생성 시 Cloud Run token-only 자격증명으로 인한 500 오류

## Baseline

- Git SHA: `46b2781`
- Branch: main

## Root Cause

`GET /contents/{content_id}` 흐름에서 콘텐츠 파일 URL을 브라우저 접근용 signed URL로
변환할 때 `blob.generate_signed_url(...)` 호출이 발생합니다.

Cloud Run 런타임 자격증명이 `google.auth.compute_engine.credentials.Credentials` (token-only)
상태였고, signed URL 서명에 필요한 private key signer를 제공하지 못해 예외가 발생하고,
이 예외가 except 절을 빠져나가 500 응답으로 직행합니다.

> "you need a private key to sign credentials. the credentials you are currently using
> <class 'google.auth.compute_engine.credentials.Credentials'> just contains a token"

## Steps to Reproduce

1. Cloud Run 환경에서 private key signer 없는 기본 자격증명으로 API 실행
2. 파일 URL이 존재하는 content에 대해 `GET /contents/{content_id}` 호출
3. signed URL 생성 단계에서 signer 예외 발생
4. 결과: 500 응답

## Expected vs Actual Behavior

**Expected**: signed URL이 생성되어 클라이언트에 반환됨
**Actual**: signing 예외가 500으로 직행, 클라이언트는 내부 오류만 확인

## Code Snapshot

```python
# infrastructure/services/gcs_storage_service.py — get_signed_url:
async def get_signed_url(self, gcs_uri: str, expiration: int = 3600) -> str:
    try:
        blob = self._bucket.blob(blob_name)
        return blob.generate_signed_url(expiration=expiration)
    except (GoogleAPICallError, RetryError) as e:
        raise InfrastructureError(f"Failed to generate signed URL: {e}")
    # ← problem: signing credential 예외(TransportError 등)가 이 except를 빠져나감
```

## Blast Radius

`get_signed_url` 호출처 (RCA 시점 확인):
- `application/content/use_cases/get_content.py` — content 상세 조회 [Fact]
- `application/content/use_cases/list_contents.py` — content 목록 조회 [Inference, 확인 필요]

Re-verify: `grep -r "get_signed_url" apps/api/src/`

## Confidence

| Claim | Level | Verification |
|-------|-------|--------------|
| except 절이 GoogleAPICallError/RetryError만 처리 | Fact | 코드에서 직접 확인 |
| Cloud Run 자격증명이 token-only | Fact | 에러 로그 원문 확인 |
| list_contents도 동일 경로를 탈 가능성 | Inference | 해당 파일에서 get_signed_url 호출 여부 확인 |
| IAM signBlob이 현재 SA 권한으로 가능 | Inference | IAM 정책 확인 필요 |

## Action Items

1. `gcs_storage_service.py`: except 절을 `Exception`으로 확장하여 signing 예외 포함 → (2의 전제)
2. `gcs_storage_service.py`: IAM signBlob 기반 signer fallback 구현 → (3의 전제)
3. `get_content.py`: signed URL 실패 시 file_url=null로 DTO 반환 (500 방지)
4. 테스트: token-only credential 시나리오에서 signed URL 생성 동작 테스트 추가
5. 구조화 로그: `credential_type`, `signer_available` 필드 추가 (독립)

## File Scope

| Action | Path | Note |
|--------|------|------|
| Modify | `infrastructure/services/gcs_storage_service.py` | except 확장 + signer fallback |
| Modify | `application/content/use_cases/get_content.py` | signed URL 실패 시 DTO 처리 |
| Create | `tests/infrastructure/test_gcs_storage_signing.py` | signing 실패 시나리오 테스트 |
| Do Not Modify | `domain/` 하위 전체 | 인프라 변경이 도메인에 침투하면 안 됨 |
| Do Not Modify | `StorageService` protocol 시그니처 | 기존 인터페이스 계약 유지 |

## Verification

```bash
# 기존 테스트 전체 통과
uv run pytest tests/ -v --tb=short

# signing 관련 신규 테스트 통과
uv run pytest tests/infrastructure/test_gcs_storage_signing.py -v

# 타입 체크
uv run mypy src/superstate_api/infrastructure/services/gcs_storage_service.py

# lint
uv run ruff check src/superstate_api/infrastructure/services/gcs_storage_service.py
```

Success criteria:
- 위 명령 전부 exit code 0
- `get_signed_url`에서 어떤 예외도 500으로 직행하지 않음
- 기존 `StorageService` protocol 시그니처 변경 없음

## Escalation Criteria

- IAM signBlob 권한(`iam.serviceAccounts.signBlob`)이 현재 SA에 없는 경우 → 인프라 권한 변경 필요
- `StorageService` protocol 시그니처 변경이 불가피한 경우 → 아키텍처 판단 필요
- Verification 전체 통과했으나 staging에서 동일 에러 재현 시 → 환경 설정 문제

---

## Pipeline Metadata (optional)

| Key | Value |
|-----|-------|
| Model | claude-opus-4-6 |
| RCA Timestamp | 2026-02-18T01:30:00Z |
| Session ID | 00175e71-911d-47e1-a25b-461d9697fa5b |
```

### Bad Agent Pipeline Bug (with issues)

```markdown
## Bug Report

**Title**: signed URL 오류

## Context

- Incident Time: 2026-02-17 23:52:40 UTC
- Monitoring URL: https://console.cloud.google.com/monitoring/alerting/alerts/0.o4e7rwe4qcy7
- request_id: ba560d38-b56d-43ce-93f4-ff9539facade
- trace_id: c73ebf7b5f294ec8f7dd306f75f19142

## Root Cause

signed URL 생성이 실패합니다.

## Impact

- 500 요청 2건 발생
- 관련 latency policy도 동시에 firing됨

## Evidence

1. Webhook 수신 정상 (status=200)
2. Cloud Trace에서 500 확인
3. request_failed 로그에서 에러 메시지 확인

## Action Items

- [ ] Signed URL 생성 안정화: fallback(IAM SignBlob 또는 안전한 degrade) 구현
- [ ] 에러 매핑 개선
- [ ] 사전 검증 추가
- [ ] 회귀 테스트 추가
- [ ] 관측성 보강

## Supporting Context

- metric-trace 직접 join은 불가하므로 incident window 기반 상관 절차를 사용
- 민감정보는 마스킹 처리
```

**What's Wrong:**
- **CRITICAL**: Baseline(Git SHA) 누락 — 구현 에이전트가 코드 시점을 특정할 수 없음
- **CRITICAL**: Code Snapshot 누락 — 어떤 코드를 수정해야 하는지 알 수 없음
- **CRITICAL**: Verification 누락 — 구현 완료 판정 불가
- **CRITICAL**: Action Items에 "또는" 포함 — 구현 에이전트가 임의 선택하게 됨
- **MAJOR**: File Scope 누락 — 수정 범위와 금지 영역을 모름
- **MAJOR**: Escalation Criteria 누락 — 막혔을 때 어떻게 해야 하는지 모름
- **MAJOR**: Blast Radius 누락 — 단일 경로 패치로 끝낼 위험
- **MAJOR**: Confidence 구분 없음 — Fact와 Inference가 혼재
- **MAJOR**: Monitoring URL, Correlation Keys 포함 — 에이전트가 접근 불가한 외부 시스템 참조
- **MINOR**: Supporting Context가 RCA 방법론 설명 — 구현에 무관한 정보
- **MINOR**: Impact 건수/타임스탬프 — 에이전트에게 불필요한 severity 정보
