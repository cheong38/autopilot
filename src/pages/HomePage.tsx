import { useApp } from "@/context/AppContext";
import HiQueue from "@/components/hi-queue/HiQueue";
import KanbanBoard from "@/components/kanban/KanbanBoard";

export default function HomePage() {
  const { currentProject } = useApp();

  return (
    <div className="flex flex-col gap-6 p-6">
      <HiQueue />
      <KanbanBoard projectId={currentProject.id} />
    </div>
  );
}
