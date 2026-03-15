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
  session: "bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300",
  step: "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300",
  cli_call: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  tool_use: "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300",
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
  isLast,
}: {
  trace: AgentTrace;
  depth: number;
  globalStart: number;
  globalEnd: number;
  isLast: boolean;
}) {
  const [expanded, setExpanded] = useState(depth < 2);

  const hasChildren = trace.children && trace.children.length > 0;
  const indentPx = depth * 24;

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

  const waterfallColor = WATERFALL_COLORS[trace.level] ?? "#6b7280";

  return (
    <div>
      <div
        className="flex items-center gap-1.5 py-1.5 hover:bg-accent/30 transition-colors cursor-pointer group relative"
        style={{ paddingLeft: indentPx + 8 }}
        onClick={() => hasChildren && setExpanded(!expanded)}
      >
        {/* Tree connector lines */}
        {depth > 0 && (
          <>
            {/* Vertical connector from parent */}
            <span
              className="absolute border-l border-border/60 dark:border-border/40"
              style={{
                left: indentPx - 12 + 8,
                top: 0,
                height: isLast ? "50%" : "100%",
              }}
            />
            {/* Horizontal connector to node */}
            <span
              className="absolute border-t border-border/60 dark:border-border/40"
              style={{
                left: indentPx - 12 + 8,
                top: "50%",
                width: 12,
              }}
            />
          </>
        )}

        {/* Expand/collapse or spacer */}
        {hasChildren ? (
          expanded ? (
            <ChevronDown className="size-3.5 shrink-0 text-muted-foreground transition-transform" />
          ) : (
            <ChevronRight className="size-3.5 shrink-0 text-muted-foreground transition-transform" />
          )
        ) : (
          <span className="inline-block w-3.5 shrink-0" />
        )}

        {/* Level badge */}
        <Badge
          variant="secondary"
          className={`text-[10px] shrink-0 border-none ${LEVEL_COLORS[trace.level] ?? ""}`}
        >
          {trace.level}
        </Badge>

        {/* Label */}
        <span className="text-xs font-medium truncate max-w-[280px]">
          {trace.label}
        </span>

        {/* Duration */}
        <span className="flex items-center gap-0.5 font-technical text-[10px] text-muted-foreground ml-auto mr-2 shrink-0">
          <Clock className="size-2.5" />
          {formatDuration(trace.startedAt, trace.endedAt)}
        </span>

        {/* Waterfall bar with gradient */}
        <div className="relative w-[200px] h-4 shrink-0 bg-muted/30 dark:bg-muted/20 rounded-md overflow-hidden">
          <div
            className="absolute top-0.5 bottom-0.5 rounded-sm waterfall-bar"
            style={
              {
                left: `${barLeft}%`,
                width: `${barWidth}%`,
                "--waterfall-color": waterfallColor,
              } as React.CSSProperties
            }
          />
        </div>
      </div>

      {/* Children */}
      {expanded && hasChildren && (
        <div className="relative">
          {trace.children!.map((child, idx) => (
            <TraceNode
              key={child.id}
              trace={child}
              depth={depth + 1}
              globalStart={globalStart}
              globalEnd={globalEnd}
              isLast={idx === trace.children!.length - 1}
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
    <div className="rounded-xl border border-border bg-card shadow-sm">
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <h3 className="text-sm font-semibold">Trace View</h3>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          {Object.entries(LEVEL_COLORS).map(([level, cls]) => (
            <span key={level} className="flex items-center gap-1">
              <Badge variant="secondary" className={`text-[9px] px-1.5 py-0 border-none ${cls}`}>
                {level}
              </Badge>
            </span>
          ))}
        </div>
      </div>

      <ScrollArea className="h-[400px]">
        <div className="py-1">
          {displayTraces.length > 0 ? (
            displayTraces.map((trace, idx) => (
              <TraceNode
                key={trace.id}
                trace={trace}
                depth={0}
                globalStart={globalStart}
                globalEnd={globalEnd}
                isLast={idx === displayTraces.length - 1}
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
