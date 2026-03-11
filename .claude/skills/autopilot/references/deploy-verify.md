# Deploy-Verify Workflow

Post-merge deployment verification. Runs after pre-deploy verification (Step 6.5) succeeds and code is deployed.

## Relationship to Existing Steps

```
6.5 PRE-DEPLOY-VERIFY   Local/CI verification (existing, renamed from VERIFY)
6.6 DEPLOY-DETECT       Detect deployment environment
6.7 DEPLOY-VERIFY       Post-deploy verification in live environment
7.  TRIAGE               Classify failures (existing)
```

PRE-DEPLOY-VERIFY checks code locally (tests, lint, Playwright on localhost).
DEPLOY-VERIFY checks the deployed artifact in the target environment.

## Step 6.6: DEPLOY-DETECT

Detect if and where code was deployed after merge.

### Detection Methods

| Environment | Detection | Deploy URL Pattern |
|-------------|-----------|-------------------|
| Vercel | `vercel ls --scope <team> 2>/dev/null` | `https://<project>-*.vercel.app` |
| Docker | `docker ps --filter name=<project>` | `http://localhost:<port>` |
| Kubernetes | `kubectl get pods -l app=<project>` | Service URL from ingress |
| Manual | Ask user via UIP | User provides URL |

### Flow

1. Check for deployment indicators in order: Vercel → Docker → K8s → CI deploy step
2. If detected → extract deploy URL → proceed to 6.7
3. If not detected → ask user:

> **User Interaction** (UIP-27): 배포 환경 감지 / Deploy environment detection

| Option | Action |
|--------|--------|
| **Provide URL (Recommended)** | User provides deployed URL |
| **Skip deploy verify** | Mark as pre-deploy only |
| **Not deployed** | No deployment; skip 6.7 |
| **Other** | User provides custom input |

### Trace Recording

```bash
trace.py start-span --session $SID --name "deploy-detect" --kind sub_step
trace.py end-span --session $SID --span-id $SPAN --attr env=vercel --attr deploy_url=https://...
```

## Step 6.7: DEPLOY-VERIFY

Verify the deployed application meets acceptance criteria.

### 6.7.1 TEST-DATA-SETUP

Prepare test data/accounts for verification in the deployed environment.

- Create test accounts if needed (use `.env.test` for credentials)
- Seed test data (API calls or scripts)
- **Security**: Never commit credentials. Use `.env.test` (must be in `.gitignore`)
- Trace: `start-span --name "test-data-setup" --kind sub_step`

### 6.7.2 VERIFY-ATTEMPT

Fallback chain (try in order until one succeeds):

1. **Playwright** (Priority 1): Browser automation against deploy URL
   ```
   browser_navigate(deploy_url)
   browser_snapshot()
   Assert expected elements/behavior
   ```

2. **CLI/API** (Priority 2): curl/httpie against deploy URL
   ```bash
   curl -s -o /dev/null -w "%{http_code}" $DEPLOY_URL/api/health
   ```

3. **Manual Guide** (Priority 3): LLM generates step-by-step verification guide
   - Guide is context-aware: includes deploy URL, feature description, test accounts
   - User follows steps and confirms each one
   - Format follows [Verification Matrix](verification-matrix.md) manual template

- Trace: `start-span --name "verify-automated" --kind sub_step --attr method=playwright`

### 6.7.3 AUTH-HANDOFF

When verification requires authentication in the deployed environment:

1. Check if test credentials exist (`.env.test`, environment variables)
2. If available → auto-login via Playwright or API token
3. If not → ask user to authenticate, then hand back control

> **User Interaction** (UIP-28): 배포 환경 인증 / Deploy environment auth

| Option | Action |
|--------|--------|
| **I'll log in (Recommended)** | User authenticates, confirms ready |
| **Provide credentials** | User provides test credentials |
| **Skip auth-gated checks** | Skip checks requiring auth |
| **Other** | User provides custom input |

**Security**: Never store or log credentials. Trace records only:
- `auth_type`: web_login, api_token, skip
- `wait_duration_ms`: time waiting for user
- `resolved`: true/false

Trace:
```bash
trace.py add-event --session $SID --span-id $SPAN --event "auth-handoff" \
  --attr auth_type=web_login --attr resolved=true
```

### 6.7.4 CLEANUP

Optional: clean up test data created in 6.7.1.

- Delete test accounts/data via API
- Only if `cleanup_test_data: true` in config (default: false)

### Result Output

```
DEPLOY_VERIFY_RESULT_BEGIN
METHOD=playwright|cli|api|manual
STATUS=pass|fail|skip
AUTH_HANDOFF=true|false
DEPLOY_URL=<url>
DEPLOY_VERIFY_RESULT_END
```

**Pass** → continue to Step 8 (CHECKPOINT)
**Fail** → Step 7 (TRIAGE) with deploy-verify context
**Skip** → continue with note in trace

## Trace Recording Summary

| Sub-step | Span Name | Kind | Key Attributes |
|----------|-----------|------|---------------|
| DEPLOY-DETECT | deploy-detect | sub_step | env, deploy_url |
| TEST-DATA-SETUP | test-data-setup | sub_step | |
| VERIFY-ATTEMPT | verify-automated | sub_step | method, verification_result |
| AUTH-HANDOFF | (event on verify span) | event | auth_type, resolved |
| CLEANUP | test-data-cleanup | sub_step | |
