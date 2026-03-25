import { request } from "@/src/shared/api/http";
import type { TrajectoryStepResponse } from "@/src/shared/api/contract";
import { mapStep } from "./mapper";

export async function getTrajectory(runId: string) {
  return (await request<TrajectoryStepResponse[]>(`/api/v1/runs/${runId}/trajectory`)).map(mapStep);
}
