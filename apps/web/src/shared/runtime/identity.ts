import type { ExecutorConfig } from "@/src/shared/api/contract";
import {
  CLAUDE_CODE_CLI_ADAPTER,
  CLAUDE_CODE_CLI_ADAPTER_LABEL
} from "@/src/shared/runtime/constants";

function readAdapterName(metadata: Record<string, unknown>) {
  const adapterName = metadata.runner_adapter;
  if (typeof adapterName === "string" && adapterName.trim()) {
    return adapterName.trim();
  }

  const adapterProfile = metadata.adapter_profile;
  if (typeof adapterProfile === "string" && adapterProfile.trim()) {
    return adapterProfile.trim();
  }

  if (metadata.claude_code_cli && typeof metadata.claude_code_cli === "object") {
    return CLAUDE_CODE_CLI_ADAPTER;
  }

  return null;
}

export function formatRunnerAdapterLabel(adapterName: string | null) {
  if (!adapterName) {
    return null;
  }

  const normalized = adapterName.trim().toLowerCase();
  if (normalized === CLAUDE_CODE_CLI_ADAPTER) {
    return CLAUDE_CODE_CLI_ADAPTER_LABEL;
  }

  return `${adapterName} adapter`;
}

export function executionProfileSummary(runtimeProfile?: ExecutorConfig | null) {
  if (!runtimeProfile?.backend) {
    return "snapshot default";
  }

  const parts = [runtimeProfile.backend];
  const metadata =
    runtimeProfile.metadata && typeof runtimeProfile.metadata === "object" ? runtimeProfile.metadata : null;
  const adapterLabel = metadata ? formatRunnerAdapterLabel(readAdapterName(metadata)) : null;

  if (adapterLabel) {
    parts.push(adapterLabel);
  }

  if (runtimeProfile.runner_image) {
    parts.push(runtimeProfile.runner_image);
  }

  return parts.join(" · ");
}
