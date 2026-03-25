"use client";

import { ArrowLeft, RefreshCcw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { ReplayDiff } from "@/src/features/replay-diff/ReplayDiff";
import { ReplayEditor } from "@/src/features/replay-editor/ReplayEditor";
import { ReplaySourceSelector } from "@/src/features/replay-source-selector/ReplaySourceSelector";
import { PromoteReplayAction } from "@/src/features/promote-run/PromoteReplayAction";
import { useCreateReplayMutation, useRunsQuery, useTrajectoryQuery } from "@/src/shared/query/hooks";
import { Button } from "@/src/shared/ui/Button";
import { MetricCard } from "@/src/shared/ui/MetricCard";
import { Panel } from "@/src/shared/ui/Panel";

type Props = {
  runId?: string;
  initialStepId?: string;
};

export default function ReplayWorkspace({ runId, initialStepId }: Props = {}) {
  const runsQuery = useRunsQuery();
  const createReplayMutation = useCreateReplayMutation();
  const [selectedRun, setSelectedRun] = useState(runId ?? "");
  const [selectedStepId, setSelectedStepId] = useState(initialStepId ?? "");
  const [prompt, setPrompt] = useState("");
  const [toolPayload, setToolPayload] = useState('{\n  "carrier": "FedEx"\n}');
  const [model, setModel] = useState("gpt-4.1-mini");
  const [lastDiff, setLastDiff] = useState("Waiting for replay...");
  const runs = runsQuery.data ?? [];
  const trajectoryQuery = useTrajectoryQuery(selectedRun);
  const steps = trajectoryQuery.data ?? [];

  const candidate = steps.find((step) => step.id === selectedStepId) ?? null;

  useEffect(() => {
    if (runId) {
      setSelectedRun(runId);
    }
  }, [runId]);

  useEffect(() => {
    if (!runId && !selectedRun && runs[0]) {
      setSelectedRun(runs[0].runId);
    }
  }, [runId, runs, selectedRun]);

  useEffect(() => {
    const preferredStep =
      (initialStepId && steps.find((step) => step.id === initialStepId)?.id) ?? steps[0]?.id ?? "";

    setSelectedStepId(preferredStep);

    if (steps[0]) {
      const active = steps.find((step) => step.id === preferredStep) ?? steps[0];
      setPrompt(active.prompt);
      setModel(active.model);
    }
  }, [initialStepId, steps]);

  useEffect(() => {
    if (!candidate) return;
    setPrompt(candidate.prompt);
    setModel(candidate.model);
  }, [candidate, selectedStepId]);

  const modifiedOutput = useMemo(() => {
    if (!candidate) return "Select a step to replay.";
    return `Patched output:\n${candidate.output} -> with model ${model} and payload ${toolPayload.slice(0, 32)}...`;
  }, [candidate, model, toolPayload]);

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Replay</p>
          <h2 className="section-title">Step replay</h2>
          <p className="kicker">
            Replay a single trajectory step, compare the diff, and promote the patch into a candidate run.
          </p>
        </div>
        <div className="toolbar">
          <Button href={selectedRun ? `/runs/${selectedRun}` : "/runs"} variant="secondary">
            <ArrowLeft size={14} /> Open source run
          </Button>
          <Button
            disabled={createReplayMutation.isPending || !candidate}
            onClick={async () => {
              if (!candidate) return;
              try {
                const result = await createReplayMutation.mutateAsync({
                  runId: candidate.runId,
                  stepId: candidate.id,
                  editedPrompt: prompt,
                  model,
                  toolOverrides: JSON.parse(toolPayload),
                  rationale: "Replay from UI"
                });
                setLastDiff(result.diff || `Replay completed: ${result.replayId}`);
              } catch (error) {
                setLastDiff(error instanceof Error ? error.message : "Replay failed");
              }
            }}
          >
            <RefreshCcw size={14} /> Replay step
          </Button>
        </div>
      </header>

      <div className="summary-strip">
        <MetricCard label="Source run" value={candidate?.runId ?? (selectedRun || "-")} />
        <MetricCard label="Active step" value={candidate?.id ?? "-"} />
        <MetricCard label="Model" value={model} />
        <MetricCard label="Replay state" value={createReplayMutation.isPending ? "Running" : "Idle"} />
      </div>

      <div className="workspace-grid workspace-grid-wide">
        <Panel tone="strong">
          <div className="surface-header">
            <div>
              <p className="surface-kicker">Replay controls</p>
              <h3 className="panel-title">Choose the source step, patch prompt or tool payload, then replay</h3>
            </div>
          </div>

          <div className="two-col">
            <ReplaySourceSelector
              runIdLocked={Boolean(runId)}
              runs={runs}
              selectedRun={selectedRun}
              selectedStepId={selectedStepId}
              steps={steps}
              onRunChange={setSelectedRun}
              onStepChange={setSelectedStepId}
            />
            <div className="field">
              <ReplayEditor
                prompt={prompt}
                model={model}
                toolPayload={toolPayload}
                onPromptChange={setPrompt}
                onModelChange={setModel}
                onToolPayloadChange={setToolPayload}
              />
            </div>
          </div>
          <p className="muted-note" style={{ marginTop: 10 }}>
            Step: {candidate?.id ?? "-"} · Source run: {candidate?.runId ?? "-"} · Tool output baseline:
          </p>
          <p className="output-log mono">{candidate?.output ?? "No baseline output."}</p>
          <p className="muted-note">
            {createReplayMutation.isPending ? "Replay running..." : "Replay idle. The output diff updates after replay."}
          </p>
        </Panel>

        <Panel as="aside">
          <div className="surface-header">
            <div>
              <p className="surface-kicker">Diff workspace</p>
              <h3 className="panel-title">Prompt and output diff</h3>
            </div>
          </div>
          <ReplayDiff
            original={`Original:\n${candidate?.prompt ?? ""}\n\nOutput:\n${candidate?.output ?? ""}`}
            modified={`Replayed prompt:\n${prompt}\n\n${modifiedOutput}`}
            lastDiff={lastDiff}
          />
          <div className="toolbar" style={{ marginTop: 8 }}>
            <PromoteReplayAction
              candidate={candidate}
              model={model}
              prompt={prompt}
              lastDiff={lastDiff}
              onUpdated={setLastDiff}
            />
          </div>
        </Panel>
      </div>
    </section>
  );
}
