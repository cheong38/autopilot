import { useRef, useEffect, useState, useMemo } from "react";
import type { AgentEvent, AgentSession } from "@/types";

interface PulseChartProps {
  events: AgentEvent[];
  sessions: AgentSession[];
}

type TimeWindow = "1m" | "3m" | "5m" | "10m";

const WINDOW_MS: Record<TimeWindow, number> = {
  "1m": 60_000,
  "3m": 180_000,
  "5m": 300_000,
  "10m": 600_000,
};

const WINDOWS: TimeWindow[] = ["1m", "3m", "5m", "10m"];

export default function PulseChart({ events, sessions }: PulseChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [timeWindow, setTimeWindow] = useState<TimeWindow>("5m");

  // Use a fixed "now" based on the latest event for demo purposes
  const now = useMemo(() => {
    if (events.length === 0) return Date.now();
    return Math.max(...events.map((e) => new Date(e.timestamp).getTime())) + 60_000;
  }, [events]);

  const windowMs = WINDOW_MS[timeWindow];
  const bucketCount = 20;
  const bucketMs = windowMs / bucketCount;

  // Compute bucketed data
  const { toolBuckets, eventBuckets, activeBuckets } = useMemo(() => {
    const startTime = now - windowMs;
    const tBuckets = new Array<number>(bucketCount).fill(0);
    const eBuckets = new Array<number>(bucketCount).fill(0);
    const aBuckets = new Array<number>(bucketCount).fill(0);

    events.forEach((event) => {
      const et = new Date(event.timestamp).getTime();
      if (et < startTime || et > now) return;
      const idx = Math.min(
        Math.floor((et - startTime) / bucketMs),
        bucketCount - 1
      );
      eBuckets[idx]++;
      if (event.toolName) tBuckets[idx]++;
    });

    // Active agent count per bucket
    for (let i = 0; i < bucketCount; i++) {
      const bucketTime = startTime + i * bucketMs;
      aBuckets[i] = sessions.filter((s) => {
        const start = new Date(s.startedAt).getTime();
        const end = s.endedAt ? new Date(s.endedAt).getTime() : now;
        return start <= bucketTime + bucketMs && end >= bucketTime;
      }).length;
    }

    return { toolBuckets: tBuckets, eventBuckets: eBuckets, activeBuckets: aBuckets };
  }, [events, sessions, now, windowMs, bucketMs, bucketCount]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;

    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.scale(dpr, dpr);

    ctx.clearRect(0, 0, w, h);

    const padding = { top: 20, right: 16, bottom: 30, left: 40 };
    const chartW = w - padding.left - padding.right;
    const chartH = h - padding.top - padding.bottom;

    const maxVal = Math.max(
      ...eventBuckets,
      ...toolBuckets,
      ...activeBuckets,
      1
    );

    const barWidth = chartW / bucketCount;

    // Grid lines
    ctx.strokeStyle = "#e5e7eb";
    ctx.lineWidth = 0.5;
    const gridLines = 4;
    for (let i = 0; i <= gridLines; i++) {
      const y = padding.top + chartH - (chartH * i) / gridLines;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(w - padding.right, y);
      ctx.stroke();

      ctx.fillStyle = "#9ca3af";
      ctx.font = "10px 'Geist Variable', monospace";
      ctx.textAlign = "right";
      const label = Math.round((maxVal * i) / gridLines);
      ctx.fillText(String(label), padding.left - 6, y + 3);
    }

    // Event rate bars (background)
    ctx.globalAlpha = 0.3;
    eventBuckets.forEach((val, i) => {
      const x = padding.left + i * barWidth;
      const barH = (val / maxVal) * chartH;
      ctx.fillStyle = "#6366f1";
      ctx.fillRect(x + 1, padding.top + chartH - barH, barWidth - 2, barH);
    });
    ctx.globalAlpha = 1;

    // Tool call bars (foreground)
    toolBuckets.forEach((val, i) => {
      const x = padding.left + i * barWidth;
      const barH = (val / maxVal) * chartH;
      ctx.fillStyle = "#06b6d4";
      ctx.fillRect(
        x + barWidth * 0.15,
        padding.top + chartH - barH,
        barWidth * 0.7,
        barH
      );
    });

    // Active agent line
    ctx.strokeStyle = "#f59e0b";
    ctx.lineWidth = 2;
    ctx.beginPath();
    activeBuckets.forEach((val, i) => {
      const x = padding.left + i * barWidth + barWidth / 2;
      const y = padding.top + chartH - (val / maxVal) * chartH;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();

    // Active agent dots
    activeBuckets.forEach((val, i) => {
      const x = padding.left + i * barWidth + barWidth / 2;
      const y = padding.top + chartH - (val / maxVal) * chartH;
      ctx.beginPath();
      ctx.arc(x, y, 3, 0, Math.PI * 2);
      ctx.fillStyle = "#f59e0b";
      ctx.fill();
    });

    // X-axis time labels
    ctx.fillStyle = "#9ca3af";
    ctx.font = "10px 'Geist Variable', monospace";
    ctx.textAlign = "center";
    const startTime = now - windowMs;
    const labelInterval = Math.max(1, Math.floor(bucketCount / 5));
    for (let i = 0; i < bucketCount; i += labelInterval) {
      const t = new Date(startTime + i * bucketMs);
      const label = `${t.getUTCHours().toString().padStart(2, "0")}:${t.getUTCMinutes().toString().padStart(2, "0")}`;
      const x = padding.left + i * barWidth + barWidth / 2;
      ctx.fillText(label, x, h - padding.bottom + 16);
    }
  }, [eventBuckets, toolBuckets, activeBuckets, bucketCount, now, windowMs, bucketMs]);

  return (
    <div className="rounded-lg border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border px-4 py-2">
        <h3 className="text-sm font-semibold">Pulse Chart</h3>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <span className="inline-block size-2.5 rounded-sm bg-indigo-500 opacity-30" />
              Events
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-block size-2.5 rounded-sm bg-cyan-500" />
              Tools
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-block size-2.5 rounded-full bg-amber-500" />
              Active agents
            </span>
          </div>
          <div className="flex rounded-md border border-border overflow-hidden">
            {WINDOWS.map((w) => (
              <button
                key={w}
                className={`px-2 py-0.5 text-xs font-medium transition-colors ${
                  w === timeWindow
                    ? "bg-primary text-primary-foreground"
                    : "hover:bg-accent"
                }`}
                onClick={() => setTimeWindow(w)}
              >
                {w}
              </button>
            ))}
          </div>
        </div>
      </div>
      <canvas ref={canvasRef} className="w-full" style={{ height: 200 }} />
    </div>
  );
}
