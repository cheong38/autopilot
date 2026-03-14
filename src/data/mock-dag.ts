export interface DagEdge {
  from: string; // issue id
  to: string;   // issue id
  type: "depends_on";
}

/**
 * DAG edges representing issue dependencies.
 * Direction: `from` blocks `to` (i.e. `to` depends on `from`).
 *
 * proj-1 (autopilot) internal dependencies:
 *   issue-5 (session color-coding discussion) -> issue-1 (UI prototype)
 *   issue-3 (dark mode toggle)               -> issue-1 (UI prototype)
 *   issue-1 (UI prototype)                   -> issue-2 (DAG visualization)
 *   issue-1 (UI prototype)                   -> issue-4 (sidebar bug)
 *   issue-6 (Tauri IPC bridge)               -> issue-7 (WebSocket events)
 *   issue-7 (WebSocket events)               -> issue-8 (session timeout)
 *
 * Cross-project dependency:
 *   issue-7 (WebSocket events, proj-1) -> issue-9 (payment endpoint v2, proj-2)
 *     e-commerce-api relies on the autopilot event stream for deployment triggers
 */
export const mockDagEdges: DagEdge[] = [
  // proj-1 internal chain: discussing -> implementing -> backlog / bug
  { from: "issue-5", to: "issue-1", type: "depends_on" },
  { from: "issue-3", to: "issue-1", type: "depends_on" },
  { from: "issue-1", to: "issue-2", type: "depends_on" },
  { from: "issue-1", to: "issue-4", type: "depends_on" },

  // proj-1 backend chain: ready -> merged -> failed
  { from: "issue-6", to: "issue-7", type: "depends_on" },
  { from: "issue-7", to: "issue-8", type: "depends_on" },

  // Cross-project: autopilot issue-7 blocks e-commerce issue-9
  { from: "issue-7", to: "issue-9", type: "depends_on" },

  // proj-2 internal chain
  { from: "issue-9",  to: "issue-10", type: "depends_on" },
  { from: "issue-9",  to: "issue-11", type: "depends_on" },
  { from: "issue-13", to: "issue-9",  type: "depends_on" },
  { from: "issue-10", to: "issue-12", type: "depends_on" },
];
