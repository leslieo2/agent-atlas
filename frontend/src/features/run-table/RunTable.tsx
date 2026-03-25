import Link from "next/link";
import type { RunRecord } from "@/src/entities/run/model";
import { formatRunDate } from "@/src/entities/run/presentation";
import { TableShell } from "@/src/shared/ui/TableShell";
import { StatusPill } from "@/src/shared/ui/StatusPill";

export function RunTable({ rows, message }: { rows: RunRecord[]; message: string }) {
  return (
    <TableShell plain>
      <table>
        <thead>
          <tr>
            <th>Run ID</th>
            <th>Input Summary</th>
            <th>Status</th>
            <th>Project</th>
            <th>Dataset</th>
            <th>Latency</th>
            <th>Tokens</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={8} className="muted-note">
                {message}
              </td>
            </tr>
          ) : (
            rows.map((run) => (
              <tr key={run.runId}>
                <td>
                  <Link className="table-link" href={`/runs/${run.runId}`}>
                    {run.runId}
                  </Link>
                </td>
                <td>{run.inputSummary}</td>
                <td>
                  <StatusPill
                    tone={run.status === "failed" ? "error" : run.status === "running" ? "warn" : "success"}
                  >
                    {run.status}
                  </StatusPill>
                </td>
                <td>{run.project}</td>
                <td>{run.dataset}</td>
                <td>{run.latencyMs ? `${run.latencyMs} ms` : "-"}</td>
                <td>{run.tokenCost.toLocaleString()}</td>
                <td>{formatRunDate(run.createdAt)}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </TableShell>
  );
}
