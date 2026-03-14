import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import { mockSessions } from "@/data/mock-data";
import type { Issue, IssueStatus } from "@/types";
import { ExternalLinkIcon, GitPullRequestIcon, CheckCircleIcon, XCircleIcon } from "lucide-react";

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

interface IssueDetailModalProps {
  issue: Issue | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function IssueDetailModal({
  issue,
  open,
  onOpenChange,
}: IssueDetailModalProps) {
  if (!issue) return null;

  const session = mockSessions.find((s) => s.id === issue.sessionId);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          {/* Title with type + status badges */}
          <div className="flex items-start gap-2">
            <div className="flex flex-1 flex-col gap-2">
              <div className="flex items-center gap-2">
                <Badge
                  className={cn(
                    "border-none text-[10px] font-medium uppercase tracking-wider",
                    typeStyles[issue.type]
                  )}
                >
                  {issue.type}
                </Badge>
                <Badge variant="outline" className="text-[10px] font-normal">
                  {statusLabels[issue.status]}
                </Badge>
              </div>
              <DialogTitle className="text-base leading-snug">
                {issue.title}
              </DialogTitle>
            </div>
          </div>

          {/* Issue number + link */}
          <DialogDescription asChild>
            <div className="flex items-center gap-1.5">
              <a
                href={issue.issueUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                #{issue.issueNumber}
                <ExternalLinkIcon className="size-3" />
              </a>
            </div>
          </DialogDescription>
        </DialogHeader>

        <Separator />

        {/* Description */}
        {issue.description && (
          <div className="flex flex-col gap-1.5">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Description
            </span>
            <p className="text-sm leading-relaxed text-foreground/90">
              {issue.description}
            </p>
          </div>
        )}

        {/* Details grid */}
        <div className="grid grid-cols-2 gap-3">
          {/* Session */}
          <div className="flex flex-col gap-1">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Session
            </span>
            <div className="flex items-center gap-2">
              <span
                className="size-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: session?.color ?? "#888" }}
              />
              <span className="text-sm">{session?.name ?? "Unknown"}</span>
            </div>
          </div>

          {/* Verification status */}
          <div className="flex flex-col gap-1">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Verification
            </span>
            <div className="flex items-center gap-1.5">
              {issue.verified ? (
                <>
                  <CheckCircleIcon className="size-4 text-emerald-500" />
                  <span className="text-sm text-emerald-600 dark:text-emerald-400">
                    Verified
                  </span>
                </>
              ) : (
                <>
                  <XCircleIcon className="size-4 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">
                    Not verified
                  </span>
                </>
              )}
            </div>
          </div>

          {/* PR link */}
          {issue.prNumber && (
            <div className="flex flex-col gap-1">
              <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Pull Request
              </span>
              <a
                href={issue.prUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                <GitPullRequestIcon className="size-3.5" />
                PR #{issue.prNumber}
                <ExternalLinkIcon className="size-3" />
              </a>
            </div>
          )}

          {/* Requirement IDs */}
          {issue.requirementIds && issue.requirementIds.length > 0 && (
            <div className="flex flex-col gap-1">
              <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Requirements
              </span>
              <div className="flex flex-wrap gap-1">
                {issue.requirementIds.map((reqId) => (
                  <Badge
                    key={reqId}
                    variant="secondary"
                    className="text-[10px] font-mono"
                  >
                    {reqId}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>

        <DialogFooter showCloseButton />
      </DialogContent>
    </Dialog>
  );
}
