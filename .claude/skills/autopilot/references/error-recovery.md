# Error Recovery

Recovery strategies for common autopilot failure scenarios.

| Scenario | Action |
|----------|--------|
| `/issue` skill fails | Retry once, then direct creation fallback |
| `/issue-impl` fails 3x | UIP-26 (skip/retry/abort) |
| DAG cycle detected | Remove last edge, alert user |
| Verification timeout | Mark as manual, present steps to user |
| State file corrupted | Rebuild from meta-issue comments |
| Network failure mid-step | Retry with exponential backoff (3 attempts) |
| Lock conflict on resume | UIP-25 |
| Provider CLI not auth'd | Error with setup instructions |
| Playwright not available | Fall back to manual verification |
