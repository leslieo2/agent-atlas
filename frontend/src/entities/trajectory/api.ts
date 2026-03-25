import { request } from "@/src/shared/api/http";
import { mapStep, type ApiTrajectoryStep } from "./mapper";

export async function getTrajectory(runId: string) {
  return (await request<ApiTrajectoryStep[]>(`/api/v1/runs/${runId}/trajectory`)).map(mapStep);
}

