import { expect, test } from "@playwright/test";
import { buildRun, mockRunsIndex } from "./support/mockApi";

test("dashboard supports create run and export jsonl/parquet artifacts", async ({ page }) => {
  let runs = [buildRun()];
  let nextRunId = 2;
  const exportCalls: Array<{ format: string; runIds: string[] }> = [];

  await mockRunsIndex(page, {
    list: () => runs,
    create: () => {
      const newRun = buildRun({
        run_id: `run-${String(nextRunId).padStart(3, "0")}`,
        input_summary: "Manual run from dashboard",
        status: "queued",
        latency_ms: 12,
        token_cost: 11,
        tool_calls: 0,
        project: "workbench",
        tags: ["ui"],
        created_at: new Date().toISOString()
      });
      nextRunId += 1;
      runs = [newRun, ...runs];
      return newRun;
    }
  });

  await page.route("**/api/v1/artifacts/export", async (route) => {
    const payload = route.request().postDataJSON() as {
      run_ids: string[];
      format?: "jsonl" | "parquet";
    };
    const format = payload.format ?? "jsonl";
    exportCalls.push({ format, runIds: payload.run_ids });
    const artifact =
      format === "parquet"
        ? {
            artifact_id: "artifact-002",
            path: "/tmp/artifact-002.parquet",
            size_bytes: 2048
          }
        : {
            artifact_id: "artifact-001",
            path: "/tmp/artifact-001.jsonl",
            size_bytes: 1234
          };
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(artifact)
    });
  });

  await page.goto("http://127.0.0.1:3000/runs");
  await expect(page.getByRole("heading", { name: "Run dashboard" })).toBeVisible();
  await expect(page.getByText("run-001")).toBeVisible();

  await page.getByRole("button", { name: "New Run" }).click();
  await expect(page.getByText(/Created run run-002/)).toBeVisible();

  await page.getByRole("button", { name: "Export JSONL" }).click();
  await expect(page.getByText(/Exported artifact-001/)).toBeVisible();

  await page.getByRole("button", { name: "Export Parquet" }).click();
  await expect(page.getByText(/Exported artifact-002/)).toBeVisible();

  expect(exportCalls).toEqual([
    { format: "jsonl", runIds: ["run-002"] },
    { format: "parquet", runIds: ["run-002"] }
  ]);
});
