"use client";

import { useQueryClient } from "@tanstack/react-query";
import { Play } from "lucide-react";
import { useEffect, useRef } from "react";
import type { RunRecord } from "@/src/entities/run/model";
import { runQueryOptions, useCreateRunMutation } from "@/src/entities/run/query";
import { trajectoryQueryOptions } from "@/src/entities/trajectory/query";
import { Button } from "@/src/shared/ui/Button";

const RUN_POLL_INTERVAL_MS = 500;

type Props = {
  prompt: string;
  agentType: string;
  model: string;
  tools: string;
  latestRunId: string;
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

function formatRunLog({
  run,
  agentType,
  prompt,
  tools
}: {
  run: RunRecord;
  agentType: string;
  prompt: string;
  tools: string;
}) {
  const lines = [
    `run_id: ${run.runId}`,
    `agent: ${agentType}`,
    `model: ${run.model}`,
    `prompt: ${prompt}`,
    `tools: ${tools}`,
    `status: ${run.status}`,
    `token_cost: ${run.tokenCost}`,
    `latency_ms: ${run.latencyMs}`
  ];

  if (run.terminationReason) {
    lines.push(`termination_reason: ${run.terminationReason}`);
  }

  return lines.join("\n");
}

export function ManualRunActions({
  prompt,
  agentType,
  model,
  tools,
  latestRunId,
  onLatestRunChange,
  onLogChange
}: Props) {
  const queryClient = useQueryClient();
  const createRunMutation = useCreateRunMutation();
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
    const steps = await queryClient.fetchQuery(trajectoryQueryOptions(run.runId));

    if (requestId !== activeRunPollRef.current) {
      return;
    }

    const baseLog = formatRunLog({ run, agentType, prompt, tools });
    onLogChange(
      steps.length
        ? [baseLog, "", "trace:", ...steps.map((step) => `${step.id} | ${step.stepType} | ${step.output}`)].join("\n")
        : `${baseLog}\n\nNo trajectory found for ${run.runId}`
    );
  };

  const pollRunUntilTerminal = async (runId: string, requestId: number) => {
    while (requestId === activeRunPollRef.current) {
      const run = await queryClient.fetchQuery(runQueryOptions(runId));

      if (requestId !== activeRunPollRef.current) {
        return null;
      }

      onLogChange(`${formatRunLog({ run, agentType, prompt, tools })}\n\nWaiting for run completion...`);

      if (isTerminalStatus(run.status)) {
        return run;
      }

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
        dataset: "crm-v2",
        model,
        agentType: agentType === "LangChain" ? "langchain" : "openai-agents-sdk",
        inputSummary: prompt.slice(0, 80),
        prompt,
        tags: tools
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean)
      });

      if (requestId !== activeRunPollRef.current) {
        return;
      }

      onLatestRunChange(run.runId);
      onLogChange(`${formatRunLog({ run, agentType, prompt, tools })}\n\nWaiting for run completion...`);

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

  return (
    <div className="toolbar" style={{ marginTop: 12 }}>
      <Button onClick={runManual}>
        <Play size={14} /> Run now
      </Button>
      <Button variant="ghost" onClick={() => navigator.clipboard?.writeText(latestRunId)}>
        Save snapshot
      </Button>
      <Button
        variant="ghost"
        onClick={async () => {
          if (!latestRunId) return;
          const run = await queryClient.fetchQuery(runQueryOptions(latestRunId));
          await syncTraceLog({ run, requestId: activeRunPollRef.current });
        }}
      >
        Open latest trace
      </Button>
    </div>
  );
}
