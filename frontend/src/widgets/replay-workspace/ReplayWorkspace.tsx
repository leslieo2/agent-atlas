"use client";

import { ArrowLeft, RefreshCcw } from "lucide-react";
import { useEffect, useState } from "react";
import { useCreateReplayMutation } from "@/src/entities/replay/query";
import type { ReplayResult } from "@/src/entities/replay/model";
import { useRunsQuery } from "@/src/entities/run/query";
import type { TrajectoryStep } from "@/src/entities/trajectory/model";
import { useTrajectoryQuery } from "@/src/entities/trajectory/query";
import { ReplayDiff } from "@/src/features/replay-diff/ReplayDiff";
import { ReplayEditor } from "@/src/features/replay-editor/ReplayEditor";
import { ReplaySourceSelector } from "@/src/features/replay-source-selector/ReplaySourceSelector";
import { PromoteReplayAction } from "@/src/features/promote-run/PromoteReplayAction";
import { Button } from "@/src/shared/ui/Button";
import { MetricCard } from "@/src/shared/ui/MetricCard";
import { Notice } from "@/src/shared/ui/Notice";
import { Panel } from "@/src/shared/ui/Panel";

type Props = {
  runId?: string;
  initialStepId?: string;
};

function resolveReplayModel(step: TrajectoryStep | null, runModel?: string) {
  if (!step) {
    return runModel ?? "gpt-4.1-mini";
  }

  return step.stepType === "llm" ? (step.model ?? runModel ?? "gpt-4.1-mini") : (runModel ?? step.model ?? "gpt-4.1-mini");
}

export default function ReplayWorkspace({ runId, initialStepId }: Props = {}) {
  const runsQuery = useRunsQuery();
  const createReplayMutation = useCreateReplayMutation();
  const [selectedRun, setSelectedRun] = useState(runId ?? "");
  const [selectedStepId, setSelectedStepId] = useState(initialStepId ?? "");
  const [prompt, setPrompt] = useState("");
  const [toolPayload, setToolPayload] = useState('{\n  "carrier": "FedEx"\n}');
  const [model, setModel] = useState("gpt-4.1-mini");
  const [lastDiff, setLastDiff] = useState("Waiting for replay...");
  const [latestReplay, setLatestReplay] = useState<ReplayResult | null>(null);
  const [latestCandidateRunId, setLatestCandidateRunId] = useState("");
  const runs = runsQuery.data ?? [];
  const trajectoryQuery = useTrajectoryQuery(selectedRun);
  const steps = trajectoryQuery.data ?? [];

  const selectedRunRecord = runs.find((run) => run.runId === selectedRun) ?? null;
  const replayUnsupported = Boolean(selectedRunRecord?.agentId);
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
      setModel(resolveReplayModel(active, selectedRunRecord?.model));
    }
  }, [initialStepId, selectedRunRecord?.model, steps]);

  useEffect(() => {
    if (!candidate) return;
    setPrompt(candidate.prompt);
    setModel(resolveReplayModel(candidate, selectedRunRecord?.model));
  }, [candidate, selectedRunRecord?.model, selectedStepId]);

  useEffect(() => {
    setLatestReplay(null);
    setLastDiff("Waiting for replay...");
    setLatestCandidateRunId("");
  }, [selectedRun, selectedStepId]);

  const activeReplay = latestReplay?.stepId === candidate?.id && latestReplay?.runId === candidate?.runId ? latestReplay : null;
  const replayedPrompt = activeReplay?.updatedPrompt ?? prompt;
  const replayedOutput = activeReplay?.replayOutput ?? "Run replay to generate output.";
  const evalHref =
    selectedRunRecord && latestCandidateRunId
      ? selectedRunRecord.dataset
        ? `/evals?runIds=${selectedRunRecord.runId},${latestCandidateRunId}&dataset=${selectedRunRecord.dataset}`
        : `/evals?runIds=${selectedRunRecord.runId},${latestCandidateRunId}`
      : "";

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
          {evalHref && !replayUnsupported ? (
            <Button href={evalHref} variant="secondary">
              Compare in eval
            </Button>
          ) : null}
          <Button
            disabled={createReplayMutation.isPending || !candidate || replayUnsupported}
            onClick={async () => {
              if (!candidate) return;
              try {
                const parsedToolOverrides = JSON.parse(toolPayload) as Record<string, unknown>;
                const result = await createReplayMutation.mutateAsync({
                  runId: candidate.runId,
                  stepId: candidate.id,
                  editedPrompt: prompt,
                  model,
                  toolOverrides: parsedToolOverrides,
                  rationale: "Replay from UI"
                });
                setLatestReplay(result);
                setLastDiff(result.diff || `Replay completed: ${result.replayId}`);
              } catch (error) {
                setLatestReplay(null);
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
        <MetricCard label="Agent ID" value={selectedRunRecord?.agentId ?? "-"} />
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
          {replayUnsupported ? <Notice>Replay is not supported for registered agent runs in v1.</Notice> : null}

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
            modified={`Replayed prompt:\n${replayedPrompt}\n\nOutput:\n${replayedOutput}`}
            lastDiff={lastDiff}
          />
          <p className="muted-note" style={{ marginTop: 8 }}>
            Latest replay output
          </p>
          <div className="output-log mono">{replayedOutput}</div>
          <div className="toolbar" style={{ marginTop: 8 }}>
            <PromoteReplayAction
              candidate={candidate}
              sourceRun={selectedRunRecord}
              replayResult={activeReplay}
              model={model}
              prompt={prompt}
              toolOverrides={(() => {
                try {
                  return JSON.parse(toolPayload) as Record<string, unknown>;
                } catch {
                  return {};
                }
              })()}
              lastDiff={lastDiff}
              onUpdated={setLastDiff}
              onCandidateCreated={setLatestCandidateRunId}
            />
          </div>
          {latestCandidateRunId ? (
            <p className="muted-note" style={{ marginTop: 8 }}>
              Candidate run {latestCandidateRunId.slice(0, 8)} is ready for eval comparison.
            </p>
          ) : null}
        </Panel>
      </div>
    </section>
  );
}
