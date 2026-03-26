import type { RunRecord } from "./model";

export function formatRunDate(date: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(date));
}

function readPrompt(projectMetadata: RunRecord["projectMetadata"], fallback: string) {
  const prompt = projectMetadata?.prompt;
  return typeof prompt === "string" && prompt.trim() ? prompt.trim() : fallback;
}

export function buildPlaygroundRerunHref(run: RunRecord) {
  const params = new URLSearchParams();

  if (run.agentId) {
    params.set("agent", run.agentId);
  }
  if (run.dataset) {
    params.set("dataset", run.dataset);
  }
  params.set("prompt", readPrompt(run.projectMetadata, run.inputSummary));
  if (run.tags.length) {
    params.set("tags", run.tags.join(","));
  }

  const query = params.toString();
  return query ? `/playground?${query}` : "/playground";
}
