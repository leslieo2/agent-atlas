import { describe, expect, it } from "vitest";
import {
  buildTrajectoryEdges,
  buildTrajectoryNodes,
  getComparableRuns
} from "@/src/widgets/trajectory-workspace/selectors";

const steps = [
  {
    id: "s1",
    runId: "run-001",
    stepType: "planner" as const,
    prompt: "plan",
    output: "planner",
    model: null,
    temperature: 0,
    latencyMs: 4,
    tokenUsage: 0,
    success: true,
    parentStepId: null
  },
  {
    id: "s2",
    runId: "run-001",
    stepType: "tool" as const,
    prompt: "lookup",
    output: "lookup done",
    model: "tool",
    temperature: 0,
    latencyMs: 8,
    tokenUsage: 0,
    success: true,
    toolName: "crm_lookup",
    parentStepId: "s1"
  },
  {
    id: "s3",
    runId: "run-001",
    stepType: "tool" as const,
    prompt: "search",
    output: "search done",
    model: "tool",
    temperature: 0,
    latencyMs: 9,
    tokenUsage: 0,
    success: false,
    toolName: "policy_guard",
    parentStepId: "s1"
  },
  {
    id: "s4",
    runId: "run-001",
    stepType: "llm" as const,
    prompt: "respond",
    output: "done",
    model: "gpt-5.4-mini",
    temperature: 0.2,
    latencyMs: 12,
    tokenUsage: 22,
    success: true,
    parentStepId: "s2"
  }
];

describe("trajectory workspace selectors", () => {
  it("builds edges from parent step relationships instead of step order", () => {
    const edges = buildTrajectoryEdges(steps);

    expect(edges.map((edge) => `${edge.source}->${edge.target}`)).toEqual(["s1->s2", "s1->s3", "s2->s4"]);
  });

  it("lays out child nodes by depth so branches are visually separated", () => {
    const nodes = buildTrajectoryNodes(steps, "s2");
    const positions = Object.fromEntries(nodes.map((node) => [node.id, node.position]));

    expect(positions.s1.x).toBeLessThan(positions.s2.x);
    expect(positions.s2.x).toBe(positions.s3.x);
    expect(positions.s4.x).toBeGreaterThan(positions.s2.x);
    expect(positions.s2.y).not.toBe(positions.s3.y);
  });

  it("lists comparable runs inside the same project dataset and agent scope", () => {
    const currentRun = {
      runId: "run-current",
      inputSummary: "Summarize latest support tickets",
      status: "succeeded" as const,
      latencyMs: 100,
      tokenCost: 20,
      toolCalls: 4,
      project: "support",
      dataset: "tickets-v1",
      agentId: "customer_service",
      model: "gpt-5.4-mini",
      agentType: "openai-agents-sdk" as const,
      tags: [],
      createdAt: "2026-03-25T10:00:00Z"
    };
    const runs = [
      currentRun,
      {
        ...currentRun,
        runId: "run-unrelated-input",
        inputSummary: "Draft an onboarding email",
        createdAt: "2026-03-25T09:59:00Z"
      },
      {
        ...currentRun,
        runId: "run-unrelated-dataset",
        dataset: "tickets-v2",
        createdAt: "2026-03-25T09:58:00Z"
      },
      {
        ...currentRun,
        runId: "run-match-latest",
        inputSummary: "A different prompt should still be comparable",
        createdAt: "2026-03-25T09:57:00Z"
      },
      {
        ...currentRun,
        runId: "run-match-older",
        createdAt: "2026-03-25T09:30:00Z"
      },
      {
        ...currentRun,
        runId: "run-newer-match",
        createdAt: "2026-03-25T10:01:00Z"
      }
    ];

    expect(getComparableRuns(runs, currentRun).map((run) => run.runId)).toEqual([
      "run-newer-match",
      "run-unrelated-input",
      "run-match-latest",
      "run-match-older"
    ]);
  });

  it("returns no comparable runs when dataset project or agent id drift", () => {
    const currentRun = {
      runId: "run-current",
      inputSummary: "Summarize latest support tickets",
      status: "succeeded" as const,
      latencyMs: 100,
      tokenCost: 20,
      toolCalls: 4,
      project: "support",
      dataset: "tickets-v1",
      agentId: "customer_service",
      model: "gpt-5.4-mini",
      agentType: "openai-agents-sdk" as const,
      tags: [],
      createdAt: "2026-03-25T10:00:00Z"
    };
    const runs = [
      currentRun,
      {
        ...currentRun,
        runId: "run-other-agent",
        agentId: "different-agent",
        createdAt: "2026-03-25T09:57:00Z"
      },
      {
        ...currentRun,
        runId: "run-other-project",
        project: "sales",
        createdAt: "2026-03-25T09:56:00Z"
      }
    ];

    expect(getComparableRuns(runs, currentRun)).toEqual([]);
  });
});
