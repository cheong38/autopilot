import { Badge } from "@/components/ui/badge";
import { MessageCircleWarning } from "lucide-react";
import { mockHiItems } from "@/data/mock-data";
import HiQueueItem from "./HiQueueItem";

export default function HiQueue() {
  const pendingItems = mockHiItems
    .filter((item) => item.status === "pending")
    .sort(
      (a, b) =>
        new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
    );

  if (pendingItems.length === 0) {
    return null;
  }

  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <MessageCircleWarning className="size-4 text-amber-500" />
        <h2 className="text-sm font-semibold tracking-tight">
          Human Intervention Queue
        </h2>
        <Badge
          variant="secondary"
          className="size-5 justify-center rounded-full p-0 text-xs font-semibold"
        >
          {pendingItems.length}
        </Badge>
      </div>

      <div className="flex flex-col gap-2">
        {pendingItems.map((item) => (
          <HiQueueItem key={item.id} item={item} />
        ))}
      </div>
    </section>
  );
}
