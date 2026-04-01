import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import * as agentApi from "@/src/entities/agent/api";
import * as datasetApi from "@/src/entities/dataset/api";
import * as experimentApi from "@/src/entities/experiment/api";
import * as exportApi from "@/src/entities/export/api";
import * as policyApi from "@/src/entities/policy/api";
import { renderWithQueryClient } from "@/test/setup";
import ExperimentsWorkspace from "@/src/widgets/experiments-workspace/ExperimentsWorkspace";

vi.mock("@/src/entities/agent/api", () => ({
  listDiscoveredAgents: vi.fn(),
  listPublishedAgents: vi.fn(),
  publishAgent: vi.fn(),
  unpublishAgent: vi.fn()
}));

vi.mock("@/src/entities/dataset/api", () => ({
  listDatasets: vi.fn()
}));

vi.mock("@/src/entities/experiment/api", () => ({
  listExperiments: vi.fn(),
  listExperimentRuns: vi.fn(),
  createExperiment: vi.fn(),
  startExperiment: vi.fn(),
  cancelExperiment: vi.fn(),
  compareExperiments: vi.fn(),
  patchExperimentRun: vi.fn()
}));

vi.mock("@/src/entities/policy/api", () => ({
  listPolicies: vi.fn()
}));

vi.mock("@/src/entities/export/api", () => ({
  listExports: vi.fn(),
  createExport: vi.fn(),
  getExportDownloadUrl: vi.fn((exportId: string) => `http://127.0.0.1:8000/api/v1/exports/${exportId}`)
}));

type MockedApiFn = ReturnType<typeof vi.fn>;

