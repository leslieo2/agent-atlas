"use client";

import { ArrowUpRight } from "lucide-react";
import { useMemo, useState } from "react";
import {
  useCreateClaudeCodeBridgeAssetMutation,
  useImportAgentMutation,
  usePublishedAgentsQuery,
  useStartValidationRunMutation
} from "@/src/entities/agent/query";
import { getAgentValidationLifecycle } from "@/src/entities/agent/lifecycle";
import type {
  AgentRecord,
  AgentValidationEvidenceSummaryRecord,
  AgentValidationOutcomeSummaryRecord,
  AgentValidationRunReferenceRecord,
  ExecutionReferenceRecord,
  ImportAgentInput
} from "@/src/entities/agent/model";
import { executionProfileSummary } from "@/src/shared/runtime/identity";
import { Button } from "@/src/shared/ui/Button";
import { Field } from "@/src/shared/ui/Field";
import { MetricCard } from "@/src/shared/ui/MetricCard";
import { Notice } from "@/src/shared/ui/Notice";
import { Panel } from "@/src/shared/ui/Panel";
import { StatusPill } from "@/src/shared/ui/StatusPill";
import styles from "./AgentsWorkspace.module.css";

type AgentGroup = {
  title: string;
  description: string;
  items: AgentRecord[];
};

type AgentReadiness = "ready" | "validating" | "needs_validation" | "needs_review";

type EntryFocus = {
  agentId: string;
  name: string;
};

const CLAUDE_CODE_BRIDGE_AGENT_ID = "claude-code-starter";

function fallbackValidationTimestamp(agent: AgentRecord) {
  return (
    agent.latestValidation?.completedAt ??
    agent.latestValidation?.startedAt ??
    agent.latestValidation?.createdAt ??
    agent.publishedAt ??
    new Date(0).toISOString()
  );
}

function getAgentReadiness(agent: AgentRecord): AgentReadiness {
  const validationLifecycle = getAgentValidationLifecycle(agent);
  if (validationLifecycle.isActive) {
    return "validating";
  }
  if (validationLifecycle.isSuccessful) {
    return "ready";
  }
  if (validationLifecycle.isBlocking) {
    return "needs_review";
  }
  return "needs_validation";
}

function readinessLabel(state: AgentReadiness) {
  if (state === "validating") {
    return "Validating";
  }
  if (state === "needs_validation") {
    return "Needs validation";
  }
  if (state === "needs_review") {
    return "Needs review";
  }
  return "Ready";
}

function validationTone(agent: AgentRecord) {
  return getAgentValidationLifecycle(agent).tone;
}

function validationRunTone(status?: string | null) {
  return getAgentValidationLifecycle({
    latestValidation: status ? ({ status } as AgentValidationRunReferenceRecord) : null,
    validationOutcome: null
  }).tone;
}

function executionReferenceSummary(executionReference?: ExecutionReferenceRecord | null) {
  if (!executionReference) {
    return "-";
  }
  if (executionReference.imageRef) {
    return executionReference.imageRef;
  }
  if (executionReference.artifactRef) {
    return executionReference.artifactRef;
  }
  return "-";
}

function shortSourceFingerprint(sourceFingerprint?: string) {
  const fingerprint = sourceFingerprint?.trim() ?? "";
  if (!fingerprint) {
    return "-";
  }
  return fingerprint.slice(0, 12);
}

function defaultRuntimeSummary(agent: AgentRecord) {
  return executionProfileSummary(agent.executionProfile);
}

function formatValidationTimestamp(validationRun?: AgentValidationRunReferenceRecord | null) {
  const value = validationRun?.completedAt ?? validationRun?.startedAt ?? validationRun?.createdAt ?? null;
  if (!value) {
    return "-";
  }
  return new Date(value).toLocaleString("en");
}

function validationSummaryStatus(
  validationRun?: AgentValidationRunReferenceRecord | null,
  validationOutcome?: AgentValidationOutcomeSummaryRecord | null
) {
  return validationRun?.status ?? validationOutcome?.status ?? "unknown";
}

