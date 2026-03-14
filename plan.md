# Implementation Plan: Simulated UI Prototype

**Issue**: #4
**Created**: 2026-03-14
**Status**: Draft

## Overview

Build a frontend-only clickable prototype of the Autopilot web app with hardcoded mock data. Uses React/TypeScript/Vite with shadcn/ui + Tailwind for components, React Flow for DAG visualization. No backend — all data is in-memory mock data.

## Vertical Slice Decomposition

| Phase | Feature Slice | Value Delivered |
|-------|--------------|-----------------|
| 1 | Project scaffold + app shell | User sees sidebar nav with routing |
| 2 | Mock data + Home view (HI queue + Kanban) | User sees HI items and issues on Kanban board |
| 3 | Issue detail modal + Kanban interactions | User clicks card, sees details, filters by session |
| 4 | DAG view with React Flow | User sees dependency graph, clicks nodes |
| 5 | Chat popover with simulated OP + UL demo | User interacts with OP, sees UL violation handling |
| 6 | Settings page | User sees project/auth/config forms |

---

## Phase 1: Project Scaffold + App Shell

**Goal**: Runnable app with sidebar navigation and routing
**Value**: "User can navigate between Home, DAG, and Settings pages via sidebar"
**Status**: Pending

### E2E Acceptance Test

```gherkin
Feature: App Shell
  Scenario: Navigate between pages
    Given the app is running
    When I visit the root URL
    Then I see a sidebar with Home, DAG, and Settings links
    And the Home page is active by default
    When I click "DAG" in the sidebar
    Then I see the DAG page
    When I click "Settings" in the sidebar
    Then I see the Settings page

  Scenario: Project switcher
    Given the app is running
    When I click the project switcher in the sidebar
    Then I see a list of mock projects
    When I select a project
    Then the project switcher shows the selected project name
```

### Tasks (TDD)

- [ ] **RED**: E2E test for sidebar navigation + project switcher
- [ ] **GREEN**: Scaffold Vite + React + TypeScript project with Bun
- [ ] **GREEN**: Install and configure Tailwind CSS + shadcn/ui
- [ ] **GREEN**: Install React Router, set up routes (/, /dag, /settings)
- [ ] **GREEN**: Build Sidebar component with nav links + project switcher dropdown
- [ ] **GREEN**: Build Layout component (sidebar + main content area)
- [ ] **GREEN**: Create placeholder pages (Home, DAG, Settings)
- [ ] **REFACTOR**: Clean up, ensure consistent file structure

### Quality Gate

- [ ] E2E acceptance test passes
- [ ] `bun run build` succeeds
- [ ] Lint + type check pass
- [ ] App renders at localhost with working navigation

### Affected Files

```
package.json, vite.config.ts, tailwind.config.ts
src/main.tsx, src/App.tsx
src/components/layout/Sidebar.tsx
src/components/layout/Layout.tsx
src/pages/HomePage.tsx, src/pages/DagPage.tsx, src/pages/SettingsPage.tsx
src/data/mock-projects.ts
e2e/app-shell.spec.ts
```

---

## Phase 2: Mock Data + Home View (HI Queue + Kanban)

**Goal**: Home page shows global HI queue and project-scoped Kanban board
**Value**: "User sees pending HI items at top, Kanban board with issues across 7 columns below"
**Status**: Pending

### E2E Acceptance Test

```gherkin
Feature: Home View
  Scenario: HI queue displays items
    Given the app is running on Home page
    Then I see the HI queue section with pending items
    And each HI item shows project name and prompt text

  Scenario: Kanban board shows issues
    Given the app is running on Home page
    Then I see a Kanban board with 7 columns
    And columns are: Discussing, To Do, In Progress, Verifying, Done, Failed, Deferred
    And each column contains issue cards with titles
    And cards are color-coded by session
```

### Tasks (TDD)

- [ ] **RED**: E2E test for HI queue + Kanban rendering
- [ ] **RED**: Unit tests for mock data structure validation
- [ ] **GREEN**: Create comprehensive mock data (projects, issues, HI items, sessions)
- [ ] **GREEN**: Build HiQueueItem component
- [ ] **GREEN**: Build HiQueue component (list of items)
- [ ] **GREEN**: Build KanbanCard component (issue card with session color)
- [ ] **GREEN**: Build KanbanColumn component
- [ ] **GREEN**: Build KanbanBoard component (7 columns, maps statuses)
- [ ] **GREEN**: Integrate HI queue + Kanban into HomePage
- [ ] **REFACTOR**: Extract shared types, clean up

### Quality Gate

- [ ] E2E acceptance test passes
- [ ] All unit tests pass
- [ ] Build succeeds
- [ ] Lint + type check pass

