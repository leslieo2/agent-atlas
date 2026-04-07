import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import * as agentApi from "@/src/entities/agent/api";
import * as datasetApi from "@/src/entities/dataset/api";
import type { AgentRecord } from "@/src/entities/agent/model";
import { renderWithQueryClient } from "@/test/setup";
import AgentsWorkspace from "@/src/widgets/agents-workspace/AgentsWorkspace";

vi.mock("@/src/entities/agent/api", () => ({
  listPublishedAgents: vi.fn(),
  createClaudeCodeBridgeAsset: vi.fn(),
  importAgent: vi.fn(),
  startValidationRun: vi.fn()
}));

vi.mock("@/src/entities/dataset/api", () => ({
  createDataset: vi.fn(),
  createDatasetVersion: vi.fn(),
  ensureClaudeCodeStarterDataset: vi.fn(),
  listDatasets: vi.fn()
}));

type MockedApiFn = ReturnType<typeof vi.fn>;

describe("Agents workspace", () => {
  beforeEach(() => {
    const publishedAgents: AgentRecord[] = [
      {
        agentId: "basic",
        name: "Basic",
        description: "Ready governed asset.",
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
          backend: "external-runner"
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
      },
      {
        agentId: "fresh_import",
        name: "Fresh Import",
        description: "Published asset that has not completed validation yet.",
        framework: "openai-agents-sdk",
        frameworkVersion: "0.1.0",
        entrypoint: "snapshots/fresh-import:run",
        defaultModel: "gpt-5.4-mini",
        tags: ["new"],
        capabilities: ["submit"],
        publishedAt: "2026-03-25T00:00:00Z",
        sourceFingerprint: "fresh-import-fingerprint-123456",
        executionReference: {
          artifactRef: "source://fresh_import@fresh-import-fingerprint-123456"
        },
        executionProfile: { backend: "external-runner" }
      }
    ];

    (agentApi.listPublishedAgents as unknown as MockedApiFn).mockReset();
    (agentApi.createClaudeCodeBridgeAsset as unknown as MockedApiFn).mockReset();
    (agentApi.importAgent as unknown as MockedApiFn).mockReset();
    (agentApi.startValidationRun as unknown as MockedApiFn).mockReset();
    (datasetApi.ensureClaudeCodeStarterDataset as unknown as MockedApiFn).mockReset();

    (agentApi.listPublishedAgents as unknown as MockedApiFn).mockImplementation(async () => publishedAgents);
    (agentApi.createClaudeCodeBridgeAsset as unknown as MockedApiFn).mockResolvedValue(null);
    (agentApi.importAgent as unknown as MockedApiFn).mockResolvedValue(null);
    (agentApi.startValidationRun as unknown as MockedApiFn).mockImplementation(async (agentId: string) => ({
      run_id: `validation-${agentId}`,
      status: "queued"
    }));
    (datasetApi.ensureClaudeCodeStarterDataset as unknown as MockedApiFn).mockResolvedValue({
      name: "claude-code-code-edit"
    });
  });

  it("groups governed assets by validation readiness and routes ready assets into experiments", async () => {
    renderWithQueryClient(<AgentsWorkspace />);

    expect(await screen.findByRole("heading", { name: "Agents" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Add an asset, review validation, then use ready assets" })).toBeInTheDocument();
    await waitFor(() => expect(agentApi.listPublishedAgents).toHaveBeenCalledTimes(1));

    expect(await screen.findByText("Ready governed asset.")).toBeInTheDocument();
    expect(screen.getByText("Published asset with an active validation run.")).toBeInTheDocument();
    expect(screen.getByText("Published asset whose latest validation failed.")).toBeInTheDocument();
    expect(screen.getByText("Published asset that has not completed validation yet.")).toBeInTheDocument();
    expect(screen.getAllByText("external-runner").length).toBeGreaterThan(0);
    expect(screen.getByText("source://basic@basic-fingerprint-123456")).toBeInTheDocument();
    expect(screen.getByText("run-validation-001")).toBeInTheDocument();
    expect(screen.getByText("bundle://basic-validation-001")).toBeInTheDocument();
    expect(screen.getAllByText("Validation run completed with evidence attached.")).toHaveLength(2);
    expect(screen.getByText("Hand this ready asset into the next experiment.")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Atlas is still running the latest validation. Wait for the active run to finish before handing this asset into experiments."
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Review the latest validation run and evidence before handing this asset into a new experiment."
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText("Run validation on this governed asset before Atlas treats it as experiment-ready.")
    ).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Run validation" })[0]).toBeEnabled();
    expect(
      screen.getAllByRole("link", { name: /Create experiment/i }).map((link) => link.getAttribute("href"))
    ).toEqual(expect.arrayContaining(["/experiments?agent=basic"]));
    expect(
      screen.getAllByRole("link", { name: /Create experiment/i }).map((link) => link.getAttribute("href"))
    ).not.toEqual(expect.arrayContaining(["/experiments?agent=customer_service"]));
    expect(
      screen.getAllByRole("link", { name: /Create experiment/i }).map((link) => link.getAttribute("href"))
    ).not.toEqual(expect.arrayContaining(["/experiments?agent=failed_live"]));
    expect(
      screen.getAllByRole("link", { name: /Create experiment/i }).map((link) => link.getAttribute("href"))
    ).not.toEqual(expect.arrayContaining(["/experiments?agent=fresh_import"]));
    expect(screen.getAllByRole("button", { name: "Run validation" })[1]).toBeDisabled();
    expect(screen.getAllByText("Needs validation").length).toBeGreaterThan(0);
    expect(screen.getByLabelText("Default model")).toHaveValue("");
    expect(screen.getByRole("button", { name: "Import asset" })).toBeDisabled();

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
        description: "Governed asset from the live catalog.",
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

    expect(await screen.findByText("Governed asset from the live catalog.")).toBeInTheDocument();
    expect(screen.getByText("Live Agent")).toBeInTheDocument();
    expect(screen.getByText("Hand this ready asset into the next experiment.")).toBeInTheDocument();
    expect(screen.getByText("bundle://live-agent-validation")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open validation evidence" })).toHaveAttribute(
      "href",
      "http://phoenix.local/trace/live-agent-validation"
    );
  });

  it("imports the first governed agent asset from the empty state action and keeps the bridge path secondary", async () => {
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

    expect(await screen.findByText("No ready assets yet")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add Claude Code bridge" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Agent ID"), { target: { value: "imported-basic" } });
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Imported Basic" } });
    fireEvent.change(screen.getByLabelText("Description"), {
      target: { value: "Governed asset imported explicitly from a runnable entrypoint." }
    });
    fireEvent.change(screen.getByLabelText("Default model"), {
      target: { value: "gpt-5-mini" }
    });
    fireEvent.change(screen.getByLabelText("Entrypoint"), {
      target: { value: "agents.imported_basic:build_agent" }
    });

    fireEvent.click(screen.getByRole("button", { name: "Import asset" }));

    await waitFor(() => expect(agentApi.importAgent).toHaveBeenCalledTimes(1));
    expect((agentApi.importAgent as unknown as MockedApiFn).mock.calls[0]?.[0]).toEqual(
      expect.objectContaining({
        agentId: "imported-basic",
        name: "Imported Basic",
        entrypoint: "agents.imported_basic:build_agent",
        framework: "openai-agents-sdk",
        defaultModel: "gpt-5-mini"
      })
    );
    expect(await screen.findByText("Governed asset imported explicitly from a runnable entrypoint.")).toBeInTheDocument();
    expect(
      screen.getByText("Imported Imported Basic. Review its validation here before using the asset in experiments.")
    ).toBeInTheDocument();
    expect(screen.getByText("Imported Basic is the current import focus on this surface.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Create experiment/i })).toHaveAttribute(
      "href",
      "/experiments?agent=imported-basic"
    );
  });

  it("reuses the existing Claude Code bridge instead of creating it again when the governed asset already exists", async () => {
    const publishedAgents: AgentRecord[] = [
      {
        agentId: "claude-code-starter",
        name: "Claude Code Starter",
        description: "Starter agent template for live-mode Atlas validation and experiment flows.",
        framework: "claude-code-cli",
        frameworkVersion: "1.0.0",
        entrypoint: "starters.claude_code:build_agent",
        defaultModel: "claude-sonnet-4",
        tags: ["bridge"],
        capabilities: ["submit"],
        publishedAt: "2026-04-06T12:00:00Z",
        sourceFingerprint: "claude-bridge-fingerprint",
        executionReference: {
          artifactRef: "bundle://claude-code-starter"
        },
        latestValidation: {
          runId: "run-claude-starter-validation",
          status: "succeeded",
          createdAt: "2026-04-06T12:01:00Z",
          startedAt: "2026-04-06T12:02:00Z",
          completedAt: "2026-04-06T12:03:00Z"
        },
        validationEvidence: {
          artifactRef: "bundle://claude-starter-validation",
          traceUrl: "http://phoenix.local/trace/claude-starter-validation"
        },
        validationOutcome: {
          status: "succeeded",
          reason: "Validation succeeded."
        },
        executionProfile: { backend: "external-runner" }
      }
    ];

    (agentApi.listPublishedAgents as unknown as MockedApiFn).mockImplementation(async () => publishedAgents);

    renderWithQueryClient(<AgentsWorkspace />);

    expect(await screen.findByText("Starter agent template for live-mode Atlas validation and experiment flows.")).toBeInTheDocument();
    const button = screen.getByRole("button", { name: "Review Claude Code bridge" });
    fireEvent.click(button);

    expect(agentApi.createClaudeCodeBridgeAsset).not.toHaveBeenCalled();
    await waitFor(() => expect(datasetApi.ensureClaudeCodeStarterDataset).toHaveBeenCalledTimes(1));
    expect(
      await screen.findByText(
        "Claude Code Starter already exists as the Claude Code bridge, and the starter code-edit dataset is ready too. Review its validation here before using it in experiments."
      )
    ).toBeInTheDocument();
    expect(screen.getByText("Claude Code Starter is the current import focus on this surface.")).toBeInTheDocument();
  });

  it("collapses bridge-id conflicts back into the existing-bridge state instead of surfacing the raw backend error", async () => {
    let publishedAgents: AgentRecord[] = [];
    const existingBridge: AgentRecord = {
      agentId: "claude-code-starter",
      name: "Claude Code Starter",
      description: "Starter agent template for live-mode Atlas validation and experiment flows.",
      framework: "claude-code-cli",
      frameworkVersion: "1.0.0",
      entrypoint: "starters.claude_code:build_agent",
      defaultModel: "claude-sonnet-4",
      tags: ["bridge"],
      capabilities: ["submit"],
      publishedAt: "2026-04-06T12:00:00Z",
      sourceFingerprint: "claude-bridge-fingerprint",
      executionReference: {
        artifactRef: "bundle://claude-code-starter"
      },
      latestValidation: {
        runId: "run-claude-starter-validation",
        status: "succeeded",
        createdAt: "2026-04-06T12:01:00Z",
        startedAt: "2026-04-06T12:02:00Z",
        completedAt: "2026-04-06T12:03:00Z"
      },
      validationEvidence: {
        artifactRef: "bundle://claude-starter-validation",
        traceUrl: "http://phoenix.local/trace/claude-starter-validation"
      },
      validationOutcome: {
        status: "succeeded",
        reason: "Validation succeeded."
      },
      executionProfile: { backend: "external-runner" }
    };

    (agentApi.listPublishedAgents as unknown as MockedApiFn).mockImplementation(async () => publishedAgents);
    (agentApi.createClaudeCodeBridgeAsset as unknown as MockedApiFn).mockImplementation(async () => {
      publishedAgents = [existingBridge];
      throw new Error("agent_id 'claude-code-starter' conflicts with an existing governed asset");
    });

    renderWithQueryClient(<AgentsWorkspace />);

    expect(await screen.findByText("No ready assets yet")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Add Claude Code bridge" }));

    await waitFor(() => expect(agentApi.createClaudeCodeBridgeAsset).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(datasetApi.ensureClaudeCodeStarterDataset).toHaveBeenCalledTimes(2));
    expect(
      await screen.findByText(
        "Claude Code Starter already exists as the Claude Code bridge, and the starter code-edit dataset is ready too. Review its validation here before using it in experiments."
      )
    ).toBeInTheDocument();
    expect(screen.queryByText("agent_id 'claude-code-starter' conflicts with an existing governed asset")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Review Claude Code bridge" })).toBeInTheDocument();
  });

  it("adds the Claude Code bridge and imports the starter dataset together", async () => {
    let publishedAgents: AgentRecord[] = [];
    const starterAgent: AgentRecord = {
      agentId: "claude-code-starter",
      name: "Claude Code Starter",
      description: "Starter agent template for live code-edit validation and experiment flows.",
      framework: "claude-code-cli",
      frameworkVersion: "1.0.0",
      entrypoint: "app.modules.agents.domain.reference_assets:build_claude_code_starter",
      defaultModel: "claude-sonnet-4",
      tags: ["starter"],
      capabilities: [],
      publishedAt: "2026-04-06T12:00:00Z",
      sourceFingerprint: "claude-starter-fingerprint",
      executionReference: {
        artifactRef: "source://claude-code-starter@claude-starter-fingerprint"
      },
      executionProfile: { backend: "external-runner" }
    };

    (agentApi.listPublishedAgents as unknown as MockedApiFn).mockImplementation(async () => publishedAgents);
    (agentApi.createClaudeCodeBridgeAsset as unknown as MockedApiFn).mockImplementation(async () => {
      publishedAgents = [starterAgent];
      return starterAgent;
    });

    renderWithQueryClient(<AgentsWorkspace />);

    expect(await screen.findByText("No ready assets yet")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Add Claude Code bridge" }));

    await waitFor(() => expect(agentApi.createClaudeCodeBridgeAsset).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(datasetApi.ensureClaudeCodeStarterDataset).toHaveBeenCalledTimes(1));
    expect(
      await screen.findByText(
        "Added Claude Code Starter as the Claude Code bridge and prepared the starter code-edit dataset. Review validation here, then use the starter flow in experiments."
      )
    ).toBeInTheDocument();
  });

  it("re-ensures the starter dataset when the bridge already exists after a prior partial success", async () => {
    let publishedAgents: AgentRecord[] = [];
    const starterAgent: AgentRecord = {
      agentId: "claude-code-starter",
      name: "Claude Code Starter",
      description: "Starter agent template for live code-edit validation and experiment flows.",
      framework: "claude-code-cli",
      frameworkVersion: "1.0.0",
      entrypoint: "app.modules.agents.domain.reference_assets:build_claude_code_starter",
      defaultModel: "claude-sonnet-4",
      tags: ["starter"],
      capabilities: [],
      publishedAt: "2026-04-06T12:00:00Z",
      sourceFingerprint: "claude-starter-fingerprint",
      executionReference: {
        artifactRef: "source://claude-code-starter@claude-starter-fingerprint"
      },
      executionProfile: { backend: "external-runner" }
    };
    let datasetAttempts = 0;

    (agentApi.listPublishedAgents as unknown as MockedApiFn).mockImplementation(async () => publishedAgents);
    (agentApi.createClaudeCodeBridgeAsset as unknown as MockedApiFn).mockImplementation(async () => {
      publishedAgents = [starterAgent];
      return starterAgent;
    });
    (datasetApi.ensureClaudeCodeStarterDataset as unknown as MockedApiFn).mockImplementation(async () => {
      datasetAttempts += 1;
      if (datasetAttempts === 1) {
        throw new Error("starter dataset import failed");
      }
      return { name: "claude-code-code-edit" };
    });

    renderWithQueryClient(<AgentsWorkspace />);

    expect(await screen.findByText("No ready assets yet")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Add Claude Code bridge" }));

    await waitFor(() => expect(agentApi.createClaudeCodeBridgeAsset).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(datasetApi.ensureClaudeCodeStarterDataset).toHaveBeenCalledTimes(1));
    expect(await screen.findByText("starter dataset import failed")).toBeInTheDocument();

    await waitFor(() => expect(screen.getByRole("button", { name: "Review Claude Code bridge" })).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "Review Claude Code bridge" }));

    await waitFor(() => expect(datasetApi.ensureClaudeCodeStarterDataset).toHaveBeenCalledTimes(2));
    expect(
      await screen.findByText(
        "Claude Code Starter already exists as the Claude Code bridge, and the starter code-edit dataset is ready too. Review its validation here before using it in experiments."
      )
    ).toBeInTheDocument();
  });
});
