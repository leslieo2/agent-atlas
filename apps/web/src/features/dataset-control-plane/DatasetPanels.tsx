"use client";

import type { ChangeEvent, RefObject } from "react";
import type { Dataset, DatasetRow } from "@/src/entities/dataset/model";
import { DatasetUpload } from "@/src/features/dataset-upload/DatasetUpload";
import { Button } from "@/src/shared/ui/Button";
import { Field } from "@/src/shared/ui/Field";
import { Notice } from "@/src/shared/ui/Notice";
import { Panel } from "@/src/shared/ui/Panel";

export function DatasetIngestPanel(props: {
  createPending: boolean;
  datasetDescription: string;
  datasetName: string;
  datasetSource: string;
  datasetVersion: string;
  fileInputRef: RefObject<HTMLInputElement | null>;
  onClearPendingUpload: () => void;
  onDatasetDescriptionChange: (value: string) => void;
  onDatasetNameChange: (value: string) => void;
  onDatasetSourceChange: (value: string) => void;
  onDatasetUpload: (event: ChangeEvent<HTMLInputElement>) => Promise<void>;
  onDatasetVersionChange: (value: string) => void;
  onImportPendingUpload: () => void;
  pendingUpload: {
    fileName: string;
    rows: DatasetRow[];
  } | null;
  styles: Record<string, string>;
}) {
  return (
    <Panel tone="strong">
      <div className="surface-header">
        <div>
          <p className="surface-kicker">Ingest</p>
          <h3 className="panel-title">Import a dataset asset</h3>
          <p className="muted-note">
            Start with the canonical JSONL. Atlas can infer the dataset name from the file, then you can confirm or
            refine provenance before import.
          </p>
        </div>
        <DatasetUpload fileInputRef={props.fileInputRef} onChange={props.onDatasetUpload} />
      </div>

      <div className={props.styles.managementGrid}>
        <div className={props.styles.sectionBlock}>
          <div className={props.styles.sectionHeading}>
            <h4>Dataset metadata</h4>
            <p className="muted-note">
              Upload first, then confirm the asset identity and any optional provenance before import.
            </p>
          </div>
          {props.pendingUpload ? (
            <Notice>
              Selected <strong>{props.pendingUpload.fileName}</strong> with <strong>{props.pendingUpload.rows.length}</strong>{" "}
              sample{props.pendingUpload.rows.length === 1 ? "" : "s"}.
            </Notice>
          ) : (
            <Notice>Select a JSONL file to start the ingest flow. Atlas will stage it here before import.</Notice>
          )}
          <div className={props.styles.formGrid}>
            <Field label="Dataset name" htmlFor="dataset-name">
              <input id="dataset-name" value={props.datasetName} onChange={(event) => props.onDatasetNameChange(event.target.value)} />
            </Field>
            <Field label="Version" htmlFor="dataset-version">
              <input
                id="dataset-version"
                value={props.datasetVersion}
                onChange={(event) => props.onDatasetVersionChange(event.target.value)}
                placeholder="2026-03-rl-v1"
              />
            </Field>
            <Field label="Source" htmlFor="dataset-source">
              <input
                id="dataset-source"
                value={props.datasetSource}
                onChange={(event) => props.onDatasetSourceChange(event.target.value)}
                placeholder="customer-support-regression"
              />
            </Field>
            <Field label="Description" htmlFor="dataset-description" wide>
              <textarea
                id="dataset-description"
                rows={3}
                value={props.datasetDescription}
                onChange={(event) => props.onDatasetDescriptionChange(event.target.value)}
                placeholder="High-value escalation prompts curated for RL data collection."
              />
            </Field>
          </div>
          <div className={props.styles.actionRow}>
            <Button onClick={props.onImportPendingUpload} disabled={!props.pendingUpload || props.createPending}>
              {props.createPending ? "Importing..." : "Import dataset"}
            </Button>
            {props.pendingUpload ? (
              <Button variant="ghost" onClick={props.onClearPendingUpload} disabled={props.createPending}>
                Choose another file
              </Button>
            ) : null}
          </div>
          <Notice>
            Upload JSONL is the canonical dataset bootstrap path. Atlas derives row-level slices, tags, and export
            eligibility from the imported file, while dataset-level provenance stays optional at ingest time.
          </Notice>
        </div>
      </div>
    </Panel>
  );
}

