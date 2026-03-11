# Plan Review Criteria

## Priority 1: Delivery Structure (Critical)

| Criterion | Key Questions |
|-----------|---------------|
| **Vertical Slices** | Are phases organized as vertical slices (not horizontal layers)? Does each phase include Domain + App + Infra + API + UI for ONE feature? |
| **Per-Phase Deployability** | Can each phase be deployed independently? Does each phase deliver standalone user value? |
| **E2E Test First** | Does each phase start with E2E/acceptance test? Are acceptance criteria defined before implementation? |
| **TDD Cycle** | Does each phase follow RED → GREEN → REFACTOR? Are unit/integration tests written before implementation? |

## Priority 1b: Fix Completeness (Critical — Bug issues only)

Applies when the source issue is labeled `bug`. Skip for story/task issues.

| Criterion | Key Questions |
|-----------|---------------|
| **Blast Radius** | 수정 대상 함수/메서드의 모든 호출처를 Grep으로 식별했는가? 플랜이 전체 호출처를 커버하는가? |
| **Fix Layer** | 수정이 올바른 아키텍처 레이어에서 이루어지는가? N개 Use Case를 개별 보호 vs 공통 Infrastructure 1곳 수정 — 근거가 있는가? |
| **Fix Effectiveness** | Fallback/대체값이 실제 프로덕션 환경에서 동작하는가? (예: private 버킷에 unsigned URL 반환 → 403 유발) |
| **Environment Impact** | 수정이 대상 환경 외 다른 환경(로컬, CI)에 부작용을 만드는가? 추가 권한/설정 요구사항이 있는가? |

## Priority 2: Plan Quality (Important)

| Criterion | Key Questions |
|-----------|---------------|
| **Feasibility** | Technically achievable? Dependencies available? Realistic scope? |
| **Clarity** | Task breakdowns with file paths? Quality gates defined? |
| **Backward-Compatibility** | Existing functionality preserved? Migration path? |
| **Security** | Auth/authz? Input validation? PII protection? |
| **No Contradictions** | Internal consistency? Tasks don't conflict? |
| **Completeness** | All phases have quality gates? Testing strategy defined? |

## Severity Tiers

| Tier | Blocks? | Examples |
|------|---------|----------|
| CRITICAL | YES | Horizontal layers instead of vertical slices, no E2E tests |
| MAJOR | YES | Non-deployable phases, missing quality gates |
| MINOR | NO | Minor clarity improvements, better task naming |
| SUGGESTION(STRONG) | NO | Architecture optimization, additional tests |
| SUGGESTION(WEAK) | NO | Documentation formatting, stylistic |

## Approval Rule

**APPROVE when**: Only MINOR + SUGGESTION(WEAK) remain.
**NEEDS_WORK when**: Any CRITICAL or MAJOR findings.

## Automatic FAIL Conditions

1. Phases organized by architecture layer instead of feature
2. Phases don't start with acceptance tests
3. Any phase leaves codebase in broken/non-deployable state
4. Phases don't deliver standalone user value
5. (Bug only) 수정 대상 함수의 호출처 분석 없이 단일 경로만 수정
6. (Bug only) Fallback 값이 실제 환경에서 동작하지 않는 것이 명백한 경우

## Review Output Format

```markdown
## Plan Review

**Verdict**: APPROVE / NEEDS_WORK
**Plan**: [plan file path]

### Delivery Structure (Critical)

| Criterion | Status | Finding |
|-----------|--------|---------|
| Vertical Slices | OK/FAIL | [detail] |
| Per-Phase Deployability | OK/FAIL | [detail] |
| E2E Test First | OK/FAIL | [detail] |
| TDD Cycle | OK/FAIL | [detail] |

### Fix Completeness (Critical — Bug only, skip for story/task)

| Criterion | Status | Finding |
|-----------|--------|---------|
| Blast Radius | OK/FAIL/N/A | [detail] |
| Fix Layer | OK/FAIL/N/A | [detail] |
| Fix Effectiveness | OK/FAIL/N/A | [detail] |
| Environment Impact | OK/WARN/N/A | [detail] |

### Plan Quality (Important)

| Criterion | Status | Finding |
|-----------|--------|---------|
| Feasibility | OK/WARN/FAIL | [detail] |
| Clarity | OK/WARN/FAIL | [detail] |
| ... | ... | ... |

### Findings

#### CRITICAL
- [Finding] → [Fix]

#### MAJOR
- [Finding] → [Fix]

#### MINOR
- [Finding] → [Suggestion]

### Phase Analysis

Phase 1: [Name] - Vertical Slice: OK, Deployable: OK, E2E First: OK
Phase 2: [Name] - Vertical Slice: OK, Deployable: OK, E2E First: OK
```
