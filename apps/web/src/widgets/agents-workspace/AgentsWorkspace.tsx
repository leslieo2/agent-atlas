"use client";

import { Notice } from "@/src/shared/ui/Notice";
import { MetricCard } from "@/src/shared/ui/MetricCard";
import { AgentCatalogSections } from "@/src/features/agent-control-plane/AgentCatalogSections";
import { AgentEntryPanel } from "@/src/features/agent-control-plane/AgentEntryPanel";
import { useAgentControlPlane } from "@/src/features/agent-control-plane/useAgentControlPlane";
import styles from "./AgentsWorkspace.module.css";

export default function AgentsWorkspace() {
  const controlPlane = useAgentControlPlane();

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
              Visible <strong>{controlPlane.agents.length}</strong>
            </span>
            <span className="page-tag">
              Ready for experiments <strong>{controlPlane.groups[0].items.length}</strong>
            </span>
            <span className="page-tag">
              Needs validation <strong>{controlPlane.groups[2].items.length}</strong>
            </span>
            <span className="page-tag">
              Needs review <strong>{controlPlane.groups[3].items.length}</strong>
            </span>
          </div>
        </div>
        <div className="page-info-grid">
          <div className="page-info-item">
            <span className="page-info-label">Catalog status</span>
            <span className="page-info-value">
              {controlPlane.groups[0].items.length} ready / {controlPlane.groups[1].items.length} validating /{" "}
              {controlPlane.groups[2].items.length} needs validation / {controlPlane.groups[3].items.length} review
            </span>
            <p className="page-info-detail">
              Start with governed assets, use the latest validation summary to decide what to hand off next, and
              keep intake narrow rather than teaching repo-local draft management.
            </p>
          </div>
        </div>
      </header>

      <div className="summary-strip">
        <MetricCard label="Ready" value={controlPlane.groups[0].items.length} />
        <MetricCard label="Validating" value={controlPlane.groups[1].items.length} />
        <MetricCard label="Needs validation" value={controlPlane.groups[2].items.length} />
        <MetricCard label="Needs review" value={controlPlane.groups[3].items.length} />
      </div>

      <AgentEntryPanel
        bootstrapPending={controlPlane.bootstrapMutation.isPending}
        entryFocus={controlPlane.entryFocus}
        existingClaudeBridge={controlPlane.existingClaudeBridge}
        focusedAgent={controlPlane.focusedAgent}
        groups={controlPlane.groups}
        importForm={controlPlane.importForm}
        importPending={controlPlane.importMutation.isPending}
        onBootstrap={() => void controlPlane.handleBootstrap()}
        onImport={() => void controlPlane.handleImport()}
        onUpdateImportField={controlPlane.updateImportField}
        starterDatasetPending={controlPlane.starterDatasetMutation.isPending}
        styles={styles}
        validationBacklog={controlPlane.validationBacklog}
      />

      {controlPlane.actionMessage ? <Notice>{controlPlane.actionMessage}</Notice> : null}
      {controlPlane.errorMessage ? <Notice>{controlPlane.errorMessage}</Notice> : null}

      <AgentCatalogSections
        agents={controlPlane.agents}
        groups={controlPlane.groups}
        isLoading={controlPlane.isLoading}
        onValidate={(agent) => void controlPlane.handleValidation(agent)}
        styles={styles}
        validationPending={controlPlane.validationMutation.isPending}
      />
    </section>
  );
}
