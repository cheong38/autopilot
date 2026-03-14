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

export type KanbanColumnId = "discussing" | "todo" | "in_progress" | "verifying" | "done" | "failed" | "deferred";

export interface KanbanColumnConfig {
  id: KanbanColumnId;
  title: string;
  statuses: IssueStatus[];
}
