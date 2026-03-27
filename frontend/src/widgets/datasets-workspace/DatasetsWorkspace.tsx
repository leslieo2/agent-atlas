"use client";

import { ArrowUpRight } from "lucide-react";
import { type ChangeEvent, useEffect, useMemo, useRef, useState } from "react";
import type { DatasetRow } from "@/src/entities/dataset/model";
import { parseDatasetJsonl } from "@/src/entities/dataset/parser";
import { useCreateDatasetMutation, useDatasetsQuery } from "@/src/entities/dataset/query";
import { DatasetUpload } from "@/src/features/dataset-upload/DatasetUpload";
import { Button } from "@/src/shared/ui/Button";
import { Field } from "@/src/shared/ui/Field";
import { MetricCard } from "@/src/shared/ui/MetricCard";
import { Notice } from "@/src/shared/ui/Notice";
import { Panel } from "@/src/shared/ui/Panel";
import styles from "./DatasetsWorkspace.module.css";

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

export default function DatasetsWorkspace() {
  const datasetsQuery = useDatasetsQuery();
  const createDatasetMutation = useCreateDatasetMutation();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [selectedDataset, setSelectedDataset] = useState("");
  const [datasetName, setDatasetName] = useState("");
  const [sampleInput, setSampleInput] = useState("");
  const [expectedOutput, setExpectedOutput] = useState("");
  const [sampleTagsText, setSampleTagsText] = useState("");
  const [feedback, setFeedback] = useState("");
  const [latestImportedDataset, setLatestImportedDataset] = useState("");

  const datasets = useMemo(() => datasetsQuery.data ?? [], [datasetsQuery.data]);
  const totalSamples = useMemo(
    () => datasets.reduce((count, dataset) => count + dataset.rows.length, 0),
    [datasets]
  );
  const selectedDatasetRecord = useMemo(
    () => datasets.find((item) => item.name === selectedDataset) ?? null,
    [datasets, selectedDataset]
  );
  const previewRows = selectedDatasetRecord?.rows.slice(0, 3) ?? [];
  const importStatus = createDatasetMutation.isPending
    ? "Importing..."
    : latestImportedDataset
      ? `Ready · ${latestImportedDataset}`
      : datasets.length
        ? "Ready"
        : "Waiting";

  useEffect(() => {
    if (!datasets.length) {
      if (selectedDataset) {
        setSelectedDataset("");
      }
      return;
    }

    if (!selectedDataset || !datasets.some((item) => item.name === selectedDataset)) {
      setSelectedDataset(datasets[0].name);
    }
  }, [datasets, selectedDataset]);

  const completeCreate = async (rows: DatasetRow[], nextDatasetName: string, sourceLabel: string) => {
    const created = await createDatasetMutation.mutateAsync({
      name: nextDatasetName,
      rows
    });

    setSelectedDataset(created.name);
    setLatestImportedDataset(created.name);
    setDatasetName("");
    setSampleInput("");
    setExpectedOutput("");
    setSampleTagsText("");
    setFeedback(`${sourceLabel} ${created.name} with ${created.rows.length} sample${created.rows.length === 1 ? "" : "s"}.`);
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
      await completeCreate(rows, normalizedName, "Created dataset");
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Failed to create dataset.");
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

      await completeCreate(rows, nextDatasetName, "Imported dataset");
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Failed to upload dataset JSONL.");
    } finally {
      event.target.value = "";
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Shared dataset input</p>
          <h2 className="section-title">Datasets workspace</h2>
          <p className="kicker">
            Import, inspect, and prepare datasets once, then reuse them across eval batches and manual playground runs.
          </p>
          <div className="page-tag-list">
            <span className="page-tag">
              Datasets <strong>{datasets.length}</strong>
            </span>
            <span className="page-tag">
              Samples <strong>{totalSamples}</strong>
            </span>
            <span className="page-tag">
              Import status <strong>{importStatus}</strong>
            </span>
          </div>
        </div>
        <div className="page-info-grid">
          <div className="page-info-item">
            <span className="page-info-label">Current dataset</span>
            <span className="page-info-value">{selectedDatasetRecord?.name ?? "Waiting for dataset import"}</span>
            <p className="page-info-detail">
              {selectedDatasetRecord
                ? `${selectedDatasetRecord.rows.length} samples ready for eval and playground reuse.`
                : "Upload JSONL or create a single-sample dataset to seed both downstream workspaces."}
            </p>
          </div>
          <div className="toolbar">
            {selectedDatasetRecord ? (
              <Button href={`/evals?dataset=${encodeURIComponent(selectedDatasetRecord.name)}`} variant="secondary">
                Open in evals <ArrowUpRight size={14} />
              </Button>
            ) : null}
            {selectedDatasetRecord ? (
              <Button href={`/playground?dataset=${encodeURIComponent(selectedDatasetRecord.name)}`} variant="secondary">
                Open in playground <ArrowUpRight size={14} />
              </Button>
            ) : null}
          </div>
        </div>
      </header>

      <div className="summary-strip">
        <MetricCard label="Dataset count" value={datasets.length} />
        <MetricCard label="Total samples" value={totalSamples} />
        <MetricCard label="Selected dataset" value={selectedDatasetRecord?.name ?? "-"} />
        <MetricCard label="Preview rows" value={previewRows.length} />
        <MetricCard label="Latest import" value={latestImportedDataset || "-"} />
      </div>

      {feedback ? (
        <Notice>
          {feedback}
          {latestImportedDataset ? " " : ""}
          {latestImportedDataset ? (
            <Button href={`/evals?dataset=${encodeURIComponent(latestImportedDataset)}`} variant="ghost">
              Open imported dataset in evals
            </Button>
          ) : null}
          {latestImportedDataset ? " " : ""}
          {latestImportedDataset ? (
            <Button href={`/playground?dataset=${encodeURIComponent(latestImportedDataset)}`} variant="ghost">
              Open imported dataset in playground
            </Button>
          ) : null}
        </Notice>
      ) : null}

      <div className={styles.workspaceGrid}>
        <Panel tone="strong">
          <div className="surface-header">
            <div>
              <p className="surface-kicker">Import and create</p>
              <h3 className="panel-title">Manage dataset ingestion from one workspace</h3>
              <p className="muted-note">
                Reuse the existing JSONL contract and single-sample creation flow without embedding dataset setup inside evals or playground.
              </p>
            </div>
            <DatasetUpload fileInputRef={fileInputRef} onChange={handleDatasetUpload} />
          </div>

          <div className={styles.managementGrid}>
            <div className={styles.sectionBlock}>
              <div className={styles.sectionHeading}>
                <h4>JSONL import</h4>
                <p className="muted-note">
                  Upload a page-local JSONL file. If dataset name is blank, the filename becomes the dataset name.
                </p>
              </div>
              <Field label="Dataset name" htmlFor="datasets-name">
                <input
                  id="datasets-name"
                  value={datasetName}
                  onChange={(event) => setDatasetName(event.target.value)}
                  placeholder="support-batch"
                />
              </Field>
              <p className={["muted-note", styles.uploadHint].join(" ")}>
                Expected row shape: <span className="mono">sample_id</span>, <span className="mono">input</span>, optional{" "}
                <span className="mono">expected</span>, and optional <span className="mono">tags</span>.
              </p>
            </div>

            <div className={styles.sectionBlock}>
              <div className={styles.sectionHeading}>
                <h4>Single-sample dataset</h4>
                <p className="muted-note">
                  Create a quick dataset seed when you only need one example row before moving into evals or playground.
                </p>
              </div>
              <div className={styles.formGrid}>
                <Field label="Sample tags" htmlFor="datasets-tags">
                  <input
                    id="datasets-tags"
                    value={sampleTagsText}
                    onChange={(event) => setSampleTagsText(event.target.value)}
                    placeholder="refund, escalation"
                  />
                </Field>
                <Field label="Expected output" htmlFor="datasets-expected">
                  <textarea
                    id="datasets-expected"
                    rows={4}
                    value={expectedOutput}
                    onChange={(event) => setExpectedOutput(event.target.value)}
                    placeholder="Optional expected output."
                  />
                </Field>
                <Field label="Sample input" htmlFor="datasets-input">
                  <textarea
                    id="datasets-input"
                    rows={4}
                    value={sampleInput}
                    onChange={(event) => setSampleInput(event.target.value)}
                    placeholder="Paste the first dataset row input here."
                  />
                </Field>
              </div>
              <div className={styles.actionRow}>
                <Button variant="secondary" onClick={handleCreateDataset} disabled={createDatasetMutation.isPending}>
                  {createDatasetMutation.isPending ? "Creating..." : "Create dataset"}
                </Button>
              </div>
            </div>
          </div>

          {datasetsQuery.isError ? <Notice>Dataset catalog unavailable. Check the API connection and try again.</Notice> : null}
        </Panel>

        <div className={styles.sideRail}>
          <Panel as="aside">
            <div className="surface-header">
              <div>
                <p className="surface-kicker">Catalog</p>
                <h3 className="panel-title">Existing datasets</h3>
                <p className="muted-note">Inspect row counts, switch previews, and keep one shared source of truth for downstream workspaces.</p>
              </div>
            </div>

            <div className={styles.datasetList}>
              {datasets.map((item) => (
                <button
                  key={item.name}
                  type="button"
                  className={`${styles.datasetRow} ${selectedDataset === item.name ? styles.datasetRowActive : ""}`}
                  onClick={() => setSelectedDataset(item.name)}
                >
                  <div>
                    <strong>{item.name}</strong>
                    <p className="muted-note">{item.rows.length} samples available</p>
                  </div>
                  <div className={styles.datasetMeta}>
                    <strong>{item.rows.length}</strong>
                    <span className="muted-note">samples</span>
                  </div>
                </button>
              ))}
              {!datasets.length ? (
                <div className={styles.emptyState}>
                  <Notice>No datasets yet. Upload JSONL or create a single-sample dataset from this workspace.</Notice>
                </div>
              ) : null}
            </div>
          </Panel>

          <Panel as="aside">
            <div className={styles.previewHeading}>
              <p className="surface-kicker">Sample preview</p>
              <h3 className="panel-title">Inspect the first rows before launching work</h3>
              <p className="muted-note">Preview the first few records so eval and playground entrypoints start from the same inspected dataset.</p>
            </div>

            {selectedDatasetRecord ? (
              <div className={styles.previewList}>
                {previewRows.length ? (
                  previewRows.map((row) => (
                    <article key={row.sampleId} className={styles.previewCard}>
                      <div className={styles.previewHeader}>
                        <strong>{row.sampleId}</strong>
                        <span className="muted-note">{selectedDatasetRecord.name}</span>
                      </div>
                      <p className={styles.previewInput}>{row.input}</p>
                      {row.expected ? <p className={styles.previewExpected}>Expected: {row.expected}</p> : null}
                      {row.tags?.length ? (
                        <div className={styles.tagList}>
                          {row.tags.map((tag) => (
                            <span key={tag} className={styles.tag}>
                              {tag}
                            </span>
                          ))}
                        </div>
                      ) : null}
                    </article>
                  ))
                ) : (
                  <div className={styles.emptyState}>
                    <Notice>This dataset has no samples yet.</Notice>
                  </div>
                )}
              </div>
            ) : (
              <div className={styles.emptyState}>
                <Notice>Select a dataset to inspect its first few samples.</Notice>
              </div>
            )}
          </Panel>
        </div>
      </div>
    </section>
  );
}
