"use client";

import type { RunRecord } from "@/src/entities/run/model";
import { Button } from "@/src/shared/ui/Button";

type Props = {
  comparableRuns: RunRecord[];
  selectedRunId: string;
  onSelectedRunIdChange: (runId: string) => void;
  onCompare: () => Promise<void>;
};

export function ComparePreviousRunAction({
  comparableRuns,
  selectedRunId,
  onSelectedRunIdChange,
  onCompare
}: Props) {
  const disabled = comparableRuns.length === 0 || !selectedRunId;

  return (
    <>
      <label style={{ display: "grid", gap: 6 }}>
        <span className="page-info-label">Compare run</span>
        <select
          aria-label="Compare run"
          value={selectedRunId}
          disabled={comparableRuns.length === 0}
          onChange={(event) => onSelectedRunIdChange(event.target.value)}
        >
          {comparableRuns.length === 0 ? <option value="">No comparable runs</option> : null}
          {comparableRuns.map((run) => (
            <option key={run.runId} value={run.runId}>
              {run.runId} · {run.status} · {run.createdAt}
            </option>
          ))}
        </select>
      </label>
      <Button variant="ghost" onClick={onCompare} disabled={disabled}>
        Compare selected run
      </Button>
    </>
  );
}
