import { expect, test, type APIRequestContext } from "@playwright/test";

type ApiRun = {
  run_id: string;
  status: "queued" | "running" | "succeeded" | "failed" | "terminated";
};

const liveEnabled = process.env.AFLIGHT_E2E_LIVE === "1";
const apiBaseUrl = process.env.AFLIGHT_API_BASE_URL ?? "http://127.0.0.1:8000";
const runTimeoutMs = Number(process.env.AFLIGHT_LIVE_RUN_TIMEOUT_MS ?? 120000);
const pollIntervalMs = 500;

function sleep(milliseconds: number) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

function isTerminalStatus(status: ApiRun["status"]) {
  return status === "succeeded" || status === "failed" || status === "terminated";
}

async function createRun(
  request: APIRequestContext,
  payload: {
    project: string;
    dataset: string;
    model: string;
    agent_type: "openai-agents-sdk";
    input_summary: string;
    prompt: string;
    tags?: string[];
  }
) {
  const response = await request.post(`${apiBaseUrl}/api/v1/runs`, { data: payload });
  expect(response.ok()).toBeTruthy();
  return (await response.json()) as ApiRun & { created_at: string };
}

async function waitForRunTerminal(request: APIRequestContext, runId: string) {
  const deadline = Date.now() + runTimeoutMs;

  while (Date.now() < deadline) {
    const response = await request.get(`${apiBaseUrl}/api/v1/runs/${runId}`);
    expect(response.ok()).toBeTruthy();
    const run = (await response.json()) as ApiRun & { latency_ms: number; token_cost: number };

    if (isTerminalStatus(run.status)) {
      return run;
    }

    await sleep(pollIntervalMs);
  }

  throw new Error(`run ${runId} did not reach a terminal state within ${runTimeoutMs}ms`);
}

test.describe("live smoke", () => {
  test.skip(!liveEnabled, "set AFLIGHT_E2E_LIVE=1 to run the real backend smoke");

  test("trajectory diff uses the previous comparable live run", async ({ page, request }) => {
    const scope = `live-diff-${Date.now()}`;
    const comparableRun = {
      project: scope,
      dataset: `${scope}-dataset`,
      model: "gpt-4.1-mini",
      agent_type: "openai-agents-sdk" as const,
      input_summary: "reply with the token alpha",
      prompt: "Reply with exactly one token: alpha",
      tags: ["live", "smoke", "diff"]
    };

    const previousRun = await createRun(request, comparableRun);
    const previousState = await waitForRunTerminal(request, previousRun.run_id);
    expect(previousState.status).toBe("succeeded");

    const unrelatedRun = await createRun(request, {
      ...comparableRun,
      project: `${scope}-seed`,
      dataset: `${scope}-seed-dataset`,
      input_summary: "seed control run",
      prompt: "Reply with exactly one token: seed"
    });
    const unrelatedState = await waitForRunTerminal(request, unrelatedRun.run_id);
    expect(unrelatedState.status).toBe("succeeded");

    const currentRun = await createRun(request, comparableRun);
    const currentState = await waitForRunTerminal(request, currentRun.run_id);
    expect(currentState.status).toBe("succeeded");

    await page.goto(`/runs/${currentRun.run_id}`);
    await expect(page.getByRole("heading", { name: "Trajectory viewer" })).toBeVisible();
    await page.getByRole("button", { name: "Diff with previous run" }).click();

    await expect(page.getByText(new RegExp(`Compared with ${previousRun.run_id.slice(0, 8)}`))).toBeVisible();
    await expect(page.getByText(new RegExp(`Compared with ${unrelatedRun.run_id.slice(0, 8)}`))).toHaveCount(0);
  });
});
