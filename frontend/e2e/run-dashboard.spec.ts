import { expect, test } from "@playwright/test";
import { buildRun, mockArtifactExport, mockRunsIndex } from "./support/mockApi";

test("dashboard supports create run and export artifact", async ({ page }) => {
  let runs = [buildRun()];
  let nextRunId = 2;

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

  await mockArtifactExport(page, {
    artifact_id: "artifact-001",
    path: "/tmp/artifact-001.jsonl",
    size_bytes: 1234
  });

  await page.goto("http://127.0.0.1:3000/");
  await expect(page.getByRole("heading", { name: "Run dashboard" })).toBeVisible();
  await expect(page.getByText("run-001")).toBeVisible();

  await page.getByRole("button", { name: "New Run" }).click();
  await expect(page.getByText(/Created run run-002/)).toBeVisible();

  await page.getByRole("button", { name: "Export JSONL" }).click();
  await expect(page.getByText(/Exported artifact-001/)).toBeVisible();
});
