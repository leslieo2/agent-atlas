import { expect, test } from "@playwright/test";
import { buildDataset, buildRun, mockCatalog, mockRunsIndex } from "./support/mockApi";

test("dashboard supports create run and export jsonl/parquet artifacts", async ({ page }) => {
  let runs = [buildRun()];
  const exportCalls: Array<{ format: string; runIds: string[] }> = [];

  await mockCatalog(page, {
    datasets: [buildDataset({ name: "crm-v2" })]
  });
  await mockRunsIndex(page, {
    list: () => runs
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
  await expect(page.getByText("Loaded 1 runs.")).toBeVisible();
  await expect(page.getByRole("link", { name: "run-001" })).toBeVisible();

  await expect(page.getByRole("link", { name: "New Run" })).toHaveAttribute("href", "/playground?dataset=crm-v2");

  await page.getByRole("button", { name: "Export 1 run as JSONL" }).click();
  await expect(page.getByText("Exported 1 run as JSONL.")).toBeVisible();

  await page.getByRole("button", { name: "Export 1 run as Parquet" }).click();
  await expect(page.getByText("Exported 1 run as Parquet.")).toBeVisible();

  expect(exportCalls).toEqual([
    { format: "jsonl", runIds: ["run-001"] },
    { format: "parquet", runIds: ["run-001"] }
  ]);
});
