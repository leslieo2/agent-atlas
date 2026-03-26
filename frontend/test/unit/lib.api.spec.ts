import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createReplay } from "@/src/entities/replay/api";
import { createRun, listRuns } from "@/src/entities/run/api";
import type { RunStatus } from "@/src/entities/run/model";

const jsonBody = (value: unknown, status = 200): Response =>
  new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" }
  });

describe("api client", () => {
  const fetchSpy = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchSpy as unknown as typeof fetch);
    fetchSpy.mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("maps run list snake_case to camelCase record model", async () => {
    fetchSpy.mockResolvedValueOnce(
      jsonBody([
        {
          run_id: "run-001",
          input_summary: "seed run",
          status: "succeeded" as RunStatus,
          latency_ms: 10,
          token_cost: 20,
          tool_calls: 3,
          project: "sales-assistant",
          dataset: "crm-v2",
          agent_id: "customer_service",
          model: "gpt-4.1-mini",
          agent_type: "openai-agents-sdk",
          tags: ["agent-sdk"],
          created_at: "2026-03-24T00:00:00Z"
        }
      ])
    );

    const runs = await listRuns({ status: "succeeded", project: "sales-assistant" });

    expect(runs).toHaveLength(1);
    expect(runs[0]).toMatchObject({
      runId: "run-001",
      inputSummary: "seed run",
      status: "succeeded",
      latencyMs: 10,
      tokenCost: 20,
      toolCalls: 3,
      agentId: "customer_service",
      agentType: "openai-agents-sdk",
      tags: ["agent-sdk"]
    });
    expect(fetchSpy).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/runs?status=succeeded&project=sales-assistant",
      expect.objectContaining({ headers: expect.any(Object) })
    );
  });

  it("maps replay result from API payload", async () => {
    fetchSpy.mockResolvedValueOnce(
      jsonBody({
        replay_id: "replay-001",
        run_id: "run-001",
        step_id: "step-1",
        baseline_output: "old",
        replay_output: "new",
        diff: "diff",
        updated_prompt: "patched",
        model: "gpt-4.1-mini",
        temperature: 0.0,
        started_at: "2026-03-24T00:00:00Z"
      })
    );

    const replay = await createReplay({
      runId: "run-001",
      stepId: "step-1",
      editedPrompt: "patched",
      model: "gpt-4.1-mini"
    });

    expect(replay.replayId).toBe("replay-001");
    expect(replay.baselineOutput).toBe("old");
    expect(replay.model).toBe("gpt-4.1-mini");
  });

  it("builds payload for createRun and throws on API errors", async () => {
    fetchSpy.mockResolvedValueOnce(jsonBody("server_error", 500));

    await expect(
      createRun({
        project: "sales",
        dataset: "crm-v2",
        agentId: "basic",
        inputSummary: "bad run",
        prompt: "do it"
      })
    ).rejects.toThrow("Request failed: 500");
  });

  it("sends null dataset for prompt-only createRun requests", async () => {
    fetchSpy.mockResolvedValueOnce(
      jsonBody({
        run_id: "run-001",
        input_summary: "prompt only",
        status: "queued" as RunStatus,
        latency_ms: 0,
        token_cost: 0,
        tool_calls: 0,
        project: "sales",
        dataset: null,
        agent_id: "basic",
        model: "gpt-4.1-mini",
        agent_type: "openai-agents-sdk",
        tags: [],
        created_at: "2026-03-24T00:00:00Z",
        project_metadata: {}
      })
    );

    await createRun({
      project: "sales",
      dataset: null,
      agentId: "basic",
      inputSummary: "prompt only",
      prompt: "do it"
    });

    const [, requestInit] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(requestInit.body).toBeDefined();
    expect(JSON.parse(String(requestInit.body))).toMatchObject({
      dataset: null
    });
  });

  it("surfaces structured API error messages", async () => {
    fetchSpy.mockResolvedValueOnce(
      jsonBody(
        {
          detail: {
            code: "model_not_found",
            message: "model 'planner-v1' not found",
            model: "planner-v1"
          }
        },
        400
      )
    );

    await expect(
      createReplay({
        runId: "run-001",
        stepId: "step-1",
        editedPrompt: "patched",
        model: "planner-v1"
      })
    ).rejects.toThrow("model 'planner-v1' not found");
  });
});
