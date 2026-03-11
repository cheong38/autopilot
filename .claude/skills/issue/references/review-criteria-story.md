# Story Review Criteria

## Severity Tiers

| Tier | Label | Blocks Approval? | Description |
|------|-------|-------------------|-------------|
| CRITICAL | Missing core element | YES | Story is fundamentally incomplete |
| MAJOR | Significant gap | YES | Story has notable quality issues |
| MINOR | Improvement | NO | Story could be better but is acceptable |
| SUGGESTION(STRONG) | Recommended | NO | Best practice recommendation |
| SUGGESTION(WEAK) | Optional | NO | Stylistic or preferential |

## Approval Rule

**APPROVE when**: Only MINOR and SUGGESTION(WEAK) findings remain.
**NEEDS_WORK when**: Any CRITICAL or MAJOR findings exist.

## Review Checklist

### 1. User Story Format (CRITICAL if missing)
- [ ] Has clear user role ("As a ...")
- [ ] Has specific goal ("I want to ...")
- [ ] Has business value ("So that ...")
- [ ] Value statement connects to measurable outcome

### 2. Acceptance Criteria (CRITICAL if missing, MAJOR if poor quality)
- [ ] At least 2-5 acceptance criteria defined
- [ ] Uses Given/When/Then format where applicable
- [ ] Each criterion is independently testable
- [ ] Criteria cover the happy path
- [ ] Criteria cover key error/edge cases
- [ ] No implementation details leaked into criteria

### 3. Value Delivered (MAJOR if missing)
- [ ] Clearly articulates business impact
- [ ] Connects user action to business outcome
- [ ] Quantifiable where possible

### 4. INVEST Validation (MAJOR if fails multiple)
- [ ] **Independent**: Can be developed without other stories
- [ ] **Negotiable**: Details can be discussed and refined
- [ ] **Valuable**: Delivers clear business value
- [ ] **Estimable**: Team can estimate the effort
- [ ] **Small**: Completable within a single sprint
- [ ] **Testable**: Has clear acceptance criteria

### 5. Task Outline (MINOR if missing)
- [ ] High-level breakdown exists
- [ ] Tasks describe WHAT, not HOW (no implementation details)
- [ ] Covers all acceptance criteria areas

### 6. Scope (MAJOR if too broad)
- [ ] Story is focused on a single feature/capability
- [ ] Not trying to accomplish too many things
- [ ] Clear boundary between in-scope and out-of-scope

### 7. Language & Clarity (MINOR)
- [ ] Written in user's language consistently
- [ ] Clear and unambiguous wording
- [ ] No jargon that the target user wouldn't understand
- [ ] Structural labels in English (As a/I want to/So that)

### 8. Dependencies (MINOR if missing when relevant)
- [ ] Depends on: upstream issues identified with `#N` references
- [ ] Blocks: downstream issues identified with `#N` references
- [ ] Both directions present (A depends on B → B blocks A)
- [ ] No circular dependencies

### 9. Edge Cases (SUGGESTION(STRONG))
- [ ] Common error scenarios mentioned
- [ ] Boundary conditions considered
- [ ] Notes section captures edge cases for implementation

## Review Output Format

```markdown
## Story Review

**Verdict**: APPROVE / NEEDS_WORK
**Issue**: #<number>
**Type**: Story

### Findings

#### CRITICAL
- [Finding description] → [Suggested fix]

#### MAJOR
- [Finding description] → [Suggested fix]

#### MINOR
- [Finding description] → [Suggested improvement]

#### SUGGESTIONS
- [STRONG] [Recommendation]
- [WEAK] [Optional improvement]

### Summary
[1-2 sentence overall assessment]
```
