import { useState } from "react";
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";
import { KANBAN_COLUMNS, mockIssues, mockSessions } from "@/data/mock-data";
import type { Issue } from "@/types";
import KanbanColumn from "./KanbanColumn";
import SessionFilter from "./SessionFilter";
import IssueDetailModal from "./IssueDetailModal";

interface KanbanBoardProps {
  projectId: string;
}

export default function KanbanBoard({ projectId }: KanbanBoardProps) {
  const [selectedSession, setSelectedSession] = useState("all");
  const [selectedIssue, setSelectedIssue] = useState<Issue | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  const projectSessions = mockSessions.filter(
    (s) => s.projectId === projectId
  );

  const projectIssues = mockIssues.filter((i) => {
    if (i.projectId !== projectId) return false;
    if (selectedSession !== "all" && i.sessionId !== selectedSession) return false;
    return true;
  });

  const getColumnIssues = (statuses: string[]): Issue[] =>
    projectIssues.filter((issue) => statuses.includes(issue.status));

  const handleCardClick = (issue: Issue) => {
    setSelectedIssue(issue);
    setModalOpen(true);
  };

  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold tracking-tight">Board</h2>
        <SessionFilter
          sessions={projectSessions}
          value={selectedSession}
          onChange={setSelectedSession}
        />
      </div>

      <ScrollArea className="w-full">
        <div className="flex gap-3 pb-4">
          {KANBAN_COLUMNS.map((col) => (
            <KanbanColumn
              key={col.id}
              config={col}
              issues={getColumnIssues(col.statuses)}
              onCardClick={handleCardClick}
            />
          ))}
        </div>
        <ScrollBar orientation="horizontal" />
      </ScrollArea>

      <IssueDetailModal
        issue={selectedIssue}
        open={modalOpen}
        onOpenChange={setModalOpen}
      />
    </section>
  );
}
