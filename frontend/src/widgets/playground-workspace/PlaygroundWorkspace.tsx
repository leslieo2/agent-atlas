"use client";

import { ArrowUpRight } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useDatasetsQuery } from "@/src/entities/dataset/query";
import { useRunsQuery } from "@/src/entities/run/query";
import { ManualRunActions } from "@/src/features/manual-run/ManualRunActions";
import { PlaygroundForm } from "@/src/features/playground-form/PlaygroundForm";
import { TraceLogPanel } from "@/src/features/trace-log/TraceLogPanel";
import { Button } from "@/src/shared/ui/Button";
import { MetricCard } from "@/src/shared/ui/MetricCard";
import { Notice } from "@/src/shared/ui/Notice";
import { Panel } from "@/src/shared/ui/Panel";

function countSelectedTools(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean).length;
}

export default function PlaygroundWorkspace() {
  const datasetsQuery = useDatasetsQuery();
  const runsQuery = useRunsQuery();
  const [prompt, setPrompt] = useState("Draft a concise customer response for delayed shipping.");
  const [agentType, setAgentType] = useState("OpenAI Agents SDK");
  const [model, setModel] = useState("gpt-4.1-mini");
  const [dataset, setDataset] = useState("");
  const [tools, setTools] = useState("");
  const [latestRunId, setLatestRunId] = useState("");
  const [log, setLog] = useState("trace: waiting for manual run...\n");
  const datasets = useMemo(() => datasetsQuery.data?.map((item) => item.name) ?? [], [datasetsQuery.data]);

  useEffect(() => {
    if (!latestRunId && runsQuery.data?.[0]) {
      setLatestRunId(runsQuery.data[0].runId);
    }
  }, [latestRunId, runsQuery.data]);

  useEffect(() => {
    if (dataset && !datasets.includes(dataset)) {
      setDataset("");
    }
  }, [dataset, datasets]);

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Manual run</p>
          <h2 className="section-title">Playground</h2>
          <p className="kicker">Launch a single smoke run, inspect the output, and jump straight into its run workspace.</p>
        </div>
        <div className="toolbar">
          <Button variant="secondary" onClick={() => setPrompt("Can you create a shipping itinerary?")} disabled={!dataset}>
            Attach dataset sample
          </Button>
          {latestRunId ? (
            <Button href={`/runs/${latestRunId}`}>
              Open run workspace <ArrowUpRight size={14} />
            </Button>
          ) : null}
        </div>
      </header>

      <div className="summary-strip">
        <MetricCard label="Runtime" value={agentType} />
        <MetricCard label="Model" value={model} />
        <MetricCard label="Dataset" value={dataset || "-"} />
        <MetricCard label="Latest run" value={latestRunId || "-"} />
        <MetricCard label="Tool chain" value={countSelectedTools(tools)} />
      </div>

      <div className="workspace-grid workspace-grid-wide">
        <Panel tone="strong">
          <div className="surface-header">
            <div>
              <p className="surface-kicker">Run controls</p>
              <h3 className="panel-title">Prompt and runtime settings</h3>
            </div>
          </div>
          {!dataset ? <Notice>No dataset attached. Playground will run prompt-only until you select one.</Notice> : null}
          <PlaygroundForm
            prompt={prompt}
            agentType={agentType}
            model={model}
            dataset={dataset}
            datasets={datasets}
            tools={tools}
            onPromptChange={setPrompt}
            onAgentTypeChange={setAgentType}
            onModelChange={setModel}
            onDatasetChange={setDataset}
            onToolsChange={setTools}
          />
          <ManualRunActions
            prompt={prompt}
            agentType={agentType}
            model={model}
            dataset={dataset}
            tools={tools}
            latestRunId={latestRunId}
            onLatestRunChange={setLatestRunId}
            onLogChange={setLog}
          />
        </Panel>

        <Panel as="aside">
          <div className="surface-header">
            <div>
              <p className="surface-kicker">Trace output</p>
              <h3 className="panel-title">Execution output</h3>
            </div>
          </div>
          <TraceLogPanel log={log} />
        </Panel>
      </div>
    </section>
  );
}
