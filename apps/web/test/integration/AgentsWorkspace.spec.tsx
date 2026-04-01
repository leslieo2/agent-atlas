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
  publishAgent: vi.fn(),
  unpublishAgent: vi.fn()
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
    (agentApi.publishAgent as unknown as MockedApiFn).mockReset();
    (agentApi.unpublishAgent as unknown as MockedApiFn).mockReset();

    (agentApi.listDiscoveredAgents as unknown as MockedApiFn).mockImplementation(async () => discoveredAgents);
    (agentApi.listPublishedAgents as unknown as MockedApiFn).mockResolvedValue([]);
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
    expect(screen.getByText("Use this ready snapshot to create the next experiment.")).toBeInTheDocument();
    expect(screen.getByText("Edited sample project and captured changed files.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open validation evidence" })).toHaveAttribute(
      "href",
      "http://phoenix.local/trace/validation-001"
    );
    expect(await screen.findByText("Unsupported framework plugin.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Framework")).not.toBeInTheDocument();
    expect(screen.getByText("external-runner · Claude Code CLI adapter")).toBeInTheDocument();
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
    expect(screen.getByText("Use this ready snapshot to create the next experiment.")).toBeInTheDocument();
    expect(screen.getByText("bundle://live-agent-validation")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open validation evidence" })).toHaveAttribute(
      "href",
      "http://phoenix.local/trace/live-agent-validation"
    );
    expect(screen.queryByText("No agent records are available yet.")).not.toBeInTheDocument();
  });
});
