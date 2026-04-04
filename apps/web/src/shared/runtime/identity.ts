import type { ExecutionProfile } from "@/src/shared/api/contract";

export function executionProfileSummary(runtimeProfile?: ExecutionProfile | null) {
  if (!runtimeProfile?.backend) {
    return "snapshot default";
  }

  return runtimeProfile.backend;
}
