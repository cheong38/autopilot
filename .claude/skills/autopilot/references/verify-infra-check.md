# Verify-Infra-Check (Step 5.7)

Project-level verification infrastructure check. Runs once before IMPL-LOOP to ensure
verification tooling exists. If missing, creates prerequisite issues as DAG blockers.

## When to Run

- After DAG-CONFIRM (Step 5.5), before IMPL-LOOP (Step 6)
- **Skip if**: Any issue in DAG has `type: prereq-infra` (recursion prevention)
- Runs once per project per autopilot session (not per issue)

## Check Items

| Item | Detection Method | Prerequisite Issue Title |
|------|-----------------|------------------------|
| CI Pipeline | `.github/workflows/*.yml` or `.gitlab-ci.yml` exists | Set up CI pipeline |
| Playwright | `playwright.config.*` exists | Configure Playwright for E2E testing |
| Deploy Target | `vercel.json`, `Dockerfile`, or deploy scripts exist | Configure deployment target |
| Test Data | `.env.test` or test fixtures directory exists | Set up test data and fixtures |
| Auth | Test credentials accessible (env vars or config files) | Configure test authentication |

## Flow

```
1. For each check item:
   a. Run detection method
   b. If present → mark as "available", skip
   c. If absent → create prerequisite issue

2. If any prereq issues created:
   a. Register in DAG as nodes (type: prereq-infra)
   b. Add blocker edges: prereq → ALL feature issues
   c. Return to IMPL-LOOP (prereqs will be first in ready queue)

3. If all present → proceed directly to IMPL-LOOP
```

## Prerequisite Issue Creation

For each missing infrastructure item:

```bash
# Create issue via /issue --no-brainstorm
/issue --task --no-brainstorm "Set up CI pipeline for automated testing"

# Register in state with prereq-infra type
autopilot-state.py add-issue --id <N> --url <URL> --type prereq-infra \
    --title "Set up CI pipeline"

# Add to DAG
dag-analyze.py add-node --id <N> --title "Set up CI pipeline" --type task

# Add blocker edges to all feature issues
for FEATURE_ID in $(autopilot-state.py query --open | jq -r '.[].id'); do
    dag-analyze.py add-edge --from <N> --to $FEATURE_ID --type depends_on
done
```

## Recursion Prevention

When `issue-impl` runs for a `prereq-infra` issue:
1. Check issue type in autopilot-state.py
2. If `type == "prereq-infra"` → skip VERIFY-INFRA-CHECK
3. This prevents infinite loops where infra issues trigger more infra checks

The prereq-infra issue is verified by:
- **CI**: Check pipeline runs (simple CLI check)
- **Playwright**: Check config file exists after install
- **Deploy**: Check deploy config exists
- No recursive VERIFY-INFRA-CHECK for these issues

## Trace Recording

```bash
# Step-level span
SPAN=$(trace.py start-span --session $SID --name "VERIFY-INFRA-CHECK" --kind step)

# Per-check sub-spans
CHECK=$(trace.py start-span --session $SID --name "check-ci" --kind sub_step)
trace.py end-span --session $SID --span-id $CHECK --attr found=false

# Prereq creation sub-span (if needed)
PREREQ=$(trace.py start-span --session $SID --name "prereq-create" --kind sub_step \
    --attr prereq_type=ci --attr issue_number=N)
trace.py end-span --session $SID --span-id $PREREQ

# End step span
trace.py end-span --session $SID --span-id $SPAN \
    --attr prereqs_created=2 --attr checks_passed=3
```

## Configuration

| Key | Default | Description |
|-----|---------|-------------|
| `verify_infra_check` | `true` | Enable/disable infra check |
| `infra_checks` | all items | Which items to check (list) |
