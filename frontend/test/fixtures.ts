export type RunStatus = "queued" | "running" | "succeeded" | "failed";

export interface RunRecord {
  runId: string;
  inputSummary: string;
  status: RunStatus;
  latencyMs: number;
  tokenCost: number;
  toolCalls: number;
  project: string;
  dataset: string | null;
  model: string;
  tags: string[];
  createdAt: string;
}

export interface TrajectoryStep {
  id: string;
  runId: string;
  stepType: "llm" | "tool" | "planner" | "memory";
  parentStepId?: string | null;
  prompt: string;
  output: string;
  model: string | null;
  temperature: number;
  latencyMs: number;
  tokenUsage: number;
  success: boolean;
  toolName?: string;
}

export const runRecords: RunRecord[] = [
  {
    runId: "run-001",
    inputSummary: "Generate a booking itinerary from CRM contact data",
    status: "succeeded",
    latencyMs: 1410,
    tokenCost: 1280,
    toolCalls: 5,
    project: "sales-assistant",
    dataset: "crm-v2",
    model: "gpt-4.1-mini",
    tags: ["agent-sdk", "mcp"],
    createdAt: "2026-03-23T09:12:00Z"
  },
  {
    runId: "run-002",
    inputSummary: "Summarize latest support tickets and escalate exceptions",
    status: "failed",
    latencyMs: 960,
    tokenCost: 910,
    toolCalls: 3,
    project: "support-router",
    dataset: "support-incidents",
    model: "gpt-5-mini",
    tags: ["langchain", "tooling"],
    createdAt: "2026-03-23T10:03:00Z"
  },
  {
    runId: "run-003",
    inputSummary: "Analyze policy document and extract exceptions",
    status: "running",
    latencyMs: 0,
    tokenCost: 460,
    toolCalls: 2,
    project: "policy-lab",
    dataset: "policy-review",
    model: "gpt-4.1",
    tags: ["langchain"],
    createdAt: "2026-03-24T03:40:00Z"
  },
  {
    runId: "run-004",
    inputSummary: "Run benchmark against shopping agent benchmark",
    status: "queued",
    latencyMs: 0,
    tokenCost: 0,
    toolCalls: 0,
    project: "benchmarking",
    dataset: "shopping-bench",
    model: "gpt-4.1-mini",
    tags: ["agent-sdk"],
    createdAt: "2026-03-24T04:10:00Z"
  }
];

export const steps: TrajectoryStep[] = [
  {
    id: "s1",
    runId: "run-001",
    stepType: "planner",
    parentStepId: null,
    prompt: "Plan retrieval sequence for user request and required tools.",
    output: "Detected required tools: crm_lookup, itinerary_builder, pricing_service",
    model: null,
    temperature: 0.1,
    latencyMs: 250,
    tokenUsage: 220,
    success: true
  },
  {
    id: "s2",
    runId: "run-001",
    stepType: "tool",
    parentStepId: "s1",
    toolName: "crm_lookup",
    prompt: `input: {"contact_id":"ac-119","scope":"shipping"}`
    ,
    output: `{
  "profile": "tier: gold",
  "history": ["ticket-901", "ticket-905"],
  "preferred_carrier": "FedEx"
}`,
    model: "n/a",
    temperature: 0,
    latencyMs: 430,
    tokenUsage: 0,
    success: true
  },
  {
    id: "s3",
    runId: "run-001",
    stepType: "llm",
    parentStepId: "s2",
    prompt: "Generate a safe itinerary draft from user context and tool responses.",
    output: "Itinerary prepared with best-price shipping lane and ETA.",
    model: "gpt-4.1",
    temperature: 0.3,
    latencyMs: 520,
    tokenUsage: 310,
    success: true
  },
  {
    id: "s4",
    runId: "run-001",
    stepType: "tool",
    parentStepId: "s1",
    toolName: "pricing_service",
    prompt: `input: {"from":"PVG","to":"SFO","weight_kg":2.1}`,
    output: "quote_error: fallback route disabled for destination",
    model: "n/a",
    temperature: 0,
    latencyMs: 140,
    tokenUsage: 0,
    success: false
  }
];
