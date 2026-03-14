import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { mockSessions } from "@/data/mock-data";
import type { Issue, IssueStatus } from "@/types";

const typeStyles: Record<string, string> = {
  story: "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400",
  task: "bg-sky-500/10 text-sky-600 dark:text-sky-400",
  bug: "bg-rose-500/10 text-rose-600 dark:text-rose-400",
};

const statusLabels: Record<IssueStatus, string> = {
  discussing: "Discussing",
  backlog: "Backlog",
  created: "Created",
  ready: "Ready",
  implementing: "Implementing",
  in_review: "In Review",
  merged: "Merged",
  unit_verifying: "Unit Verifying",
  e2e_verifying: "E2E Verifying",
  done: "Done",
  failed: "Failed",
  deferred: "Deferred",
};

interface KanbanCardProps {
  issue: Issue;
  onClick?: (issue: Issue) => void;
}

export default function KanbanCard({ issue, onClick }: KanbanCardProps) {
  const session = mockSessions.find((s) => s.id === issue.sessionId);

  return (
    <Card
      className="cursor-pointer gap-0 overflow-hidden border-border py-0 transition-shadow hover:shadow-md"
      onClick={() => onClick?.(issue)}
    >
      {/* Session color bar */}
      <div
        className="h-1 w-full"
        style={{ backgroundColor: session?.color ?? "#888" }}
      />

      <div className="flex flex-col gap-2 p-3">
        {/* Header: issue number + type badge */}
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-muted-foreground">
            #{issue.issueNumber}
          </span>
          <Badge
            className={cn(
              "border-none text-[10px] font-medium uppercase tracking-wider",
              typeStyles[issue.type]
            )}
          >
            {issue.type}
          </Badge>
        </div>

        {/* Title */}
        <p className="text-sm font-medium leading-snug line-clamp-2">
          {issue.title}
        </p>

        {/* Status + verified */}
        <div className="flex items-center gap-1.5">
          <Badge variant="outline" className="text-[10px] font-normal">
            {statusLabels[issue.status]}
          </Badge>
          {issue.verified && (
            <Badge className="border-none bg-emerald-500/10 text-[10px] font-normal text-emerald-600 dark:text-emerald-400">
              Verified
            </Badge>
          )}
          {issue.prNumber && (
            <span className="text-[10px] text-muted-foreground">
              PR #{issue.prNumber}
            </span>
          )}
        </div>
      </div>
    </Card>
  );
}
