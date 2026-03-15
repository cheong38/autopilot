import { useState, useMemo } from "react";
import { ChevronUp, ChevronDown, Bot, Clock, Cpu } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { mockAgentSessions } from "@/data/mock-agent-sessions";
import { mockIssues } from "@/data/mock-data";

function formatElapsed(startedAt: string): string {
  const ms = Date.now() - new Date(startedAt).getTime();
  const mins = Math.floor(ms / 60_000);
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  return `${hrs}h ${mins % 60}m`;
}

const statusColors: Record<string, string> = {
  running: "bg-green-500",
  queued: "bg-yellow-500",
  completed: "bg-blue-500",
  failed: "bg-red-500",
};

export default function AgentActivityPanel() {
  const [expanded, setExpanded] = useState(true);

  const summary = useMemo(() => {
    const running = mockAgentSessions.filter((s) => s.status === "running").length;
    const queued = mockAgentSessions.filter((s) => s.status === "queued").length;
    const totalSlots = 3;
    return { running, queued, totalSlots };
  }, []);

  const activeSessions = useMemo(
    () =>
      mockAgentSessions.filter(
        (s) => s.status === "running" || s.status === "queued"
      ),
    []
  );

  return (
    <div className="border-t border-border bg-card">
      {/* Header bar */}
      <button
        className="flex w-full items-center justify-between px-4 py-2.5 text-sm font-medium hover:bg-accent/50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <Bot className="size-4 text-muted-foreground" />
          <span>Agent Activity</span>
          <Badge
            variant="secondary"
            className="font-technical text-xs"
          >
            {summary.running}/{summary.totalSlots} active
            {summary.queued > 0 && ` | ${summary.queued} queued`}
          </Badge>
        </div>
        {expanded ? (
          <ChevronDown className="size-4 text-muted-foreground transition-transform" />
        ) : (
          <ChevronUp className="size-4 text-muted-foreground transition-transform" />
        )}
      </button>

      {/* Expandable content */}
      {expanded && (
        <div className="animate-panel-expand flex gap-3 overflow-x-auto px-4 pb-3">
          {activeSessions.map((session) => {
            const issue = mockIssues.find((i) => i.id === session.issueId);
            const isRunning = session.status === "running";
            return (
              <div
                key={session.id}
                className="hover-lift flex min-w-[220px] flex-col gap-1.5 rounded-lg border border-border bg-background p-3 transition-all duration-150"
                style={{ borderLeftColor: session.color, borderLeftWidth: 3 }}
              >
                <div className="flex items-center justify-between">
                  <span className="font-technical text-xs text-muted-foreground">
                    {issue ? `#${issue.issueNumber}` : session.sessionId.slice(0, 16)}
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span
                      className={`inline-block size-2 rounded-full ${statusColors[session.status]} ${
                        isRunning ? "animate-status-pulse" : ""
                      }`}
                    />
                    <span className="text-xs capitalize text-muted-foreground">
                      {session.status}
                    </span>
                  </span>
                </div>
                <p className="text-sm font-medium truncate">
                  {issue?.title ?? "Unknown issue"}
                </p>
                <div className="flex items-center gap-3 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <Cpu className="size-3" />
                    <span className="font-technical">{session.currentStep}</span>
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="size-3" />
                    <span className="font-technical">{formatElapsed(session.startedAt)}</span>
                  </span>
                </div>
              </div>
            );
          })}
          {activeSessions.length === 0 && (
            <p className="text-sm text-muted-foreground py-2">
              No active agents
            </p>
          )}

          {/* Quick link to Agents page */}
          <div className="flex items-center">
            <Button
              variant="ghost"
              size="sm"
              className="text-xs text-muted-foreground hover:text-foreground transition-colors"
              asChild
            >
              <a href="/agents">View all &rarr;</a>
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
