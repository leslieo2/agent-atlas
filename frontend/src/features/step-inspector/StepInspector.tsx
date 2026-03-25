"use client";

import { ChevronDown, ChevronUp, Copy } from "lucide-react";
import type { TrajectoryStep } from "@/src/entities/trajectory/model";
import { Button } from "@/src/shared/ui/Button";
import { Notice } from "@/src/shared/ui/Notice";
import { Panel } from "@/src/shared/ui/Panel";
import { StatusPill } from "@/src/shared/ui/StatusPill";

type Props = {
  steps: TrajectoryStep[];
  focusedStepId: string;
  expanded: Record<string, boolean>;
  diffSummary: string;
  message: string;
  onToggleExpanded: (stepId: string) => void;
};

export function StepInspector({ steps, focusedStepId, expanded, diffSummary, message, onToggleExpanded }: Props) {
  return (
    <Panel as="aside">
      <div className="surface-header">
        <div>
          <p className="surface-kicker">Inspector</p>
          <h3 className="panel-title">Step detail list</h3>
        </div>
      </div>
      <div className="step-list">
        {steps.map((step) => (
          <div key={step.id} className={`step-item ${focusedStepId === step.id ? "active" : ""}`}>
            <Button variant="ghost" className="step-trigger" onClick={() => onToggleExpanded(step.id)}>
              {expanded[step.id] ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
              {step.id} · {step.stepType.toUpperCase()}
            </Button>
            {expanded[step.id] ? (
              <div className="step-detail">
                <p className="muted-note">{step.prompt}</p>
                <p>
                  <StatusPill tone={step.success ? "success" : "error"}>
                    {step.success ? "success" : "error"}
                  </StatusPill>
                </p>
                <p className="muted-note">
                  model: {step.model} · temp: {step.temperature} · latency: {step.latencyMs}ms
                </p>
                {step.toolName ? <p className="muted-note">tool: {step.toolName}</p> : null}
                <div className="output-log mono">{step.output}</div>
                <Button variant="ghost" onClick={() => navigator.clipboard?.writeText(step.id)}>
                  <Copy size={14} /> Copy step id
                </Button>
              </div>
            ) : null}
          </div>
        ))}
      </div>
      {diffSummary ? <pre className="output-log mono" style={{ marginTop: 10 }}>{diffSummary}</pre> : null}
      <Notice>{message}</Notice>
    </Panel>
  );
}

