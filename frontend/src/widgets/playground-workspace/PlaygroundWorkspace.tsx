"use client";

import { ArrowUpRight } from "lucide-react";
import { type ChangeEvent, useEffect, useMemo, useRef, useState } from "react";
import { useAgentsQuery } from "@/src/entities/agent/query";
import type { DatasetRow } from "@/src/entities/dataset/model";
import { parseDatasetJsonl } from "@/src/entities/dataset/parser";
import { useCreateDatasetMutation, useDatasetsQuery } from "@/src/entities/dataset/query";
import { useCreateEvalJobMutation } from "@/src/entities/eval/query";
import { useRunsQuery } from "@/src/entities/run/query";
import { DatasetUpload } from "@/src/features/dataset-upload/DatasetUpload";
import { ManualRunActions } from "@/src/features/manual-run/ManualRunActions";
import { PlaygroundForm } from "@/src/features/playground-form/PlaygroundForm";
import { TraceLogPanel } from "@/src/features/trace-log/TraceLogPanel";
import { Button } from "@/src/shared/ui/Button";
import { Field } from "@/src/shared/ui/Field";
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

function normalizeDatasetName(value: string) {
  return value.trim();
}

function buildManualDatasetRows({
  datasetName,
  sampleInput,
  expectedOutput,
  sampleTagsText
}: {
  datasetName: string;
  sampleInput: string;
  expectedOutput: string;
  sampleTagsText: string;
}): DatasetRow[] {
  const normalizedName = normalizeDatasetName(datasetName);
  const input = sampleInput.trim();

  if (!normalizedName) {
    throw new Error("Dataset name is required before creating a dataset.");
  }
  if (!input) {
    throw new Error("Sample input is required before creating a dataset.");
  }

  return [
    {
      sampleId: `${normalizedName}-sample-1`,
      input,
      expected: expectedOutput.trim() || null,
      tags: parseTagsText(sampleTagsText)
    }
  ];
}

function inferDatasetName(currentName: string, fileName: string) {
  const normalized = normalizeDatasetName(currentName);
  if (normalized) {
    return normalized;
  }
  return fileName.replace(/\.jsonl$/i, "").trim();
}

async function readFileAsText(file: File) {
  if (typeof file.text === "function") {
    return file.text();
  }

  return await new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(typeof reader.result === "string" ? reader.result : "");
    reader.onerror = () => reject(reader.error ?? new Error("Failed to read dataset file."));
    reader.readAsText(file);
  });
}

