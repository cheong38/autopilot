# Autopilot App Design

Date: 2026-03-14

## Overview

A web app that replaces the autopilot skill entirely. The app owns all orchestration logic, using Claude CLI (with crafted prompts, not skills) for AI-heavy tasks and direct CLI calls (gh, git) for deterministic operations. The AI chat agent is named **오피(OP)**.

## Core Concepts

- **The app IS autopilot** — no skills at runtime, app owns all orchestration
- **OP (오피)** — the AI agent that chats with users. Asks one question at a time with options + custom input
- **Project** = a git repo (cloned inside container)
- **Issue** = core unit of work (story/task/bug)
- **UL + BC verification** — AOP cross-cutting concern, checked at every step of every interaction

## Tech Stack

- **Backend**: Rust (Axum), PostgreSQL
- **Frontend**: React, TypeScript, Vite, React Flow (DAG)
- **Infra**: Docker Compose (app + db containers)
- **AI**: Claude CLI with auth token (personal subscription)
- **Git**: GitHub/GitLab PAT, repos cloned inside container

## Architecture

```
Docker Compose
├── app (Rust/Axum)
│   ├── REST API + WebSocket
│   ├── Session Queue (configurable concurrency, default 1)
│   ├── Supervised CLI Process Manager + DB checkpointing
│   ├── Orchestration state machine (replaces all skills)
│   ├── Claude CLI binary (auth via token)
│   ├── gh/glab CLI (auth via PAT)
│   └── /workspace/<project>/ (cloned repos)
├── web (React SPA, static files served by app)
└── db (PostgreSQL)
```

### Recovery

- State checkpointed to DB after each step
- On restart: re-read DB, resume active work

## Data Model

### projects

| Column | Type | Description |
|--------|------|-------------|
| id | uuid | PK |
| name | text | Project name |
| remote_url | text | Git remote URL |
| local_path | text | /workspace/<name>/ |
| provider | text | github \| gitlab \| jira |
| default_branch | text | Default branch name |
| created_at | timestamptz | Creation time |

### issues

| Column | Type | Description |
|--------|------|-------------|
| id | uuid | PK |
| project_id | uuid | FK → projects |
| issue_number | int | From GitHub/GitLab |
| issue_url | text | Issue URL |
| title | text | Issue title |
| type | text | story \| task \| bug |
| status | text | See Issue Statuses |
| verified | boolean | Verification passed |
| requirement_ids | text[] | Linked requirement IDs |
| verification_methods | text[] | Verification methods |
| pr_number | int | PR number |
| pr_url | text | PR URL |
| created_at | timestamptz | Creation time |
| updated_at | timestamptz | Last update |

### issue_edges

| Column | Type | Description |
|--------|------|-------------|
| id | uuid | PK |
| from_issue_id | uuid | FK → issues |
| to_issue_id | uuid | FK → issues |
| edge_type | text | depends_on \| blocks |

### hi_queue

| Column | Type | Description |
|--------|------|-------------|
| id | uuid | PK |
| project_id | uuid | FK → projects |
| prompt_text | text | Question for user |
| options | jsonb | Array of {label, action} |
| status | text | pending \| answered \| expired |
| response | text | User's response (nullable) |
| created_at | timestamptz | Creation time |
| answered_at | timestamptz | When answered |

### settings

| Column | Type | Description |
|--------|------|-------------|
| key | text | PK |
| value | jsonb | Setting value |

## Issue Statuses

```
discussing      → OP and user are refining requirements
backlog         → Concrete issue spec defined, not yet created in tracker
created         → Created in GitHub/GitLab, waiting for dependencies
ready           → Dependencies resolved, eligible for implementation
implementing    → OP is actively implementing via Claude CLI
in_review       → PR created, under code review
merged          → PR merged
unit_verifying  → Running unit/integration tests
e2e_verifying   → Running fullstack E2E tests
done            → All verifications passed, complete
failed          → Any step failed
deferred        → Pushed to later
```

## Kanban Columns

| Column | Statuses |
|--------|----------|
| Discussing | `discussing` |
| To Do | `backlog`, `created`, `ready` |
| In Progress | `implementing`, `in_review` |
| Verifying | `merged`, `unit_verifying`, `e2e_verifying` |
| Done | `done` |
| Failed | `failed` |
| Deferred | `deferred` |

## Views & Navigation

Sidebar with project switcher at top.

### Home

- **Top section**: Global HI queue (all projects). Each item shows project name, prompt. Clicking opens chat popover with context.
- **Bottom section**: Kanban board scoped to selected project. Cards color-coded by session, filterable. Clicking a card opens issue detail modal.

### DAG

- Per-project view with React Flow.
- Nodes = issues, edges = dependencies.
- Cross-project dependency nodes shown as external (dimmed).
- Click a node → issue detail modal.

### Settings

- Projects: add (remote URL + name), remove, re-clone
- Auth: Claude Code token, GitHub/GitLab PAT
- Autopilot config: confidence thresholds, max follow-up rounds, concurrency limit

### Chat Popover

- Opens on HI item click or manually via nav icon.
- Project-scoped OP conversation.
- Can start new requirements input here.

## OP (오피) Behavior

- Always ask **one question at a time**
- Provide **generated options** (recommended first) + **custom input ("Other")**
- Wait for user response before proceeding
- UL/BC verification at every step (AOP) — if user uses unknown term, ask for clarification
- BC inferred from codebase analysis, user confirms

## CLI Integration

- App crafts prompts for Claude CLI (no skills used)
- Direct CLI calls for deterministic ops (gh, glab, git, test runners)
- Session queue with configurable concurrency (default 1)
- Parses stdout for progress
- Creates HI items when user input needed
- Writes to stdin when user responds
- On restart: resume from DB checkpoint
