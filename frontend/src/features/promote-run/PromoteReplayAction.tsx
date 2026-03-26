"use client";

import type { ReplayResult } from "@/src/entities/replay/model";
import type { RunRecord } from "@/src/entities/run/model";
import type { TrajectoryStep } from "@/src/entities/trajectory/model";
import { useCreateRunMutation } from "@/src/entities/run/query";
import { Button } from "@/src/shared/ui/Button";

type Props = {
  candidate: TrajectoryStep | null;
  sourceRun: RunRecord | null;
  replayResult: ReplayResult | null;
  model: string;
  prompt: string;
  toolOverrides: Record<string, unknown>;
  lastDiff: string;
  onUpdated: (value: string) => void;
  onCandidateCreated: (runId: string) => void;
};

function buildCandidateProjectMetadata({
  candidate,
  sourceRun,
  replayResult,
  model,
  lastDiff
}: {
  candidate: TrajectoryStep;
  sourceRun: RunRecord;
  replayResult: ReplayResult;
  model: string;
  lastDiff: string;
}) {
  return {
    candidate: {
      kind: "replay",
      replayId: replayResult.replayId,
      sourceRunId: replayResult.runId,
      sourceStepId: replayResult.stepId,
      baselineModel: candidate.model,
      replayModel: model,
      diff: lastDiff
    },
    sourceRun: {
      project: sourceRun.project,
      dataset: sourceRun.dataset,
      model: sourceRun.model,
      agentType: sourceRun.agentType
    }
  };
}

export function PromoteReplayAction({
  candidate,
  sourceRun,
  replayResult,
  model,
  prompt,
  toolOverrides,
  lastDiff,
  onUpdated,
  onCandidateCreated
}: Props) {
  const createRunMutation = useCreateRunMutation();
  const canCreateCandidate = Boolean(candidate && sourceRun && replayResult);

  return (
    <>
      <Button
        variant="ghost"
        disabled={!canCreateCandidate || createRunMutation.isPending}
        onClick={async () => {
          if (!candidate || !sourceRun || !replayResult) return;
          const run = await createRunMutation.mutateAsync({
            project: sourceRun.project,
            dataset: sourceRun.dataset,
            model,
            agentType: sourceRun.agentType,
            inputSummary: `Replay candidate from ${candidate.id}`,
            prompt,
            tags: Array.from(new Set([...sourceRun.tags, "candidate", "replay"])),
            toolConfig: toolOverrides,
            projectMetadata: buildCandidateProjectMetadata({
              candidate,
              sourceRun,
              replayResult,
              model,
              lastDiff
            })
          });
          onCandidateCreated(run.runId);
          onUpdated(`Saved replay as candidate run ${run.runId}`);
        }}
      >
        Save as candidate run
      </Button>
      <Button variant="ghost" onClick={() => navigator.clipboard?.writeText(lastDiff)}>
        Copy replay diff
      </Button>
    </>
  );
}