export default function PlaygroundWorkspace({
  initialDataset = "",
  initialAgentId = "",
  initialPrompt = "Draft a concise customer response for delayed shipping.",
  initialTags = []
}: Props) {
  const agentsQuery = useAgentsQuery();
  const datasetsQuery = useDatasetsQuery();
  const createDatasetMutation = useCreateDatasetMutation();
  const createEvalJobMutation = useCreateEvalJobMutation();
  const runsQuery = useRunsQuery();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [prompt, setPrompt] = useState(initialPrompt);
  const [agentId, setAgentId] = useState(initialAgentId);
  const [dataset, setDataset] = useState(initialDataset);
  const [tagsText, setTagsText] = useState(initialTags.join(", "));
  const [latestRunId, setLatestRunId] = useState("");
  const [log, setLog] = useState("trace: waiting for manual run...\n");
  const [datasetName, setDatasetName] = useState("");
  const [sampleInput, setSampleInput] = useState("");
  const [expectedOutput, setExpectedOutput] = useState("");
  const [sampleTagsText, setSampleTagsText] = useState("");
  const [datasetFeedback, setDatasetFeedback] = useState("");
  const [evalFeedback, setEvalFeedback] = useState("");
  const [latestEvalJobId, setLatestEvalJobId] = useState("");
  const agents = useMemo(() => agentsQuery.data ?? [], [agentsQuery.data]);
  const datasets = useMemo(() => datasetsQuery.data ?? [], [datasetsQuery.data]);
  const datasetNames = useMemo(() => datasets.map((item) => item.name), [datasets]);
  const selectedAgent = agents.find((item) => item.agentId === agentId) ?? agents[0] ?? null;
  const selectedDatasetRecord = useMemo(
    () => datasets.find((item) => item.name === dataset) ?? null,
    [dataset, datasets]
  );
  const latestRun = useMemo(
    () => runsQuery.data?.find((run) => run.runId === latestRunId) ?? null,
    [latestRunId, runsQuery.data]
  );
  const previewRows = selectedDatasetRecord?.rows.slice(0, 3) ?? [];

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
    if (!datasetsQuery.isSuccess || !dataset || !datasetNames.length) {
      return;
    }

    if (!datasetNames.includes(dataset)) {
      setDataset("");
    }
  }, [dataset, datasetNames, datasetsQuery.isSuccess]);

  const runTags = useMemo(() => parseTagsText(tagsText), [tagsText]);

  const createInlineDataset = async (rows: DatasetRow[], nextDatasetName: string) => {
    const created = await createDatasetMutation.mutateAsync({
      name: nextDatasetName,
      rows
    });

    setDataset(created.name);
    setDatasetName("");
    setSampleInput("");
    setExpectedOutput("");
    setSampleTagsText("");
    setDatasetFeedback(`Dataset ${created.name} is ready in Playground.`);
    return created;
  };

  const handleCreateDataset = async () => {
    try {
      const normalizedName = normalizeDatasetName(datasetName);
      const rows = buildManualDatasetRows({
        datasetName: normalizedName,
        sampleInput,
        expectedOutput,
        sampleTagsText
      });
      await createInlineDataset(rows, normalizedName);
    } catch (error) {
      setDatasetFeedback(error instanceof Error ? error.message : "Failed to create dataset.");
    }
  };

  const handleDatasetUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    try {
      const rows = parseDatasetJsonl(await readFileAsText(file));
      const nextDatasetName = inferDatasetName(datasetName, file.name);
      if (!nextDatasetName) {
        throw new Error("Dataset name is required before uploading JSONL.");
      }
      await createInlineDataset(rows, nextDatasetName);
    } catch (error) {
      setDatasetFeedback(error instanceof Error ? error.message : "Failed to upload dataset JSONL.");
    } finally {
      event.target.value = "";
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleCreateEvalJob = async () => {
    if (!selectedAgent || !dataset) {
      setEvalFeedback("Select both a published agent and a dataset before creating an eval.");
      return;
    }

    const created = await createEvalJobMutation.mutateAsync({
      agentId: selectedAgent.agentId,
      dataset,
      project: dataset,
      tags: ["playground"],
      scoringMode: "exact_match"
    });
    setLatestEvalJobId(created.evalJobId);
    setEvalFeedback(`Eval job ${created.evalJobId} is queued.`);
  };

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Manual run</p>
          <h2 className="section-title">Playground</h2>
          <p className="kicker">
            Launch a published agent, inspect the output, and keep dataset setup inside the same work surface.
          </p>
          <div className="page-tag-list">
            <span className="page-tag">
              Published agents <strong>{agents.length}</strong>
            </span>
            <span className="page-tag">
              Datasets <strong>{datasetNames.length}</strong>
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
            <Button
              variant="secondary"
              onClick={handleCreateEvalJob}
              disabled={!selectedAgent || !dataset || createEvalJobMutation.isPending}
            >
              {createEvalJobMutation.isPending ? "Creating eval..." : "Create eval job"}
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
        <MetricCard label="Latest eval" value={latestEvalJobId || "-"} />
        <MetricCard label="Tags" value={runTags.join(", ") || "-"} />
      </div>

      {evalFeedback ? (
        <Notice>
          {evalFeedback}
          {latestEvalJobId ? " " : ""}
          {latestEvalJobId ? <Button href={`/evals?job=${latestEvalJobId}`} variant="ghost">Open eval workspace</Button> : null}
        </Notice>
      ) : null}

      <div className="workspace-grid workspace-grid-wide">
        <Panel tone="strong">
          <div className="surface-header">
            <div>
              <p className="surface-kicker">Run controls</p>
              <h3 className="panel-title">Prompt, published agent, and dataset context</h3>
              <p className="muted-note">
                Keep agent choice, dataset attachment, creation, and run execution in one continuous working surface.
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

          <div className="layout-two" style={{ marginTop: 12 }}>
            <div>
              <PlaygroundForm
                prompt={prompt}
                agentId={agentId}
                agents={agents}
                dataset={dataset}
                datasets={datasetNames}
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

            <div className="surface">
              <div className="surface-header">
                <div>
                  <p className="surface-kicker">Dataset manager</p>
                  <h3 className="panel-title">Create or upload a dataset without leaving Playground</h3>
                  <p className="muted-note">
                    New datasets are selected immediately so you can run against them without page switches.
                  </p>
                </div>
                <DatasetUpload fileInputRef={fileInputRef} onChange={handleDatasetUpload} />
              </div>

              <div className="two-col">
                <Field label="Dataset name" htmlFor="playground-dataset-name">
                  <input
                    id="playground-dataset-name"
                    value={datasetName}
                    onChange={(event) => setDatasetName(event.target.value)}
                    placeholder="returns-review"
                  />
                </Field>
                <Field label="Sample tags" htmlFor="playground-dataset-tags">
                  <input
                    id="playground-dataset-tags"
                    value={sampleTagsText}
                    onChange={(event) => setSampleTagsText(event.target.value)}
                    placeholder="refund, escalation"
                  />
                </Field>
              </div>
              <div className="two-col" style={{ marginTop: 12 }}>
                <Field label="Sample input" htmlFor="playground-dataset-input">
                  <textarea
                    id="playground-dataset-input"
                    rows={4}
                    value={sampleInput}
                    onChange={(event) => setSampleInput(event.target.value)}
                    placeholder="Paste the first dataset row input here."
                  />
                </Field>
                <Field label="Expected output" htmlFor="playground-dataset-expected">
                  <textarea
                    id="playground-dataset-expected"
                    rows={4}
                    value={expectedOutput}
                    onChange={(event) => setExpectedOutput(event.target.value)}
                    placeholder="Optional expected output."
                  />
                </Field>
              </div>
              <div className="toolbar" style={{ marginTop: 12, justifyContent: "flex-start" }}>
                <Button
                  variant="secondary"
                  onClick={handleCreateDataset}
                  disabled={createDatasetMutation.isPending}
                >
                  {createDatasetMutation.isPending ? "Creating..." : "Create dataset"}
                </Button>
              </div>
              {datasetFeedback ? <Notice>{datasetFeedback}</Notice> : null}
              {selectedDatasetRecord ? (
                <div style={{ marginTop: 16 }}>
                  <p className="page-info-value">{`Selected dataset preview · ${selectedDatasetRecord.rows.length} rows`}</p>
                  <p className="page-info-detail">
                    {previewRows.length
                      ? "Previewing the first three samples from the currently attached dataset."
                      : "This dataset has no rows yet."}
                  </p>
                  <div className="output-log mono" style={{ minHeight: 0, marginTop: 12 }}>
                    {previewRows.length ? (
                      previewRows.map((row) => <div key={row.sampleId}>{`${row.sampleId} · ${row.input}`}</div>)
                    ) : (
                      "No samples available."
                    )}
                  </div>
                </div>
              ) : (
                <Notice>No dataset selected yet. Create one inline or attach an existing dataset.</Notice>
              )}
            </div>
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
