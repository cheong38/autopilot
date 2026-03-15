import { Badge } from "@/components/ui/badge";
import type { Issue, KanbanColumnConfig } from "@/types";
import KanbanCard from "./KanbanCard";

const columnBgStyles: Record<string, string> = {
  discussing: "bg-purple-500/5 dark:bg-purple-500/10",
  todo: "bg-slate-500/5 dark:bg-slate-500/10",
  in_progress: "bg-blue-500/5 dark:bg-blue-500/10",
  verifying: "bg-amber-500/5 dark:bg-amber-500/10",
  done: "bg-emerald-500/5 dark:bg-emerald-500/10",
  failed: "bg-rose-500/5 dark:bg-rose-500/10",
  deferred: "bg-slate-500/5 dark:bg-slate-500/10",
};

const columnCountColors: Record<string, string> = {
  discussing: "bg-purple-100 text-purple-700 dark:bg-purple-900/50 dark:text-purple-300",
  todo: "bg-slate-100 text-slate-700 dark:bg-slate-800/50 dark:text-slate-300",
  in_progress: "bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300",
  verifying: "bg-amber-100 text-amber-700 dark:bg-amber-900/50 dark:text-amber-300",
  done: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300",
  failed: "bg-rose-100 text-rose-700 dark:bg-rose-900/50 dark:text-rose-300",
  deferred: "bg-slate-100 text-slate-700 dark:bg-slate-800/50 dark:text-slate-300",
};

interface KanbanColumnProps {
  config: KanbanColumnConfig;
  issues: Issue[];
  onCardClick?: (issue: Issue) => void;
}

export default function KanbanColumn({ config, issues, onCardClick }: KanbanColumnProps) {
  return (
    <div
      className={`flex h-full w-64 shrink-0 flex-col rounded-xl border border-border/50 ${
        columnBgStyles[config.id] ?? "bg-muted/30"
      }`}
    >
      {/* Column header */}
      <div className="flex items-center gap-2 px-3 py-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {config.title}
        </h3>
        <Badge
          className={`size-5 justify-center rounded-full border-none p-0 text-[10px] font-bold ${
            columnCountColors[config.id] ?? "bg-muted text-muted-foreground"
          }`}
        >
          {issues.length}
        </Badge>
      </div>

      {/* Cards */}
      <div className="flex flex-1 flex-col gap-2 overflow-y-auto px-2 pb-2">
        {issues.map((issue) => (
          <KanbanCard key={issue.id} issue={issue} onClick={onCardClick} />
        ))}
        {issues.length === 0 && (
          <div className="flex flex-1 items-center justify-center py-8">
            <span className="text-xs text-muted-foreground/50">No issues</span>
          </div>
        )}
      </div>
    </div>
  );
}
