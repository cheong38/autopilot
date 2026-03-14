import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";
import { KANBAN_COLUMNS, mockIssues } from "@/data/mock-data";
import type { Issue } from "@/types";
import KanbanColumn from "./KanbanColumn";

interface KanbanBoardProps {
  projectId: string;
}

export default function KanbanBoard({ projectId }: KanbanBoardProps) {
  const projectIssues = mockIssues.filter((i) => i.projectId === projectId);

  const getColumnIssues = (statuses: string[]): Issue[] =>
    projectIssues.filter((issue) =>
      statuses.includes(issue.status)
    );

  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-sm font-semibold tracking-tight">Board</h2>

      <ScrollArea className="w-full">
        <div className="flex gap-3 pb-4">
          {KANBAN_COLUMNS.map((col) => (
            <KanbanColumn
              key={col.id}
              config={col}
              issues={getColumnIssues(col.statuses)}
            />
          ))}
        </div>
        <ScrollBar orientation="horizontal" />
      </ScrollArea>
    </section>
  );
}
