import { expect, test } from "@playwright/test";
import { buildRun, buildTrajectoryStep, mockRunsIndex, mockTrajectory } from "./support/mockApi";

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

  await mockRunsIndex(page, {
    list: () => runs,
    create: () => {
      const newRun = buildRun({
        run_id: "run-002",
        input_summary: "Manual run from playground",
        status: "queued",
        latency_ms: 15,
        token_cost: 12,
        tool_calls: 0,
        project: "playground",
        tags: ["ui"],
        created_at: new Date().toISOString()
      });
      runs = [newRun, ...runs];
      return newRun;
    }
  });

  await mockTrajectory(page, "run-002", [
    buildTrajectoryStep({
      id: "run-002-step-1",
      run_id: "run-002",
      output: "playground planner output",
      model: null
    })
  ]);

  await page.goto("http://127.0.0.1:3000/playground");
  await expect(page.getByRole("heading", { name: "Playground" })).toBeVisible();

  await page.getByRole("button", { name: "Attach dataset sample" }).click();
  await expect(page.locator("textarea").filter({ hasText: "Can you create a shipping itinerary?" })).toBeVisible();

  await page.getByRole("button", { name: "Run now" }).click();
  await expect(page.getByText(/run_id:\s*run-002/)).toBeVisible();

  await page.getByRole("button", { name: "Open latest trace" }).click();
  await expect(
    page.getByText(/run-002-step-1 \| planner \| playground planner output/)
  ).toBeVisible();
});
