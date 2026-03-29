import { expect, test } from "@playwright/test";
import {
  buildDataset,
  buildEvalJob,
  buildEvalSample,
  mockCatalog,
  mockEvals
} from "./support/mockApi";

test("evals workspace can create an eval job and open eval details", async ({ page }) => {
  const exportCalls: Array<{ format: string; datasetSampleIds: string[] | null }> = [];
  let evalJobs = [
    buildEvalJob({
      eval_job_id: "eval-002",
      project: "nightly-candidate",
      observability: {
        backend: "phoenix",
        project_url: "http://127.0.0.1:6006/projects/test?eval_job_id=eval-002"
      }
    }),
    buildEvalJob({
      eval_job_id: "eval-001",
      project: "nightly-baseline",
      observability: {
        backend: "phoenix",
        project_url: "http://127.0.0.1:6006/projects/test?eval_job_id=eval-001"
      },
      created_at: "2026-03-23T00:00:00Z"
    })
  ];
  const candidateSamples = [
    buildEvalSample({
      eval_job_id: "eval-002",
      dataset_sample_id: "sample-regressed",
      run_id: "run-003",
      judgement: "failed",
      input: "beta",
      expected: "beta",
      actual: "not-beta",
      failure_reason: "actual output did not exactly match expected output",
      error_code: "mismatch",
      tags: ["returns"],
      slice: "returns",
      source: "crm",
      curation_status: "review",
      export_eligible: true,
      runner_backend: "local-process",
      artifact_ref: "artifact://candidate",
      latency_ms: 12,
      tool_calls: 1,
      phoenix_trace_url: "http://127.0.0.1:6006/projects/test/traces/run-003"
    }),
    buildEvalSample({
      eval_job_id: "eval-002",
      dataset_sample_id: "sample-pass",
      run_id: "run-004",
      judgement: "passed",
      input: "alpha",
      expected: "alpha",
      actual: "alpha",
      tags: ["shipping"],
      slice: "shipping",
      source: "crm",
      curation_status: "include",
      export_eligible: true,
      runner_backend: "local-process",
      artifact_ref: "artifact://candidate",
      latency_ms: 10,
      tool_calls: 0,
      phoenix_trace_url: "http://127.0.0.1:6006/projects/test/traces/run-004"
    })
  ];
  const baselineSamples = [
    buildEvalSample({
      eval_job_id: "eval-001",
      dataset_sample_id: "sample-regressed",
      run_id: "run-001",
      judgement: "passed",
      input: "beta",
      expected: "beta",
      actual: "beta",
      tags: ["returns"],
      slice: "returns",
      source: "crm",
      curation_status: "include",
      export_eligible: true,
      runner_backend: "local-process",
      artifact_ref: "artifact://baseline",
      latency_ms: 11,
      tool_calls: 0,
      phoenix_trace_url: "http://127.0.0.1:6006/projects/test/traces/run-001"
    }),
    buildEvalSample({
      eval_job_id: "eval-001",
      dataset_sample_id: "sample-pass",
      run_id: "run-002",
      judgement: "passed",
      input: "alpha",
      expected: "alpha",
      actual: "alpha",
      tags: ["shipping"],
      slice: "shipping",
      source: "crm",
      curation_status: "include",
      export_eligible: true,
      runner_backend: "local-process",
      artifact_ref: "artifact://baseline",
      latency_ms: 9,
      tool_calls: 0,
      phoenix_trace_url: "http://127.0.0.1:6006/projects/test/traces/run-002"
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
    datasets: [
      buildDataset({
        name: "crm-v2",
        source: "crm",
        rows: [
          {
            sample_id: "sample-pass",
            input: "alpha",
            expected: "alpha",
            tags: ["shipping"],
            slice: "shipping",
            source: "crm",
            export_eligible: true
          },
          {
            sample_id: "sample-regressed",
            input: "beta",
            expected: "beta",
            tags: ["returns"],
            slice: "returns",
            source: "crm",
            export_eligible: true
          }
        ]
      })
    ]
  });

  await mockEvals(page, {
    list: () => evalJobs,
    create: () => {
      const created = buildEvalJob({
        eval_job_id: "eval-003",
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
      evalJobId === "eval-002"
        ? candidateSamples
        : evalJobId === "eval-001"
          ? baselineSamples
          : []
  });

  await page.route("**/api/v1/eval-jobs/compare?*", async (route) => {
    const url = new URL(route.request().url());
    const baselineEvalJobId = url.searchParams.get("baseline_eval_job_id");
    const candidateEvalJobId = url.searchParams.get("candidate_eval_job_id");
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        baseline_eval_job_id: baselineEvalJobId,
        candidate_eval_job_id: candidateEvalJobId,
        dataset: "crm-v2",
        distribution: {
          regressed: 1,
          unchanged_pass: 1
        },
        samples: [
          {
            dataset_sample_id: "sample-regressed",
            baseline_judgement: "passed",
            candidate_judgement: "failed",
            compare_outcome: "regressed",
            error_code: "mismatch",
            slice: "returns",
            tags: ["returns"],
            candidate_run_summary: {
              run_id: "run-003",
              actual: "not-beta",
              trace_url: "http://127.0.0.1:6006/projects/test/traces/run-003"
            }
          },
          {
            dataset_sample_id: "sample-pass",
            baseline_judgement: "passed",
            candidate_judgement: "passed",
            compare_outcome: "unchanged_pass",
            error_code: null,
            slice: "shipping",
            tags: ["shipping"],
            candidate_run_summary: {
              run_id: "run-004",
              actual: "alpha",
              trace_url: "http://127.0.0.1:6006/projects/test/traces/run-004"
            }
          }
        ]
      })
    });
  });

  await page.route("**/api/v1/eval-jobs/eval-002/samples/*", async (route) => {
    if (route.request().method() !== "PATCH") {
      return route.fallback();
    }

    const datasetSampleId = route.request().url().split("/").pop() ?? "";
    const payload = route.request().postDataJSON();
    const sample = candidateSamples.find((item) => item.dataset_sample_id === datasetSampleId);
    if (!sample) {
      return route.fulfill({ status: 404 });
    }
    if (payload.curation_status) {
      sample.curation_status = payload.curation_status;
    }
    if (typeof payload.export_eligible === "boolean") {
      sample.export_eligible = payload.export_eligible;
    }
    if ("curation_note" in payload) {
      sample.curation_note = payload.curation_note;
    }
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(sample)
    });
  });

  await page.route("**/api/v1/exports", async (route) => {
    if (route.request().method() !== "POST") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([])
      });
    }
    const payload = route.request().postDataJSON();
    exportCalls.push({
      format: payload.format,
      datasetSampleIds: payload.dataset_sample_ids
    });
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        export_id: "export-001",
        format: "jsonl",
        row_count: payload.dataset_sample_ids.length,
        created_at: "2026-03-24T00:05:00Z",
        path: "/tmp/eval-failures.jsonl",
        size_bytes: 64
      })
    });
  });

  await page.goto("/evals?agent=basic&dataset=crm-v2");
  await expect(page.getByRole("heading", { name: "Evals" })).toBeVisible();

  await expect(page.getByRole("button", { name: "Create eval job" })).toBeEnabled();
  await page.getByRole("button", { name: "Create eval job" }).click();
  await expect(page.getByText("Created eval job eval-003.")).toBeVisible();
  await expect(page.getByText("No samples match the current filters.")).toBeVisible();

  await page.getByRole("button", { name: /nightly-candidate/ }).click();
  await expect(page.getByText("sample-regressed")).toBeVisible();
  await expect(page.getByRole("link", { name: "Open Phoenix job view" })).toHaveAttribute(
    "href",
    "http://127.0.0.1:6006/projects/test?eval_job_id=eval-002"
  );

  await page.locator("#eval-baseline").selectOption("eval-001");
  await expect(page.getByRole("table").getByText("regressed", { exact: true })).toBeVisible();
  await page.locator("#eval-filter-compare").selectOption("regressed");
  await expect(page.getByText("sample-regressed")).toBeVisible();
  await expect(page.getByText("sample-pass")).toHaveCount(0);

  const sampleRow = page.locator("tr", { has: page.getByText("sample-regressed") });
  await expect(sampleRow.getByText("review", { exact: true }).first()).toBeVisible();
  await sampleRow.getByRole("button", { name: "Include" }).click();
  await expect(sampleRow.getByText("include", { exact: true }).first()).toBeVisible();

  await page.getByRole("button", { name: "Export JSONL" }).click();
  await expect(page.getByText("Created JSONL export export-001.")).toBeVisible();
  await expect(page.getByRole("link", { name: "Download export" })).toHaveAttribute(
    "href",
    /\/api\/v1\/exports\/export-001$/
  );
  expect(exportCalls).toEqual([
    {
      format: "jsonl",
      datasetSampleIds: ["sample-regressed"]
    }
  ]);
});
