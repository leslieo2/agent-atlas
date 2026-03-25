"use client";

import ReactFlow, { Background, Controls, MiniMap, type Edge, type Node } from "reactflow";
import "reactflow/dist/style.css";
import { TableShell } from "@/src/shared/ui/TableShell";

export function TrajectoryGraph({ nodes, edges }: { nodes: Node[]; edges: Edge[] }) {
  return (
    <TableShell>
      <p className="muted-note" style={{ marginBottom: 8 }}>
        Step graph (React Flow)
      </p>
      <div className="flow-wrap">
        <ReactFlow nodes={nodes} edges={edges} zoomOnScroll fitView proOptions={{ hideAttribution: true }}>
          <Background />
          <Controls />
          <MiniMap />
        </ReactFlow>
      </div>
    </TableShell>
  );
}