describe("Experiments workspace", () => {
  beforeEach(() => {
    (agentApi.listDiscoveredAgents as unknown as MockedApiFn).mockReset();
    (agentApi.listPublishedAgents as unknown as MockedApiFn).mockReset();
    (datasetApi.listDatasets as unknown as MockedApiFn).mockReset();
    (experimentApi.listExperiments as unknown as MockedApiFn).mockReset();
    (experimentApi.listExperimentRuns as unknown as MockedApiFn).mockReset();
    (experimentApi.createExperiment as unknown as MockedApiFn).mockReset();
    (experimentApi.startExperiment as unknown as MockedApiFn).mockReset();
    (experimentApi.cancelExperiment as unknown as MockedApiFn).mockReset();
    (experimentApi.compareExperiments as unknown as MockedApiFn).mockReset();
    (experimentApi.patchExperimentRun as unknown as MockedApiFn).mockReset();
    (policyApi.listPolicies as unknown as MockedApiFn).mockReset();
    (exportApi.createExport as unknown as MockedApiFn).mockReset();
    (exportApi.listExports as unknown as MockedApiFn).mockReset();

    (agentApi.listDiscoveredAgents as unknown as MockedApiFn).mockResolvedValue([
      {
        agentId: "basic",
        name: "Basic",
        description: "Minimal smoke agent.",
        framework: "openai-agents-sdk",
        frameworkVersion: "0.1.0",
        entrypoint: "app.agent_plugins.basic:build_agent",
        defaultModel: "gpt-5.4-mini",
        tags: ["example", "smoke"],
        capabilities: ["submit", "cancel"],
        publishedAt: "2026-03-20T09:00:00Z",
        publishState: "published",
        validationStatus: "valid",
        validationIssues: [],
        lastValidatedAt: "2026-03-20T09:00:00Z",
        hasUnpublishedChanges: false,
        sourceFingerprint: "basic-fingerprint-123456",
        executionReference: { artifactRef: "source://basic@basic-fingerprint-123456" },
        defaultRuntimeProfile: {
          backend: "external-runner",
          metadata: {
            claude_code_cli: {
              profile: "default"
            }
          }
        }
      }
    ]);
    (agentApi.listPublishedAgents as unknown as MockedApiFn).mockResolvedValue([
      {
        agentId: "basic",
        name: "Basic",
        description: "Minimal smoke agent.",
        framework: "openai-agents-sdk",
        frameworkVersion: "0.1.0",
        entrypoint: "app.agent_plugins.basic:build_agent",
        defaultModel: "gpt-5.4-mini",
        tags: ["example", "smoke"],
        capabilities: ["submit", "cancel"],
        publishedAt: "2026-03-20T09:00:00Z",
        publishState: "published",
        validationStatus: "valid",
        validationIssues: [],
        lastValidatedAt: "2026-03-20T09:00:00Z",
        hasUnpublishedChanges: false,
        sourceFingerprint: "basic-fingerprint-123456",
        executionReference: { artifactRef: "source://basic@basic-fingerprint-123456" },
        defaultRuntimeProfile: {
          backend: "external-runner",
          metadata: {
            claude_code_cli: {
              profile: "default"
            }
          }
        }
      },
      {
        agentId: "archived_basic",
        name: "Archived Basic",
        description: "Published snapshot no longer discoverable locally.",
        framework: "openai-agents-sdk",
        frameworkVersion: "0.1.0",
        entrypoint: "app.agent_plugins.archived_basic:build_agent",
        defaultModel: "gpt-5.4-mini",
        tags: ["archived"],
        capabilities: ["submit"],
        publishedAt: "2026-03-24T00:00:00Z",
        sourceFingerprint: "archived-fingerprint-123456",
        executionReference: { artifactRef: "source://archived_basic@archived-fingerprint-123456" },
        defaultRuntimeProfile: { backend: "k8s-job" }
      }
    ]);
    (datasetApi.listDatasets as unknown as MockedApiFn).mockResolvedValue([
      {
        name: "crm-v2",
        description: "Support data",
        source: "crm",
        createdAt: "2026-03-24T00:00:00Z",
        currentVersionId: "dataset-v2",
        version: "2026-03",
        rows: [],
        versions: [
          {
            datasetVersionId: "dataset-v2",
            datasetName: "crm-v2",
            version: "2026-03",
            createdAt: "2026-03-24T00:00:00Z",
            rowCount: 2,
            rows: []
          }
        ]
      }
    ]);
    (policyApi.listPolicies as unknown as MockedApiFn).mockResolvedValue([
      {
        approvalPolicyId: "policy-default",
        name: "Default policy",
        description: "Allow approved tools.",
        toolPolicies: [{ toolName: "search", effect: "allow", description: null }],
        createdAt: "2026-03-24T00:00:00Z"
      }
    ]);
    (experimentApi.listExperiments as unknown as MockedApiFn).mockResolvedValue([
      {
        experimentId: "exp-001",
        name: "baseline",
        datasetName: "crm-v2",
        datasetVersionId: "dataset-v2",
        publishedAgentId: "basic-v1",
        status: "completed",
        tags: ["baseline"],
        scoringMode: "exact_match",
        executorBackend: "k8s-job",
        sampleCount: 2,
        completedCount: 2,
        passedCount: 2,
        failedCount: 0,
        unscoredCount: 0,
        runtimeErrorCount: 0,
        passRate: 1,
        failureDistribution: {},
        tracing: { backend: "phoenix", projectUrl: "http://phoenix.local/project/exp-001" },
        errorCode: null,
        errorMessage: null,
        createdAt: "2026-03-24T00:00:00Z"
      },
      {
        experimentId: "exp-002",
        name: "candidate",
        datasetName: "crm-v2",
        datasetVersionId: "dataset-v2",
        publishedAgentId: "basic",
        status: "completed",
        tags: ["candidate"],
        scoringMode: "exact_match",
        executorBackend: "k8s-job",
        sampleCount: 2,
        completedCount: 2,
        passedCount: 1,
        failedCount: 1,
        unscoredCount: 0,
        runtimeErrorCount: 0,
        passRate: 0.5,
        failureDistribution: { mismatch: 1 },
        tracing: { backend: "phoenix", projectUrl: "http://phoenix.local/project/exp-002" },
        errorCode: null,
        errorMessage: null,
        createdAt: "2026-03-25T00:00:00Z"
      }
    ]);
    (experimentApi.listExperimentRuns as unknown as MockedApiFn).mockResolvedValue([
      {
        runId: "run-001",
        experimentId: "exp-002",
        datasetSampleId: "sample-pass",
        input: "alpha",
        expected: "alpha",
        actual: "alpha",
        runStatus: "succeeded",
        judgement: "passed",
        compareOutcome: null,
        failureReason: null,
        errorCode: null,
        errorMessage: null,
        tags: ["shipping"],
        slice: "shipping",
        source: "crm",
        exportEligible: true,
        curationStatus: "include",
        curationNote: null,
        publishedAgentSnapshot: null,
        artifactRef: "source://basic@fp-123",
        imageRef: null,
        executorBackend: "k8s-job",
        latencyMs: 12,
        toolCalls: 1,
        traceUrl: "http://phoenix.local/trace/run-001"
      },
      {
        runId: "run-002",
        experimentId: "exp-002",
        datasetSampleId: "sample-regressed",
        input: "beta",
        expected: "beta",
        actual: "not-beta",
        runStatus: "failed",
        judgement: "failed",
        compareOutcome: null,
        failureReason: "actual output did not exactly match expected output",
        errorCode: "mismatch",
        errorMessage: "model mismatch",
        tags: ["returns"],
        slice: "returns",
        source: "crm",
        exportEligible: true,
        curationStatus: "review",
        curationNote: null,
        publishedAgentSnapshot: null,
        artifactRef: "source://basic@fp-123",
        imageRef: null,
        executorBackend: "k8s-job",
        latencyMs: 15,
        toolCalls: 2,
        traceUrl: "http://phoenix.local/trace/run-002"
      }
    ]);
    (experimentApi.compareExperiments as unknown as MockedApiFn).mockResolvedValue({
      baselineExperimentId: "exp-001",
      candidateExperimentId: "exp-002",
      datasetVersionId: "dataset-v2",
      distribution: { improved: 0, regressed: 1, unchanged_pass: 1 },
      samples: [
        {
          datasetSampleId: "sample-pass",
          baselineJudgement: "passed",
          candidateJudgement: "passed",
          compareOutcome: "unchanged_pass",
          errorCode: null,
          slice: "shipping",
          tags: ["shipping"],
          candidateRunSummary: { runId: "run-001", actual: "alpha", traceUrl: "http://phoenix.local/trace/run-001" }
        },
        {
          datasetSampleId: "sample-regressed",
          baselineJudgement: "passed",
          candidateJudgement: "failed",
          compareOutcome: "regressed",
          errorCode: "mismatch",
          slice: "returns",
          tags: ["returns"],
          candidateRunSummary: { runId: "run-002", actual: "not-beta", traceUrl: "http://phoenix.local/trace/run-002" }
        }
      ]
    });
    (experimentApi.patchExperimentRun as unknown as MockedApiFn).mockImplementation(
      async (_experimentId: string, runId: string, payload: { curationStatus?: "include" | "exclude" | "review"; exportEligible?: boolean }) => ({
        runId,
        experimentId: "exp-002",
        datasetSampleId: runId === "run-001" ? "sample-pass" : "sample-regressed",
        input: runId === "run-001" ? "alpha" : "beta",
        expected: runId === "run-001" ? "alpha" : "beta",
        actual: runId === "run-001" ? "alpha" : "not-beta",
        runStatus: runId === "run-001" ? "succeeded" : "failed",
        judgement: runId === "run-001" ? "passed" : "failed",
        compareOutcome: null,
        failureReason: runId === "run-001" ? null : "actual output did not exactly match expected output",
        errorCode: runId === "run-001" ? null : "mismatch",
        errorMessage: runId === "run-001" ? null : "model mismatch",
        tags: runId === "run-001" ? ["shipping"] : ["returns"],
        slice: runId === "run-001" ? "shipping" : "returns",
        source: "crm",
        exportEligible: payload.exportEligible ?? true,
        curationStatus: payload.curationStatus ?? "review",
        curationNote: null,
        publishedAgentSnapshot: null,
        artifactRef: "source://basic@fp-123",
        imageRef: null,
        executorBackend: "k8s-job",
        latencyMs: runId === "run-001" ? 12 : 15,
        toolCalls: runId === "run-001" ? 1 : 2,
        traceUrl: runId === "run-001" ? "http://phoenix.local/trace/run-001" : "http://phoenix.local/trace/run-002"
      })
    );
    (experimentApi.createExperiment as unknown as MockedApiFn).mockResolvedValue({
      experimentId: "exp-003",
      name: "basic-2026-03",
      datasetName: "crm-v2",
      datasetVersionId: "dataset-v2",
      publishedAgentId: "basic",
      status: "queued",
      tags: [],
      scoringMode: "exact_match",
      executorBackend: "k8s-job",
      sampleCount: 2,
      completedCount: 0,
      passedCount: 0,
      failedCount: 0,
      unscoredCount: 2,
      runtimeErrorCount: 0,
      passRate: 0,
      failureDistribution: {},
      tracing: null,
      errorCode: null,
      errorMessage: null,
      createdAt: "2026-03-25T00:30:00Z"
    });
    (experimentApi.startExperiment as unknown as MockedApiFn).mockResolvedValue({
      experimentId: "exp-003",
      name: "basic-2026-03",
      datasetName: "crm-v2",
      datasetVersionId: "dataset-v2",
      publishedAgentId: "basic",
      status: "running",
      tags: [],
      scoringMode: "exact_match",
      executorBackend: "k8s-job",
      sampleCount: 2,
      completedCount: 0,
      passedCount: 0,
      failedCount: 0,
      unscoredCount: 2,
      runtimeErrorCount: 0,
      passRate: 0,
      failureDistribution: {},
      tracing: null,
      errorCode: null,
      errorMessage: null,
      createdAt: "2026-03-25T00:30:00Z"
    });
    (exportApi.createExport as unknown as MockedApiFn).mockResolvedValue({
      exportId: "export-001",
      format: "jsonl",
      createdAt: "2026-03-25T00:40:00Z",
      path: "/tmp/export-001.jsonl",
      sizeBytes: 128,
      rowCount: 1,
      sourceExperimentId: "exp-002",
      baselineExperimentId: "exp-001",
      candidateExperimentId: "exp-002",
      filtersSummary: {}
    });
    (exportApi.listExports as unknown as MockedApiFn).mockResolvedValue([]);
  });

  it("creates experiments, compares baseline and candidate runs, patches curation, and exports filtered rows", async () => {
    renderWithQueryClient(
      <ExperimentsWorkspace
        initialAgentId="basic"
        initialDatasetVersionId="dataset-v2"
        initialExperimentId="exp-002"
      />
    );

    expect(await screen.findByRole("heading", { name: "Experiment to evidence loop" })).toBeInTheDocument();
    await waitFor(() => expect(agentApi.listDiscoveredAgents).toHaveBeenCalled());
    await waitFor(() => expect(agentApi.listPublishedAgents).toHaveBeenCalled());
    expect(screen.getByRole("combobox", { name: "Published agent" })).toHaveValue("basic");
    expect(screen.getByRole("option", { name: "Archived Basic" })).toBeInTheDocument();
    await waitFor(() => expect(experimentApi.listExperiments).toHaveBeenCalled());
    await waitFor(() => expect(experimentApi.listExperimentRuns).toHaveBeenCalledWith("exp-002"));
    await waitFor(() => expect(experimentApi.compareExperiments).toHaveBeenCalledWith("exp-001", "exp-002"));
    expect(
      screen.getByText(
        /Execution profile is inherited from the published snapshot: external-runner · Claude Code CLI adapter\./i
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Atlas still tracks the same neutral runner status, evidence, and export loop/i)
    ).toBeInTheDocument();

    expect(screen.getByRole("link", { name: "Open Phoenix deeplink" })).toHaveAttribute(
      "href",
      "http://phoenix.local/project/exp-002"
    );
    expect(await screen.findByText("sample-regressed")).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "Exclude" })[0]);
    await waitFor(() =>
      expect(experimentApi.patchExperimentRun).toHaveBeenCalledWith("exp-002", "run-001", {
        curationStatus: "exclude",
        curationNote: null,
        exportEligible: true
      })
    );

    fireEvent.change(screen.getByLabelText("Compare"), { target: { value: "regressed" } });
    fireEvent.click(screen.getByRole("button", { name: "Create export" }));
    await waitFor(() =>
      expect(exportApi.createExport).toHaveBeenCalledWith({
        experimentId: null,
        baselineExperimentId: "exp-001",
        candidateExperimentId: "exp-002",
        datasetSampleIds: ["sample-regressed"],
        judgements: null,
        errorCodes: null,
        compareOutcomes: ["regressed"],
        tags: null,
        slices: null,
        curationStatuses: null,
        exportEligible: null,
        format: "jsonl"
      })
    );

    expect(await screen.findByText(/Created export export-001\./)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Download export" })).toHaveAttribute(
      "href",
      "http://127.0.0.1:8000/api/v1/exports/export-001"
    );

    fireEvent.click(screen.getByRole("button", { name: "Create and start" }));
    await waitFor(() =>
      expect(experimentApi.createExperiment).toHaveBeenCalledWith({
        name: "basic-2026-03",
        datasetVersionId: "dataset-v2",
        publishedAgentId: "basic",
        model: "gpt-5.4-mini",
        scoringMode: "exact_match",
        approvalPolicyId: "policy-default",
        systemPrompt: "",
        promptVersion: "2026-03",
        tags: []
      })
    );
    await waitFor(() => expect(experimentApi.startExperiment).toHaveBeenCalledWith("exp-003"));
  });

  it("keeps a published-only live agent selectable when discovery is empty", async () => {
    (agentApi.listDiscoveredAgents as unknown as MockedApiFn).mockResolvedValue([]);

    renderWithQueryClient(<ExperimentsWorkspace initialAgentId="archived_basic" initialDatasetVersionId="dataset-v2" />);

    const agentSelect = await screen.findByRole("combobox", { name: "Published agent" });

    await waitFor(() => expect(agentApi.listDiscoveredAgents).toHaveBeenCalled());
    await waitFor(() => expect(agentApi.listPublishedAgents).toHaveBeenCalled());
    expect(agentSelect).toHaveValue("archived_basic");
    expect(agentSelect).toHaveTextContent("Archived Basic");
  });
});
