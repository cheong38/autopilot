# TDD Workflow Reference

## Per-Phase TDD Cycle

```
1. E2E TEST     → Write acceptance test FIRST (defines "done")
2. RED          → Write failing unit/integration tests
3. GREEN        → Implement to pass all tests
4. REFACTOR     → Clean up while keeping tests green
5. VERIFY       → E2E test passes, all quality gates pass
6. COMMIT       → Descriptive commit per phase
```

## Layer Order (Clean Architecture)

```
Phase N: [Feature]
├── E2E: Acceptance test (Gherkin scenario)
├── Domain:
│   ├── RED: Unit tests for entities, value objects
│   └── GREEN: Implement domain logic
├── Application:
│   ├── RED: Unit tests for use cases
│   └── GREEN: Implement use cases with port interfaces
├── Infrastructure:
│   ├── GREEN: Implement repositories, adapters
│   └── Integration test: Verify against emulator/real service
├── Presentation:
│   ├── GREEN: API endpoints
│   └── GREEN: UI components
├── REFACTOR: Clean up code
└── VERIFY: E2E passes, quality gates pass
```

## Quality Gates (Per Phase)

### Automated Checks
- [ ] E2E acceptance test passes
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Build succeeds
- [ ] Lint passes
- [ ] Type check passes
- [ ] Doc/skill sync: changed file paths have corresponding docs/skills updated (per knowledge-maintenance mapping)

### Manual Verification
- [ ] Codebase is deployable
- [ ] No broken features
- [ ] Production verification (if deployed)

## Commit Convention

```
[#ISSUE] Phase N - Feature description

E2E: Acceptance test for [scenario]
- Domain: [entity/value object]
- Application: [use case]
- Infrastructure: [repository]
- Presentation: [endpoint/component]

Delivers: [user value statement]
```

## Common Patterns

### Python (FastAPI + Firestore)
```python
# Domain entity (frozen dataclass)
@dataclass(frozen=True)
class Entity:
    id: EntityId
    name: str

# Repository protocol (port)
class EntityRepository(Protocol):
    def save(self, entity: Entity) -> None: ...
    def find_by_id(self, id: EntityId) -> Entity | None: ...

# Use case
class CreateEntity:
    def __init__(self, repo: EntityRepository): ...
    def execute(self, dto: CreateEntityDTO) -> EntityDTO: ...

# Firestore repository (adapter)
class FirestoreEntityRepository:
    def __init__(self, db: firestore.Client): ...
```

### Rust (tonic gRPC + Firestore)
```rust
// Domain entity
pub struct Conversation { pub id: String, pub project_id: String, ... }

// Repository trait (port)
#[async_trait]
pub trait ConversationRepository: Send + Sync {
    async fn find_by_project_id(&self, project_id: &str) -> Result<Vec<Conversation>, DomainError>;
}

// Firestore repository (adapter)
pub struct FirestoreConversationRepo { client: FirestoreClient }

// Use case
pub struct ListConversationsUseCase { repo: Arc<dyn ConversationRepository>, ... }
```

### TypeScript (React)
```typescript
// Component with data fetching
export function EntityList() {
  const { data, isLoading } = useQuery(['entities'], fetchEntities);
  if (isLoading) return <Skeleton />;
  return <DataTable data={data} />;
}
```

## Integration & E2E Test Priority

When implementing infrastructure or new API features, write integration and E2E tests **before or alongside** unit tests — not as an afterthought. This ensures:
- Wire format correctness (gRPC, SSE, REST) is verified early
- External service integrations (Firestore, ChannelTalk, LLM) are tested against real/emulated backends
- Cross-layer regressions are caught before merge

**Guideline**: If a phase touches infra or presentation layers, include at least one integration or E2E test in that phase's RED step.

## Integration Test Strategy

### Firestore Emulator
```bash
# Python: Start emulator and run tests
firebase emulators:exec --only firestore "uv run pytest tests/integration -v"

# Rust: Start emulator on port 8888, then run
cd apps/operator-api && cargo test --test integration_tests --features integration
```

### Rust Integration Tests (wiremock)
```rust
// Use wiremock for HTTP service mocking (ChannelTalk, LLM)
let mock_server = MockServer::start().await;
Mock::given(method("GET")).and(path("/open/v5/user-chats"))
    .respond_with(ResponseTemplate::new(200).set_body_json(&response))
    .mount(&mock_server).await;
let client = ChannelTalkClient::with_base_url(mock_server.uri());
```

### Rust E2E Tests (full gRPC server)
```rust
// Boot real tonic server on random port + Firestore emulator + wiremock
let env = TestEnv::start().await;
let req = authed_request(ListConversationsRequest { ... }, &api_key);
let resp = env.client.clone().list_conversations(req).await.unwrap();
```

### Index Validation
- Test all query patterns that require composite indexes
- Document which index each query uses
- Verify against `firestore.indexes.json`

## Test Double Hygiene

- Test doubles (mocks, fakes, stubs) used in 2+ test files MUST be extracted to `tests/conftest.py` or `tests/fixtures/<domain>.py`
- Each test double implements ONLY the methods exercised by the test (minimal interface principle)
- Do NOT duplicate identical fixture definitions across multiple test files
- Name test doubles by behavior, not implementation: `FailingStorageService` not `MockGcsService`

## Exception Semantics

| Exception | Semantics | HTTP Status | Example |
|-----------|-----------|-------------|---------|
| `ValueError` | User input validation failure | 400 | Invalid email format, missing required field |
| `InfrastructureError` | Infrastructure temporary failure | 500/503 | GCS signing failure, DB connection timeout |
| `NotFoundError` | Resource does not exist | 404 | Content not found, member not found |

**Rules:**
- `ValueError` = caller provided bad input → 400 Bad Request
- `InfrastructureError` = system-level failure beyond caller's control → 500/503
- Never raise `ValueError` for infrastructure failures (e.g., GCS signing error is NOT a validation error)
- Degrade/fallback paths in use case layer MUST include `logger.warning()` with context (what failed, what fallback was used)

## Pre-Commit Quality Gate

Before every commit, run ALL quality checks:

```bash
# Python (API)
uv run ruff check . && uv run ruff format --check . && uv run mypy src/

# TypeScript (Frontend)
pnpm lint && pnpm typecheck
```

**Rules:**
- All checks MUST pass before commit — no `--no-verify` shortcuts
- Fix lint/type issues in the SAME commit as the feature code — no separate fixup commits
- If pre-commit hook fails, fix the issues and create a NEW commit (do not amend)
