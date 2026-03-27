import { expect, test } from "@playwright/test";
import {
  buildDataset,
  buildEvalJob,
  buildEvalSample,
  buildRun,
  mockCatalog,
  mockEvals
} from "./support/mockApi";

test("playground can create an eval job and open eval workspace details", async ({ page }) => {
  const exportCalls: Array<{ format: string; runIds: string[] }> = [];
  let evalJobs = [
    buildEvalJob({
      eval_job_id: "eval-001",
      project: "nightly-regression"
    })
  ];

  await mockCatalog(page, {
    agents: [
      {
        agent_id: "basic",
        name: "Basic",
        description: "Minimal smoke agent.",
        framework: "openai-agents-sdk",
        entrypoint: "app.agent_plugins.basic:build_agent",
        default_model: "gpt-5.4-mini",
        tags: ["example", "smoke"]
      }
    ],
    datasets: [buildDataset({ name: "crm-v2" })]
  });

  await page.route("**/api/v1/runs", async (route) => {
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        buildRun({
          run_id: "run-002",
          project: "nightly-regression",
          dataset: "crm-v2",
          created_at: "2026-03-24T00:00:00Z"
        })
      ])
    });
  });

  await mockEvals(page, {
    list: () => evalJobs,
    create: () => {
      const created = buildEvalJob({
        eval_job_id: "eval-002",
        project: "crm-v2",
        status: "queued",
        sample_count: 1,
        scored_count: 0,
        passed_count: 0,
        failed_count: 0,
        unscored_count: 0,
        runtime_error_count: 0,
        pass_rate: 0,
        failure_distribution: {}
      });
      evalJobs = [created, ...evalJobs];
      return created;
    },
    samples: (evalJobId) =>
      evalJobId === "eval-001"
        ? [
            buildEvalSample({
              eval_job_id: "eval-001",
              dataset_sample_id: "sample-fail",
              run_id: "run-003",
              judgement: "failed",
              input: "beta",
              expected: "beta",
              actual: "not-beta",
              failure_reason: "actual output did not exactly match expected output",
              error_code: "mismatch"
            }),
            buildEvalSample({
              eval_job_id: "eval-001",
              dataset_sample_id: "sample-runtime",
              run_id: "run-002"
            })
          ]
        : []
  });
  await page.route("**/api/v1/artifacts/export", async (route) => {
    const payload = route.request().postDataJSON();
    exportCalls.push({
      format: payload.format,
      runIds: payload.run_ids
    });
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        artifact_id: "artifact-eval-001",
        format: "jsonl",
        run_ids: payload.run_ids,
        created_at: "2026-03-24T00:05:00Z",
        path: "/tmp/eval-failures.jsonl",
        size_bytes: 64
      })
    });
  });

  await page.goto("/playground?agent=basic&dataset=crm-v2");
  await expect(page.getByRole("heading", { name: "Playground", exact: true })).toBeVisible();

  await expect(page.getByRole("button", { name: "Create eval job" })).toBeEnabled();
  await page.getByRole("button", { name: "Create eval job" }).click();
  await expect(page.getByText("Eval job eval-002 is queued.")).toBeVisible();

  await page.getByRole("link", { name: "Open eval workspace" }).click();
  await expect(page).toHaveURL(/\/evals\?job=eval-002/);
  await expect(page.getByRole("heading", { name: "Eval workbench" })).toBeVisible();
  await expect(page.getByText("No sample results yet for this eval job.")).toBeVisible();

  await page.goto("/evals?job=eval-001");
  await expect(page.getByRole("cell", { name: "provider_call" })).toBeVisible();
  await expect(page.getByText("2 of 2 failing runs selected for export.")).toBeVisible();
  await expect(page.getByText("sample-runtime")).toBeVisible();
  await page.getByRole("checkbox", { name: "Select failed run run-003" }).click();
  await expect(page.getByText("1 of 2 failing runs selected for export.")).toBeVisible();
  await page.getByRole("button", { name: "Export 1 run as JSONL" }).click();
  await expect(page.getByText("Exported 1 run as JSONL.")).toBeVisible();
  await expect(page.getByRole("link", { name: /Open run run-002/ })).toHaveAttribute(
    "href",
    "/runs/run-002"
  );
  expect(exportCalls).toEqual([{ format: "jsonl", runIds: ["run-002"] }]);
});
