"use client";

import { CheckCircle2, TriangleAlert, XCircle } from "lucide-react";
import type { EvalResult } from "@/src/entities/eval/model";
import type { TrajectoryStep } from "@/src/entities/trajectory/model";
import { Button } from "@/src/shared/ui/Button";
import { Notice } from "@/src/shared/ui/Notice";
import { TableShell } from "@/src/shared/ui/TableShell";

type Props = {
  rows: EvalResult[];
  failedCount: number;
  selectedSample: EvalResult | null;
  trajectorySteps: TrajectoryStep[];
  isDrilling: boolean;
  trajectoryError: string;
  message: string;
  onSelect: (row: EvalResult) => void;
};

export function SampleDrilldown({
  rows,
  failedCount,
  selectedSample,
  trajectorySteps,
  isDrilling,
  trajectoryError,
  message,
  onSelect
}: Props) {
  return (
    <div className="page-stack">
      <TableShell>
        <h3 className="panel-title">Failing samples ({failedCount})</h3>
        {rows
          .filter((row) => row.status === "fail" || row.status === "pass")
          .map((sample) => (
            <div key={`${sample.runId}-${sample.sampleId}`} className="step-item" style={{ marginBottom: 8 }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                <strong>{sample.sampleId}</strong>
                {sample.status === "pass" ? (
                  <CheckCircle2 size={16} color="#6effa6" />
                ) : (
                  <XCircle size={16} color="#ff7a87" />
                )}
              </div>
              <p className="muted-note">{sample.input}</p>
              <p className="muted-note">
                Run {sample.runId.slice(0, 8)} · score {sample.score}
              </p>
              <p className="muted-note">
                {sample.status === "fail" ? <TriangleAlert size={12} /> : null} {sample.reason ?? "no issues"}
              </p>
              <Button onClick={() => onSelect(sample)}>View trajectory</Button>
            </div>
          ))}
        {rows.length === 0 ? <Notice>Run an eval job to populate results.</Notice> : null}
        <Notice>{message}</Notice>
      </TableShell>

      <div className="layout-two" style={{ marginTop: 16 }}>
        <TableShell>
          <h3 className="panel-title">
            Trajectory drill-down
            {selectedSample ? ` · sample ${selectedSample.sampleId}` : ""}
          </h3>
          {isDrilling ? <Notice>Loading trajectory...</Notice> : null}
          {trajectoryError ? <Notice>{`Error: ${trajectoryError}`}</Notice> : null}
          {selectedSample && !isDrilling && !trajectoryError ? (
            <>
              <p className="muted-note" style={{ marginBottom: 8 }}>
                Run {selectedSample.runId} · input: {selectedSample.input}
              </p>
              <p className="muted-note" style={{ marginBottom: 8 }}>
                Status {selectedSample.status} · score {selectedSample.score}
                {selectedSample.reason ? ` · reason: ${selectedSample.reason}` : ""}
              </p>
              <div className="step-list">
                {trajectorySteps.length === 0 ? (
                  <Notice>No trajectory found for this run.</Notice>
                ) : (
                  trajectorySteps.map((step) => (
                    <div key={step.id} className="step-item">
                      <p>
                        {step.id} · {step.stepType.toUpperCase()} · {step.success ? "success" : "error"}
                      </p>
                      <p className="muted-note">
                        model: {step.model} · latency: {step.latencyMs}ms · tokens: {step.tokenUsage}
                      </p>
                      <p className="output-log mono" style={{ whiteSpace: "pre-wrap" }}>
                        {step.output}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </>
          ) : null}
          {!selectedSample ? <Notice>Select a sample row above to inspect trajectory details.</Notice> : null}
        </TableShell>
      </div>
    </div>
  );
}
