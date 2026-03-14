import { useState } from "react";
import { ChevronRight, ChevronDown, Clock } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { AgentTrace } from "@/types";

interface TraceTreeProps {
  traces: AgentTrace[];
  /** ID of the session to display; if null, shows all root traces */
  selectedSessionId: string | null;
}

const LEVEL_COLORS: Record<string, string> = {
  session: "bg-purple-100 text-purple-800",
  step: "bg-blue-100 text-blue-800",
  cli_call: "bg-amber-100 text-amber-800",
  tool_use: "bg-green-100 text-green-800",
};

const WATERFALL_COLORS: Record<string, string> = {
  session: "#8b5cf6",
  step: "#3b82f6",
  cli_call: "#f59e0b",
  tool_use: "#10b981",
};

function formatDuration(startedAt: string, endedAt: string | null): string {
  if (!endedAt) return "running...";
  const ms = new Date(endedAt).getTime() - new Date(startedAt).getTime();
  if (ms < 1_000) return `${ms}ms`;
  if (ms < 60_000) return `${(ms / 1_000).toFixed(1)}s`;
  const mins = Math.floor(ms / 60_000);
  const secs = Math.round((ms % 60_000) / 1_000);
  return `${mins}m ${secs}s`;
}

function TraceNode({
  trace,
  depth,
  globalStart,
  globalEnd,
}: {
  trace: AgentTrace;
  depth: number;
  globalStart: number;
  globalEnd: number;
}) {
  const [expanded, setExpanded] = useState(depth < 2);

  const hasChildren = trace.children && trace.children.length > 0;
  const indentPx = depth * 20;

  // Waterfall bar calculation
  const traceStart = new Date(trace.startedAt).getTime();
  const traceEnd = trace.endedAt
    ? new Date(trace.endedAt).getTime()
    : Date.now();
  const totalRange = globalEnd - globalStart || 1;
  const barLeft = ((traceStart - globalStart) / totalRange) * 100;
  const barWidth = Math.max(
    ((traceEnd - traceStart) / totalRange) * 100,
    0.5
  );

  return (
    <div>
      <div
        className="flex items-center gap-1 py-1 hover:bg-accent/30 transition-colors cursor-pointer group"
        style={{ paddingLeft: indentPx + 8 }}
        onClick={() => hasChildren && setExpanded(!expanded)}
      >
        {/* Expand/collapse or spacer */}
        {hasChildren ? (
          expanded ? (
            <ChevronDown className="size-3.5 shrink-0 text-muted-foreground" />
          ) : (
            <ChevronRight className="size-3.5 shrink-0 text-muted-foreground" />
          )
        ) : (
          <span className="inline-block w-3.5" />
        )}

        {/* Level badge */}
        <Badge
          variant="secondary"
          className={`text-[10px] shrink-0 ${LEVEL_COLORS[trace.level] ?? ""}`}
        >
          {trace.level}
        </Badge>

        {/* Label */}
        <span className="text-xs font-medium truncate max-w-[280px]">
          {trace.label}
        </span>

        {/* Duration */}
        <span className="flex items-center gap-0.5 text-[10px] text-muted-foreground ml-auto mr-2 shrink-0">
          <Clock className="size-2.5" />
          {formatDuration(trace.startedAt, trace.endedAt)}
        </span>

        {/* Waterfall bar */}
        <div className="relative w-[200px] h-3 shrink-0 bg-muted/40 rounded-sm overflow-hidden">
          <div
            className="absolute top-0 h-full rounded-sm opacity-80"
            style={{
              left: `${barLeft}%`,
              width: `${barWidth}%`,
              backgroundColor: WATERFALL_COLORS[trace.level] ?? "#6b7280",
            }}
          />
        </div>
      </div>

      {/* Children */}
      {expanded && hasChildren && (
        <div>
          {trace.children!.map((child) => (
            <TraceNode
              key={child.id}
              trace={child}
              depth={depth + 1}
              globalStart={globalStart}
              globalEnd={globalEnd}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function TraceTree({ traces, selectedSessionId }: TraceTreeProps) {
  const displayTraces = selectedSessionId
    ? traces.filter((t) => t.agentSessionId === selectedSessionId)
    : traces;

  // Compute global time range across all displayed traces
  const { globalStart, globalEnd } = (() => {
    let min = Infinity;
    let max = -Infinity;

    function walk(t: AgentTrace) {
      const s = new Date(t.startedAt).getTime();
      const e = t.endedAt ? new Date(t.endedAt).getTime() : Date.now();
      if (s < min) min = s;
      if (e > max) max = e;
      t.children?.forEach(walk);
    }

    displayTraces.forEach(walk);
    if (!isFinite(min)) {
      const now = Date.now();
      return { globalStart: now - 3600_000, globalEnd: now };
    }
    return { globalStart: min, globalEnd: max };
  })();

  return (
    <div className="rounded-lg border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border px-4 py-2">
        <h3 className="text-sm font-semibold">Trace View</h3>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          {Object.entries(LEVEL_COLORS).map(([level, cls]) => (
            <span key={level} className="flex items-center gap-1">
              <Badge variant="secondary" className={`text-[9px] px-1 py-0 ${cls}`}>
                {level}
              </Badge>
            </span>
          ))}
        </div>
      </div>

      <ScrollArea className="h-[400px]">
        <div className="py-1">
          {displayTraces.length > 0 ? (
            displayTraces.map((trace) => (
              <TraceNode
                key={trace.id}
                trace={trace}
                depth={0}
                globalStart={globalStart}
                globalEnd={globalEnd}
              />
            ))
          ) : (
            <p className="px-4 py-6 text-center text-sm text-muted-foreground">
              {selectedSessionId
                ? "No traces for selected session"
                : "Select an agent to view traces"}
            </p>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