function validationEvidenceLabel(validationEvidence?: AgentValidationEvidenceSummaryRecord | null) {
  if (!validationEvidence) {
    return "-";
  }
  if (validationEvidence.artifactRef) {
    return validationEvidence.artifactRef;
  }
  if (validationEvidence.imageRef) {
    return validationEvidence.imageRef;
  }
  return "-";
}

function nextStepLabel(agent: AgentRecord) {
  const readiness = getAgentReadiness(agent);
  if (readiness === "validating") {
    return "Atlas is still running the latest validation. Wait for the active run to finish before handing this asset into experiments.";
  }
  if (readiness === "needs_validation") {
    return "Run validation on this governed asset before Atlas treats it as experiment-ready.";
  }
  if (readiness === "needs_review") {
    return "Review the latest validation run and evidence before handing this asset into a new experiment.";
  }
  return "Hand this ready asset into the next experiment.";
}

function entryFocusSummary(agent?: AgentRecord | null) {
  if (!agent) {
    return "Import a runnable asset or add the Claude Code bridge, then validate it here before using the asset in experiments.";
  }
  const readiness = getAgentReadiness(agent);
  if (readiness === "validating") {
    return `${agent.name} has an active validation run. Wait for the latest run to resolve before using this asset in experiments.`;
  }
  if (readiness === "needs_validation") {
    return `${agent.name} still needs a successful validation run before Atlas exposes it as experiment-ready.`;
  }
  if (readiness === "needs_review") {
    return `${agent.name} needs validation review. Resolve the latest outcome before using this asset in experiments.`;
  }
  return `${agent.name} is ready for experiments based on its latest validation summary.`;
}

function validationPayload(agent: AgentRecord) {
  return {
    project: "atlas-validation",
    dataset: "controlled-validation",
    input_summary: `Validate ${agent.name} from the Agents surface`,
    prompt: "alpha",
    tags: ["agents-surface"],
    project_metadata: {
      validation_target: agent.agentId,
      validation_surface: "agents"
    },
    executor_config: agent.executionProfile
  };
}

function bridgeAlreadyExistsMessage(agent: AgentRecord) {
  return `${agent.name} already exists as the Claude Code bridge. Review its validation here before using it in experiments.`;
}

