import { Badge } from "@/components/ui/badge";
import type { Issue, KanbanColumnConfig } from "@/types";
import KanbanCard from "./KanbanCard";

const columnBgStyles: Record<string, string> = {
  discussing: "bg-purple-500/5",
  todo: "bg-slate-500/5",
  in_progress: "bg-blue-500/5",
  verifying: "bg-amber-500/5",
  done: "bg-emerald-500/5",
  failed: "bg-rose-500/5",
  deferred: "bg-slate-500/5",
};

interface KanbanColumnProps {
  config: KanbanColumnConfig;
  issues: Issue[];
}

export default function KanbanColumn({ config, issues }: KanbanColumnProps) {
  return (
    <div
      className={`flex h-full w-64 shrink-0 flex-col rounded-lg ${
        columnBgStyles[config.id] ?? "bg-muted/30"
      }`}
    >
      {/* Column header */}
      <div className="flex items-center gap-2 px-3 py-2.5">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {config.title}
        </h3>
        <Badge
          variant="secondary"
          className="size-5 justify-center rounded-full p-0 text-[10px] font-semibold"
        >
          {issues.length}
        </Badge>
      </div>

      {/* Cards */}
      <div className="flex flex-1 flex-col gap-2 overflow-y-auto px-2 pb-2">
        {issues.map((issue) => (
          <KanbanCard key={issue.id} issue={issue} />
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
