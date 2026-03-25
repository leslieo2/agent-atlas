"use client";

import type { RunRecord } from "@/src/entities/run/model";
import type { TrajectoryStep } from "@/src/entities/trajectory/model";
import { Field } from "@/src/shared/ui/Field";

type Props = {
  runIdLocked: boolean;
  runs: RunRecord[];
  selectedRun: string;
  selectedStepId: string;
  steps: TrajectoryStep[];
  onRunChange: (value: string) => void;
  onStepChange: (value: string) => void;
};

export function ReplaySourceSelector({
  runIdLocked,
  runs,
  selectedRun,
  selectedStepId,
  steps,
  onRunChange,
  onStepChange
}: Props) {
  return (
    <div className="field">
      {!runIdLocked ? (
        <Field label="Run" htmlFor="step-replay-run">
          <select id="step-replay-run" value={selectedRun} onChange={(event) => onRunChange(event.target.value)}>
            {runs.map((run) => (
              <option key={run.runId} value={run.runId}>
                {run.runId} · {run.project}
              </option>
            ))}
          </select>
        </Field>
      ) : null}
      <Field label="Step" htmlFor="step-replay-step">
        <select id="step-replay-step" value={selectedStepId} onChange={(event) => onStepChange(event.target.value)}>
          {steps.map((step) => (
            <option key={step.id} value={step.id}>
              {step.id} · {step.stepType}
            </option>
          ))}
        </select>
      </Field>
    </div>
  );
}

