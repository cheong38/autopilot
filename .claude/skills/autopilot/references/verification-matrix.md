# Verification Matrix

Verification strategy templates per method. Referenced by Step 1.5 (VERIFY-PLAN), Step 6.5 (PRE-DEPLOY-VERIFY), and Step 6.7 (DEPLOY-VERIFY).

## Pre-Deploy vs Post-Deploy

| Phase | Step | Scope | Environment |
|-------|------|-------|-------------|
| Pre-deploy | 6.5 PRE-DEPLOY-VERIFY | Local/CI tests, lint, Playwright on localhost | Local dev |
| Post-deploy | 6.7 DEPLOY-VERIFY | Deployed artifact in target environment | Vercel/Docker/K8s/etc |

See [Deploy-Verify](deploy-verify.md) for post-deploy workflow details.

## Method Classification

| Method | Trigger | Automation Level |
|--------|---------|------------------|
| Playwright | Web UI features | Auto |
| CLI/curl | API endpoints, services | Auto |
| Test suite | Logic, algorithms, data | Auto |
| Credential-gated | Requires auth/env setup | Semi-auto (UIP-22) |
| Manual | Hardware, visual, UX | Manual |

## Playwright Verification Template

```
1. browser_navigate → target URL
2. browser_snapshot → capture page state
3. Assert expected elements exist (selectors, text content)
4. Interact (click, fill) → verify state change
5. browser_snapshot → capture result state
```

**Example** (login feature):
```
browser_navigate("http://localhost:3000/login")
browser_fill_form([{"selector": "#email", "value": "test@example.com"}, {"selector": "#password", "value": "pass123"}])
browser_click("button[type=submit]")
browser_snapshot()  # Assert: dashboard visible, welcome message shown
```

## CLI/curl Verification Template

```bash
# API endpoint verification
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/api/resource
# Expected: 200

# Response body check
curl -s http://localhost:3000/api/resource | jq '.status'
# Expected: "ok"

# POST with payload
curl -s -X POST http://localhost:3000/api/resource \
  -H "Content-Type: application/json" \
  -d '{"key": "value"}' | jq '.id'
# Expected: non-null
```

## Test Suite Verification Template

```bash
# JavaScript/TypeScript
npm test -- --grep "feature name"
npx jest --testPathPattern="feature"

# Python
pytest tests/ -k "feature_name" -v
python3 -m unittest tests.test_feature -v

# Go
go test ./... -run TestFeature -v
```

## Manual Verification Guide Format

When automated verification is not possible, present to user:

```
## Manual Verification Steps

### Feature: <feature name>
**Issue**: #<number>

1. [ ] Open <URL or application>
2. [ ] Navigate to <location>
3. [ ] Perform <action>
4. [ ] Verify: <expected result>
   - Screenshot/output reference: <description>
5. [ ] Confirm: Does the result match? (yes/no)
```

## Mapping Requirements to Verification

Each requirement from INGEST gets a verification entry:

```json
{
  "requirement_id": "R-001",
  "verification_method": "playwright",
  "verification_details": "Navigate to /login, fill form, submit, assert dashboard",
  "verification_status": "pending"
}
```

Valid `verification_status` values: `pending`, `passed`, `failed`, `skipped`.
