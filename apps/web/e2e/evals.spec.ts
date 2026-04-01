import { expect, test } from "@playwright/test";

test("experiments workspace can compare experiments and curate runs", async ({ page }) => {
  const exportCalls: Array<{ format: string; datasetSampleIds: string[] | null }> = [];

  const agents = [
    {
      agent_id: "basic",
      name: "Basic",
      description: "Minimal smoke agent.",
      framework: "openai-agents-sdk",
      framework_type: "openai-agents-sdk",
      framework_version: "0.1.0",
      entrypoint: "app.agent_plugins.basic:build_agent",
      default_model: "gpt-5.4-mini",
      tags: ["example", "smoke"],
      capabilities: ["submit", "cancel"],
      publish_state: "published",
      validation_status: "valid",
      validation_issues: [],
      published_at: "2026-03-24T00:00:00Z",
      last_validated_at: "2026-03-24T00:00:00Z",
      has_unpublished_changes: false,
      source_fingerprint: "basic-fingerprint-123456",
      execution_reference: {
        artifact_ref: "source://basic@basic-fingerprint-123456",
        image_ref: null
      },
      default_runtime_profile: {
        backend: "external-runner",
        runner_image: null,
        timeout_seconds: 600,
        max_steps: 32,
        concurrency: 1,
        resources: {
          cpu: null,
          memory: null
        },
        tracing_backend: "state",
        artifact_path: null,
        metadata: {
          claude_code_cli: {
            profile: "default"
          }
        }
      }
    }
  ];

  const datasets = [
    {
      name: "crm-v2",
      description: "Support data",
      source: "crm",
      created_at: "2026-03-24T00:00:00Z",
      version: "2026-03",
      row_count: 2,
      rows: [
        {
          sample_id: "sample-pass",
          input: "alpha",
          expected: "alpha",
          tags: ["shipping"],
          slice: "shipping",
          source: "crm",
          metadata: null,
          export_eligible: true
        },
        {
          sample_id: "sample-regressed",
          input: "beta",
          expected: "beta",
          tags: ["returns"],
          slice: "returns",
          source: "crm",
          metadata: null,
          export_eligible: true
        }
      ],
      current_version_id: "dataset-v2",
      versions: [
        {
          dataset_version_id: "dataset-v2",
          dataset_name: "crm-v2",
          version: "2026-03",
          created_at: "2026-03-24T00:00:00Z",
          row_count: 2,
          rows: [
            {
              sample_id: "sample-pass",
              input: "alpha",
              expected: "alpha",
              tags: ["shipping"],
              slice: "shipping",
              source: "crm",
              metadata: null,
              export_eligible: true
            },
            {
              sample_id: "sample-regressed",
              input: "beta",
              expected: "beta",
              tags: ["returns"],
              slice: "returns",
              source: "crm",
              metadata: null,
              export_eligible: true
            }
          ]
        }
      ]
    }
  ];

  const buildSpec = (publishedAgentId: string) => ({
    dataset_version_id: "dataset-v2",
    published_agent_id: publishedAgentId,
    model_config: {
      model: "gpt-5.4-mini",
      provider: null,
      temperature: 0
    },
    prompt_config: {
      prompt_template: null,
      system_prompt: null,
      prompt_version: "2026-03"
    },
    toolset_config: {
      tools: [],
      metadata: {}
    },
    evaluator_config: {
      scoring_mode: "exact_match",
      metadata: {}
    },
    executor_config: {
      backend: "external-runner",
      runner_image: null,
      timeout_seconds: 600,
      max_steps: 32,
      concurrency: 1,
      resources: {},
      tracing_backend: "phoenix",
      artifact_path: null,
      metadata: {
        claude_code_cli: {
          profile: "default"
        }
      }
    },
    approval_policy_id: "policy-default",
    approval_policy: null,
    tags: []
  });

  let experiments = [
    {
      experiment_id: "exp-001",
      name: "baseline",
      dataset_name: "crm-v2",
      dataset_version_id: "dataset-v2",
      published_agent_id: "basic-v1",
      status: "completed",
      tags: ["baseline"],
      spec: buildSpec("basic-v1"),
      scoring_mode: "exact_match",
      executor_backend: "k8s-job",
      sample_count: 2,
      completed_count: 2,
      passed_count: 2,
      failed_count: 0,
      unscored_count: 0,
      runtime_error_count: 0,
      pass_rate: 1,
      failure_distribution: {},
      tracing: { backend: "phoenix", project_url: "http://127.0.0.1:6006/projects/test/exp-001" },
      error_code: null,
      error_message: null,
      created_at: "2026-03-24T00:00:00Z"
    },
    {
      experiment_id: "exp-002",
      name: "candidate",
      dataset_name: "crm-v2",
      dataset_version_id: "dataset-v2",
      published_agent_id: "basic",
      status: "completed",
      tags: ["candidate"],
      spec: buildSpec("basic"),
      scoring_mode: "exact_match",
      executor_backend: "k8s-job",
      sample_count: 2,
      completed_count: 2,
      passed_count: 1,
      failed_count: 1,
      unscored_count: 0,
      runtime_error_count: 0,
      pass_rate: 0.5,
      failure_distribution: { mismatch: 1 },
      tracing: { backend: "phoenix", project_url: "http://127.0.0.1:6006/projects/test/exp-002" },
      error_code: null,
      error_message: null,
      created_at: "2026-03-25T00:00:00Z"
    }
  ];

  const runsByExperiment: Record<string, Array<Record<string, unknown>>> = {
    "exp-001": [
      {
        run_id: "run-001",
        experiment_id: "exp-001",
        dataset_sample_id: "sample-regressed",
        input: "beta",
        expected: "beta",
        actual: "beta",
        run_status: "succeeded",
        judgement: "passed",
        compare_outcome: null,
        failure_reason: null,
        error_code: null,
        error_message: null,
        tags: ["returns"],
        slice: "returns",
        source: "crm",
        export_eligible: true,
        curation_status: "include",
        curation_note: null,
        published_agent_snapshot: null,
        artifact_ref: "source://basic@baseline",
        image_ref: null,
        executor_backend: "k8s-job",
        latency_ms: 11,
        tool_calls: 0,
        trace_url: "http://127.0.0.1:6006/projects/test/traces/run-001"
      }
    ],
    "exp-002": [
      {
        run_id: "run-002",
        experiment_id: "exp-002",
        dataset_sample_id: "sample-pass",
        input: "alpha",
        expected: "alpha",
        actual: "alpha",
        run_status: "succeeded",
        judgement: "passed",
        compare_outcome: null,
        failure_reason: null,
        error_code: null,
        error_message: null,
        tags: ["shipping"],
        slice: "shipping",
        source: "crm",
        export_eligible: true,
        curation_status: "include",
        curation_note: null,
        published_agent_snapshot: null,
        artifact_ref: "source://basic@candidate",
        image_ref: null,
        executor_backend: "k8s-job",
        latency_ms: 10,
        tool_calls: 0,
        trace_url: "http://127.0.0.1:6006/projects/test/traces/run-002"
      },
      {
        run_id: "run-003",
        experiment_id: "exp-002",
        dataset_sample_id: "sample-regressed",
        input: "beta",
        expected: "beta",
        actual: "not-beta",
        run_status: "failed",
        judgement: "failed",
        compare_outcome: null,
        failure_reason: "actual output did not exactly match expected output",
        error_code: "mismatch",
        error_message: "model mismatch",
        tags: ["returns"],
        slice: "returns",
        source: "crm",
        export_eligible: true,
        curation_status: "review",
        curation_note: null,
        published_agent_snapshot: null,
        artifact_ref: "source://basic@candidate",
        image_ref: null,
        executor_backend: "k8s-job",
        latency_ms: 12,
        tool_calls: 1,
        trace_url: "http://127.0.0.1:6006/projects/test/traces/run-003"
      }
    ],
    "exp-003": []
  };

  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    const method = request.method();

    const json = (body: unknown, status = 200) =>
      route.fulfill({
        status,
        contentType: "application/json",
        body: JSON.stringify(body)
      });

    if (path === "/api/v1/agents/discovered" && method === "GET") {
      return json(agents);
    }
    if (path === "/api/v1/datasets" && method === "GET") {
      return json(datasets);
    }
    if (path === "/api/v1/policies" && method === "GET") {
      return json([
        {
          approval_policy_id: "policy-default",
          name: "Default policy",
          description: "Allow approved tools.",
          tool_policies: [{ tool_name: "search", effect: "allow", description: null }],
          created_at: "2026-03-24T00:00:00Z"
        }
      ]);
    }
    if (path === "/api/v1/experiments" && method === "GET") {
      return json(experiments);
    }
    if (path === "/api/v1/experiments" && method === "POST") {
      const created = {
        experiment_id: "exp-003",
        name: "basic-2026-03",
        dataset_name: "crm-v2",
        dataset_version_id: "dataset-v2",
        published_agent_id: "basic",
        status: "queued",
        tags: [],
        spec: buildSpec("basic"),
        scoring_mode: "exact_match",
        executor_backend: "k8s-job",
        sample_count: 0,
        completed_count: 0,
        passed_count: 0,
        failed_count: 0,
        unscored_count: 0,
        runtime_error_count: 0,
        pass_rate: 0,
        failure_distribution: {},
        tracing: { backend: "phoenix", project_url: "http://127.0.0.1:6006/projects/test/exp-003" },
        error_code: null,
        error_message: null,
        created_at: "2026-03-26T00:00:00Z"
      };
      experiments = [created, ...experiments.filter((item) => item.experiment_id !== created.experiment_id)];
      return json(created, 201);
    }
    if (path === "/api/v1/experiments/exp-003/start" && method === "POST") {
      experiments = experiments.map((item) =>
        item.experiment_id === "exp-003" ? { ...item, status: "running" } : item
      );
      return json(experiments.find((item) => item.experiment_id === "exp-003"));
    }
    if (path === "/api/v1/experiments/compare" && method === "GET") {
      return json({
        baseline_experiment_id: url.searchParams.get("baseline_experiment_id"),
        candidate_experiment_id: url.searchParams.get("candidate_experiment_id"),
        dataset_version_id: "dataset-v2",
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
              run_id: "run-002",
              actual: "alpha",
              trace_url: "http://127.0.0.1:6006/projects/test/traces/run-002"
            }
          }
        ]
      });
    }
    if (path === "/api/v1/exports" && method === "GET") {
      return json([]);
    }
    if (path === "/api/v1/exports" && method === "POST") {
      const payload = request.postDataJSON() as {
        format: string;
        dataset_sample_ids: string[] | null;
      };
      exportCalls.push({
        format: payload.format,
        datasetSampleIds: payload.dataset_sample_ids
      });
      return json({
        export_id: "export-001",
        format: payload.format,
        row_count: payload.dataset_sample_ids?.length ?? 0,
        created_at: "2026-03-26T00:05:00Z",
        path: "/tmp/experiment-export.jsonl",
        size_bytes: 64
      });
    }

    const runsMatch = path.match(/^\/api\/v1\/experiments\/([^/]+)\/runs$/);
    if (runsMatch && method === "GET") {
      return json(runsByExperiment[runsMatch[1]] ?? []);
    }

    const patchMatch = path.match(/^\/api\/v1\/experiments\/([^/]+)\/runs\/([^/]+)$/);
    if (patchMatch && method === "PATCH") {
      const [_, experimentId, runId] = patchMatch;
      const payload = request.postDataJSON() as {
        curation_status?: "include" | "exclude" | "review" | null;
        export_eligible?: boolean | null;
      };
      const runs = runsByExperiment[experimentId] ?? [];
      const run = runs.find((item) => item.run_id === runId);
      if (!run) {
        return json({ detail: "run not found" }, 404);
      }
      if (payload.curation_status) {
        run.curation_status = payload.curation_status;
      }
      if (typeof payload.export_eligible === "boolean") {
        run.export_eligible = payload.export_eligible;
      }
      return json(run);
    }

    return route.fulfill({ status: 404 });
  });

  await page.goto("/experiments?agent=basic&datasetVersion=dataset-v2&experiment=exp-002");

  await expect(page.getByRole("heading", { name: "Experiment to evidence loop" })).toBeVisible();
  await expect(
    page.getByText(
      /Execution profile is inherited from the published snapshot: external-runner · Claude Code CLI adapter\./
    )
  ).toBeVisible();
  await page.getByRole("button", { name: /candidate · basic/ }).click();
  await expect(page.getByText("sample-regressed")).toBeVisible();
  await expect(page.getByRole("link", { name: "Open Phoenix deeplink" })).toHaveAttribute(
    "href",
    "http://127.0.0.1:6006/projects/test/exp-002"
  );

  await expect(page.getByRole("table").getByText("regressed", { exact: true })).toBeVisible();
  await page.locator("#experiment-filter-compare").selectOption("regressed");

  const sampleRow = page.locator("tr", { has: page.getByText("sample-regressed") });
  await expect(page.getByText("sample-pass")).toHaveCount(0);
  await sampleRow.getByRole("button", { name: "Include" }).click();

  await page.getByRole("button", { name: "Create export" }).click();
  await expect(page.getByText("Created export export-001.")).toBeVisible();
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
