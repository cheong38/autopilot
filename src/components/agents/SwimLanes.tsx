import { useRef, useEffect, useMemo } from "react";
import type { AgentSession, AgentEvent } from "@/types";
import { mockIssues } from "@/data/mock-data";
import { mockProjects } from "@/data/mock-projects";

interface SwimLanesProps {
  sessions: AgentSession[];
  events: AgentEvent[];
}

const LANE_HEIGHT = 80;
const HEADER_WIDTH = 260;
const PADDING = 16;
const EVENT_RADIUS = 6;
const LANE_GAP = 8;

/** Map tool names to colors */
const TOOL_COLORS: Record<string, string> = {
  Read: "#3b82f6",
  Write: "#10b981",
  Edit: "#8b5cf6",
  Bash: "#f59e0b",
  Grep: "#06b6d4",
};

function getToolColor(toolName: string | null): string {
  if (!toolName) return "#6b7280";
  return TOOL_COLORS[toolName] ?? "#6b7280";
}

export default function SwimLanes({ sessions, events }: SwimLanesProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const activeSessions = useMemo(
    () => sessions.filter((s) => s.status === "running" || s.status === "queued"),
    [sessions]
  );

  // Compute time range from events
  const { minTime, maxTime } = useMemo(() => {
    const relevantSessionIds = new Set(activeSessions.map((s) => s.id));
    const relevantEvents = events.filter((e) => relevantSessionIds.has(e.agentSessionId));
    if (relevantEvents.length === 0) {
      const now = Date.now();
      return { minTime: now - 3600_000, maxTime: now };
    }
    const times = relevantEvents.map((e) => new Date(e.timestamp).getTime());
    const min = Math.min(...times);
    const max = Math.max(...times);
    // Add padding
    const range = max - min || 60_000;
    return { minTime: min - range * 0.05, maxTime: max + range * 0.1 };
  }, [activeSessions, events]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const width = canvas.clientWidth;
    const height = Math.max(
      activeSessions.length * (LANE_HEIGHT + LANE_GAP) + PADDING * 2,
      200
    );

    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.height = `${height}px`;
    ctx.scale(dpr, dpr);

    // Clear
    ctx.clearRect(0, 0, width, height);

    const timelineWidth = width - HEADER_WIDTH - PADDING * 2;
    const timeRange = maxTime - minTime;

    function timeToX(timestamp: string): number {
      const t = new Date(timestamp).getTime();
      return HEADER_WIDTH + PADDING + ((t - minTime) / timeRange) * timelineWidth;
    }

    activeSessions.forEach((session, idx) => {
      const y = PADDING + idx * (LANE_HEIGHT + LANE_GAP);

      // Lane background
      ctx.fillStyle = session.status === "queued" ? "#fef9c3" : "#f0f9ff";
      ctx.globalAlpha = 0.3;
      ctx.fillRect(0, y, width, LANE_HEIGHT);
      ctx.globalAlpha = 1;

      // Lane border
      ctx.strokeStyle = "#e5e7eb";
      ctx.lineWidth = 1;
      ctx.strokeRect(0, y, width, LANE_HEIGHT);

      // Session color indicator
      ctx.fillStyle = session.color;
      ctx.fillRect(0, y, 4, LANE_HEIGHT);

      // Header text
      const issue = mockIssues.find((i) => i.id === session.issueId);
      const project = mockProjects.find((p) => p.id === session.projectId);

      ctx.fillStyle = "#374151";
      ctx.font = "bold 12px 'Geist Variable', sans-serif";
      ctx.fillText(
        project?.name ?? "unknown",
        12,
        y + 20
      );

      ctx.fillStyle = "#6b7280";
      ctx.font = "11px 'Geist Variable', monospace";
      ctx.fillText(
        session.sessionId.slice(0, 20),
        12,
        y + 34
      );

      ctx.fillStyle = "#374151";
      ctx.font = "11px 'Geist Variable', sans-serif";
      const issueLabel = issue ? `#${issue.issueNumber} ${issue.title.slice(0, 24)}...` : "No issue";
      ctx.fillText(issueLabel, 12, y + 50);

      // Counters
      ctx.fillStyle = "#9ca3af";
      ctx.font = "10px 'Geist Variable', sans-serif";
      ctx.fillText(
        `${session.eventCount} events | ${session.toolCount} tools | ${session.model.split("-").slice(0, 2).join("-")}`,
        12,
        y + 66
      );

      // Timeline axis line
      ctx.strokeStyle = "#d1d5db";
      ctx.lineWidth = 1;
      ctx.beginPath();
      const laneMidY = y + LANE_HEIGHT / 2;
      ctx.moveTo(HEADER_WIDTH + PADDING, laneMidY);
      ctx.lineTo(width - PADDING, laneMidY);
      ctx.stroke();

      // Plot events for this session
      const sessionEvents = events.filter(
        (e) => e.agentSessionId === session.id
      );

      sessionEvents.forEach((event) => {
        const ex = timeToX(event.timestamp);
        const ey = laneMidY;

        // Draw event dot
        ctx.beginPath();
        ctx.arc(ex, ey, EVENT_RADIUS, 0, Math.PI * 2);
        ctx.fillStyle = getToolColor(event.toolName);
        ctx.fill();

        // Outline for hook vs orchestration
        if (event.source === "orchestration") {
          ctx.strokeStyle = "#1f2937";
          ctx.lineWidth = 2;
          ctx.stroke();
        }
      });
    });

    // Time axis labels
    const tickCount = 6;
    ctx.fillStyle = "#9ca3af";
    ctx.font = "10px 'Geist Variable', monospace";
    for (let i = 0; i <= tickCount; i++) {
      const t = minTime + (timeRange * i) / tickCount;
      const x = HEADER_WIDTH + PADDING + (timelineWidth * i) / tickCount;
      const date = new Date(t);
      const label = `${date.getUTCHours().toString().padStart(2, "0")}:${date.getUTCMinutes().toString().padStart(2, "0")}`;
      ctx.fillText(label, x - 14, PADDING + activeSessions.length * (LANE_HEIGHT + LANE_GAP) + 4);
    }
  }, [activeSessions, events, minTime, maxTime]);

  return (
    <div className="rounded-lg border border-border bg-card overflow-hidden">
      <div className="flex items-center justify-between border-b border-border px-4 py-2">
        <h3 className="text-sm font-semibold">Swim Lanes</h3>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          {Object.entries(TOOL_COLORS).map(([tool, color]) => (
            <span key={tool} className="flex items-center gap-1">
              <span
                className="inline-block size-2.5 rounded-full"
                style={{ backgroundColor: color }}
              />
              {tool}
            </span>
          ))}
          <span className="flex items-center gap-1">
            <span className="inline-block size-2.5 rounded-full bg-gray-500" />
            Other
          </span>
        </div>
      </div>
      <canvas
        ref={canvasRef}
        className="w-full"
        style={{ minHeight: 200 }}
      />
    </div>
  );
}
