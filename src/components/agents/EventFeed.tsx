import { useState, useMemo } from "react";
import { ChevronRight, ChevronDown, Filter } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { AgentEvent } from "@/types";
import { mockAgentSessions } from "@/data/mock-agent-sessions";

interface EventFeedProps {
  events: AgentEvent[];
  projectId?: string;
}

const eventTypeColors: Record<string, string> = {
  session_start: "bg-green-100 text-green-800",
  session_end: "bg-gray-100 text-gray-800",
  PreToolUse: "bg-blue-100 text-blue-800",
  PostToolUse: "bg-indigo-100 text-indigo-800",
  SubagentStart: "bg-purple-100 text-purple-800",
  SubagentStop: "bg-purple-100 text-purple-800",
  hitl_blocked: "bg-yellow-100 text-yellow-800",
};

function formatTimestamp(ts: string): string {
  const d = new Date(ts);
  return d.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

export default function EventFeed({ events, projectId }: EventFeedProps) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [filterType, setFilterType] = useState<string | null>(null);
  const [filterSession, setFilterSession] = useState<string | null>(null);

  const filteredEvents = useMemo(() => {
    let result = [...events];

    if (projectId) {
      const sessionIds = new Set(
        mockAgentSessions
          .filter((s) => s.projectId === projectId)
          .map((s) => s.id)
      );
      result = result.filter((e) => sessionIds.has(e.agentSessionId));
    }

    if (filterType) {
      result = result.filter((e) => e.eventType === filterType);
    }
    if (filterSession) {
      result = result.filter((e) => e.agentSessionId === filterSession);
    }

    return result.sort(
      (a, b) =>
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );
  }, [events, projectId, filterType, filterSession]);

  const eventTypes = useMemo(
    () => [...new Set(events.map((e) => e.eventType))],
    [events]
  );

  const sessionIds = useMemo(
    () => [...new Set(events.map((e) => e.agentSessionId))],
    [events]
  );

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div className="rounded-lg border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border px-4 py-2">
        <h3 className="text-sm font-semibold">Live Event Feed</h3>
        <div className="flex items-center gap-2">
          <Filter className="size-3.5 text-muted-foreground" />
          {/* Event type filter */}
          <select
            className="rounded border border-border bg-background px-2 py-0.5 text-xs"
            value={filterType ?? ""}
            onChange={(e) =>
              setFilterType(e.target.value || null)
            }
          >
            <option value="">All types</option>
            {eventTypes.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
          {/* Session filter */}
          <select
            className="rounded border border-border bg-background px-2 py-0.5 text-xs"
            value={filterSession ?? ""}
            onChange={(e) =>
              setFilterSession(e.target.value || null)
            }
          >
            <option value="">All sessions</option>
            {sessionIds.map((id) => {
              const session = mockAgentSessions.find((s) => s.id === id);
              return (
                <option key={id} value={id}>
                  {session?.sessionId.slice(0, 16) ?? id}
                </option>
              );
            })}
          </select>
        </div>
      </div>

      <ScrollArea className="h-[320px]">
        <div className="divide-y divide-border">
          {filteredEvents.map((event) => {
            const isExpanded = expandedIds.has(event.id);
            const session = mockAgentSessions.find(
              (s) => s.id === event.agentSessionId
            );
            return (
              <div key={event.id} className="px-4 py-2">
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full justify-start gap-2 px-0 h-auto py-1"
                  onClick={() => toggleExpand(event.id)}
                >
                  {isExpanded ? (
                    <ChevronDown className="size-3.5 shrink-0 text-muted-foreground" />
                  ) : (
                    <ChevronRight className="size-3.5 shrink-0 text-muted-foreground" />
                  )}
                  <span className="text-xs font-mono text-muted-foreground w-16 shrink-0 text-left">
                    {formatTimestamp(event.timestamp)}
                  </span>
                  {session && (
                    <span
                      className="inline-block size-2 rounded-full shrink-0"
                      style={{ backgroundColor: session.color }}
                    />
                  )}
                  <Badge
                    variant="secondary"
                    className={`text-[10px] ${eventTypeColors[event.eventType] ?? "bg-gray-100 text-gray-800"}`}
                  >
                    {event.eventType}
                  </Badge>
                  {event.toolName && (
                    <span className="text-xs font-medium">{event.toolName}</span>
                  )}
                  <span className="text-xs text-muted-foreground truncate">
                    {event.source === "orchestration" ? "[orch]" : "[hook]"}
                  </span>
                </Button>
                {isExpanded && (
                  <pre className="ml-7 mt-1 rounded bg-muted p-2 text-xs font-mono overflow-x-auto whitespace-pre-wrap">
                    {JSON.stringify(event.payload, null, 2)}
                  </pre>
                )}
              </div>
            );
          })}
          {filteredEvents.length === 0 && (
            <p className="px-4 py-6 text-center text-sm text-muted-foreground">
              No events match the current filters
            </p>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