function AgentCard({
  agent,
  onValidate,
  isValidating
}: {
  agent: AgentRecord;
  onValidate: (agent: AgentRecord) => void;
  isValidating: boolean;
}) {
  const validationLifecycle = getAgentValidationLifecycle(agent);
  const readiness = getAgentReadiness(agent);
  const isRunnableSnapshot = validationLifecycle.isSuccessful;

  return (
    <article className={styles.card}>
      <div className={styles.cardHeader}>
        <div className={styles.cardTitle}>
          <div>
            <p className="page-eyebrow">Agent</p>
            <h3 className="panel-title">{agent.name}</h3>
          </div>
          <p className="muted-note">{agent.description}</p>
        </div>
        <div className="toolbar">
          <StatusPill tone={readiness === "ready" ? "success" : "warn"}>{readinessLabel(readiness)}</StatusPill>
          <StatusPill tone={validationTone(agent)}>{validationLifecycle.status}</StatusPill>
        </div>
      </div>

      {readiness === "validating" ? (
        <p className={styles.driftNotice}>
          Atlas is projecting this asset from the active validation run. The experiment handoff stays blocked until that run resolves.
        </p>
      ) : null}

      <div>
        <p className="page-eyebrow">Next step</p>
        <p className="muted-note">{nextStepLabel(agent)}</p>
      </div>

      {agent.latestValidation || agent.validationOutcome || agent.validationEvidence ? (
        <div>
          <div className="toolbar">
            <p className="page-eyebrow">Latest validation</p>
            <StatusPill tone={validationRunTone(validationSummaryStatus(agent.latestValidation, agent.validationOutcome))}>
              {validationSummaryStatus(agent.latestValidation, agent.validationOutcome)}
            </StatusPill>
          </div>
          <p className="muted-note">
            {agent.validationOutcome?.reason ?? "Validation evidence is available for the latest run."}
          </p>
          <div className={styles.meta}>
            <div className={styles.metaItem}>
              <span className={styles.metaLabel}>Validation run</span>
              <span className={`${styles.metaValue} mono`}>{agent.latestValidation?.runId ?? "-"}</span>
            </div>
            <div className={styles.metaItem}>
              <span className={styles.metaLabel}>Validated at</span>
              <span className={styles.metaValue}>{formatValidationTimestamp(agent.latestValidation)}</span>
            </div>
            <div className={styles.metaItem}>
              <span className={styles.metaLabel}>Evidence ref</span>
              <span className={`${styles.metaValue} mono`}>{validationEvidenceLabel(agent.validationEvidence)}</span>
            </div>
            <div className={styles.metaItem}>
              <span className={styles.metaLabel}>Outcome</span>
              <span className={styles.metaValue}>{agent.validationOutcome?.reason ?? "Validation summary available"}</span>
            </div>
          </div>
          {agent.validationEvidence?.terminalSummary ? (
            <p className="muted-note">{agent.validationEvidence.terminalSummary}</p>
          ) : null}
          {agent.validationEvidence?.traceUrl ? (
            <Button href={agent.validationEvidence.traceUrl} variant="ghost">
              Open validation evidence <ArrowUpRight size={14} />
            </Button>
          ) : null}
        </div>
      ) : null}

      <div className={styles.meta}>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Execution profile</span>
          <span className={`${styles.metaValue} mono`}>{defaultRuntimeSummary(agent)}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Last validated</span>
          <span className={styles.metaValue}>
            {new Date(fallbackValidationTimestamp(agent)).toLocaleString("en")}
          </span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Agent ID</span>
          <span className={`${styles.metaValue} mono`}>{agent.agentId}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Entrypoint</span>
          <span className={`${styles.metaValue} mono`}>{agent.entrypoint}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Tags</span>
          <span className={styles.metaValue}>{agent.tags.length ? agent.tags.join(", ") : "none"}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Cataloged at</span>
          <span className={styles.metaValue}>{agent.publishedAt ? new Date(agent.publishedAt).toLocaleString("en") : "-"}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Execution ref</span>
          <span className={`${styles.metaValue} mono`}>{executionReferenceSummary(agent.executionReference)}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Source fingerprint</span>
          <span className={`${styles.metaValue} mono`}>{shortSourceFingerprint(agent.sourceFingerprint)}</span>
        </div>
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Default model</span>
          <span className={styles.metaValue}>{agent.defaultModel || "-"}</span>
        </div>
      </div>

      <div className={styles.actions}>
        <Button variant="secondary" onClick={() => onValidate(agent)} disabled={isValidating || validationLifecycle.isActive}>
          Run validation
        </Button>
        {isRunnableSnapshot ? (
          <Button href={`/experiments?agent=${encodeURIComponent(agent.agentId)}`} variant="secondary">
            Create experiment <ArrowUpRight size={14} />
          </Button>
        ) : null}
      </div>
    </article>
  );
}

