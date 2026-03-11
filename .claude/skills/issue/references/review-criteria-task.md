# Task Review Criteria

## Severity Tiers

| Tier | Label | Blocks Approval? | Description |
|------|-------|-------------------|-------------|
| CRITICAL | Missing core element | YES | Task is fundamentally incomplete |
| MAJOR | Significant gap | YES | Task has notable quality issues |
| MINOR | Improvement | NO | Task could be better but is acceptable |
| SUGGESTION(STRONG) | Recommended | NO | Best practice recommendation |
| SUGGESTION(WEAK) | Optional | NO | Stylistic or preferential |

## Approval Rule

**APPROVE when**: Only MINOR and SUGGESTION(WEAK) findings remain.
**NEEDS_WORK when**: Any CRITICAL or MAJOR findings exist.

## Review Checklist

### 1. Title (CRITICAL if missing or vague)
- [ ] Title is clear and actionable (imperative form)
- [ ] Title describes the outcome, not just the activity
- [ ] Title is specific enough to distinguish from similar tasks

### 2. Description (CRITICAL if missing, MAJOR if vague)
- [ ] Clearly explains WHAT needs to be done
- [ ] Explains WHY (context, motivation)
- [ ] Sufficient detail for someone unfamiliar to understand scope
- [ ] No ambiguous or undefined terms

### 3. Done Criteria (CRITICAL if missing, MAJOR if poor quality)
- [ ] At least 2-5 done criteria defined
- [ ] Each criterion is independently verifiable
- [ ] Criteria are specific and measurable (not "it should work")
- [ ] Criteria cover the complete scope of the task
- [ ] No implementation details leaked into criteria

### 4. Scope (MAJOR if too broad)
- [ ] Task is focused on a single objective
- [ ] Completable within a reasonable timeframe
- [ ] Clear boundary between in-scope and out-of-scope
- [ ] Not bundling multiple unrelated changes

### 5. Dependencies (MINOR if missing when relevant)
- [ ] Depends on: upstream issues identified with `#N` references
- [ ] Blocks: downstream issues identified with `#N` references
- [ ] Both directions present (A depends on B → B blocks A)
- [ ] No circular dependencies

### 6. Constraints (MINOR if missing when relevant)
- [ ] Technical constraints documented if any
- [ ] Compatibility requirements noted
- [ ] Timeline constraints mentioned if applicable

### 7. Language & Clarity (MINOR)
- [ ] Written in user's language consistently
- [ ] Clear and unambiguous wording
- [ ] Technical terms are appropriate for the audience

## Review Output Format

```markdown
## Task Review

**Verdict**: APPROVE / NEEDS_WORK
**Issue**: #<number>
**Type**: Task

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
