"use client";

import type { EvalResult } from "@/src/entities/eval/model";
import { TableShell } from "@/src/shared/ui/TableShell";

export function EvalResultsTable({
  rows,
  selectedSampleId,
  onSelect
}: {
  rows: EvalResult[];
  selectedSampleId?: string;
  onSelect: (row: EvalResult) => void;
}) {
  return (
    <TableShell>
      <h3 className="panel-title">Run comparison table</h3>
      <table>
        <thead>
          <tr>
            <th>Run ID</th>
            <th>Sample ID</th>
            <th>Success</th>
            <th>Score</th>
            <th>Reason</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={`${row.runId}-${row.sampleId}`}
              onClick={() => onSelect(row)}
              style={{
                cursor: "pointer",
                outline: selectedSampleId === row.sampleId ? "1px solid rgba(110, 255, 166, 0.6)" : "none"
              }}
            >
              <td>{row.runId.slice(0, 8)}</td>
              <td>{row.sampleId}</td>
              <td>{row.status === "pass" ? "pass" : "fail"}</td>
              <td>{row.score}</td>
              <td>{row.reason ?? "-"}</td>
              <td>{row.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </TableShell>
  );
}