export default function AgentsWorkspace() {
  const publishedAgentsQuery = usePublishedAgentsQuery();
  const bootstrapMutation = useCreateClaudeCodeBridgeAssetMutation();
  const importMutation = useImportAgentMutation();
  const validationMutation = useStartValidationRunMutation();
  const [actionMessage, setActionMessage] = useState("");
  const [entryFocus, setEntryFocus] = useState<EntryFocus | null>(null);
  const [importForm, setImportForm] = useState<ImportAgentInput>({
    agentId: "",
    name: "",
    description: "",
    framework: "openai-agents-sdk",
    defaultModel: "",
    entrypoint: "",
    tags: []
  });
  const agents = useMemo<AgentRecord[]>(() => publishedAgentsQuery.data ?? [], [publishedAgentsQuery.data]);
  const focusedAgent = useMemo(
    () => agents.find((agent) => agent.agentId === entryFocus?.agentId) ?? null,
    [agents, entryFocus]
  );
  const existingClaudeBridge = useMemo(
    () => agents.find((agent) => agent.agentId === CLAUDE_CODE_BRIDGE_AGENT_ID) ?? null,
    [agents]
  );

  const groups = useMemo<AgentGroup[]>(
    () => [
      {
        title: "Ready",
        description: "Governed assets ready to generate RL evaluation data.",
        items: agents.filter((agent) => getAgentReadiness(agent) === "ready")
      },
      {
        title: "Validating",
        description: "Assets with an active validation run that still owns the current lifecycle state.",
        items: agents.filter((agent) => getAgentReadiness(agent) === "validating")
      },
      {
        title: "Needs validation",
        description: "Governed assets that still need one successful validation run before Atlas exposes them to experiments.",
        items: agents.filter((agent) => getAgentReadiness(agent) === "needs_validation")
      },
      {
        title: "Needs review",
        description: "Assets whose latest validation run ended in a blocking state and need evidence review before handoff.",
        items: agents.filter((agent) => getAgentReadiness(agent) === "needs_review")
      }
    ],
    [agents]
  );

  const errorMessage =
    (importMutation.error instanceof Error && importMutation.error.message) ||
    (bootstrapMutation.error instanceof Error && bootstrapMutation.error.message) ||
    (validationMutation.error instanceof Error && validationMutation.error.message) ||
    (publishedAgentsQuery.error instanceof Error && publishedAgentsQuery.error.message) ||
    "";

  const isLoading = publishedAgentsQuery.isLoading;
  const validationBacklog = groups[1].items.length + groups[2].items.length + groups[3].items.length;

  async function handleBootstrap() {
    if (existingClaudeBridge) {
      bootstrapMutation.reset();
      setEntryFocus({ agentId: existingClaudeBridge.agentId, name: existingClaudeBridge.name });
      setActionMessage(bridgeAlreadyExistsMessage(existingClaudeBridge));
      return;
    }

    try {
      const agent = await bootstrapMutation.mutateAsync();
      setEntryFocus({ agentId: agent.agentId, name: agent.name });
      setActionMessage(
        `Added ${agent.name} as the Claude Code bridge. Review its validation here before using the asset in experiments.`
      );
    } catch (error) {
      if (error instanceof Error && error.message.includes("conflicts with an existing governed asset")) {
        const refreshed = await publishedAgentsQuery.refetch();
        const bridge = refreshed.data?.find((agent) => agent.agentId === CLAUDE_CODE_BRIDGE_AGENT_ID) ?? null;
        if (bridge) {
          bootstrapMutation.reset();
          setEntryFocus({ agentId: bridge.agentId, name: bridge.name });
          setActionMessage(bridgeAlreadyExistsMessage(bridge));
        }
      }
    }
  }

  function updateImportField<K extends keyof ImportAgentInput>(key: K, value: ImportAgentInput[K]) {
    setImportForm((current) => ({ ...current, [key]: value }));
  }

  async function handleImport() {
    try {
      const agent = await importMutation.mutateAsync(importForm);
      setEntryFocus({ agentId: agent.agentId, name: agent.name });
      setActionMessage(
        `Imported ${agent.name}. Review its validation here before using the asset in experiments.`
      );
      setImportForm({
        agentId: "",
        name: "",
        description: "",
        framework: "openai-agents-sdk",
        defaultModel: "",
        entrypoint: "",
        tags: []
      });
    } catch {
      // Error state is surfaced through the shared notice area.
    }
  }

  async function handleValidation(agent: AgentRecord) {
    try {
      const run = await validationMutation.mutateAsync({
        agentId: agent.agentId,
        payload: validationPayload(agent)
      });
      setActionMessage(
        `Started validation run ${run.run_id} for ${agent.name}. Atlas will attach the latest validation evidence here so the asset handoff stays explicit.`
      );
    } catch {
      // Error state is surfaced through the shared notice area.
    }
  }

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <p className="page-eyebrow">Agent control plane</p>
          <h2 className="section-title">Agents</h2>
          <p className="kicker">
            Govern formal agent assets, review the latest validation evidence, and hand the right asset into
            experiment orchestration.
          </p>
          <div className="page-tag-list">
            <span className="page-tag">
              Visible <strong>{agents.length}</strong>
            </span>
            <span className="page-tag">
              Ready for experiments <strong>{groups[0].items.length}</strong>
            </span>
            <span className="page-tag">
              Needs validation <strong>{groups[2].items.length}</strong>
            </span>
            <span className="page-tag">
              Needs review <strong>{groups[3].items.length}</strong>
            </span>
          </div>
        </div>
        <div className="page-info-grid">
          <div className="page-info-item">
            <span className="page-info-label">Catalog status</span>
            <span className="page-info-value">
              {groups[0].items.length} ready / {groups[1].items.length} validating / {groups[2].items.length} needs validation / {groups[3].items.length} review
            </span>
            <p className="page-info-detail">
              Start with governed assets, use the latest validation summary to decide what to hand off next, and
              keep intake narrow rather than teaching repo-local draft management.
            </p>
          </div>
        </div>
      </header>

      <div className="summary-strip">
        <MetricCard label="Ready" value={groups[0].items.length} />
        <MetricCard label="Validating" value={groups[1].items.length} />
        <MetricCard label="Needs validation" value={groups[2].items.length} />
        <MetricCard label="Needs review" value={groups[3].items.length} />
      </div>

      <Panel tone="strong" className={styles.entryPanel}>
        <div className="surface-header">
          <div>
            <p className="surface-kicker">Governed entry</p>
            <h3 className="panel-title">Add an asset, review validation, then use ready assets</h3>
            <p className="muted-note">
              Keep the current operator path in one place: import a runnable asset or add the Claude Code bridge,
              review the latest validation status on this surface, then hand ready assets into experiments.
            </p>
          </div>
        </div>
        <div className={styles.entryGrid}>
          <div className="page-stack">
            <div className={styles.formGrid}>
              <Field label="Agent ID" htmlFor="agent-import-id">
                <input
                  id="agent-import-id"
                  value={importForm.agentId}
                  onChange={(event) => updateImportField("agentId", event.target.value)}
                  placeholder="customer-service"
                />
              </Field>
              <Field label="Name" htmlFor="agent-import-name">
                <input
                  id="agent-import-name"
                  value={importForm.name}
                  onChange={(event) => updateImportField("name", event.target.value)}
                  placeholder="Customer Service"
                />
              </Field>
              <Field label="Asset family" htmlFor="agent-import-framework">
                <select
                  id="agent-import-framework"
                  value={importForm.framework}
                  onChange={(event) => updateImportField("framework", event.target.value)}
                >
                  <option value="openai-agents-sdk">openai-agents-sdk</option>
                  <option value="langchain">langchain</option>
                  <option value="claude-code-cli">claude-code-cli</option>
                </select>
              </Field>
              <Field label="Default model" htmlFor="agent-import-model">
                <input
                  id="agent-import-model"
                  value={importForm.defaultModel}
                  onChange={(event) => updateImportField("defaultModel", event.target.value)}
                  placeholder="Enter the asset default model"
                />
              </Field>
              <Field label="Entrypoint" htmlFor="agent-import-entrypoint" wide>
                <input
                  id="agent-import-entrypoint"
                  value={importForm.entrypoint}
                  onChange={(event) => updateImportField("entrypoint", event.target.value)}
                  placeholder="agents.customer_service:build_agent"
                />
              </Field>
              <Field label="Description" htmlFor="agent-import-description" wide>
                <textarea
                  id="agent-import-description"
                  rows={3}
                  value={importForm.description}
                  onChange={(event) => updateImportField("description", event.target.value)}
                  placeholder="Governed support agent imported from a runnable entrypoint."
                />
              </Field>
            </div>
            <div className={styles.actions}>
              <Button
                onClick={() => void handleImport()}
                disabled={
                  importMutation.isPending ||
                  !importForm.agentId.trim() ||
                  !importForm.name.trim() ||
                  !importForm.description.trim() ||
                  !importForm.defaultModel.trim() ||
                  !importForm.entrypoint.trim()
                }
              >
                {importMutation.isPending ? "Importing asset..." : "Import asset"}
              </Button>
              <Button onClick={() => void handleBootstrap()} variant="ghost" disabled={bootstrapMutation.isPending}>
                {bootstrapMutation.isPending
                  ? "Adding bridge..."
                  : existingClaudeBridge
                    ? "Review Claude Code bridge"
                    : "Add Claude Code bridge"}
              </Button>
            </div>
          </div>

          <div className={styles.entryRail}>
            <div className={styles.entryStep}>
              <div className={styles.entryStepHeader}>
                <span className={styles.entryStepTitle}>1. Add asset</span>
                <StatusPill tone={entryFocus ? "success" : "warn"}>{entryFocus ? "Focused" : "Idle"}</StatusPill>
              </div>
              <p className="muted-note">
                {entryFocus
                  ? `${entryFocus.name} is the current import focus on this surface.`
                  : "Use explicit import as the primary path. The Claude Code bridge stays available only as a beginner/reference path."}
              </p>
            </div>

            <div className={styles.entryStep}>
              <div className={styles.entryStepHeader}>
                <span className={styles.entryStepTitle}>2. Validation status</span>
                <StatusPill tone={validationBacklog ? "warn" : "success"}>
                  {validationBacklog ? `${validationBacklog} pending` : "Clear"}
                </StatusPill>
              </div>
              <p className="muted-note">
                {focusedAgent
                  ? nextStepLabel(focusedAgent)
                  : "Run validation on the new intake before Atlas treats it as the next experiment-ready asset."}
              </p>
            </div>

            <div className={styles.entryStep}>
              <div className={styles.entryStepHeader}>
                <span className={styles.entryStepTitle}>3. Ready for experiments</span>
                <StatusPill tone={groups[0].items.length ? "success" : "warn"}>
                  {groups[0].items.length ? `${groups[0].items.length} ready` : "No ready assets"}
                </StatusPill>
              </div>
              <p className="muted-note">{entryFocusSummary(focusedAgent)}</p>
            </div>
          </div>
        </div>
      </Panel>

      {actionMessage ? <Notice>{actionMessage}</Notice> : null}
      {errorMessage ? <Notice>{errorMessage}</Notice> : null}
      {isLoading ? <Notice>Loading agents...</Notice> : null}
      {!isLoading && !agents.length ? (
        <Panel tone="plain">
          <div className="surface-header">
            <div>
              <p className="surface-kicker">No agents yet</p>
              <h3 className="panel-title">No ready assets yet</h3>
              <p className="muted-note">
                Use the governed entry panel above to import the first asset, run validation, and move ready assets
                into the catalog below.
              </p>
            </div>
          </div>
          <div className="page-stack">
            <Notice>Import starts the catalog entry here, and validation determines when an asset is ready to use.</Notice>
            <Notice>The catalog below only shows current governed assets after intake and validation.</Notice>
          </div>
        </Panel>
      ) : null}

      {agents.length
        ? groups.map((group) => (
        <Panel key={group.title} tone="plain" className={styles.group}>
          <div className="surface-header">
            <div>
              <p className="surface-kicker">{group.title}</p>
              <h3 className="panel-title">{group.description}</h3>
              <p className="muted-note">{group.items.length} agents in this section.</p>
            </div>
          </div>

          {group.items.length ? (
            <div className={styles.cards}>
              {group.items.map((agent) => (
                <AgentCard
                  key={`${group.title}-${agent.agentId}`}
                  agent={agent}
                  onValidate={(currentAgent) => void handleValidation(currentAgent)}
                  isValidating={validationMutation.isPending}
                />
              ))}
            </div>
          ) : (
            <Notice>No agents in this section.</Notice>
          )}
        </Panel>
          ))
        : null}
    </section>
  );
}
