"use client";

import type { AgentRecord, ImportAgentInput } from "@/src/entities/agent/model";
import { Button } from "@/src/shared/ui/Button";
import { Field } from "@/src/shared/ui/Field";
import { Panel } from "@/src/shared/ui/Panel";
import { StatusPill } from "@/src/shared/ui/StatusPill";
import { entryFocusSummary, nextStepLabel, type AgentGroup, type EntryFocus } from "./model";

type Props = {
  bootstrapPending: boolean;
  entryFocus: EntryFocus | null;
  existingClaudeBridge: AgentRecord | null;
  focusedAgent: AgentRecord | null;
  groups: AgentGroup[];
  importForm: ImportAgentInput;
  importPending: boolean;
  onBootstrap: () => void;
  onImport: () => void;
  onUpdateImportField: <K extends keyof ImportAgentInput>(key: K, value: ImportAgentInput[K]) => void;
  styles: Record<string, string>;
  starterDatasetPending: boolean;
  validationBacklog: number;
};

export function AgentEntryPanel({
  bootstrapPending,
  entryFocus,
  existingClaudeBridge,
  focusedAgent,
  groups,
  importForm,
  importPending,
  onBootstrap,
  onImport,
  onUpdateImportField,
  starterDatasetPending,
  styles,
  validationBacklog
}: Props) {
  return (
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
                onChange={(event) => onUpdateImportField("agentId", event.target.value)}
                placeholder="customer-service"
              />
            </Field>
            <Field label="Name" htmlFor="agent-import-name">
              <input
                id="agent-import-name"
                value={importForm.name}
                onChange={(event) => onUpdateImportField("name", event.target.value)}
                placeholder="Customer Service"
              />
            </Field>
            <Field label="Asset family" htmlFor="agent-import-framework">
              <select
                id="agent-import-framework"
                value={importForm.framework}
                onChange={(event) => onUpdateImportField("framework", event.target.value)}
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
                onChange={(event) => onUpdateImportField("defaultModel", event.target.value)}
                placeholder="Enter the asset default model"
              />
            </Field>
            <Field label="Entrypoint" htmlFor="agent-import-entrypoint" wide>
              <input
                id="agent-import-entrypoint"
                value={importForm.entrypoint}
                onChange={(event) => onUpdateImportField("entrypoint", event.target.value)}
                placeholder="agents.customer_service:build_agent"
              />
            </Field>
            <Field label="Description" htmlFor="agent-import-description" wide>
              <textarea
                id="agent-import-description"
                rows={3}
                value={importForm.description}
                onChange={(event) => onUpdateImportField("description", event.target.value)}
                placeholder="Governed support agent imported from a runnable entrypoint."
              />
            </Field>
          </div>
          <div className={styles.actions}>
            <Button
              onClick={onImport}
              disabled={
                importPending ||
                !importForm.agentId.trim() ||
                !importForm.name.trim() ||
                !importForm.description.trim() ||
                !importForm.defaultModel.trim() ||
                !importForm.entrypoint.trim()
              }
            >
              {importPending ? "Importing asset..." : "Import asset"}
            </Button>
            <Button onClick={onBootstrap} variant="ghost" disabled={bootstrapPending || starterDatasetPending}>
              {bootstrapPending || starterDatasetPending
                ? "Preparing starter..."
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
  );
}
