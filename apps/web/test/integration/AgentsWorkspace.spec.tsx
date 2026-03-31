import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import * as agentApi from "@/src/entities/agent/api";
import type { DiscoveredAgentRecord } from "@/src/entities/agent/model";
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
        runtimeArtifact: {
          buildStatus: "ready",
          sourceFingerprint: "basic-fingerprint-123456",
          artifactRef: "source://basic@basic-fingerprint-123456"
        },
        provenance: null
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
        runtimeArtifact: {
          buildStatus: "ready",
          sourceFingerprint: "customer-fingerprint-123456",
          artifactRef: "source://customer_service@customer-fingerprint-123456"
        },
        provenance: null
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
        provenance: null
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
        provenance: null
      }
    ];

    (agentApi.listDiscoveredAgents as unknown as MockedApiFn).mockReset();
    (agentApi.listPublishedAgents as unknown as MockedApiFn).mockReset();
    (agentApi.publishAgent as unknown as MockedApiFn).mockReset();
    (agentApi.unpublishAgent as unknown as MockedApiFn).mockReset();

    (agentApi.listDiscoveredAgents as unknown as MockedApiFn).mockImplementation(async () => discoveredAgents);
    (agentApi.listPublishedAgents as unknown as MockedApiFn).mockResolvedValue([
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
        publishedAt: "2026-03-20T09:00:00Z",
        runtimeArtifact: {
          buildStatus: "ready",
          sourceFingerprint: "basic-fingerprint-123456",
          artifactRef: "source://basic@basic-fingerprint-123456"
        },
        provenance: null
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
        publishedAt: "2026-03-10T09:00:00Z",
        runtimeArtifact: {
          buildStatus: "ready",
          sourceFingerprint: "archived-fingerprint-123456",
          artifactRef: "source://archived_basic@archived-fingerprint-123456"
        },
        provenance: null
      }
    ]);
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
    expect(screen.getByText("Published snapshot no longer discoverable locally.")).toBeInTheDocument();
    expect(screen.getByText("framework 'mcp' is not supported for discovery")).toBeInTheDocument();
    expect(
      screen
        .getAllByRole("link", { name: /Create experiment/i })
        .map((link) => link.getAttribute("href"))
    ).toEqual(
      expect.arrayContaining([
        "/experiments?agent=basic",
        "/experiments?agent=customer_service"
      ])
    );
    expect(
      screen
        .getAllByRole("link", { name: /Create experiment/i })
        .map((link) => link.getAttribute("href"))
    ).not.toContain("/experiments?agent=archived_basic");
    expect(screen.getByText("source://basic@basic-fingerprint-123456")).toBeInTheDocument();
    expect(screen.getByText("Published snapshots that Atlas still knows about even though the local plugin is unavailable.")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Framework"), { target: { value: "mcp" } });
    expect(await screen.findByText("Unsupported framework plugin.")).toBeInTheDocument();
    expect(screen.queryByText("Ready OpenAI smoke agent.")).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Framework"), { target: { value: "all" } });
    fireEvent.click(screen.getByRole("button", { name: "Publish" }));
    await waitFor(() => expect(agentApi.publishAgent).toHaveBeenCalledWith("tools"));

    fireEvent.click(screen.getAllByRole("button", { name: "Unpublish" })[0]);
    await waitFor(() => expect(agentApi.unpublishAgent).toHaveBeenCalledWith("basic"));
  });
});
