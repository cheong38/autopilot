import { Badge } from "@/components/ui/badge";
import { mockProjects } from "@/data/mock-projects";
import { useApp } from "@/context/AppContext";
import type { HiItem } from "@/types";

function timeAgo(dateStr: string): string {
  const now = new Date();
  const date = new Date(dateStr);
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);

  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDays = Math.floor(diffHr / 24);
  return `${diffDays}d ago`;
}

interface HiQueueItemProps {
  item: HiItem;
}

export default function HiQueueItem({ item }: HiQueueItemProps) {
  const project = mockProjects.find((p) => p.id === item.projectId);
  const { openChatForHiItem } = useApp();

  const handleClick = () => {
    openChatForHiItem(item.id);
  };

  return (
    <button
      onClick={handleClick}
      className="hover-lift group flex w-full items-start gap-3 rounded-lg border border-amber-200 bg-card p-3 text-left transition-all duration-150 hover:border-amber-300 hover:bg-amber-50/50 dark:border-amber-800/50 dark:hover:border-amber-700/60 dark:hover:bg-amber-950/30"
    >
      {/* Pulse indicator for pending items */}
      <div className="mt-1.5 flex shrink-0 items-center">
        <span className="relative flex size-2.5">
          <span className="absolute inline-flex size-full animate-ping rounded-full bg-amber-400 opacity-75" />
          <span className="relative inline-flex size-2.5 rounded-full bg-amber-500" />
        </span>
      </div>

      <div className="flex min-w-0 flex-1 flex-col gap-1.5">
        <div className="flex items-center gap-2">
          <Badge variant="secondary" className="shrink-0 text-xs font-normal">
            {project?.name ?? "Unknown"}
          </Badge>
          <span className="font-technical text-[11px] text-muted-foreground">
            {timeAgo(item.createdAt)}
          </span>
        </div>
        <p className="text-sm font-medium leading-snug text-foreground line-clamp-2">
          {item.promptText}
        </p>
        <div className="flex flex-wrap gap-1.5">
          {item.options.map((opt) => (
            <Badge
              key={opt.action}
              variant={opt.recommended ? "default" : "outline"}
              className="text-xs font-normal transition-colors"
            >
              {opt.label}
            </Badge>
          ))}
        </div>
      </div>
    </button>
  );
}
