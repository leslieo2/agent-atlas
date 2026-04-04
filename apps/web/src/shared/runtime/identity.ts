import type { ExecutionProfile_Output } from "@/src/shared/api/contract";

export function executionProfileSummary(runtimeProfile?: ExecutionProfile_Output | null) {
  if (!runtimeProfile?.backend) {
    return "snapshot default";
  }

  return runtimeProfile.backend;
}
