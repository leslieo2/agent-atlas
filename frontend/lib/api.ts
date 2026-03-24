"use client";

export type RunStatus = "queued" | "running" | "succeeded" | "failed";

type ApiRunRecord = {
  run_id: string;
  input_summary: string;
  status: RunStatus;
  latency_ms: number;
  token_cost: number;
  tool_calls: number;
  project: string;
  dataset: string;
  model: string;
  agent_type: string;
  tags: string[];
  created_at: string;
};

type ApiTrajectoryStep = {
  id: string;
  run_id: string;
  step_type: "llm" | "tool" | "planner" | "memory";
  prompt: string;
  output: string;
  model: string;
  temperature: number;
  latency_ms: number;
  token_usage: number;
  success: boolean;
  tool_name?: string | null;
};

type ApiReplayResult = {
  replay_id: string;
  run_id: string;
  step_id: string;
  baseline_output: string;
  replay_output: string;
  diff: string;
  updated_prompt?: string | null;
  model: string;
  temperature: number;
  started_at: string;
};

type ApiDataset = {
  name: string;
  rows: Array<{ sample_id: string; input: string }>;
};

type ApiEvalResult = {
  sample_id: string;
  run_id: string;
  input: string;
  status: "pass" | "fail" | "running";
  score: number;
  reason?: string | null;
};

type ApiEvalJob = {
  job_id: string;
  run_ids: string[];
  dataset: string;
  status: string;
  results: ApiEvalResult[];
  created_at: string;
};

type ApiArtifact = {
  artifact_id: string;
  path: string;
  size_bytes: number;
};

export interface RunRecord {
  runId: string;
  inputSummary: string;
  status: RunStatus;
  latencyMs: number;
  tokenCost: number;
  toolCalls: number;
  project: string;
  dataset: string;
  model: string;
  agentType: string;
  tags: string[];
  createdAt: string;
}

export interface RunListFilters {
  status?: RunStatus;
  project?: string;
  dataset?: string;
  model?: string;
  tag?: string;
  createdFrom?: string;
  createdTo?: string;
}

export interface TrajectoryStep {
  id: string;
  runId: string;
  stepType: "llm" | "tool" | "planner" | "memory";
  prompt: string;
  output: string;
  model: string;
  temperature: number;
  latencyMs: number;
  tokenUsage: number;
  success: boolean;
  toolName?: string | null;
}

export interface ReplayResult {
  replayId: string;
  runId: string;
  stepId: string;
  baselineOutput: string;
  replayOutput: string;
  diff: string;
  updatedPrompt?: string | null;
  model: string;
  temperature: number;
  startedAt: string;
}

export interface Dataset {
  name: string;
  rows: Array<{ sampleId: string; input: string }>;
}

export interface EvalResult {
  sampleId: string;
  runId: string;
  input: string;
  status: "pass" | "fail" | "running";
  score: number;
  reason?: string | null;
}

export interface EvalJob {
  jobId: string;
  runIds: string[];
  dataset: string;
  status: string;
  results: EvalResult[];
  createdAt: string;
}

