import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import * as agentApi from "@/src/entities/agent/api";
import type { AgentRecord } from "@/src/entities/agent/model";
import { renderWithQueryClient } from "@/test/setup";
import AgentsWorkspace from "@/src/widgets/agents-workspace/AgentsWorkspace";

vi.mock("@/src/entities/agent/api", () => ({
  listPublishedAgents: vi.fn(),
  createClaudeCodeStarterAsset: vi.fn(),
  importAgent: vi.fn(),
  startValidationRun: vi.fn()
}));

type MockedApiFn = ReturnType<typeof vi.fn>;

describe("Agents workspace", () => {
  beforeEach(() => {
    const publishedAgents: AgentRecord[] = [
      {
        agentId: "basic",
        name: "Basic",
        description: "Ready governed snapshot.",
        framework: "openai-agents-sdk",
        frameworkVersion: "0.1.0",
        entrypoint: "snapshots/basic:run",
        defaultModel: "gpt-5.4-mini",
        tags: ["example", "smoke"],
        capabilities: ["submit", "cancel"],
        publishedAt: "2026-03-20T09:00:00Z",
        sourceFingerprint: "basic-fingerprint-123456",
        executionReference: {
          artifactRef: "source://basic@basic-fingerprint-123456"
        },
        latestValidation: {
          runId: "run-validation-001",
          status: "succeeded",
          createdAt: "2026-03-26T08:55:00Z",
          startedAt: "2026-03-26T08:56:00Z",
          completedAt: "2026-03-26T08:57:00Z"
        },
        validationEvidence: {
          artifactRef: "bundle://basic-validation-001",
          imageRef: null,
          traceUrl: "http://phoenix.local/trace/validation-001",
          terminalSummary: "Edited sample project and captured changed files."
        },
        validationOutcome: {
          status: "succeeded",
          reason: "Validation run completed with evidence attached."
        },
        executionProfile: {
          backend: "external-runner",
          metadata: {
            claude_code_cli: {
              profile: "default"
            }
          }
        }
      },
      {
        agentId: "customer_service",
        name: "Customer Service",
        description: "Published asset with an active validation run.",
        framework: "openai-agents-sdk",
        frameworkVersion: "0.1.0",
        entrypoint: "snapshots/customer-service:run",
        defaultModel: "gpt-5.4-mini",
        tags: ["support", "ops"],
        capabilities: ["submit", "cancel"],
        publishedAt: "2026-03-18T08:30:00Z",
        sourceFingerprint: "customer-fingerprint-123456",
        executionReference: {
          artifactRef: "source://customer_service@customer-fingerprint-123456"
        },
        latestValidation: {
          runId: "run-validation-002",
          status: "running",
          createdAt: "2026-03-26T09:05:00Z",
          startedAt: "2026-03-26T09:06:00Z",
          completedAt: null
        },
        validationOutcome: {
          status: "running",
          reason: "Validation is still collecting evidence."
        },
        executionProfile: { backend: "k8s-job" }
      },
      {
        agentId: "failed_live",
        name: "Failed Live",
        description: "Published asset whose latest validation failed.",
        framework: "openai-agents-sdk",
        frameworkVersion: "0.1.0",
        entrypoint: "snapshots/failed-live:run",
        defaultModel: "gpt-5.4-mini",
        tags: ["archived"],
        capabilities: ["submit"],
        publishedAt: "2026-03-24T00:00:00Z",
        sourceFingerprint: "failed-fingerprint-123456",
        executionReference: {
          artifactRef: "source://failed_live@failed-fingerprint-123456"
        },
        latestValidation: {
          runId: "run-failed-live",
          status: "failed",
          createdAt: "2026-03-24T00:00:00Z",
          startedAt: "2026-03-24T00:01:00Z",
          completedAt: "2026-03-24T00:02:00Z"
        },
        validationOutcome: {
          status: "failed",
          reason: "Validation failed."
        },
        executionProfile: { backend: "k8s-job" }
      }
    ];

    (agentApi.listPublishedAgents as unknown as MockedApiFn).mockReset();
    (agentApi.createClaudeCodeStarterAsset as unknown as MockedApiFn).mockReset();
    (agentApi.importAgent as unknown as MockedApiFn).mockReset();
    (agentApi.startValidationRun as unknown as MockedApiFn).mockReset();

    (agentApi.listPublishedAgents as unknown as MockedApiFn).mockImplementation(async () => publishedAgents);
    (agentApi.createClaudeCodeStarterAsset as unknown as MockedApiFn).mockResolvedValue(null);
    (agentApi.importAgent as unknown as MockedApiFn).mockResolvedValue(null);
    (agentApi.startValidationRun as unknown as MockedApiFn).mockImplementation(async (agentId: string) => ({
      run_id: `validation-${agentId}`,
      status: "queued"
    }));
  });

  it("groups governed assets by validation readiness and routes ready assets into experiments", async () => {
    renderWithQueryClient(<AgentsWorkspace />);

    expect(await screen.findByRole("heading", { name: "Agents" })).toBeInTheDocument();
    await waitFor(() => expect(agentApi.listPublishedAgents).toHaveBeenCalledTimes(1));

    expect(await screen.findByText("Ready governed snapshot.")).toBeInTheDocument();
    expect(screen.getByText("Published asset with an active validation run.")).toBeInTheDocument();
    expect(screen.getByText("Published asset whose latest validation failed.")).toBeInTheDocument();
    expect(screen.getByText("external-runner")).toBeInTheDocument();
    expect(screen.getByText("source://basic@basic-fingerprint-123456")).toBeInTheDocument();
    expect(screen.getByText("run-validation-001")).toBeInTheDocument();
    expect(screen.getByText("bundle://basic-validation-001")).toBeInTheDocument();
    expect(screen.getAllByText("Validation run completed with evidence attached.")).toHaveLength(2);
    expect(screen.getByText("Hand this ready snapshot into the next experiment.")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Atlas is still running the latest validation. Wait for the active run to finish before handing this snapshot into experiments."
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Review the latest validation run and evidence before handing this snapshot into a new experiment."
      )
    ).toBeInTheDocument();
    expect(
      screen.getAllByRole("link", { name: /Create experiment/i }).map((link) => link.getAttribute("href"))
    ).toEqual(expect.arrayContaining(["/experiments?agent=basic"]));
    expect(
      screen.getAllByRole("link", { name: /Create experiment/i }).map((link) => link.getAttribute("href"))
    ).not.toEqual(expect.arrayContaining(["/experiments?agent=customer_service"]));
    expect(
      screen.getAllByRole("link", { name: /Create experiment/i }).map((link) => link.getAttribute("href"))
    ).not.toEqual(expect.arrayContaining(["/experiments?agent=failed_live"]));

    fireEvent.click(screen.getAllByRole("button", { name: "Run validation" })[0]);
    await waitFor(() =>
      expect(agentApi.startValidationRun).toHaveBeenCalledWith(
        "basic",
        expect.objectContaining({
          project: "atlas-validation",
          dataset: "controlled-validation",
          input_summary: "Validate Basic from the Agents surface",
          prompt: "alpha"
        })
      )
    );
  });

  it("renders published agents when the catalog already contains governed assets", async () => {
    const publishedAgents: AgentRecord[] = [
      {
        agentId: "live-agent",
        name: "Live Agent",
        description: "Published snapshot from the live catalog.",
        framework: "openai-agents-sdk",
        frameworkVersion: "0.1.0",
        entrypoint: "snapshots/live-agent:run",
        defaultModel: "gpt-5.4-mini",
        tags: ["live"],
        capabilities: ["submit"],
        publishedAt: "2026-04-01T08:00:00Z",
        sourceFingerprint: "live-agent-fingerprint-123456",
        executionReference: {
          artifactRef: "bundle://live-agent-snapshot"
        },
        latestValidation: {
          runId: "run-live-validation-001",
          status: "succeeded",
          createdAt: "2026-04-01T08:10:00Z",
          startedAt: "2026-04-01T08:11:00Z",
          completedAt: "2026-04-01T08:12:00Z"
        },
        validationEvidence: {
          artifactRef: "bundle://live-agent-validation",
          traceUrl: "http://phoenix.local/trace/live-agent-validation"
        },
        validationOutcome: {
          status: "succeeded",
          reason: "Published validation passed."
        },
        executionProfile: {
          backend: "external-runner"
        }
      }
    ];

    (agentApi.listPublishedAgents as unknown as MockedApiFn).mockResolvedValue(publishedAgents);

    renderWithQueryClient(<AgentsWorkspace />);

    expect(await screen.findByText("Published snapshot from the live catalog.")).toBeInTheDocument();
    expect(screen.getByText("Live Agent")).toBeInTheDocument();
    expect(screen.getByText("Hand this ready snapshot into the next experiment.")).toBeInTheDocument();
    expect(screen.getByText("bundle://live-agent-validation")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open validation evidence" })).toHaveAttribute(
      "href",
      "http://phoenix.local/trace/live-agent-validation"
    );
  });

  it("imports the first governed agent asset from the empty state action and keeps starter intake secondary", async () => {
    let publishedAgents: AgentRecord[] = [];
    const importedAgent: AgentRecord = {
      agentId: "imported-basic",
      name: "Imported Basic",
      description: "Governed asset imported explicitly from a runnable entrypoint.",
      framework: "openai-agents-sdk",
      frameworkVersion: "0.1.0",
      entrypoint: "agents.imported_basic:build_agent",
      defaultModel: "gpt-5.4-mini",
      tags: ["import", "ops"],
      capabilities: ["submit"],
      publishedAt: "2026-04-02T09:00:00Z",
      sourceFingerprint: "imported-basic-fingerprint-123456",
      executionReference: {
        artifactRef: "source://imported-basic@imported-basic-fingerprint-123456"
      },
      latestValidation: {
        runId: "run-imported-basic-validation",
        status: "succeeded",
        createdAt: "2026-04-02T09:01:00Z",
        startedAt: "2026-04-02T09:02:00Z",
        completedAt: "2026-04-02T09:03:00Z"
      },
      validationEvidence: {
        artifactRef: "bundle://imported-basic-validation",
        traceUrl: "http://phoenix.local/trace/imported-basic-validation"
      },
      validationOutcome: {
        status: "succeeded",
        reason: "Explicit import completed with validation evidence."
      },
      executionProfile: {
        backend: "external-runner"
      }
    };

    (agentApi.listPublishedAgents as unknown as MockedApiFn).mockImplementation(async () => publishedAgents);
    (agentApi.importAgent as unknown as MockedApiFn).mockImplementation(async () => {
      publishedAgents = [importedAgent];
      return importedAgent;
    });

    renderWithQueryClient(<AgentsWorkspace />);

    expect(await screen.findByText("Import the first governed agent asset")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create Claude Code starter" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Agent ID"), { target: { value: "imported-basic" } });
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Imported Basic" } });
    fireEvent.change(screen.getByLabelText("Description"), {
      target: { value: "Governed asset imported explicitly from a runnable entrypoint." }
    });
    fireEvent.change(screen.getByLabelText("Entrypoint"), {
      target: { value: "agents.imported_basic:build_agent" }
    });

    fireEvent.click(screen.getByRole("button", { name: "Import agent" }));

    await waitFor(() => expect(agentApi.importAgent).toHaveBeenCalledTimes(1));
    expect((agentApi.importAgent as unknown as MockedApiFn).mock.calls[0]?.[0]).toEqual(
      expect.objectContaining({
        agentId: "imported-basic",
        name: "Imported Basic",
        entrypoint: "agents.imported_basic:build_agent",
        framework: "openai-agents-sdk"
      })
    );
    expect(await screen.findByText("Governed asset imported explicitly from a runnable entrypoint.")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Imported Imported Basic. Atlas can now validate the governed asset and hand the sealed snapshot into experiments from this surface."
      )
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Create experiment/i })).toHaveAttribute(
      "href",
      "/experiments?agent=imported-basic"
    );
  });
});
