import { expect, test } from "@playwright/test";
import { buildRun, buildTrajectoryStep, mockRunsIndex, mockTrajectory } from "./support/mockApi";

test("trajectory page renders steps and can diff with previous run", async ({ page }) => {
  await mockRunsIndex(page, {
    list: () => [
      buildRun({
        run_id: "run-001",
        input_summary: "current run",
        latency_ms: 20,
        token_cost: 5,
        tool_calls: 2,
        project: "project-a",
        tags: ["ui"],
        created_at: "2026-03-24T01:00:00Z"
      }),
      buildRun({
        run_id: "run-000",
        input_summary: "current run",
        status: "failed",
        latency_ms: 12,
        token_cost: 3,
        tool_calls: 1,
        project: "project-a",
        tags: ["ui"],
        created_at: "2026-03-23T21:00:00Z"
      })
    ]
  });
  await mockTrajectory(page, "run-001", [buildTrajectoryStep()]);
  await mockTrajectory(
    page,
    "run-000",
    [
      buildTrajectoryStep({
        id: "p1",
        run_id: "run-000",
        prompt: "old plan",
        output: "previous planner output",
        latency_ms: 6,
        token_usage: 3
      })
    ]
  );

  await page.goto("http://127.0.0.1:3000/runs/run-001");
  await expect(page.getByRole("heading", { name: "Trajectory viewer" })).toBeVisible();
  await expect(page.getByText("Loaded 1 steps.")).toBeVisible();
  await expect(page.getByRole("button", { name: "s1 · PLANNER" })).toBeVisible();
  await page.getByRole("button", { name: "Diff with previous run" }).click();
  await expect(page.getByText(/Compared with run-000/)).toBeVisible();
});
