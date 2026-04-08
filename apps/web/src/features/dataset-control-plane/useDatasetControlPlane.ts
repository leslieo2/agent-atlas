"use client";

import { type ChangeEvent, useEffect, useMemo, useRef, useState } from "react";
import type { DatasetRow } from "@/src/entities/dataset/model";
import { parseDatasetJsonl } from "@/src/entities/dataset/parser";
import { useCreateDatasetMutation, useDatasetsQuery } from "@/src/entities/dataset/query";
import {
  collectUnique,
  datasetSummary,
  datasetVersionLabel,
  inferDatasetName,
  matchesDatasetRowFilters
} from "./model";

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

type PendingUpload = {
  fileName: string;
  rows: DatasetRow[];
};

export function useDatasetControlPlane() {
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
  const [pendingUpload, setPendingUpload] = useState<PendingUpload | null>(null);

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
        matchesDatasetRowFilters({ row, sliceFilter, tagFilter, sourceFilter })
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

  const resetFileInput = () => {
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

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
    setPendingUpload(null);
    setFeedback(`${sourceLabel} ${created.name} with ${created.rows.length} sample${created.rows.length === 1 ? "" : "s"}.`);
  };

  const handleDatasetUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    try {
      const rows = parseDatasetJsonl(await readFileAsText(file));
      const inferredDatasetName = inferDatasetName(datasetName, file.name);
      if (!datasetName.trim() && inferredDatasetName) {
        setDatasetName(inferredDatasetName);
      }
      setLatestImportedDatasetVersionId("");
      setPendingUpload({ fileName: file.name, rows });
      setFeedback(
        `Ready to import ${rows.length} sample${rows.length === 1 ? "" : "s"} from ${file.name}. Review metadata if needed, then confirm import.`
      );
    } catch (error) {
      setPendingUpload(null);
      setFeedback(error instanceof Error ? error.message : "Failed to upload dataset JSONL.");
    } finally {
      event.target.value = "";
      resetFileInput();
    }
  };

  const handleImportPendingUpload = async () => {
    if (!pendingUpload) {
      return;
    }

    try {
      const nextDatasetName = inferDatasetName(datasetName, pendingUpload.fileName);
      if (!nextDatasetName) {
        throw new Error("Dataset name is required before import.");
      }

      await completeCreate(pendingUpload.rows, nextDatasetName, "Imported dataset");
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Failed to import dataset JSONL.");
    }
  };

  const clearPendingUpload = () => {
    setPendingUpload(null);
    setFeedback("");
    setLatestImportedDatasetVersionId("");
    resetFileInput();
  };

  return {
    createDatasetMutation,
    datasetDescription,
    datasetName,
    datasetSource,
    datasetSummary,
    datasetVersion,
    datasetVersionLabel,
    datasets,
    datasetsQuery,
    exportEligibleCount,
    feedback,
    fileInputRef,
    filteredRows,
    handleDatasetUpload,
    handleImportPendingUpload,
    latestImportedDatasetVersionId,
    pendingUpload,
    previewRows,
    selectedDataset,
    selectedDatasetRecord,
    setDatasetDescription,
    setDatasetName,
    setDatasetSource,
    setDatasetVersion,
    setSelectedDataset,
    setSliceFilter,
    setSourceFilter,
    setTagFilter,
    sliceFilter,
    sliceOptions,
    sourceFilter,
    sourceOptions,
    tagFilter,
    tagOptions,
    totalSamples,
    clearPendingUpload
  };
}
