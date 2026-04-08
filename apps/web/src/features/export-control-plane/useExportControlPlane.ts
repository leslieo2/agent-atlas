"use client";

import { useEffect, useMemo, useState } from "react";
import {
  buildCompareLookup,
  matchesRunPreviewFilters,
  resolveRunCompareOutcome
} from "@/src/entities/experiment/compare";
import { useCreateExportMutation, useExportsQuery } from "@/src/entities/export/query";
import { useExperimentCompareQuery, useExperimentRunsQuery, useExperimentsQuery } from "@/src/entities/experiment/query";
import type { CompareOutcome, CurationStatus, SampleJudgement } from "@/src/shared/api/contract";
import { buildActiveFilters, uniqueStrings } from "./model";

type Args = {
  initialExperimentId?: string;
  initialBaselineExperimentId?: string;
  initialCandidateExperimentId?: string;
};

export function useExportControlPlane({
  initialExperimentId = "",
  initialBaselineExperimentId = "",
  initialCandidateExperimentId = ""
}: Args) {
  const experimentsQuery = useExperimentsQuery();
  const exportsQuery = useExportsQuery();
  const createExportMutation = useCreateExportMutation();

  const [experimentId, setExperimentId] = useState(initialExperimentId);
  const [baselineExperimentId, setBaselineExperimentId] = useState(initialBaselineExperimentId);
  const [candidateExperimentId, setCandidateExperimentId] = useState(initialCandidateExperimentId);
  const [judgementFilter, setJudgementFilter] = useState<SampleJudgement | "">("");
  const [errorCodeFilter, setErrorCodeFilter] = useState("");
  const [sliceFilter, setSliceFilter] = useState("");
  const [tagFilter, setTagFilter] = useState("");
  const [compareOutcomeFilter, setCompareOutcomeFilter] = useState<CompareOutcome | "">("");
  const [curationFilter, setCurationFilter] = useState<CurationStatus | "">("");
  const [exportEligibleOnly, setExportEligibleOnly] = useState(true);
  const [format, setFormat] = useState<"jsonl" | "parquet">("jsonl");
  const [actionMessage, setActionMessage] = useState("");
  const [latestExportId, setLatestExportId] = useState<string | null>(null);

  const experiments = useMemo(() => experimentsQuery.data ?? [], [experimentsQuery.data]);
  const selectedSourceExperimentId = candidateExperimentId || experimentId;
  const sourceExperiment = useMemo(
    () => experiments.find((record) => record.experimentId === selectedSourceExperimentId) ?? null,
    [experiments, selectedSourceExperimentId]
  );
  const selectedRunsQuery = useExperimentRunsQuery(selectedSourceExperimentId);
  const compareQuery = useExperimentCompareQuery(baselineExperimentId, candidateExperimentId);
  const runs = useMemo(() => selectedRunsQuery.data ?? [], [selectedRunsQuery.data]);
  const compareLookup = useMemo(() => buildCompareLookup(compareQuery.data?.samples ?? []), [compareQuery.data?.samples]);

  const errorCodeOptions = useMemo(() => uniqueStrings(runs.map((run) => run.errorCode)), [runs]);
  const sliceOptions = useMemo(() => uniqueStrings(runs.map((run) => run.slice)), [runs]);
  const tagOptions = useMemo(() => uniqueStrings(runs.flatMap((run) => run.tags)), [runs]);
  const previewRows = useMemo(
    () =>
      runs.filter((run) =>
        matchesRunPreviewFilters({
          run,
          compareOutcome: resolveRunCompareOutcome(run, compareLookup),
          judgementFilter,
          errorCodeFilter,
          sliceFilter,
          tagFilter,
          compareOutcomeFilter,
          curationFilter,
          exportEligibleOnly
        })
      ),
    [
      runs,
      compareLookup,
      judgementFilter,
      errorCodeFilter,
      sliceFilter,
      tagFilter,
      compareOutcomeFilter,
      curationFilter,
      exportEligibleOnly
    ]
  );
  const previewReviewCount = useMemo(
    () => previewRows.filter((run) => run.curationStatus === "review").length,
    [previewRows]
  );
  const activeFilters = useMemo(
    () =>
      buildActiveFilters({
        judgementFilter,
        errorCodeFilter,
        sliceFilter,
        tagFilter,
        compareOutcomeFilter,
        curationFilter,
        exportEligibleOnly
      }),
    [judgementFilter, errorCodeFilter, sliceFilter, tagFilter, compareOutcomeFilter, curationFilter, exportEligibleOnly]
  );
  const baselineOptions = useMemo(
    () =>
      sourceExperiment
        ? experiments.filter(
            (record) =>
              record.datasetVersionId === sourceExperiment.datasetVersionId &&
              record.experimentId !== sourceExperiment.experimentId
          )
        : [],
    [experiments, sourceExperiment]
  );

  useEffect(() => {
    setExperimentId(initialExperimentId);
  }, [initialExperimentId]);

  useEffect(() => {
    setBaselineExperimentId(initialBaselineExperimentId);
  }, [initialBaselineExperimentId]);

  useEffect(() => {
    setCandidateExperimentId(initialCandidateExperimentId);
  }, [initialCandidateExperimentId]);

  useEffect(() => {
    if (!selectedSourceExperimentId && experiments[0]) {
      setExperimentId(experiments[0].experimentId);
    }
  }, [experiments, selectedSourceExperimentId]);

  useEffect(() => {
    if (candidateExperimentId) {
      return;
    }

    if (baselineExperimentId && baselineOptions.some((record) => record.experimentId === baselineExperimentId)) {
      return;
    }

    setBaselineExperimentId("");
  }, [baselineExperimentId, baselineOptions, candidateExperimentId]);

  const handleCreateExport = async () => {
    if (!selectedSourceExperimentId) {
      setActionMessage("Select an experiment source before creating an export.");
      return;
    }

    const exported = await createExportMutation.mutateAsync({
      experimentId: candidateExperimentId ? null : experimentId || null,
      baselineExperimentId: baselineExperimentId || null,
      candidateExperimentId: candidateExperimentId || null,
      datasetSampleIds: previewRows.map((run) => run.datasetSampleId),
      judgements: judgementFilter ? [judgementFilter] : null,
      errorCodes: errorCodeFilter ? [errorCodeFilter] : null,
      compareOutcomes: compareOutcomeFilter ? [compareOutcomeFilter] : null,
      tags: tagFilter ? [tagFilter] : null,
      slices: sliceFilter ? [sliceFilter] : null,
      curationStatuses: curationFilter ? [curationFilter] : null,
      exportEligible: exportEligibleOnly,
      format
    });

    setLatestExportId(exported.exportId);
    setActionMessage(`Created export ${exported.exportId}.`);
  };

  const handleResetFilters = () => {
    setJudgementFilter("");
    setErrorCodeFilter("");
    setSliceFilter("");
    setTagFilter("");
    setCompareOutcomeFilter("");
    setCurationFilter("");
    setExportEligibleOnly(true);
  };

  return {
    actionMessage,
    activeFilters,
    baselineExperimentId,
    baselineOptions,
    candidateExperimentId,
    compareOutcomeFilter,
    createExportMutation,
    curationFilter,
    errorCodeFilter,
    errorCodeOptions,
    experimentId,
    experiments,
    exportEligibleOnly,
    exportsQuery,
    format,
    handleCreateExport,
    handleResetFilters,
    judgementFilter,
    latestExportId,
    previewReviewCount,
    previewRows,
    runs,
    selectedRunsQuery,
    setBaselineExperimentId,
    setCandidateExperimentId,
    setCompareOutcomeFilter,
    setCurationFilter,
    setErrorCodeFilter,
    setExperimentId,
    setExportEligibleOnly,
    setFormat,
    setJudgementFilter,
    setSliceFilter,
    setTagFilter,
    sliceFilter,
    sliceOptions,
    sourceExperiment,
    tagFilter,
    tagOptions
  };
}