### Affected Files

```
src/data/mock-data.ts (projects, issues, hi-items, sessions)
src/types/index.ts (Project, Issue, HiItem, Session, IssueStatus, KanbanColumn)
src/components/hi-queue/HiQueueItem.tsx
src/components/hi-queue/HiQueue.tsx
src/components/kanban/KanbanCard.tsx
src/components/kanban/KanbanColumn.tsx
src/components/kanban/KanbanBoard.tsx
src/pages/HomePage.tsx
e2e/home-view.spec.ts
```

---

## Phase 3: Issue Detail Modal + Kanban Interactions

**Goal**: Clickable Kanban cards with detail modal and session filtering
**Value**: "User clicks a card, sees issue details in a modal; can filter Kanban by session"
**Status**: Pending

### E2E Acceptance Test

```gherkin
Feature: Issue Detail Modal
  Scenario: Open modal from Kanban
    Given the app is on the Home page
    When I click an issue card on the Kanban board
    Then I see a modal with issue title, status, type, and description
    And the modal shows PR link and verification status
    When I close the modal
    Then the modal disappears

  Scenario: Filter by session
    Given the app is on the Home page
    When I select a session filter
    Then only issues from that session are shown on the Kanban
    When I clear the filter
    Then all issues are shown again
```

### Tasks (TDD)

- [ ] **RED**: E2E test for modal open/close + filter
- [ ] **GREEN**: Build IssueDetailModal component (uses shadcn Dialog)
- [ ] **GREEN**: Add click handler to KanbanCard → opens modal
- [ ] **GREEN**: Build SessionFilter component (dropdown)
- [ ] **GREEN**: Wire filter state to KanbanBoard (show/hide cards)
- [ ] **REFACTOR**: Clean up state management

### Quality Gate

- [ ] E2E acceptance test passes
- [ ] All unit tests pass
- [ ] Build succeeds
- [ ] Lint + type check pass

### Affected Files

```
src/components/kanban/IssueDetailModal.tsx
src/components/kanban/SessionFilter.tsx
src/components/kanban/KanbanBoard.tsx (filter logic)
src/components/kanban/KanbanCard.tsx (click handler)
e2e/issue-detail.spec.ts
```

---

## Phase 4: DAG View with React Flow

**Goal**: Interactive dependency graph with clickable nodes
**Value**: "User sees issue dependency graph on DAG page, clicks nodes to see details"
**Status**: Pending

### E2E Acceptance Test

```gherkin
Feature: DAG View
  Scenario: Render dependency graph
    Given the app is on the DAG page
    Then I see a React Flow graph with issue nodes and dependency edges
    And nodes show issue number and title
    And edges show dependency direction

  Scenario: Click node opens detail
    Given the app is on the DAG page
    When I click a node
    Then I see the issue detail modal

  Scenario: Cross-project nodes
    Given the app is on the DAG page
    Then external dependency nodes are visually dimmed
```

### Tasks (TDD)

- [ ] **RED**: E2E test for DAG rendering + node click
- [ ] **GREEN**: Install and configure React Flow
- [ ] **GREEN**: Create mock DAG data (nodes + edges from mock issues)
- [ ] **GREEN**: Build DagNode custom component (issue info + status color)
- [ ] **GREEN**: Build DagPage with React Flow canvas
- [ ] **GREEN**: Add node click → issue detail modal (reuse from Phase 3)
- [ ] **GREEN**: Style external nodes as dimmed
- [ ] **REFACTOR**: Layout algorithm tuning

### Quality Gate

- [ ] E2E acceptance test passes
- [ ] All unit tests pass
- [ ] Build succeeds
- [ ] Lint + type check pass

### Affected Files

```
src/data/mock-dag.ts
src/components/dag/DagNode.tsx
src/components/dag/DagEdge.tsx
src/pages/DagPage.tsx
e2e/dag-view.spec.ts
```

---

## Phase 5: Chat Popover with Simulated OP + UL Demo

**Goal**: Chat popover with scripted OP conversation demonstrating interaction pattern and UL violation
**Value**: "User opens chat, interacts with simulated OP who asks one question at a time with options, and flags an unknown domain term"
**Status**: Pending

### E2E Acceptance Test

```gherkin
Feature: Chat Popover
  Scenario: Open via HI item
    Given the app is on the Home page
    When I click an HI queue item
    Then the chat popover opens
    And I see the OP conversation with the HI context

  Scenario: Open manually
    Given the app is on any page
    When I click the chat icon in the nav
    Then the chat popover opens

  Scenario: OP interaction pattern
    Given the chat popover is open
    Then I see OP's message with a question
    And I see option buttons (recommended first) and a custom input field
    When I click an option
    Then OP responds with the next question

  Scenario: UL violation detection
    Given the chat popover is open with a simulated conversation
    Then at some point OP flags an unknown domain term
    And asks "You said '<term>'. Did you mean '<existing UL term>' or is this a new concept?"
    And provides options: existing term, define new, skip
```

