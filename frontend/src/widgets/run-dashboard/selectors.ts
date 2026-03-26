import type { RunRecord } from "@/src/entities/run/model";

export function filterRuns(runRecords: RunRecord[], query: string) {
  const needle = query.trim().toLowerCase();

  return runRecords.filter((run) =>
    needle
      ? [run.inputSummary, run.runId, run.project, run.dataset ?? "", run.agentId].join(" ").toLowerCase().includes(needle)
      : true
  );
}

export function getFilterOptions(runRecords: RunRecord[]) {
  return {
    projects: Array.from(new Set(runRecords.map((run) => run.project))),
    datasets: Array.from(new Set(runRecords.map((run) => run.dataset).filter((dataset): dataset is string => Boolean(dataset)))),
    agents: Array.from(new Set(runRecords.map((run) => run.agentId).filter(Boolean))),
    models: Array.from(new Set(runRecords.map((run) => run.model))),
    tags: Array.from(new Set(runRecords.flatMap((run) => run.tags)))
  };
}

export function getRunStats(runRecords: RunRecord[]) {
  const failed = runRecords.filter((run) => run.status === "failed").length;
  const running = runRecords.filter((run) => run.status === "running").length;
  const avgLatency =
    runRecords.reduce((total, run) => total + run.latencyMs, 0) / Math.max(runRecords.length, 1);

  return {
    total: runRecords.length,
    failed,
    running,
    avgLatency: Math.round(avgLatency)
  };
}
