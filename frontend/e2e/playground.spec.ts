import { expect, test } from "@playwright/test";
import { buildDataset, buildRun, mockCatalog, mockRunTraces, mockRunsIndex } from "./support/mockApi";

test("playground can launch a run and open the latest trace", async ({ page }) => {
  let runs = [
    buildRun({
      run_id: "run-001",
      input_summary: "seed run",
      project: "playground",
      tags: ["ui"],
      created_at: "2026-03-24T00:00:00Z"
    })
  ];
  const createdRun = buildRun({
    run_id: "run-002",
    input_summary: "Manual run from playground",
    status: "succeeded",
    latency_ms: 15,
    token_cost: 12,
    tool_calls: 0,
    project: "playground",
    dataset: "crm-v2",
    tags: ["ui"],
    created_at: "2026-03-24T00:01:00Z"
  });

  await mockCatalog(page, {
    datasets: [buildDataset({ name: "crm-v2" })]
  });
  await mockRunsIndex(page, {
    list: () => runs,
    create: () => {
      runs = [createdRun, ...runs];
      return createdRun;
    }
  });
  await mockRunTraces(page, "run-002", [
    {
      run_id: "run-002",
      span_id: "trace-1",
      parent_span_id: null,
      step_type: "planner",
      input: {},
      output: { output: "playground planner output" },
      latency_ms: 12,
      token_usage: 0,
      received_at: "2026-03-24T00:01:00Z"
    }
  ]);

  await page.goto("http://127.0.0.1:3000/playground");
  await expect(page.getByRole("heading", { name: "Playground" })).toBeVisible();
  await expect(page.getByLabel("Dataset")).toContainText("crm-v2");

  await page.getByLabel("Dataset").selectOption("crm-v2");
  await page.getByRole("button", { name: "Attach dataset sample" }).click();
  await expect(page.locator("textarea").filter({ hasText: "Can you create a shipping itinerary?" })).toBeVisible();

  await page.getByRole("button", { name: "Run now" }).click();
  await expect(page.getByText(/run_id:\s*run-002/)).toBeVisible();

  await page.getByRole("button", { name: "Refresh live trace" }).click();
  await expect(page.getByText(/trace-1 \| planner \| playground planner output/)).toBeVisible();
});
