"use client";

import { ArrowUpRight } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useAgentsQuery } from "@/src/entities/agent/query";
import { useDatasetsQuery } from "@/src/entities/dataset/query";
import { useRunsQuery } from "@/src/entities/run/query";
import { ManualRunActions } from "@/src/features/manual-run/ManualRunActions";
import { PlaygroundForm } from "@/src/features/playground-form/PlaygroundForm";
import { TraceLogPanel } from "@/src/features/trace-log/TraceLogPanel";
import { Button } from "@/src/shared/ui/Button";
import { MetricCard } from "@/src/shared/ui/MetricCard";
import { Notice } from "@/src/shared/ui/Notice";
import { Panel } from "@/src/shared/ui/Panel";

type Props = {
  initialDataset?: string;
  initialAgentId?: string;
};

export default function PlaygroundWorkspace({ initialDataset = "", initialAgentId = "" }: Props) {
  const agentsQuery = useAgentsQuery();
  const datasetsQuery = useDatasetsQuery();
  const runsQuery = useRunsQuery();
  const [prompt, setPrompt] = useState("Draft a concise customer response for delayed shipping.");
  const [agentId, setAgentId] = useState(initialAgentId);
  const [dataset, setDataset] = useState(initialDataset);
  const [latestRunId, setLatestRunId] = useState("");
  const [log, setLog] = useState("trace: waiting for manual run...\n");
  const agents = useMemo(() => agentsQuery.data ?? [], [agentsQuery.data]);
  const selectedAgent = agents.find((item) => item.agentId === agentId) ?? agents[0] ?? null;
  const datasets = useMemo(() => datasetsQuery.data?.map((item) => item.name) ?? [], [datasetsQuery.data]);
  const latestRun = useMemo(
    () => runsQuery.data?.find((run) => run.runId === latestRunId) ?? null,
    [latestRunId, runsQuery.data]
  );

  useEffect(() => {
    if (!latestRunId && runsQuery.data?.[0]) {
      setLatestRunId(runsQuery.data[0].runId);
    }
  }, [latestRunId, runsQuery.data]);

  useEffect(() => {
    if (!agents.length) {
      return;
    }

    if (!agentId || !agents.some((agent) => agent.agentId === agentId)) {
      setAgentId(agents[0].agentId);
    }
  }, [agentId, agents]);

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
          <p className="kicker">
            Launch a published agent, inspect the output, and jump straight into its run workspace.
          </p>
          <div className="page-tag-list">
            <span className="page-tag">
              Published agents <strong>{agents.length}</strong>
            </span>
            <span className="page-tag">
              Datasets <strong>{datasets.length}</strong>
            </span>
            <span className="page-tag">
              Run state <strong>{latestRun?.status ?? "idle"}</strong>
            </span>
          </div>
        </div>
        <div className="page-info-grid">
          <div className="page-info-item">
            <span className="page-info-label">Execution target</span>
            <span className="page-info-value">{selectedAgent?.name ?? "Waiting for a published agent"}</span>
            <p className="page-info-detail">
              {dataset ? `Dataset attached: ${dataset}.` : "Prompt-only mode is active until a dataset is selected."}
            </p>
          </div>
          <div className="toolbar">
            <Button
              variant="secondary"
              onClick={() => setPrompt("Can you create a shipping itinerary?")}
              disabled={!dataset}
            >
              Attach dataset sample
            </Button>
            {latestRunId ? (
              <Button href={`/runs/${latestRunId}`}>
                Open run workspace <ArrowUpRight size={14} />
              </Button>
            ) : null}
          </div>
        </div>
      </header>

      <div className="summary-strip">
        <MetricCard label="Agent" value={selectedAgent?.name ?? "-"} />
        <MetricCard label="Agent ID" value={selectedAgent?.agentId ?? "-"} />
        <MetricCard label="Default model" value={selectedAgent?.defaultModel ?? "-"} />
        <MetricCard label="Dataset" value={dataset || "-"} />
        <MetricCard label="Latest run" value={latestRunId || "-"} />
        <MetricCard label="Framework" value={selectedAgent?.framework ?? "-"} />
      </div>

      <div className="workspace-grid workspace-grid-wide">
        <Panel tone="strong">
          <div className="surface-header">
            <div>
              <p className="surface-kicker">Run controls</p>
              <h3 className="panel-title">Prompt and published agent settings</h3>
              <p className="muted-note">
                Keep agent choice, dataset attachment, and run execution in one continuous working surface.
              </p>
            </div>
          </div>
          {agentsQuery.isError ? (
            <Notice>Agent catalog unavailable. Check the API connection and try again.</Notice>
          ) : null}
          {selectedAgent ? (
            <Notice>
              {`${selectedAgent.description} Default model: ${selectedAgent.defaultModel}. Tags: ${
                selectedAgent.tags.length ? selectedAgent.tags.join(", ") : "none"
              }.`}
            </Notice>
          ) : null}
          {!dataset ? (
            <Notice>No dataset attached. Playground will run prompt-only until you select one.</Notice>
          ) : null}
          <PlaygroundForm
            prompt={prompt}
            agentId={agentId}
            agents={agents}
            dataset={dataset}
            datasets={datasets}
            onPromptChange={setPrompt}
            onAgentIdChange={setAgentId}
            onDatasetChange={setDataset}
          />
          <ManualRunActions
            prompt={prompt}
            agentId={selectedAgent?.agentId ?? ""}
            agentName={selectedAgent?.name ?? "Unknown"}
            dataset={dataset}
            latestRunId={latestRunId}
            latestRunStatus={latestRun?.status ?? null}
            onLatestRunChange={setLatestRunId}
            onLogChange={setLog}
          />
        </Panel>

        <Panel as="aside">
          <div className="surface-header">
            <div>
              <p className="surface-kicker">Trace output</p>
              <h3 className="panel-title">Execution output</h3>
              <p className="muted-note">
                Stream raw trace feedback beside the run controls so failures are visible immediately.
              </p>
            </div>
          </div>
          <TraceLogPanel log={log} />
        </Panel>
      </div>
    </section>
  );
}
