export type IssueStatus =
  | "discussing" | "backlog" | "created" | "ready"
  | "implementing" | "in_review" | "merged"
  | "unit_verifying" | "e2e_verifying" | "done"
  | "failed" | "deferred";

export type IssueType = "story" | "task" | "bug";
export type Provider = "github" | "gitlab" | "jira";

export interface Project {
  id: string;
  name: string;
  remoteUrl: string;
  provider: Provider;
}

export interface Issue {
  id: string;
  projectId: string;
  issueNumber: number;
  issueUrl: string;
  title: string;
  type: IssueType;
  status: IssueStatus;
  verified: boolean;
  prNumber?: number;
  prUrl?: string;
  sessionId: string;
  description?: string;
  requirementIds?: string[];
}

export interface HiItem {
  id: string;
  projectId: string;
  issueId?: string;
  promptText: string;
  options: { label: string; action: string; recommended?: boolean }[];
  status: "pending" | "answered" | "expired";
  response?: string;
  createdAt: string;
}

export interface Session {
  id: string;
  projectId: string;
  name: string;
  color: string;
}

// Chat types
export interface ChatMessage {
  id: string;
  role: "op" | "user";
  content: string;
  timestamp: string;
  options?: ChatOption[];
  ulViolation?: {
    unknownTerm: string;
    suggestedTerm?: string;
  };
}

export interface ChatOption {
  label: string;
  value: string;
  recommended?: boolean;
}

export interface Conversation {
  id: string;
  projectId: string;
  hiItemId?: string;
  messages: ChatMessage[];
  status: "active" | "resolved";
}

export type KanbanColumnId = "discussing" | "todo" | "in_progress" | "verifying" | "done" | "failed" | "deferred";

export interface KanbanColumnConfig {
  id: KanbanColumnId;
  title: string;
  statuses: IssueStatus[];
}

// Agent observability types

export type AgentSessionStatus = "queued" | "running" | "completed" | "failed";

export interface AgentSession {
  id: string;
  projectId: string;
  issueId: string | null;
  sessionId: string;
  status: AgentSessionStatus;
  currentStep: string;
  startedAt: string;
  endedAt: string | null;
  slotIndex: number;
  /** Color assigned for visual identification */
  color: string;
  /** Model used (e.g. "claude-sonnet-4-20250514") */
  model: string;
  /** Running counters */
  eventCount: number;
  toolCount: number;
}

export type AgentEventSource = "orchestration" | "hook";

export interface AgentEvent {
  id: string;
  agentSessionId: string;
  source: AgentEventSource;
  eventType: string;
  toolName: string | null;
  payload: Record<string, unknown>;
  timestamp: string;
}

export type AgentTraceLevel = "session" | "step" | "cli_call" | "tool_use";

export interface AgentTrace {
  id: string;
  agentSessionId: string;
  parentTraceId: string | null;
  level: AgentTraceLevel;
  label: string;
  startedAt: string;
  endedAt: string | null;
  metadata: Record<string, unknown>;
  children?: AgentTrace[];
}