export function DatasetCatalogPanel(props: {
  datasetVersionLabel: (version: string | null | undefined) => string;
  datasets: Dataset[];
  datasetsQueryError: boolean;
  datasetsQueryPending: boolean;
  onSelectedDatasetChange: (value: string) => void;
  onSliceFilterChange: (value: string) => void;
  onSourceFilterChange: (value: string) => void;
  onTagFilterChange: (value: string) => void;
  previewRows: DatasetRow[];
  selectedDataset: string;
  selectedDatasetRecord: Dataset | null;
  sliceFilter: string;
  sliceOptions: string[];
  sourceFilter: string;
  sourceOptions: string[];
  styles: Record<string, string>;
  tagFilter: string;
  tagOptions: string[];
}) {
  return (
    <div className={props.styles.sideRail}>
      <Panel tone="plain">
        <div className="surface-header">
          <div>
            <p className="surface-kicker">Catalog</p>
            <h3 className="panel-title">Available dataset assets</h3>
            <p className="muted-note">Pick one asset, inspect its slices, then send it into eval orchestration.</p>
          </div>
        </div>

        {props.datasetsQueryPending ? <Notice>Loading datasets...</Notice> : null}
        {props.datasetsQueryError ? <Notice>Dataset catalog is temporarily unavailable.</Notice> : null}

        <div className={props.styles.datasetList}>
          {props.datasets.map((datasetRecord) => {
            const isActive = datasetRecord.name === props.selectedDataset;
            return (
              <button
                key={datasetRecord.name}
                type="button"
                className={[props.styles.datasetRow, isActive ? props.styles.datasetRowActive : ""].filter(Boolean).join(" ")}
                onClick={() => props.onSelectedDatasetChange(datasetRecord.name)}
              >
                <div>
                  <strong>{datasetRecord.name}</strong>
                  <p className="muted-note">{datasetRecord.description || "No description."}</p>
                </div>
                <div className={props.styles.datasetMeta}>
                  <strong>{datasetRecord.rows.length} rows</strong>
                  <span className="muted-note">{props.datasetVersionLabel(datasetRecord.version)}</span>
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

        {props.selectedDatasetRecord ? (
          <>
            <div className={props.styles.formGrid}>
              <Field label="Slice filter" htmlFor="dataset-filter-slice">
                <select
                  id="dataset-filter-slice"
                  value={props.sliceFilter}
                  onChange={(event) => props.onSliceFilterChange(event.target.value)}
                >
                  <option value="">All slices</option>
                  {props.sliceOptions.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Tag filter" htmlFor="dataset-filter-tag">
                <select id="dataset-filter-tag" value={props.tagFilter} onChange={(event) => props.onTagFilterChange(event.target.value)}>
                  <option value="">All tags</option>
                  {props.tagOptions.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Source filter" htmlFor="dataset-filter-source">
                <select
                  id="dataset-filter-source"
                  value={props.sourceFilter}
                  onChange={(event) => props.onSourceFilterChange(event.target.value)}
                >
                  <option value="">All sources</option>
                  {props.sourceOptions.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </Field>
            </div>

            <div className={props.styles.previewList}>
              {props.previewRows.length ? (
                props.previewRows.map((row) => (
                  <article key={row.sampleId} className={props.styles.previewCard}>
                    <div className={props.styles.previewHeader}>
                      <div className={props.styles.previewHeading}>
                        <h4>{row.sampleId}</h4>
                        <p className="muted-note">
                          {(row.slice || "no slice") +
                            " · " +
                            (row.source || props.selectedDatasetRecord?.source || "unknown source")}
                        </p>
                      </div>
                      <strong>{row.exportEligible === false ? "Hold out" : "Exportable"}</strong>
                    </div>
                    <p className={props.styles.previewInput}>{row.input}</p>
                    {row.expected ? <p className={props.styles.previewExpected}>Expected: {row.expected}</p> : null}
                    {row.tags?.length ? (
                      <div className={props.styles.tagList}>
                        {row.tags.map((tag) => (
                          <span key={`${row.sampleId}-${tag}`} className={props.styles.tag}>
                            {tag}
                          </span>
                        ))}
                      </div>
                    ) : null}
                  </article>
                ))
              ) : (
                <div className={props.styles.emptyState}>
                  <p className="muted-note">No rows match the current slice, tag, and source filters.</p>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className={props.styles.emptyState}>
            <p className="muted-note">Select a dataset asset to inspect its samples.</p>
          </div>
        )}
      </Panel>
    </div>
  );
}
