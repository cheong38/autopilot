# Self-Review Criteria

Per-step self-review checklists. The orchestrator validates these before proceeding to the next step.

## WHY-CONTEXT (Step 0.5)

- [ ] Both dimensions (user_problem, decision_context) addressed?
- [ ] Each dimension is specific and actionable (not vague)?
- [ ] Narrative summary captures the judgment criterion?
- [ ] Meta-issue body updated with ## Why Context section?
- [ ] No assumptions made without user confirmation?

## INGEST (Step 1)

- [ ] All requirements extracted from source?
- [ ] No ambiguous requirements (confidence < 80% flagged)?
- [ ] Out-of-scope items identified?
- [ ] Feature list covers the full PRD scope?
- [ ] Each requirement has a unique R-xxx ID?

## VERIFY-PLAN (Step 1.5)

- [ ] Every requirement has a verification method assigned?
- [ ] Auto-verifiable requirements use appropriate tool (Playwright/CLI/test)?
- [ ] Manual verification steps are clear and actionable?
- [ ] Credential requirements identified for semi-auto verification?

## UL-CHECK (Step 2)

- [ ] All new domain terms identified?
- [ ] Each registered term has correct canonical name?
- [ ] Aliases are accurate and non-overlapping?
- [ ] Domain classification is correct?

## CLARIFY (Step 2.5)

- [ ] All requirements at 99%+ confidence?
- [ ] Verification matrix still valid after clarifications?
- [ ] No requirement was silently reinterpreted without user input?

## DECOMPOSE (Step 3)

- [ ] No duplicate issues (scope overlap)?
- [ ] No gaps (every R-xxx covered by at least one issue)?
- [ ] Dependencies are logical (no circular, no missing prerequisites)?
- [ ] Each issue is small enough for a single PR (≤ 3 phases)?
- [ ] Every issue has `requirement_ids` and `verification_methods` populated?

## CREATE (Step 4)

- [ ] Each created issue matches its specification (title, type, labels)?
- [ ] Issue body contains acceptance criteria?
- [ ] All issues stored in state with correct metadata?

## DAG-BUILD (Step 5)

- [ ] No cycles in the graph?
- [ ] Topological sort produces valid execution order?
- [ ] All issue nodes present in DAG?
- [ ] All dependency edges correctly added?
- [ ] DAG pushed successfully?

## IMPL (Step 6, per issue)

- [ ] All done criteria checked off in the issue?
- [ ] PR/MR was merged successfully? (GitHub: `gh pr view <N> --json state --jq '.state'` → must be `MERGED`. GitLab: `glab mr view <N> --json state`)
- [ ] Deployment pipeline passed?
- [ ] No regressions detected (full test suite)?

## VERIFY (Step 6.5, per issue)

- [ ] Verification method executed correctly?
- [ ] Expected behavior confirmed?
- [ ] No side effects on other features?
- [ ] Result recorded in state (`verified: true/false`)?

## FINAL-VERIFY (Step 11)

- [ ] All cross-feature integrations verified?
- [ ] Full test suite passes across all changes?
- [ ] End-to-end user journeys work correctly?
- [ ] No regressions from feature interactions?

## REPORT (Step 12 / S4)

- [ ] Follow-up round가 발생했으면 교훈이 state에 기록되었는가?
- [ ] State의 교훈이 프로젝트 메모리에 저장되었는가?
- [ ] 검증 우선순위(Playwright → CLI → Manual) 준수 여부 확인되었는가?