### Tasks (TDD)

- [ ] **RED**: E2E test for chat popover open/close + OP interaction
- [ ] **GREEN**: Create scripted conversation data (messages, options, UL violation)
- [ ] **GREEN**: Build ChatMessage component (OP message vs user message)
- [ ] **GREEN**: Build ChatOptions component (option buttons + custom input)
- [ ] **GREEN**: Build ChatPopover component (popover panel, message list, input)
- [ ] **GREEN**: Build conversation state machine (step through scripted messages)
- [ ] **GREEN**: Wire HI queue item click → open popover with context
- [ ] **GREEN**: Add chat icon to sidebar/nav for manual open
- [ ] **GREEN**: Implement UL violation step in scripted conversation
- [ ] **REFACTOR**: Polish animations, transitions

### Quality Gate

- [ ] E2E acceptance test passes
- [ ] All unit tests pass
- [ ] Build succeeds
- [ ] Lint + type check pass

### Affected Files

```
src/data/mock-conversations.ts
src/components/chat/ChatMessage.tsx
src/components/chat/ChatOptions.tsx
src/components/chat/ChatPopover.tsx
src/hooks/useChatConversation.ts
src/components/layout/Sidebar.tsx (chat icon)
src/components/hi-queue/HiQueueItem.tsx (click → open chat)
e2e/chat-popover.spec.ts
```

---

## Phase 6: Settings Page

**Goal**: Settings forms for projects, auth, and config
**Value**: "User sees forms for managing projects, auth tokens, and autopilot configuration"
**Status**: Pending

### E2E Acceptance Test

```gherkin
Feature: Settings Page
  Scenario: View settings sections
    Given the app is on the Settings page
    Then I see sections: Projects, Authentication, Configuration

  Scenario: Project management form
    Given the app is on the Settings page
    Then I see a list of mock projects with remove buttons
    And I see an "Add Project" form with name and remote URL fields

  Scenario: Auth inputs
    Given the app is on the Settings page
    Then I see input fields for Claude Code token and GitHub PAT
    And token fields are masked (password type)

  Scenario: Config inputs
    Given the app is on the Settings page
    Then I see inputs for concurrency limit and confidence threshold
```

### Tasks (TDD)

- [ ] **RED**: E2E test for settings page sections and forms
- [ ] **GREEN**: Build ProjectList component (list + remove button)
- [ ] **GREEN**: Build AddProjectForm component (name + URL inputs)
- [ ] **GREEN**: Build AuthSettings component (token inputs)
- [ ] **GREEN**: Build ConfigSettings component (number inputs)
- [ ] **GREEN**: Compose SettingsPage with all sections
- [ ] **REFACTOR**: Consistent form styling

### Quality Gate

- [ ] E2E acceptance test passes
- [ ] All unit tests pass
- [ ] Build succeeds
- [ ] Lint + type check pass

### Affected Files

```
src/components/settings/ProjectList.tsx
src/components/settings/AddProjectForm.tsx
src/components/settings/AuthSettings.tsx
src/components/settings/ConfigSettings.tsx
src/pages/SettingsPage.tsx
e2e/settings.spec.ts
```

---

## Architecture Notes

### Project Structure

```
src/
├── components/
│   ├── layout/      (Sidebar, Layout)
│   ├── hi-queue/    (HiQueue, HiQueueItem)
│   ├── kanban/      (KanbanBoard, KanbanCard, KanbanColumn, SessionFilter, IssueDetailModal)
│   ├── dag/         (DagNode, DagEdge)
│   ├── chat/        (ChatPopover, ChatMessage, ChatOptions)
│   └── settings/    (ProjectList, AddProjectForm, AuthSettings, ConfigSettings)
├── data/            (mock data files)
├── hooks/           (custom hooks)
├── pages/           (HomePage, DagPage, SettingsPage)
├── types/           (TypeScript types)
├── lib/             (shadcn/ui utils)
└── main.tsx
e2e/                 (Playwright tests)
```

### State Management

In-memory React state only (useState/useContext). No backend persistence. Mock data loaded at startup.

### Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| shadcn/ui setup complexity | L | M | Follow official Vite guide |
| React Flow layout issues | M | M | Use dagre for auto-layout |
| Chat state machine complexity | M | L | Keep scripted, no real AI |
