import { request } from "@/src/shared/api/http";
import type { ReplayRequest, ReplayResponse } from "@/src/shared/api/contract";
import { mapReplay } from "./mapper";
import type { CreateReplayInput } from "./model";

export async function createReplay(payload: CreateReplayInput) {
  const body: ReplayRequest = {
    run_id: payload.runId,
    step_id: payload.stepId,
    edited_prompt: payload.editedPrompt ?? null,
    model: payload.model ?? null,
    tool_overrides: payload.toolOverrides ?? {},
    rationale: payload.rationale ?? null
  };

  return mapReplay(
    await request<ReplayResponse>("/api/v1/replays", {
      method: "POST",
      body: JSON.stringify(body)
    })
  );
}
