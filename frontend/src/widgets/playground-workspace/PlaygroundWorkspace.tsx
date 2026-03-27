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
  initialPrompt?: string;
  initialTags?: string[];
};

function parseTagsText(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export default function PlaygroundWorkspace({
  initialDataset = "",
  initialAgentId = "",
  initialPrompt = "Draft a concise customer response for delayed shipping.",
  initialTags = []
}: Props) {
  const agentsQuery = useAgentsQuery();
  const datasetsQuery = useDatasetsQuery();
  const runsQuery = useRunsQuery();
  const [prompt, setPrompt] = useState(initialPrompt);
  const [agentId, setAgentId] = useState(initialAgentId);
  const [dataset, setDataset] = useState(initialDataset);
  const [tagsText, setTagsText] = useState(initialTags.join(", "));
  const [latestRunId, setLatestRunId] = useState("");
  const [log, setLog] = useState("trace: waiting for manual run...\n");
  const agents = useMemo(() => agentsQuery.data ?? [], [agentsQuery.data]);
  const datasets = useMemo(() => datasetsQuery.data ?? [], [datasetsQuery.data]);
  const selectedAgent = agents.find((item) => item.agentId === agentId) ?? agents[0] ?? null;
  const selectedDataset = datasets.find((item) => item.name === dataset) ?? null;
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
    if (initialDataset) {
      setDataset(initialDataset);
      return;
    }

    if (dataset && datasets.length && !datasets.some((item) => item.name === dataset)) {
      setDataset("");
    }
  }, [dataset, datasets, initialDataset]);

  const runTags = useMemo(() => parseTagsText(tagsText), [tagsText]);
  const selectedDatasetSample = selectedDataset?.rows[0] ?? null;

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Manual run</p>
          <h2 className="section-title">Playground</h2>
          <p className="kicker">
            Launch a published agent, inspect the output, and iterate on direct manual runs.
          </p>
          <div className="page-tag-list">
            <span className="page-tag">
              Published agents <strong>{agents.length}</strong>
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
              {selectedDataset
                ? `Prompt-driven execution is active with dataset ${selectedDataset.name}.`
                : "Prompt-driven execution is active in this workspace."}
            </p>
          </div>
          <div className="toolbar">
            <Button variant="secondary" onClick={() => setPrompt("Can you create a shipping itinerary?")}>
              Load sample prompt
            </Button>
            <Button
              variant="ghost"
              onClick={() => setPrompt(selectedDatasetSample?.input ?? prompt)}
              disabled={!selectedDatasetSample}
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
        <MetricCard label="Dataset" value={selectedDataset?.name ?? "-"} />
        <MetricCard label="Default model" value={selectedAgent?.defaultModel ?? "-"} />
        <MetricCard label="Latest run" value={latestRunId || "-"} />
        <MetricCard label="Tags" value={runTags.join(", ") || "-"} />
      </div>

      <div className="workspace-grid workspace-grid-wide">
        <Panel tone="strong">
          <div className="surface-header">
            <div>
              <p className="surface-kicker">Run controls</p>
              <h3 className="panel-title">Prompt and published agent context</h3>
              <p className="muted-note">
                Keep agent choice, prompt editing, and run execution in one continuous working surface.
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
          {datasetsQuery.isError ? <Notice>Dataset catalog unavailable. You can still launch prompt-only runs.</Notice> : null}
          <Notice>
            {selectedDataset
              ? `Dataset ${selectedDataset.name} attached. Playground will reuse its first sample when you want a quick seed prompt.`
              : "No dataset attached. Playground will run prompt-only until you select one."}
          </Notice>
          <Notice>Dataset-oriented flows live in Evals and Datasets. Playground stays focused on direct manual runs.</Notice>

          <div style={{ marginTop: 12 }}>
            <PlaygroundForm
              prompt={prompt}
              agentId={agentId}
              agents={agents}
              dataset={dataset}
              datasets={datasets}
              tagsText={tagsText}
              onPromptChange={setPrompt}
              onAgentIdChange={setAgentId}
              onDatasetChange={setDataset}
              onTagsTextChange={setTagsText}
            />

            <ManualRunActions
              prompt={prompt}
              agentId={selectedAgent?.agentId ?? ""}
              agentName={selectedAgent?.name ?? "Unknown"}
              dataset={dataset}
              tags={runTags}
              latestRunId={latestRunId}
              latestRunStatus={latestRun?.status ?? null}
              onLatestRunChange={setLatestRunId}
              onLogChange={setLog}
            />
          </div>
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
