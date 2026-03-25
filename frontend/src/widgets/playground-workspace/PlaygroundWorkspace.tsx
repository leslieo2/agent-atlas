"use client";

import { ArrowUpRight } from "lucide-react";
import { useEffect, useState } from "react";
import { useRunsQuery } from "@/src/entities/run/query";
import { ManualRunActions } from "@/src/features/manual-run/ManualRunActions";
import { PlaygroundForm } from "@/src/features/playground-form/PlaygroundForm";
import { TraceLogPanel } from "@/src/features/trace-log/TraceLogPanel";
import { Button } from "@/src/shared/ui/Button";
import { MetricCard } from "@/src/shared/ui/MetricCard";
import { Panel } from "@/src/shared/ui/Panel";

export default function PlaygroundWorkspace() {
  const runsQuery = useRunsQuery();
  const [prompt, setPrompt] = useState("Draft a concise customer response for delayed shipping.");
  const [agentType, setAgentType] = useState("OpenAI Agents SDK");
  const [model, setModel] = useState("gpt-4.1-mini");
  const [tools, setTools] = useState("crm_lookup, pricing_service, policy_guard");
  const [latestRunId, setLatestRunId] = useState("");
  const [log, setLog] = useState("trace: waiting for manual run...\n");

  useEffect(() => {
    if (!latestRunId && runsQuery.data?.[0]) {
      setLatestRunId(runsQuery.data[0].runId);
    }
  }, [latestRunId, runsQuery.data]);

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Manual run</p>
          <h2 className="section-title">Playground</h2>
          <p className="kicker">Launch a single smoke run, inspect the output, and jump straight into its run workspace.</p>
        </div>
        <div className="toolbar">
          <Button variant="secondary" onClick={() => setPrompt("Can you create a shipping itinerary?")}>
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
        <MetricCard label="Latest run" value={latestRunId || "-"} />
        <MetricCard label="Tool chain" value={tools.split(",").length} />
      </div>

      <div className="workspace-grid workspace-grid-wide">
        <Panel tone="strong">
          <div className="surface-header">
            <div>
              <p className="surface-kicker">Run controls</p>
              <h3 className="panel-title">Prompt and runtime settings</h3>
            </div>
          </div>
          <PlaygroundForm
            prompt={prompt}
            agentType={agentType}
            model={model}
            tools={tools}
            onPromptChange={setPrompt}
            onAgentTypeChange={setAgentType}
            onModelChange={setModel}
            onToolsChange={setTools}
          />
          <ManualRunActions
            prompt={prompt}
            agentType={agentType}
            model={model}
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
