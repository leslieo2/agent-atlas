import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import * as agentApi from "@/src/entities/agent/api";
import type { AgentRecord, DiscoveredAgentRecord } from "@/src/entities/agent/model";
import { renderWithQueryClient } from "@/test/setup";
import AgentsWorkspace from "@/src/widgets/agents-workspace/AgentsWorkspace";

vi.mock("@/src/entities/agent/api", () => ({
  listPublishedAgents: vi.fn(),
  listDiscoveredAgents: vi.fn(),
  bootstrapClaudeCodeAgent: vi.fn(),
  publishAgent: vi.fn(),
  unpublishAgent: vi.fn(),
  startValidationRun: vi.fn()
}));

type MockedApiFn = ReturnType<typeof vi.fn>;

describe("Agents workspace", () => {
  beforeEach(() => {
    let discoveredAgents: DiscoveredAgentRecord[] = [
      {
        agentId: "basic",
        name: "Basic",
        description: "Ready OpenAI smoke agent.",
        framework: "openai-agents-sdk",
        frameworkVersion: "0.1.0",
        entrypoint: "app.agent_plugins.basic:build_agent",
        defaultModel: "gpt-5.4-mini",
        tags: ["example", "smoke"],
        capabilities: ["submit", "cancel"],
        publishState: "published",
        validationStatus: "valid",
        validationIssues: [],
        publishedAt: "2026-03-20T09:00:00Z",
        lastValidatedAt: "2026-03-26T09:00:00Z",
        hasUnpublishedChanges: false,
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
        agentId: "customer_service",
        name: "Customer Service",
        description: "Published agent with local changes.",
        framework: "openai-agents-sdk",
        frameworkVersion: "0.1.0",
        entrypoint: "app.agent_plugins.customer_service:build_agent",
        defaultModel: "gpt-5.4-mini",
        tags: ["support", "ops"],
        capabilities: ["submit", "cancel"],
        publishState: "published",
        validationStatus: "valid",
        validationIssues: [],
        publishedAt: "2026-03-18T08:30:00Z",
        lastValidatedAt: "2026-03-26T09:00:00Z",
        hasUnpublishedChanges: true,
        sourceFingerprint: "customer-fingerprint-123456",
        executionReference: {
          artifactRef: "source://customer_service@customer-fingerprint-123456"
        },
        defaultRuntimeProfile: { backend: "k8s-job" }
      },
      {
        agentId: "tools",
        name: "Tools",
        description: "Draft tool agent.",
        framework: "openai-agents-sdk",
        frameworkVersion: "0.1.0",
        entrypoint: "app.agent_plugins.tools:build_agent",
        defaultModel: "gpt-5.4-mini",
        tags: ["example", "tools"],
        capabilities: ["submit"],
        publishState: "draft",
        validationStatus: "valid",
        validationIssues: [],
        lastValidatedAt: "2026-03-26T09:00:00Z",
        hasUnpublishedChanges: false,
        sourceFingerprint: "tools-fingerprint-123456",
        executionReference: null,
        defaultRuntimeProfile: { backend: "k8s-job" }
      },
      {
        agentId: "unsupported",
        name: "Unsupported",
        description: "Unsupported framework plugin.",
        framework: "mcp",
        frameworkVersion: "0.1.0",
        entrypoint: "app.agent_plugins.unsupported:build_agent",
        defaultModel: "gpt-5.4-mini",
        tags: [],
        capabilities: [],
        publishState: "draft",
        validationStatus: "invalid",
        validationIssues: [{ code: "framework_unsupported", message: "framework 'mcp' is not supported for discovery" }],
        lastValidatedAt: "2026-03-26T09:00:00Z",
        hasUnpublishedChanges: false,
        sourceFingerprint: "unsupported-fingerprint-123456",
        executionReference: null,
        defaultRuntimeProfile: { backend: "k8s-job" }
      }
    ];

    (agentApi.listDiscoveredAgents as unknown as MockedApiFn).mockReset();
    (agentApi.listPublishedAgents as unknown as MockedApiFn).mockReset();
    (agentApi.bootstrapClaudeCodeAgent as unknown as MockedApiFn).mockReset();
    (agentApi.publishAgent as unknown as MockedApiFn).mockReset();
    (agentApi.unpublishAgent as unknown as MockedApiFn).mockReset();
    (agentApi.startValidationRun as unknown as MockedApiFn).mockReset();

    (agentApi.listDiscoveredAgents as unknown as MockedApiFn).mockImplementation(async () => discoveredAgents);
    (agentApi.listPublishedAgents as unknown as MockedApiFn).mockResolvedValue([]);
    (agentApi.bootstrapClaudeCodeAgent as unknown as MockedApiFn).mockResolvedValue(null);
    (agentApi.publishAgent as unknown as MockedApiFn).mockImplementation(async (agentId: string) => {
      discoveredAgents = discoveredAgents.map((agent) =>
        agent.agentId === agentId ? { ...agent, publishState: "published" } : agent
      );
      return discoveredAgents.find((agent) => agent.agentId === agentId);
    });
    (agentApi.unpublishAgent as unknown as MockedApiFn).mockImplementation(async (agentId: string) => {
      discoveredAgents = discoveredAgents.map((agent) =>
        agent.agentId === agentId ? { ...agent, publishState: "draft" } : agent
      );
      return { agent_id: agentId, published: false };
    });
    (agentApi.startValidationRun as unknown as MockedApiFn).mockImplementation(async (agentId: string) => ({
      run_id: `validation-${agentId}`,
      status: "queued"
    }));
  });

  it("groups discovered agents and routes published agents into experiments", async () => {
    renderWithQueryClient(<AgentsWorkspace />);

    expect(await screen.findByRole("heading", { name: "Agents" })).toBeInTheDocument();
    await waitFor(() => expect(agentApi.listDiscoveredAgents).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(agentApi.listPublishedAgents).toHaveBeenCalledTimes(1));

    expect(await screen.findByText("Ready OpenAI smoke agent.")).toBeInTheDocument();
    expect(screen.getByText("Published agent with local changes.")).toBeInTheDocument();
    expect(screen.getByText("framework 'mcp' is not supported for discovery")).toBeInTheDocument();
    expect(
      screen
        .getAllByRole("link", { name: /Create experiment/i })
        .map((link) => link.getAttribute("href"))
    ).toEqual(
      expect.arrayContaining([
        "/experiments?agent=basic"
      ])
    );
    expect(
      screen
        .getAllByRole("link", { name: /Create experiment/i })
        .map((link) => link.getAttribute("href"))
    ).not.toEqual(expect.arrayContaining(["/experiments?agent=customer_service"]));
    expect(
      screen
        .getAllByRole("link", { name: /Create experiment/i })
        .map((link) => link.getAttribute("href"))
    ).not.toEqual(expect.arrayContaining(["/experiments?agent=archived_basic"]));
    expect(screen.getByText("source://basic@basic-fingerprint-123456")).toBeInTheDocument();
    expect(screen.getByText("run-validation-001")).toBeInTheDocument();
    expect(screen.getByText("bundle://basic-validation-001")).toBeInTheDocument();
    expect(screen.getAllByText("Validation run completed with evidence attached.")).toHaveLength(2);
    expect(screen.getByText("Hand this ready snapshot into the next experiment.")).toBeInTheDocument();
    expect(screen.getByText("Edited sample project and captured changed files.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open validation evidence" })).toHaveAttribute(
      "href",
      "http://phoenix.local/trace/validation-001"
    );
    expect(await screen.findByText("Unsupported framework plugin.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Framework")).not.toBeInTheDocument();
    expect(screen.getByText("external-runner · Claude Code CLI adapter")).toBeInTheDocument();
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
    fireEvent.click(screen.getByRole("button", { name: "Publish" }));
    await waitFor(() => expect(agentApi.publishAgent).toHaveBeenCalledWith("tools"));

    fireEvent.click(screen.getAllByRole("button", { name: "Unpublish" })[0]);
    await waitFor(() => expect(agentApi.unpublishAgent).toHaveBeenCalledWith("basic"));
  });

  it("renders published agents in live mode when discovery returns no records", async () => {
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
        defaultRuntimeProfile: {
          backend: "external-runner"
        }
      }
    ];

    (agentApi.listDiscoveredAgents as unknown as MockedApiFn).mockResolvedValue([]);
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
    expect(screen.queryByText("No agent records are available yet.")).not.toBeInTheDocument();
  });

  it("bootstraps the first governed agent asset from the empty state action", async () => {
    let publishedAgents: AgentRecord[] = [];
    let discoveredAgents: DiscoveredAgentRecord[] = [];
    const starterAgent: AgentRecord = {
      agentId: "claude-code-starter",
      name: "Claude Code Starter",
      description: "Published starter snapshot created from the formal live bootstrap route.",
      framework: "openai-agents-sdk",
      frameworkVersion: "0.1.0",
      entrypoint: "snapshots/claude-code-starter:run",
      defaultModel: "gpt-5.4-mini",
      tags: ["starter", "live"],
      capabilities: ["submit"],
      publishedAt: "2026-04-02T09:00:00Z",
      sourceFingerprint: "claude-code-starter-fingerprint-123456",
      executionReference: {
        artifactRef: "bundle://claude-code-starter"
      },
      latestValidation: {
        runId: "run-claude-code-starter-validation",
        status: "succeeded",
        createdAt: "2026-04-02T09:01:00Z",
        startedAt: "2026-04-02T09:02:00Z",
        completedAt: "2026-04-02T09:03:00Z"
      },
      validationEvidence: {
        artifactRef: "bundle://claude-code-starter-validation",
        traceUrl: "http://phoenix.local/trace/claude-code-starter-validation"
      },
      validationOutcome: {
        status: "succeeded",
        reason: "Starter bootstrap completed with reusable validation evidence."
      },
      defaultRuntimeProfile: {
        backend: "external-runner",
        runner_image: "atlas-claude-validation:local",
        metadata: {
          runner_backend: "docker-container",
          claude_code_cli: {
            command: "claude",
            version: "starter"
          }
        }
      }
    };
    const starterDiscovered: DiscoveredAgentRecord = {
      ...starterAgent,
      publishState: "published",
      validationStatus: "valid",
      validationIssues: [],
      lastValidatedAt: "2026-04-02T09:03:00Z",
      hasUnpublishedChanges: false
    };

    (agentApi.listDiscoveredAgents as unknown as MockedApiFn).mockImplementation(async () => discoveredAgents);
    (agentApi.listPublishedAgents as unknown as MockedApiFn).mockImplementation(async () => publishedAgents);
    (agentApi.bootstrapClaudeCodeAgent as unknown as MockedApiFn).mockImplementation(async () => {
      publishedAgents = [starterAgent];
      discoveredAgents = [starterDiscovered];
      return starterAgent;
    });
    (agentApi.unpublishAgent as unknown as MockedApiFn).mockImplementation(async (agentId: string) => {
      publishedAgents = [];
      discoveredAgents = discoveredAgents.map((agent) =>
        agent.agentId === agentId ? { ...agent, publishState: "draft", publishedAt: undefined } : agent
      );
      return { agent_id: agentId, published: false };
    });

    renderWithQueryClient(<AgentsWorkspace />);

    expect(await screen.findByText("Bootstrap the first governed Claude Code asset")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Bootstrap Claude Code asset" }));

    await waitFor(() => expect(agentApi.bootstrapClaudeCodeAgent).toHaveBeenCalledTimes(1));
    expect(await screen.findByText("Published starter snapshot created from the formal live bootstrap route.")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Created Claude Code Starter. Atlas can now validate it, return it to draft, or hand the governed snapshot into experiments from this surface."
      )
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Create experiment/i })).toHaveAttribute(
      "href",
      "/experiments?agent=claude-code-starter"
    );

    fireEvent.click(screen.getByRole("button", { name: "Unpublish" }));
    await waitFor(() => expect(agentApi.unpublishAgent).toHaveBeenCalledWith("claude-code-starter"));
    expect(await screen.findByRole("button", { name: "Publish" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run validation" })).toBeInTheDocument();
  });
});
