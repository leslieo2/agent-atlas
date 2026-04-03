"use client";

import { ArrowUpRight } from "lucide-react";
import { type ChangeEvent, useEffect, useMemo, useRef, useState } from "react";
import type { Dataset, DatasetRow } from "@/src/entities/dataset/model";
import { parseDatasetJsonl } from "@/src/entities/dataset/parser";
import { useCreateDatasetMutation, useDatasetsQuery } from "@/src/entities/dataset/query";
import { DatasetUpload } from "@/src/features/dataset-upload/DatasetUpload";
import { Button } from "@/src/shared/ui/Button";
import { Field } from "@/src/shared/ui/Field";
import { MetricCard } from "@/src/shared/ui/MetricCard";
import { Notice } from "@/src/shared/ui/Notice";
import { Panel } from "@/src/shared/ui/Panel";
import styles from "./DatasetsWorkspace.module.css";

function normalizeDatasetName(value: string) {
  return value.trim();
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

function collectUnique(values: Array<string | null | undefined>) {
  return Array.from(new Set(values.filter((value): value is string => Boolean(value)))).sort();
}

function matchesRowFilters({
  row,
  sliceFilter,
  tagFilter,
  sourceFilter
}: {
  row: DatasetRow;
  sliceFilter: string;
  tagFilter: string;
  sourceFilter: string;
}) {
  if (sliceFilter && row.slice !== sliceFilter) {
    return false;
  }
  if (tagFilter && !row.tags?.includes(tagFilter)) {
    return false;
  }
  if (sourceFilter && row.source !== sourceFilter) {
    return false;
  }
  return true;
}

function datasetSummary(dataset: Dataset | null) {
  if (!dataset) {
    return "Waiting for dataset import";
  }

  const parts = [
    `${dataset.rows.length} samples`,
    dataset.source ? `source ${dataset.source}` : null,
    dataset.version ? `version ${dataset.version}` : null
  ].filter(Boolean);

  return parts.join(" · ");
}

function datasetVersionLabel(version: string | null | undefined) {
  return version ? `Version ${version}` : "Unversioned";
}

export default function DatasetsWorkspace() {
  const datasetsQuery = useDatasetsQuery();
  const createDatasetMutation = useCreateDatasetMutation();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [selectedDataset, setSelectedDataset] = useState("");
  const [datasetName, setDatasetName] = useState("");
  const [datasetDescription, setDatasetDescription] = useState("");
  const [datasetSource, setDatasetSource] = useState("");
  const [datasetVersion, setDatasetVersion] = useState("");
  const [sliceFilter, setSliceFilter] = useState("");
  const [tagFilter, setTagFilter] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [feedback, setFeedback] = useState("");
  const [latestImportedDatasetVersionId, setLatestImportedDatasetVersionId] = useState("");

  const datasets = useMemo(() => datasetsQuery.data ?? [], [datasetsQuery.data]);
  const totalSamples = useMemo(() => datasets.reduce((count, dataset) => count + dataset.rows.length, 0), [datasets]);
  const selectedDatasetRecord = useMemo(
    () => datasets.find((item) => item.name === selectedDataset) ?? null,
    [datasets, selectedDataset]
  );
  const sliceOptions = useMemo(
    () => collectUnique(selectedDatasetRecord?.rows.map((row) => row.slice) ?? []),
    [selectedDatasetRecord]
  );
  const tagOptions = useMemo(
    () => collectUnique((selectedDatasetRecord?.rows ?? []).flatMap((row) => row.tags ?? [])),
    [selectedDatasetRecord]
  );
  const sourceOptions = useMemo(
    () => collectUnique(selectedDatasetRecord?.rows.map((row) => row.source) ?? []),
    [selectedDatasetRecord]
  );
  const filteredRows = useMemo(
    () =>
      (selectedDatasetRecord?.rows ?? []).filter((row) =>
        matchesRowFilters({ row, sliceFilter, tagFilter, sourceFilter })
      ),
    [selectedDatasetRecord, sliceFilter, tagFilter, sourceFilter]
  );
  const previewRows = filteredRows.slice(0, 6);
  const exportEligibleCount = useMemo(
    () => (selectedDatasetRecord?.rows ?? []).filter((row) => row.exportEligible !== false).length,
    [selectedDatasetRecord]
  );

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

  useEffect(() => {
    setSliceFilter("");
    setTagFilter("");
    setSourceFilter("");
  }, [selectedDataset]);

  const completeCreate = async (rows: DatasetRow[], nextDatasetName: string, sourceLabel: string) => {
    const created = await createDatasetMutation.mutateAsync({
      name: nextDatasetName,
      description: datasetDescription.trim() || null,
      source: datasetSource.trim() || null,
      version: datasetVersion.trim() || null,
      rows
    });

    setSelectedDataset(created.name);
    setLatestImportedDatasetVersionId(created.currentVersionId ?? "");
    setDatasetName("");
    setDatasetDescription("");
    setDatasetSource("");
    setDatasetVersion("");
    setFeedback(`${sourceLabel} ${created.name} with ${created.rows.length} sample${created.rows.length === 1 ? "" : "s"}.`);
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
          <p className="page-eyebrow">RL data assets</p>
          <h2 className="section-title">Datasets</h2>
          <p className="kicker">
            Treat datasets as source-of-truth training assets. Define slices, provenance, and export eligibility before
            you fan out experiments.
          </p>
          <div className="page-tag-list">
            <span className="page-tag">
              Datasets <strong>{datasets.length}</strong>
            </span>
            <span className="page-tag">
              Samples <strong>{totalSamples}</strong>
            </span>
            <span className="page-tag">
              Export-ready <strong>{exportEligibleCount}</strong>
            </span>
          </div>
        </div>
        <div className="page-info-grid">
          <div className="page-info-item">
            <span className="page-info-label">Selected dataset</span>
            <span className="page-info-value">{selectedDatasetRecord?.name ?? "Waiting for dataset import"}</span>
            <p className="page-info-detail">
              {selectedDatasetRecord
                ? datasetSummary(selectedDatasetRecord)
                : "Import JSONL to create the next dataset asset for experiments and exports."}
            </p>
          </div>
          <div className="toolbar">
            {selectedDatasetRecord ? (
              <Button
                href={
                  selectedDatasetRecord.currentVersionId
                    ? `/experiments?datasetVersion=${encodeURIComponent(selectedDatasetRecord.currentVersionId)}`
                    : "/experiments"
                }
                variant="secondary"
              >
                Open in experiments <ArrowUpRight size={14} />
              </Button>
            ) : null}
          </div>
        </div>
      </header>

      <div className="summary-strip">
        <MetricCard label="Dataset count" value={datasets.length} />
        <MetricCard label="Total samples" value={totalSamples} />
        <MetricCard label="Selected rows" value={filteredRows.length} />
        <MetricCard label="Slices" value={sliceOptions.length} />
        <MetricCard label="Sources" value={sourceOptions.length} />
      </div>

      {feedback ? (
        <Notice>
          {feedback}{" "}
          {latestImportedDatasetVersionId ? (
            <Button
              href={`/experiments?datasetVersion=${encodeURIComponent(latestImportedDatasetVersionId)}`}
              variant="ghost"
            >
              Open imported dataset in experiments
            </Button>
          ) : null}
        </Notice>
      ) : null}

      <div className={styles.workspaceGrid}>
        <Panel tone="strong">
          <div className="surface-header">
            <div>
              <p className="surface-kicker">Ingest</p>
              <h3 className="panel-title">Import a dataset asset</h3>
              <p className="muted-note">
                Capture dataset-level provenance once, then import the canonical JSONL payload that downstream compare
                and export flows will use.
              </p>
            </div>
            <DatasetUpload fileInputRef={fileInputRef} onChange={handleDatasetUpload} />
          </div>

          <div className={styles.managementGrid}>
            <div className={styles.sectionBlock}>
              <div className={styles.sectionHeading}>
                <h4>Dataset metadata</h4>
                <p className="muted-note">Describe the asset that drives future experiments and RL exports.</p>
              </div>
              <div className={styles.formGrid}>
                <Field label="Dataset name" htmlFor="dataset-name">
                  <input id="dataset-name" value={datasetName} onChange={(event) => setDatasetName(event.target.value)} />
                </Field>
                <Field label="Version" htmlFor="dataset-version">
                  <input
                    id="dataset-version"
                    value={datasetVersion}
                    onChange={(event) => setDatasetVersion(event.target.value)}
                    placeholder="2026-03-rl-v1"
                  />
                </Field>
                <Field label="Source" htmlFor="dataset-source">
                  <input
                    id="dataset-source"
                    value={datasetSource}
                    onChange={(event) => setDatasetSource(event.target.value)}
                    placeholder="customer-support-regression"
                  />
                </Field>
                <Field label="Description" htmlFor="dataset-description" wide>
                  <textarea
                    id="dataset-description"
                    rows={3}
                    value={datasetDescription}
                    onChange={(event) => setDatasetDescription(event.target.value)}
                    placeholder="High-value escalation prompts curated for RL data collection."
                  />
                </Field>
              </div>
              <Notice>
                Upload JSONL is the canonical dataset bootstrap path. Atlas derives row-level slices, tags, and export
                eligibility from the imported file.
              </Notice>
            </div>
          </div>
        </Panel>

        <div className={styles.sideRail}>
          <Panel tone="plain">
            <div className="surface-header">
              <div>
                <p className="surface-kicker">Catalog</p>
                <h3 className="panel-title">Available dataset assets</h3>
                <p className="muted-note">Pick one asset, inspect its slices, then send it into eval orchestration.</p>
              </div>
            </div>

            {datasetsQuery.isPending ? <Notice>Loading datasets...</Notice> : null}
            {datasetsQuery.isError ? <Notice>Dataset catalog is temporarily unavailable.</Notice> : null}

            <div className={styles.datasetList}>
              {datasets.map((datasetRecord) => {
                const isActive = datasetRecord.name === selectedDataset;
                return (
                  <button
                    key={datasetRecord.name}
                    type="button"
                    className={[styles.datasetRow, isActive ? styles.datasetRowActive : ""].filter(Boolean).join(" ")}
                    onClick={() => setSelectedDataset(datasetRecord.name)}
                  >
                    <div>
                      <strong>{datasetRecord.name}</strong>
                      <p className="muted-note">{datasetRecord.description || "No description."}</p>
                    </div>
                    <div className={styles.datasetMeta}>
                      <strong>{datasetRecord.rows.length} rows</strong>
                      <span className="muted-note">{datasetVersionLabel(datasetRecord.version)}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </Panel>

          <Panel tone="plain">
            <div className="surface-header">
              <div>
                <p className="surface-kicker">Filter samples</p>
                <h3 className="panel-title">Inspect the selected asset</h3>
                <p className="muted-note">Browse by slice, tag, and source before launching a batch eval.</p>
              </div>
            </div>

            {selectedDatasetRecord ? (
              <>
                <div className={styles.formGrid}>
                  <Field label="Slice filter" htmlFor="dataset-filter-slice">
                    <select
                      id="dataset-filter-slice"
                      value={sliceFilter}
                      onChange={(event) => setSliceFilter(event.target.value)}
                    >
                      <option value="">All slices</option>
                      {sliceOptions.map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <Field label="Tag filter" htmlFor="dataset-filter-tag">
                    <select id="dataset-filter-tag" value={tagFilter} onChange={(event) => setTagFilter(event.target.value)}>
                      <option value="">All tags</option>
                      {tagOptions.map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <Field label="Source filter" htmlFor="dataset-filter-source">
                    <select
                      id="dataset-filter-source"
                      value={sourceFilter}
                      onChange={(event) => setSourceFilter(event.target.value)}
                    >
                      <option value="">All sources</option>
                      {sourceOptions.map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </select>
                  </Field>
                </div>

                <div className={styles.previewList}>
                  {previewRows.length ? (
                    previewRows.map((row) => (
                      <article key={row.sampleId} className={styles.previewCard}>
                        <div className={styles.previewHeader}>
                          <div className={styles.previewHeading}>
                            <h4>{row.sampleId}</h4>
                            <p className="muted-note">
                              {(row.slice || "no slice") + " · " + (row.source || selectedDatasetRecord.source || "unknown source")}
                            </p>
                          </div>
                          <strong>{row.exportEligible === false ? "Hold out" : "Exportable"}</strong>
                        </div>
                        <p className={styles.previewInput}>{row.input}</p>
                        {row.expected ? <p className={styles.previewExpected}>Expected: {row.expected}</p> : null}
                        {row.tags?.length ? (
                          <div className={styles.tagList}>
                            {row.tags.map((tag) => (
                              <span key={`${row.sampleId}-${tag}`} className={styles.tag}>
                                {tag}
                              </span>
                            ))}
                          </div>
                        ) : null}
                      </article>
                    ))
                  ) : (
                    <div className={styles.emptyState}>
                      <p className="muted-note">No rows match the current slice, tag, and source filters.</p>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className={styles.emptyState}>
                <p className="muted-note">Select a dataset asset to inspect its samples.</p>
              </div>
            )}
          </Panel>
        </div>
      </div>
    </section>
  );
}
