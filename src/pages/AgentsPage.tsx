import { useState } from "react";
import { useApp } from "@/context/AppContext";
import { mockAgentSessions } from "@/data/mock-agent-sessions";
import { mockAgentEvents } from "@/data/mock-agent-events";
import { mockAgentTraces } from "@/data/mock-agent-traces";
import SwimLanes from "@/components/agents/SwimLanes";
import EventFeed from "@/components/agents/EventFeed";
import PulseChart from "@/components/agents/PulseChart";
import TraceTree from "@/components/agents/TraceTree";

export default function AgentsPage() {
  const { currentProject } = useApp();
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);

  // When inside a project view, scope to that project
  const scopedSessions = currentProject
    ? mockAgentSessions.filter((s) => s.projectId === currentProject.id)
    : mockAgentSessions;

  const scopedSessionIds = new Set(scopedSessions.map((s) => s.id));
  const scopedEvents = mockAgentEvents.filter((e) =>
    scopedSessionIds.has(e.agentSessionId)
  );

  return (
    <div className="flex flex-col gap-4 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">Agents</h1>
          <p className="text-sm text-muted-foreground">
            {currentProject
              ? `Scoped to ${currentProject.name}`
              : "Global view — all projects"}
          </p>
        </div>

        {/* Session selector for trace view */}
        <div className="flex items-center gap-2">
          <label className="text-xs text-muted-foreground">Trace session:</label>
          <select
            className="rounded border border-border bg-background px-2 py-1 text-xs"
            value={selectedSessionId ?? ""}
            onChange={(e) =>
              setSelectedSessionId(e.target.value || null)
            }
          >
            <option value="">All sessions</option>
            {scopedSessions.map((s) => (
              <option key={s.id} value={s.id}>
                {s.sessionId.slice(0, 20)} ({s.status})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Swim Lanes — canvas-based timeline */}
      <SwimLanes sessions={scopedSessions} events={scopedEvents} />

      {/* Middle row: Pulse Chart + Event Feed side by side */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <PulseChart events={scopedEvents} sessions={scopedSessions} />
        <EventFeed events={scopedEvents} projectId={currentProject?.id} />
      </div>

      {/* Trace Tree — expandable hierarchical view */}
      <TraceTree traces={mockAgentTraces} selectedSessionId={selectedSessionId} />
    </div>
  );
}
