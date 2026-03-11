# Code Review Criteria

## Review Priority (STRICT)

| Priority | Category | Action |
|----------|----------|--------|
| 1 | BUGS | Logic errors, control flow, async issues → MUST block |
| 2 | SECURITY | Injection, auth, data exposure → MUST block |
| 2.5 | FIX COMPLETENESS | Incomplete fix, unprotected callers → MUST block (bug only) |
| 3 | ARCHITECTURE | Layer violations, SOLID, dependencies → SHOULD block |
| 4 | TESTS | Coverage gaps, test quality, edge cases → SHOULD block |
| 5 | STYLE | Naming, formatting, conventions → MAY comment |

## Severity Tiers

| Tier | Criteria | Action | Examples |
|------|----------|--------|----------|
| CRITICAL | Bugs, security issues, data loss risk | BLOCK | SQL injection, null crash, auth bypass |
| MAJOR | Architecture violations, test gaps | BLOCK | Layer violations, untested critical path |
| MINOR | Improvements, style, suggestions | COMMENT | Better naming, minor optimization |

## Approval Rule

**APPROVE when**: No CRITICAL or MAJOR issues found.
**REQUEST_CHANGES when**: Any CRITICAL or MAJOR issues.

## Review Checklist

### Bugs
- [ ] Null/undefined handling
- [ ] Boundary conditions
- [ ] Error handling
- [ ] Race conditions
- [ ] Async/await issues

### Security
- [ ] Input validation/sanitization
- [ ] Injection vulnerabilities
- [ ] Secrets/credentials exposure
- [ ] Auth/authz implementation
- [ ] Sensitive data logging

### Architecture
- [ ] Layer boundary violations
- [ ] Dependency direction (Clean Architecture)
- [ ] Coupling/cohesion
- [ ] SOLID principles
- [ ] Exception types match semantics (ValueError=input, InfrastructureError=infra, NotFoundError=404)
- [ ] Test doubles not duplicated across files (shared via conftest/fixtures)
- [ ] Cross-cutting pattern applied to 3+ call sites: (a) behavior fits each site's contract, (b) repeated code extracted
- [ ] Degrade/fallback paths have warning-level logging in use case layer

### Tests
- [ ] Test coverage for new code
- [ ] Edge cases coverage
- [ ] Error path testing
- [ ] Test quality (no false positives)

### Fix Completeness (Bug issues only — skip for story/task)
- [ ] 수정된 함수의 모든 호출처가 보호되는가 (Grep으로 확인)
- [ ] Fallback/대체값이 프로덕션 환경에서 실제로 유효한가
- [ ] 수정이 증상(symptom)이 아닌 근본 원인(root cause)을 해결하는가
- [ ] 비대상 환경에 대한 후방 호환성이 유지되는가
- [ ] 동일 패턴의 다른 코드 경로에 같은 취약점이 없는가

## Review Output Format

```markdown
## Code Review: [PR Title]

### Summary
[1-2 sentence overall assessment]

### CRITICAL Issues (BLOCKING)
- **[file:line]** [Description] - [Why critical]
  **Fix**: [Suggested solution]

### MAJOR Concerns (BLOCKING)
- **[file:line]** [Description] - [Why matters]
  **Fix**: [Suggested solution]

### MINOR Suggestions (Non-blocking)
- **[file:line]** [Recommendation]

### What's Good
- [Positive observation]

---
**Verdict**: APPROVE / REQUEST_CHANGES
**Reviewed**: [X files, Y additions, Z deletions]
```
