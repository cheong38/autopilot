import { useMemo, useState, useCallback } from "react";
import {
  ReactFlow,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
  MarkerType,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import dagre from "@dagrejs/dagre";

import { useApp } from "@/context/AppContext";
import { mockIssues, mockSessions } from "@/data/mock-data";
import { mockDagEdges } from "@/data/mock-dag";
import DagNodeComponent, { type DagNodeData } from "@/components/dag/DagNode";
import IssueDetailModal from "@/components/kanban/IssueDetailModal";
import type { Issue } from "@/types";

const NODE_WIDTH = 240;
const NODE_HEIGHT = 100;

const nodeTypes = {
  dagNode: DagNodeComponent,
};

/** Use dagre to compute a top-to-bottom layout for the nodes. */
function layoutGraph(
  nodes: Node<DagNodeData>[],
  edges: Edge[]
): Node<DagNodeData>[] {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({
    rankdir: "TB",
    nodesep: 60,
    ranksep: 80,
    marginx: 40,
    marginy: 40,
  });

  for (const node of nodes) {
    g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  }

  for (const edge of edges) {
    g.setEdge(edge.source, edge.target);
  }

  dagre.layout(g);

  return nodes.map((node) => {
    const pos = g.node(node.id);
    return {
      ...node,
      position: {
        x: pos.x - NODE_WIDTH / 2,
        y: pos.y - NODE_HEIGHT / 2,
      },
    };
  });
}

export default function DagPage() {
  const { currentProject, isDark } = useApp();
  const [selectedIssue, setSelectedIssue] = useState<Issue | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  // Build the graph data from mock issues + edges, scoped to current project
  const { initialNodes, initialEdges } = useMemo(() => {
    // Issues belonging to the current project
    const projectIssues = mockIssues.filter(
      (i) => i.projectId === currentProject.id
    );
    const projectIssueIds = new Set(projectIssues.map((i) => i.id));

    // Find edges that touch at least one project issue
    const relevantEdges = mockDagEdges.filter(
      (e) => projectIssueIds.has(e.from) || projectIssueIds.has(e.to)
    );

    // Collect external issue IDs (from other projects but connected)
    const externalIssueIds = new Set<string>();
    for (const edge of relevantEdges) {
      if (!projectIssueIds.has(edge.from)) externalIssueIds.add(edge.from);
      if (!projectIssueIds.has(edge.to)) externalIssueIds.add(edge.to);
    }

    const externalIssues = mockIssues.filter((i) =>
      externalIssueIds.has(i.id)
    );

    // Build React Flow nodes
    const allIssues = [...projectIssues, ...externalIssues];
    const rfNodes: Node<DagNodeData>[] = allIssues.map((issue) => {
      const session = mockSessions.find((s) => s.id === issue.sessionId);
      return {
        id: issue.id,
        type: "dagNode",
        position: { x: 0, y: 0 }, // will be set by dagre
        data: {
          issue,
          sessionColor: session?.color ?? "#888",
          isExternal: externalIssueIds.has(issue.id),
        },
      };
    });

    // Build React Flow edges with theme-aware colors
    const edgeColor = isDark ? "rgba(148, 163, 184, 0.5)" : "var(--color-muted-foreground)";
    const rfEdges: Edge[] = relevantEdges.map((e, idx) => ({
      id: `edge-${idx}`,
      source: e.from,
      target: e.to,
      animated: true,
      style: { stroke: edgeColor, strokeWidth: 1.5 },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: edgeColor,
        width: 16,
        height: 16,
      },
    }));

    // Layout
    const laidOutNodes = layoutGraph(rfNodes, rfEdges);

    return { initialNodes: laidOutNodes, initialEdges: rfEdges };
  }, [currentProject.id, isDark]);

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      const issue = mockIssues.find((i) => i.id === node.id) ?? null;
      if (issue) {
        setSelectedIssue(issue);
        setModalOpen(true);
      }
    },
    []
  );

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="shrink-0 border-b px-6 py-4">
        <h1 className="text-lg font-semibold tracking-tight">
          Dependency Graph
        </h1>
        <p className="mt-0.5 text-sm text-muted-foreground">
          Issue dependencies for{" "}
          <span className="font-medium text-foreground">
            {currentProject.name}
          </span>
          . Dimmed nodes are cross-project dependencies.
        </p>
      </div>

      {/* React Flow Canvas */}
      <div className="relative flex-1">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.3}
          maxZoom={2}
          proOptions={{ hideAttribution: true }}
        >
          <Controls className="!bg-card !border-border !shadow-md !rounded-lg [&>button]:!bg-card [&>button]:!border-border [&>button]:!text-foreground hover:[&>button]:!bg-accent" />
          <MiniMap
            className="!bg-card !border-border !shadow-md !rounded-lg"
            nodeColor={(node) => {
              const data = node.data as DagNodeData;
              return data.sessionColor;
            }}
            maskColor={isDark ? "rgba(0, 0, 0, 0.3)" : "rgba(0, 0, 0, 0.1)"}
            pannable
            zoomable
          />
          <Background
            variant={BackgroundVariant.Dots}
            gap={20}
            size={1}
            color={isDark ? "rgba(255, 255, 255, 0.06)" : "var(--color-border)"}
          />
        </ReactFlow>
      </div>

      {/* Reuse the Kanban issue detail modal */}
      <IssueDetailModal
        issue={selectedIssue}
        open={modalOpen}
        onOpenChange={setModalOpen}
      />
    </div>
  );
}
