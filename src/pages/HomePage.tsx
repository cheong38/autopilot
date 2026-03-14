import { useApp } from "@/context/AppContext";
import HiQueue from "@/components/hi-queue/HiQueue";
import KanbanBoard from "@/components/kanban/KanbanBoard";
import AgentActivityPanel from "@/components/agents/AgentActivityPanel";

export default function HomePage() {
  const { currentProject } = useApp();

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 flex flex-col gap-6 overflow-auto p-6">
        <HiQueue />
        <KanbanBoard projectId={currentProject.id} />
      </div>
      <AgentActivityPanel />
    </div>
  );
}
