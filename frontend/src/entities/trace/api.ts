import { request } from "@/src/shared/api/http";
import type { RunTraceSpanResponse } from "@/src/shared/api/contract";
import { mapTraceSpan } from "./mapper";

export async function listRunTraces(runId: string) {
  return (await request<RunTraceSpanResponse[]>(`/api/v1/runs/${runId}/traces`)).map(
    mapTraceSpan
  );
}
