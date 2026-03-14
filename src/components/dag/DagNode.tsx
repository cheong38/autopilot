import { memo } from "react";
import { Handle, Position, type NodeProps, type Node } from "@xyflow/react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { Issue, IssueStatus, IssueType } from "@/types";

const typeStyles: Record<IssueType, string> = {
  story: "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400",
  task: "bg-sky-500/10 text-sky-600 dark:text-sky-400",
  bug: "bg-rose-500/10 text-rose-600 dark:text-rose-400",
};

const statusColors: Record<IssueStatus, string> = {
  discussing: "bg-purple-400",
  backlog: "bg-slate-400",
  created: "bg-slate-500",
  ready: "bg-blue-400",
  implementing: "bg-amber-400",
  in_review: "bg-orange-400",
  merged: "bg-cyan-400",
  unit_verifying: "bg-teal-400",
  e2e_verifying: "bg-teal-500",
  done: "bg-emerald-500",
  failed: "bg-red-500",
  deferred: "bg-gray-400",
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

export type DagNodeData = {
  issue: Issue;
  sessionColor: string;
  isExternal: boolean;
};

type DagNodeType = Node<DagNodeData, "dagNode">;

function DagNodeComponent({ data }: NodeProps<DagNodeType>) {
  const { issue, sessionColor, isExternal } = data;

  const truncatedTitle =
    issue.title.length > 40 ? issue.title.slice(0, 40) + "..." : issue.title;

  return (
    <>
      <Handle type="target" position={Position.Top} className="!bg-border !w-2 !h-2" />

      <div
        className={cn(
          "w-[240px] rounded-lg border bg-card text-card-foreground shadow-sm transition-shadow hover:shadow-md cursor-pointer overflow-hidden",
          isExternal && "opacity-60 border-dashed border-muted-foreground/40"
        )}
      >
        {/* Session color bar */}
        <div
          className="h-1 w-full"
          style={{ backgroundColor: sessionColor }}
        />

        <div className="flex flex-col gap-1.5 p-3">
          {/* Header row: issue number + type badge */}
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground">
              #{issue.issueNumber}
              {isExternal && (
                <span className="ml-1 text-[10px] text-muted-foreground/70">
                  (ext)
                </span>
              )}
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
          <p className="text-sm font-medium leading-snug">{truncatedTitle}</p>

          {/* Status badge */}
          <div className="flex items-center gap-1.5">
            <span
              className={cn(
                "size-2 shrink-0 rounded-full",
                statusColors[issue.status]
              )}
            />
            <span className="text-[11px] text-muted-foreground">
              {statusLabels[issue.status]}
            </span>
          </div>
        </div>
      </div>

      <Handle type="source" position={Position.Bottom} className="!bg-border !w-2 !h-2" />
    </>
  );
}

export default memo(DagNodeComponent);
