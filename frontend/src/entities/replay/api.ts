import { request } from "@/src/shared/api/http";
import { mapReplay, type ApiReplayResult } from "./mapper";
import type { CreateReplayInput } from "./model";

export async function createReplay(payload: CreateReplayInput) {
  return mapReplay(
    await request<ApiReplayResult>("/api/v1/replays", {
      method: "POST",
      body: JSON.stringify({
        run_id: payload.runId,
        step_id: payload.stepId,
        edited_prompt: payload.editedPrompt,
        model: payload.model,
        tool_overrides: payload.toolOverrides ?? {},
        rationale: payload.rationale
      })
    })
  );
}