export interface ArtifactExport {
  artifactId: string;
  path: string;
  sizeBytes: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    cache: "no-store"
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

function mapRun(run: ApiRunRecord): RunRecord {
  return {
    runId: run.run_id,
    inputSummary: run.input_summary,
    status: run.status,
    latencyMs: run.latency_ms,
    tokenCost: run.token_cost,
    toolCalls: run.tool_calls,
    project: run.project,
    dataset: run.dataset,
    model: run.model,
    agentType: run.agent_type,
    tags: run.tags,
    createdAt: run.created_at
  };
}

function mapStep(step: ApiTrajectoryStep): TrajectoryStep {
  return {
    id: step.id,
    runId: step.run_id,
    stepType: step.step_type,
    prompt: step.prompt,
    output: step.output,
    model: step.model,
    temperature: step.temperature,
    latencyMs: step.latency_ms,
    tokenUsage: step.token_usage,
    success: step.success,
    toolName: step.tool_name
  };
}

function mapReplay(result: ApiReplayResult): ReplayResult {
  return {
    replayId: result.replay_id,
    runId: result.run_id,
    stepId: result.step_id,
    baselineOutput: result.baseline_output,
    replayOutput: result.replay_output,
    diff: result.diff,
    updatedPrompt: result.updated_prompt,
    model: result.model,
    temperature: result.temperature,
    startedAt: result.started_at
  };
}

function mapDataset(dataset: ApiDataset): Dataset {
  return {
    name: dataset.name,
    rows: dataset.rows.map((row) => ({ sampleId: row.sample_id, input: row.input }))
  };
}

function mapEvalResult(result: ApiEvalResult): EvalResult {
  return {
    sampleId: result.sample_id,
    runId: result.run_id,
    input: result.input,
    status: result.status,
    score: result.score,
    reason: result.reason
  };
}

function mapEvalJob(job: ApiEvalJob): EvalJob {
  return {
    jobId: job.job_id,
    runIds: job.run_ids,
    dataset: job.dataset,
    status: job.status,
    results: job.results.map(mapEvalResult),
    createdAt: job.created_at
  };
}

function mapArtifact(artifact: ApiArtifact): ArtifactExport {
  return {
    artifactId: artifact.artifact_id,
    path: artifact.path,
    sizeBytes: artifact.size_bytes
  };
}

export async function listRuns(filters: RunListFilters = {}) {
  const query = new URLSearchParams();
  if (filters.status) query.set("status", filters.status);
  if (filters.project) query.set("project", filters.project);
  if (filters.dataset) query.set("dataset", filters.dataset);
  if (filters.model) query.set("model", filters.model);
  if (filters.tag) query.set("tag", filters.tag);
  if (filters.createdFrom) query.set("created_from", filters.createdFrom);
  if (filters.createdTo) query.set("created_to", filters.createdTo);
  const suffix = query.toString();
  const path = suffix ? `/api/v1/runs?${suffix}` : "/api/v1/runs";
  return (await request<ApiRunRecord[]>(path)).map(mapRun);
}

export async function getTrajectory(runId: string) {
  return (await request<ApiTrajectoryStep[]>(`/api/v1/runs/${runId}/trajectory`)).map(mapStep);
}

export async function createReplay(payload: {
  runId: string;
  stepId: string;
  editedPrompt?: string;
  model?: string;
  toolOverrides?: Record<string, unknown>;
  rationale?: string;
}) {
  return mapReplay(
    await request<ApiReplayResult>("/api/v1/replays", {
      method: "POST",
      body: JSON.stringify({
        run_id: payload.runId,
        step_id: payload.stepId,
        edited_prompt: payload.editedPrompt,
        model: payload.model,
        tool_overrides: payload.toolOverrides ?? {},
        rationale: payload.rationale
      })
    })
  );
}

export async function listDatasets() {
  return (await request<ApiDataset[]>("/api/v1/datasets")).map(mapDataset);
}

export async function createDataset(payload: {
  name: string;
  rows: Array<{ sampleId: string; input: string; expected?: string | null; tags?: string[] }>;
}) {
  return mapDataset(
    await request<ApiDataset>("/api/v1/datasets", {
      method: "POST",
      body: JSON.stringify({
        name: payload.name,
        rows: payload.rows.map((row) => ({
          sample_id: row.sampleId,
          input: row.input,
          expected: row.expected ?? null,
          tags: row.tags ?? []
        }))
      })
    })
  );
}

export async function createEvalJob(payload: {
  runIds: string[];
  dataset: string;
  evaluators?: string[];
}) {
  return mapEvalJob(
    await request<ApiEvalJob>("/api/v1/eval-jobs", {
      method: "POST",
      body: JSON.stringify({
        run_ids: payload.runIds,
        dataset: payload.dataset,
        evaluators: payload.evaluators ?? []
      })
    })
  );
}

export async function createRun(payload: {
  project: string;
  dataset: string;
  model: string;
  agentType: string;
  inputSummary: string;
  prompt: string;
  tags?: string[];
}) {
  return mapRun(
    await request<ApiRunRecord>("/api/v1/runs", {
      method: "POST",
      body: JSON.stringify({
        project: payload.project,
        dataset: payload.dataset,
        model: payload.model,
        agent_type: payload.agentType,
        input_summary: payload.inputSummary,
        prompt: payload.prompt,
        tags: payload.tags ?? []
      })
    })
  );
}

export async function exportArtifact(payload: { runIds: string[]; format?: "jsonl" | "parquet" }) {
  return mapArtifact(
    await request<ApiArtifact>("/api/v1/artifacts/export", {
      method: "POST",
      body: JSON.stringify({
        run_ids: payload.runIds,
        format: payload.format ?? "jsonl"
      })
    })
  );
}
