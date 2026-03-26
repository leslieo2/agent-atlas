import type { Page, Route } from "@playwright/test";

export type ApiAgent = {
  agent_id: string;
  name: string;
  description: string;
  framework: string;
  entrypoint: string;
  default_model: string;
  tags: string[];
};

export type ApiDataset = {
  name: string;
  rows: Array<{
    sample_id: string;
    input: string;
    expected?: string | null;
    tags?: string[];
  }>;
};

export type ApiRun = {
  run_id: string;
  input_summary: string;
  status: "queued" | "running" | "succeeded" | "failed";
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

export type ApiTrajectoryStep = {
  id: string;
  run_id: string;
  step_type: "llm" | "tool" | "planner" | "memory";
  prompt: string;
  output: string;
  model: string | null;
  temperature: number;
  latency_ms: number;
  token_usage: number;
  success: boolean;
  tool_name?: string | null;
};

const json = async (route: Route, body: unknown, status = 200) =>
  route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body)
  });

export const buildAgent = (overrides: Partial<ApiAgent> = {}): ApiAgent => ({
  agent_id: "basic",
  name: "Basic",
  description: "Minimal smoke agent.",
  framework: "openai-agents-sdk",
  entrypoint: "app.agent_plugins.basic:build_agent",
  default_model: "gpt-4.1-mini",
  tags: ["example", "smoke"],
  ...overrides
});

export const buildDataset = (overrides: Partial<ApiDataset> = {}): ApiDataset => ({
  name: "crm-v2",
  rows: [{ sample_id: "sample-001", input: "Can you create a shipping itinerary?" }],
  ...overrides
});

export const buildRun = (overrides: Partial<ApiRun> = {}): ApiRun => ({
  run_id: "run-001",
  input_summary: "Generate a booking itinerary from CRM contact data",
  status: "succeeded",
  latency_ms: 1410,
  token_cost: 1280,
  tool_calls: 5,
  project: "sales-assistant",
  dataset: "crm-v2",
  model: "gpt-4.1-mini",
  agent_type: "openai-agents-sdk",
  tags: ["agent-sdk", "mcp"],
  created_at: "2026-03-23T09:12:00Z",
  ...overrides
});

export const buildTrajectoryStep = (
  overrides: Partial<ApiTrajectoryStep> = {}
): ApiTrajectoryStep => ({
  id: "s1",
  run_id: "run-001",
  step_type: "planner",
  prompt: "plan",
  output: "current planner output",
  model: null,
  temperature: 0,
  latency_ms: 10,
  token_usage: 5,
  success: true,
  ...overrides
});

export async function mockCatalog(
  page: Page,
  {
    agents = [buildAgent()],
    datasets = [buildDataset()]
  }: {
    agents?: ApiAgent[];
    datasets?: ApiDataset[];
  } = {}
) {
  await page.route("**/api/v1/agents", async (route) => json(route, agents));
  await page.route("**/api/v1/datasets", async (route) => json(route, datasets));
}

export async function mockRunsIndex(
  page: Page,
  handlers: {
    list: () => ApiRun[];
    create?: () => ApiRun;
    detail?: (runId: string) => ApiRun | undefined;
  }
) {
  await page.route("**/api/v1/runs", async (route) => {
    if (route.request().method() === "POST" && handlers.create) {
      return json(route, handlers.create(), 201);
    }
    return json(route, handlers.list());
  });

  await page.route("**/api/v1/runs/*", async (route) => {
    const url = new URL(route.request().url());
    const runId = url.pathname.split("/").pop() ?? "";
    const run = handlers.detail?.(runId);

    if (!run) {
      return route.fallback();
    }

    return json(route, run);
  });
}

export async function mockTrajectory(page: Page, runId: string, steps: ApiTrajectoryStep[]) {
  await page.route(`**/api/v1/runs/${runId}/trajectory`, async (route) => json(route, steps));
}

export async function mockRunTraces(
  page: Page,
  runId: string,
  traces: Array<{
    run_id: string;
    span_id: string;
    parent_span_id?: string | null;
    step_type: "llm" | "tool" | "planner" | "memory";
    input: Record<string, unknown>;
    output: { output?: string } | Record<string, unknown>;
    latency_ms: number;
    token_usage: number;
    received_at: string;
  }>
) {
  await page.route(`**/api/v1/runs/${runId}/traces`, async (route) => json(route, traces));
}

export async function mockArtifactExport(
  page: Page,
  artifact: { artifact_id: string; path: string; size_bytes: number }
) {
  await page.route("**/api/v1/artifacts/export", async (route) => json(route, artifact));
}
