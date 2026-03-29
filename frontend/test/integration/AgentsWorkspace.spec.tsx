import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import * as agentApi from "@/src/entities/agent/api";
import type { DiscoveredAgentRecord } from "@/src/entities/agent/model";
import { renderWithQueryClient } from "@/test/setup";
import AgentsWorkspace from "@/src/widgets/agents-workspace/AgentsWorkspace";

vi.mock("@/src/entities/agent/api", () => ({
  listAgents: vi.fn(),
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
        entrypoint: "app.agent_plugins.basic:build_agent",
        defaultModel: "gpt-5.4-mini",
        tags: ["example", "smoke"],
        publishState: "published" as const,
        validationStatus: "valid" as const,
        validationIssues: [],
        publishedAt: "2026-03-20T09:00:00Z",
        lastValidatedAt: "2026-03-26T09:00:00Z",
        hasUnpublishedChanges: false,
        runtimeArtifact: {
          buildStatus: "ready",
          sourceFingerprint: "basic-fingerprint-123456",
          artifactRef: "source://basic@basic-fingerprint-123456"
        }
      },
      {
        agentId: "graph-bot",
        name: "Graph Bot",
        description: "Ready LangChain agent.",
        framework: "langchain",
        entrypoint: "test_agent_plugins.graph_bot:build_agent",
        defaultModel: "gpt-5.4-mini",
        tags: ["langchain", "graph"],
        publishState: "published" as const,
        validationStatus: "valid" as const,
        validationIssues: [],
        publishedAt: "2026-03-19T09:00:00Z",
        lastValidatedAt: "2026-03-26T09:00:00Z",
        hasUnpublishedChanges: false,
        runtimeArtifact: {
          buildStatus: "ready",
          sourceFingerprint: "graph-fingerprint-123456",
          artifactRef: "source://graph-bot@graph-fingerprint-123456"
        }
      },
      {
        agentId: "customer_service",
        name: "Customer Service",
        description: "Published agent with local changes.",
        framework: "openai-agents-sdk",
        entrypoint: "app.agent_plugins.customer_service:build_agent",
        defaultModel: "gpt-5.4-mini",
        tags: ["support", "ops"],
        publishState: "published" as const,
        validationStatus: "valid" as const,
        validationIssues: [],
        publishedAt: "2026-03-18T08:30:00Z",
        lastValidatedAt: "2026-03-26T09:00:00Z",
        hasUnpublishedChanges: true,
        runtimeArtifact: {
          buildStatus: "ready",
          sourceFingerprint: "customer-fingerprint-123456",
          artifactRef: "source://customer_service@customer-fingerprint-123456"
        }
      },
      {
        agentId: "tools",
        name: "Tools",
        description: "Draft tool agent.",
        framework: "openai-agents-sdk",
        entrypoint: "app.agent_plugins.tools:build_agent",
        defaultModel: "gpt-5.4-mini",
        tags: ["example", "tools"],
        publishState: "draft" as const,
        validationStatus: "valid" as const,
        validationIssues: [],
        publishedAt: undefined,
        lastValidatedAt: "2026-03-26T09:00:00Z",
        hasUnpublishedChanges: false
      },
      {
        agentId: "broken",
        name: "Broken",
        description: "Broken plugin.",
        framework: "openai-agents-sdk",
        entrypoint: "app.agent_plugins.broken:build_agent",
        defaultModel: "gpt-5.4-mini",
        tags: [],
        publishState: "published" as const,
        validationStatus: "invalid" as const,
        validationIssues: [{ code: "build_agent_failed", message: "entrypoint validation failed" }],
        publishedAt: "2026-03-12T10:00:00Z",
        lastValidatedAt: "2026-03-26T09:00:00Z",
        hasUnpublishedChanges: false
      },
      {
        agentId: "unsupported",
        name: "Unsupported",
        description: "Unsupported framework plugin.",
        framework: "mcp",
        entrypoint: "app.agent_plugins.unsupported:build_agent",
        defaultModel: "gpt-5.4-mini",
        tags: [],
        publishState: "draft" as const,
        validationStatus: "invalid" as const,
        validationIssues: [{ code: "framework_unsupported", message: "framework 'mcp' is not supported for discovery" }],
        publishedAt: undefined,
        lastValidatedAt: "2026-03-26T09:00:00Z",
        hasUnpublishedChanges: false
      }
    ];

    (agentApi.listDiscoveredAgents as unknown as MockedApiFn).mockReset();
    (agentApi.publishAgent as unknown as MockedApiFn).mockReset();
    (agentApi.unpublishAgent as unknown as MockedApiFn).mockReset();

    (agentApi.listDiscoveredAgents as unknown as MockedApiFn).mockImplementation(async () => discoveredAgents);
    (agentApi.publishAgent as unknown as MockedApiFn).mockImplementation(async (agentId: string) => {
      discoveredAgents = discoveredAgents.map((agent) =>
        agent.agentId === agentId ? { ...agent, publishState: "published" as const } : agent
      );
      return discoveredAgents.find((agent) => agent.agentId === agentId);
    });
    (agentApi.unpublishAgent as unknown as MockedApiFn).mockImplementation(async (agentId: string) => {
      discoveredAgents = discoveredAgents.map((agent) =>
        agent.agentId === agentId ? { ...agent, publishState: "draft" as const } : agent
      );
      return { agent_id: agentId, published: false };
    });
  });

  it("groups discovered agents and refreshes after publish and unpublish", async () => {
    renderWithQueryClient(<AgentsWorkspace />);

    expect(await screen.findByText("Agents")).toBeInTheDocument();
    expect(await screen.findByText("Ready OpenAI smoke agent.")).toBeInTheDocument();
    expect(await screen.findByText("Ready LangChain agent.")).toBeInTheDocument();
    expect(await screen.findByText("Published agent with local changes.")).toBeInTheDocument();
    expect(await screen.findByText("Draft tool agent.")).toBeInTheDocument();
    expect(await screen.findByText("entrypoint validation failed")).toBeInTheDocument();
    expect(await screen.findByText("framework 'mcp' is not supported for discovery")).toBeInTheDocument();
    expect(screen.getByText("OpenAI Agents SDK validation issues")).toBeInTheDocument();
    expect(screen.getByText("Unsupported framework issues")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /Run eval/i })[0]).toHaveAttribute("href", "/evals?agent=basic");
    expect(screen.getByText("Ready to run")).toBeInTheDocument();
    expect(screen.getByText("Published with draft changes")).toBeInTheDocument();
    expect(screen.getByText("Current repository code differs from the published snapshot.")).toBeInTheDocument();
    expect(screen.getAllByText("Build ready")).not.toHaveLength(0);
    expect(screen.getByText("source://basic@basic-fingerprint-123456")).toBeInTheDocument();
    expect(screen.getByText("basic-finger")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Framework"), { target: { value: "langchain" } });
    expect(await screen.findByText("Ready LangChain agent.")).toBeInTheDocument();
    expect(screen.queryByText("Ready OpenAI smoke agent.")).not.toBeInTheDocument();
    expect(screen.queryByText("Draft tool agent.")).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Framework"), { target: { value: "all" } });
    fireEvent.click(screen.getByRole("button", { name: "Publish" }));
    await waitFor(() => expect(agentApi.publishAgent).toHaveBeenCalledWith("tools"));
    await waitFor(() => expect(agentApi.listDiscoveredAgents).toHaveBeenCalledTimes(3));

    fireEvent.click(screen.getAllByRole("button", { name: "Unpublish" })[0]);
    await waitFor(() => expect(agentApi.unpublishAgent).toHaveBeenCalled());
    await waitFor(() => expect(agentApi.listDiscoveredAgents).toHaveBeenCalledTimes(5));
  });
});
