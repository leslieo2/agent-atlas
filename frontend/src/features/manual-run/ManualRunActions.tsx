"use client";

import { useQueryClient } from "@tanstack/react-query";
import { Play } from "lucide-react";
import { useEffect, useRef } from "react";
import { useCreateRunMutation, useTerminateRunMutation, runQueryOptions } from "@/src/entities/run/query";
import type { RunRecord } from "@/src/entities/run/model";
import { traceQueryOptions } from "@/src/entities/trace/query";
import { trajectoryQueryOptions } from "@/src/entities/trajectory/query";
import { Button } from "@/src/shared/ui/Button";

const RUN_POLL_INTERVAL_MS = 500;

type Props = {
  prompt: string;
  agentId: string;
  agentName: string;
  dataset: string;
  latestRunId: string;
  latestRunStatus: RunRecord["status"] | null;
  onLatestRunChange: (value: string) => void;
  onLogChange: (value: string) => void;
};

function sleep(milliseconds: number) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, milliseconds);
  });
}

function isTerminalStatus(status: RunRecord["status"]) {
  return status === "succeeded" || status === "failed" || status === "terminated";
}

function isTerminableStatus(status: RunRecord["status"]) {
  return status === "queued" || status === "running";
}

function formatRunLog({
  run,
  agentId,
  agentName,
  prompt
}: {
  run: RunRecord;
  agentId: string;
  agentName: string;
  prompt: string;
}) {
  const lines = [
    `run_id: ${run.runId}`,
    `agent_id: ${agentId}`,
    `agent_name: ${agentName}`,
    `framework: ${run.agentType}`,
    `model: ${run.model}`,
    `prompt: ${prompt}`,
    `dataset: ${run.dataset ?? "-"}`,
    `status: ${run.status}`,
    `token_cost: ${run.tokenCost}`,
    `latency_ms: ${run.latencyMs}`
  ];

  if (run.terminationReason) {
    lines.push(`termination_reason: ${run.terminationReason}`);
  }

  return lines.join("\n");
}

function formatTraceValue(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }

  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

export function ManualRunActions({
  prompt,
  agentId,
  agentName,
  dataset,
  latestRunId,
  latestRunStatus,
  onLatestRunChange,
  onLogChange
}: Props) {
  const queryClient = useQueryClient();
  const createRunMutation = useCreateRunMutation();
  const terminateRunMutation = useTerminateRunMutation();
  const activeRunPollRef = useRef(0);

  useEffect(() => {
    return () => {
      activeRunPollRef.current += 1;
    };
  }, []);

  const syncTraceLog = async ({
    run,
    requestId
  }: {
    run: RunRecord;
    requestId: number;
  }) => {
    const traces = await queryClient.fetchQuery(traceQueryOptions(run.runId));

    if (requestId !== activeRunPollRef.current) {
      return;
    }

    const baseLog = formatRunLog({ run, agentId, agentName, prompt });
    if (traces.length) {
      onLogChange(
        [
          baseLog,
          "",
          "trace:",
          ...traces.map(
            (span) =>
              `${span.spanId} | ${span.stepType} | ${formatTraceValue(span.output.output ?? span.output)}`
          )
        ].join("\n")
      );
      return;
    }

    const steps = await queryClient.fetchQuery(trajectoryQueryOptions(run.runId));

    if (requestId !== activeRunPollRef.current) {
      return;
    }

    onLogChange(
      steps.length
        ? [baseLog, "", "trace:", ...steps.map((step) => `${step.id} | ${step.stepType} | ${step.output}`)].join("\n")
        : `${baseLog}\n\nNo trace or trajectory found for ${run.runId}`
    );
  };

  const pollRunUntilTerminal = async (runId: string, requestId: number) => {
    while (requestId === activeRunPollRef.current) {
      const run = await queryClient.fetchQuery(runQueryOptions(runId));

      if (requestId !== activeRunPollRef.current) {
        return null;
      }

      await syncTraceLog({ run, requestId });

      if (isTerminalStatus(run.status)) {
        return run;
      }

      onLogChange(`${formatRunLog({ run, agentId, agentName, prompt })}\n\nWaiting for run completion...`);
      await sleep(RUN_POLL_INTERVAL_MS);
    }

    return null;
  };

  const runManual = async () => {
    const requestId = activeRunPollRef.current + 1;
    activeRunPollRef.current = requestId;

    try {
      const run = await createRunMutation.mutateAsync({
        project: "playground",
        dataset: dataset || null,
        agentId,
        inputSummary: prompt.slice(0, 80),
        prompt
      });

      if (requestId !== activeRunPollRef.current) {
        return;
      }

      onLatestRunChange(run.runId);
      onLogChange(`${formatRunLog({ run, agentId, agentName, prompt })}\n\nWaiting for run completion...`);

      const finalRun = isTerminalStatus(run.status) ? run : await pollRunUntilTerminal(run.runId, requestId);

      if (!finalRun || requestId !== activeRunPollRef.current) {
        return;
      }

      await queryClient.invalidateQueries({ queryKey: ["runs"] });
      await syncTraceLog({ run: finalRun, requestId });
    } catch (error) {
      if (requestId !== activeRunPollRef.current) {
        return;
      }

      onLogChange(error instanceof Error ? error.message : "Failed to start manual run.");
    }
  };

  const refreshLiveTrace = async () => {
    if (!latestRunId) return;

    try {
      const run = await queryClient.fetchQuery(runQueryOptions(latestRunId));
      await syncTraceLog({ run, requestId: activeRunPollRef.current });
    } catch (error) {
      onLogChange(error instanceof Error ? error.message : "Failed to refresh live trace.");
    }
  };

  const terminateLatestRun = async () => {
    if (!latestRunId) return;

    const requestId = activeRunPollRef.current + 1;
    activeRunPollRef.current = requestId;

    try {
      const run = await queryClient.fetchQuery(runQueryOptions(latestRunId));

      if (!isTerminableStatus(run.status)) {
        onLogChange(
          `${formatRunLog({ run, agentId, agentName, prompt })}\n\nRun ${run.runId} is already ${run.status} and can no longer be terminated.`
        );
        return;
      }

      const result = await terminateRunMutation.mutateAsync(latestRunId);

      if (requestId !== activeRunPollRef.current) {
        return;
      }

      onLogChange(
        `run_id: ${result.runId}\nstatus: ${result.status}\ntermination_reason: ${result.terminationReason ?? "terminated by user"}`
      );
    } catch (error) {
      if (requestId !== activeRunPollRef.current) {
        return;
      }

      onLogChange(error instanceof Error ? error.message : "Failed to terminate run.");
    }
  };

  return (
    <div className="toolbar" style={{ marginTop: 12 }}>
      <Button onClick={runManual}>
        <Play size={14} /> Run now
      </Button>
      <Button variant="ghost" onClick={() => navigator.clipboard?.writeText(latestRunId)}>
        Save snapshot
      </Button>
      <Button variant="ghost" onClick={refreshLiveTrace} disabled={!latestRunId}>
        Refresh live trace
      </Button>
      <Button
        variant="ghost"
        onClick={terminateLatestRun}
        disabled={
          !latestRunId ||
          terminateRunMutation.isPending ||
          createRunMutation.isPending ||
          (latestRunStatus !== null && !isTerminableStatus(latestRunStatus))
        }
      >
        Terminate run
      </Button>
    </div>
  );
}
