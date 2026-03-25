"use client";

import { Play } from "lucide-react";
import { createRun } from "@/src/entities/run/api";
import { getTrajectory } from "@/src/entities/trajectory/api";
import { Button } from "@/src/shared/ui/Button";

type Props = {
  prompt: string;
  agentType: string;
  model: string;
  tools: string;
  latestRunId: string;
  onLatestRunChange: (value: string) => void;
  onLogChange: (value: string) => void;
};

export function ManualRunActions({
  prompt,
  agentType,
  model,
  tools,
  latestRunId,
  onLatestRunChange,
  onLogChange
}: Props) {
  const runManual = async () => {
    const run = await createRun({
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

    onLatestRunChange(run.runId);
    onLogChange(
      [
        `run_id: ${run.runId}`,
        `agent: ${agentType}`,
        `model: ${model}`,
        `prompt: ${prompt}`,
        `tools: ${tools}`,
        `status: ${run.status}`,
        `token_cost: ${run.tokenCost}`,
        `latency_ms: ${run.latencyMs}`
      ].join("\n")
    );
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
          const steps = await getTrajectory(latestRunId);
          onLogChange(
            steps.length
              ? steps.map((step) => `${step.id} | ${step.stepType} | ${step.output}`).join("\n")
              : `No trajectory found for ${latestRunId}`
          );
        }}
      >
        Open latest trace
      </Button>
    </div>
  );
}

