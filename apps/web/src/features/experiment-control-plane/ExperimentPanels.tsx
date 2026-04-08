"use client";

import { ArrowUpRight, Radar, RotateCcw } from "lucide-react";
import { compareTone, COMPARE_OUTCOME_OPTIONS } from "@/src/entities/experiment/compare";
import type { ExperimentRunRecord } from "@/src/entities/experiment/model";
import type { CompareOutcome, CurationStatus, SampleJudgement, ScoringMode } from "@/src/shared/api/contract";
import type { ExecutionProfile } from "@/src/shared/api/contract";
import { executionProfileSummary } from "@/src/shared/runtime/identity";
import { Button } from "@/src/shared/ui/Button";
import { Field } from "@/src/shared/ui/Field";
import { MetricCard } from "@/src/shared/ui/MetricCard";
import { Notice } from "@/src/shared/ui/Notice";
import { Panel } from "@/src/shared/ui/Panel";
import { StatusPill } from "@/src/shared/ui/StatusPill";
import { TableShell } from "@/src/shared/ui/TableShell";
import {
  canCurateRun,
  curationDisabledReason,
  experimentLabel,
  experimentNextStep,
  experimentTone,
  exportsHandoffHref,
  judgementTone
} from "./model";

export function ExperimentCreatePanel(props: {
  actionMessage: string;
  agentId: string;
  agents: Array<{ agentId: string; name: string; executionProfile: ExecutionProfile }>;
  approvalPolicyId: string;
  createPending: boolean;
  datasetVersionId: string;
  datasetVersions: Array<{ datasetVersionId: string; datasetLabel: string }>;
  isAgentsLoading: boolean;
  model: string;
  onAgentIdChange: (value: string) => void;
  onApprovalPolicyIdChange: (value: string) => void;
  onCreateExperiment: () => void;
  onDatasetVersionIdChange: (value: string) => void;
  onModelChange: (value: string) => void;
  onScoringModeChange: (value: ScoringMode) => void;
  onSystemPromptChange: (value: string) => void;
  onTagsTextChange: (value: string) => void;
  policies: Array<{ approvalPolicyId: string; name: string }>;
  scoringMode: ScoringMode;
  selectedAgent: { executionProfile: ExecutionProfile } | null;
  styles: Record<string, string>;
  systemPrompt: string;
  tagsText: string;
}) {
  return (
    <Panel>
      <div className="surface-header">
        <div>
          <p className="surface-kicker">Create experiment</p>
          <h3 className="panel-title">Bind governed asset, dataset version, and policy</h3>
          <p className="muted-note">
            Start with one ready governed asset, pair it with a dataset version, then let Atlas create the
            evidence loop you will compare and curate.
          </p>
        </div>
      </div>
      {props.isAgentsLoading ? <Notice>Loading agents...</Notice> : null}
      {!props.isAgentsLoading && !props.agents.length ? (
        <Notice>No governed assets are ready yet. Add and validate one on Agents before creating an experiment.</Notice>
      ) : null}
      <div className={props.styles?.filtersGrid ?? ""}>
        <Field label="Governed asset" htmlFor="experiment-agent">
          <select id="experiment-agent" value={props.agentId} onChange={(event) => props.onAgentIdChange(event.target.value)}>
            {props.agents.map((agent) => (
              <option key={agent.agentId} value={agent.agentId}>
                {agent.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Dataset version" htmlFor="experiment-dataset">
          <select
            id="experiment-dataset"
            value={props.datasetVersionId}
            onChange={(event) => props.onDatasetVersionIdChange(event.target.value)}
          >
            {props.datasetVersions.map((version) => (
              <option key={version.datasetVersionId} value={version.datasetVersionId}>
                {version.datasetLabel}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Model" htmlFor="experiment-model">
          <input id="experiment-model" value={props.model} onChange={(event) => props.onModelChange(event.target.value)} />
        </Field>
        <Field label="Scoring" htmlFor="experiment-scoring">
          <select
            id="experiment-scoring"
            value={props.scoringMode}
            onChange={(event) => props.onScoringModeChange(event.target.value as ScoringMode)}
          >
            <option value="exact_match">exact match</option>
            <option value="contains">contains</option>
          </select>
        </Field>
        <Field label="Approval policy" htmlFor="experiment-policy">
          <select
            id="experiment-policy"
            value={props.approvalPolicyId}
            onChange={(event) => props.onApprovalPolicyIdChange(event.target.value)}
          >
            {props.policies.map((policy) => (
              <option key={policy.approvalPolicyId} value={policy.approvalPolicyId}>
                {policy.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Tags" htmlFor="experiment-tags">
          <input
            id="experiment-tags"
            placeholder="candidate, nightly"
            value={props.tagsText}
            onChange={(event) => props.onTagsTextChange(event.target.value)}
          />
        </Field>
        <Field label="System prompt" htmlFor="experiment-prompt">
          <input
            id="experiment-prompt"
            placeholder="Enforce stable tool usage and concise final answers."
            value={props.systemPrompt}
            onChange={(event) => props.onSystemPromptChange(event.target.value)}
          />
        </Field>
      </div>
      <p className="muted-note">
        Only ready, governed assets appear in this selector. Execution profile is inherited from the selected
        asset: {executionProfileSummary(props.selectedAgent?.executionProfile)}. Atlas keeps the same run, evidence, and
        export chain regardless of the underlying execution path.
      </p>
      <div className={props.styles?.actions ?? ""}>
        <Button onClick={props.onCreateExperiment} disabled={props.createPending}>
          <Radar size={14} /> {props.createPending ? "Creating..." : "Create and start"}
        </Button>
        <p className={props.styles?.actionNote ?? ""}>
          {props.actionMessage || "Atlas creates the record and immediately starts the run on the current neutral execution path."}
        </p>
      </div>
    </Panel>
  );
}

export function ExperimentSelectionPanels(props: {
  cancelPending: boolean;
  experiments: Array<any>;
  experimentsPending: boolean;
  filteredRunsCount: number;
  onCancel: (experimentId: string) => void;
  onSelectExperiment: (value: string) => void;
  policiesCount: number;
  selectedExperiment: any;
  styles: Record<string, string>;
}) {
  return (
    <div className={props.styles.layout}>
      <Panel>
        <div className={props.styles.sectionHeader}>
          <div>
            <p className="surface-kicker">Experiments</p>
            <h3 className="panel-title">Select the active experiment</h3>
          </div>
        </div>
        {props.experimentsPending ? <Notice>Loading experiments...</Notice> : null}
        <div className={props.styles.jobList}>
          {props.experiments.map((record) => (
            <button
              key={record.experimentId}
              className={props.styles.jobCard}
              data-active={props.selectedExperiment?.experimentId === record.experimentId}
              onClick={() => props.onSelectExperiment(record.experimentId)}
            >
              <div className={props.styles.jobCardHeader}>
                <strong>{experimentLabel(record)}</strong>
                <StatusPill tone={experimentTone(record.status)}>{record.status}</StatusPill>
              </div>
              <p className="muted-note">{record.datasetName}</p>
            </button>
          ))}
        </div>
      </Panel>

      <Panel>
        <div className={props.styles.sectionHeader}>
          <div>
            <p className="surface-kicker">Summary</p>
            <h3 className="panel-title">Selected experiment evidence</h3>
            <p className="muted-note">{experimentNextStep(props.selectedExperiment)}</p>
          </div>
          {props.selectedExperiment ? (
            <div className="toolbar">
              <Button
                variant="secondary"
                onClick={() => props.onCancel(props.selectedExperiment.experimentId)}
                disabled={props.cancelPending || props.selectedExperiment.status === "cancelled"}
              >
                <RotateCcw size={14} /> Cancel
              </Button>
            </div>
          ) : null}
        </div>
        {props.selectedExperiment ? (
          <>
            <div className={props.styles.metricGrid}>
              <MetricCard label="Pass rate" value={`${Math.round(props.selectedExperiment.passRate * 100)}%`} />
              <MetricCard label="Completed" value={props.selectedExperiment.completedCount} />
              <MetricCard label="Runtime errors" value={props.selectedExperiment.runtimeErrorCount} />
            </div>
            {props.selectedExperiment.tracing?.projectUrl ? (
              <Button href={props.selectedExperiment.tracing.projectUrl} variant="ghost">
                Open Phoenix deeplink <ArrowUpRight size={14} />
              </Button>
            ) : null}
          </>
        ) : (
          <Notice>No experiments yet.</Notice>
        )}
      </Panel>
    </div>
  );
}

export function ExperimentComparePanel(props: {
  baselineExperimentId: string;
  baselineOptions: Array<any>;
  compareDistribution?: Record<string, number>;
  onBaselineExperimentIdChange: (value: string) => void;
  styles: Record<string, string>;
}) {
  return (
    <Panel>
      <div className={props.styles.sectionHeader}>
        <div>
          <p className="surface-kicker">Compare</p>
          <h3 className="panel-title">Baseline vs candidate</h3>
        </div>
      </div>
      <div className={props.styles.filtersGrid}>
        <Field label="Baseline experiment" htmlFor="experiment-baseline">
          <select
            id="experiment-baseline"
            value={props.baselineExperimentId}
            onChange={(event) => props.onBaselineExperimentIdChange(event.target.value)}
          >
            <option value="">No baseline</option>
            {props.baselineOptions.map((record) => (
              <option key={record.experimentId} value={record.experimentId}>
                {experimentLabel(record)}
              </option>
            ))}
          </select>
        </Field>
      </div>
      {props.compareDistribution ? (
        <div className={props.styles.metricGrid}>
          {Object.entries(props.compareDistribution).map(([label, count]) => (
            <MetricCard key={label} label={label} value={count} />
          ))}
        </div>
      ) : null}
    </Panel>
  );
}

export function ExperimentRunsPanel(props: {
  baselineExperimentId: string;
  compareLookup: Map<string, CompareOutcome>;
  compareOutcomeFilter: CompareOutcome | "";
  curationFilter: CurationStatus | "";
  errorCodeFilter: string;
  errorCodeOptions: string[];
  filteredRuns: ExperimentRunRecord[];
  judgementFilter: SampleJudgement | "";
  onCompareOutcomeFilterChange: (value: CompareOutcome | "") => void;
  onCurationFilterChange: (value: CurationStatus | "") => void;
  onErrorCodeFilterChange: (value: string) => void;
  onJudgementFilterChange: (value: SampleJudgement | "") => void;
  onPatchRun: (run: ExperimentRunRecord, payload: { curationStatus?: CurationStatus }) => void;
  onSliceFilterChange: (value: string) => void;
  onTagFilterChange: (value: string) => void;
  patchPending: boolean;
  runsPending: boolean;
  selectedExperiment: any;
  sliceFilter: string;
  sliceOptions: string[];
  styles: Record<string, string>;
  tagFilter: string;
  tagOptions: string[];
}) {
  return (
    <Panel>
      <div className={props.styles.sectionHeader}>
        <div>
          <p className="surface-kicker">Runs</p>
          <h3 className="panel-title">Curate sample outcomes before export handoff</h3>
          <p className="muted-note">
            Use compare and curation to shape the evidence-backed rows, then continue into Exports for the actual
            offline handoff.
          </p>
        </div>
        <div className="toolbar">
          {props.selectedExperiment ? (
            <Button href={exportsHandoffHref(props.selectedExperiment, props.baselineExperimentId)} variant="secondary">
              Continue to Exports <ArrowUpRight size={14} />
            </Button>
          ) : (
            <Button variant="secondary" disabled>
              Continue to Exports <ArrowUpRight size={14} />
            </Button>
          )}
        </div>
      </div>
      <div className={props.styles.filtersGrid}>
        <Field label="Judgement" htmlFor="experiment-filter-judgement">
          <select
            id="experiment-filter-judgement"
            value={props.judgementFilter}
            onChange={(event) => props.onJudgementFilterChange(event.target.value as SampleJudgement | "")}
          >
            <option value="">All judgements</option>
            <option value="passed">passed</option>
            <option value="failed">failed</option>
            <option value="unscored">unscored</option>
            <option value="runtime_error">runtime_error</option>
          </select>
        </Field>
        <Field label="Error code" htmlFor="experiment-filter-error">
          <select id="experiment-filter-error" value={props.errorCodeFilter} onChange={(event) => props.onErrorCodeFilterChange(event.target.value)}>
            <option value="">All errors</option>
            {props.errorCodeOptions.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Slice" htmlFor="experiment-filter-slice">
          <select id="experiment-filter-slice" value={props.sliceFilter} onChange={(event) => props.onSliceFilterChange(event.target.value)}>
            <option value="">All slices</option>
            {props.sliceOptions.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Tag" htmlFor="experiment-filter-tag">
          <select id="experiment-filter-tag" value={props.tagFilter} onChange={(event) => props.onTagFilterChange(event.target.value)}>
            <option value="">All tags</option>
            {props.tagOptions.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Curation" htmlFor="experiment-filter-curation">
          <select
            id="experiment-filter-curation"
            value={props.curationFilter}
            onChange={(event) => props.onCurationFilterChange(event.target.value as CurationStatus | "")}
          >
            <option value="">All curation states</option>
            <option value="include">include</option>
            <option value="review">review</option>
            <option value="exclude">exclude</option>
          </select>
        </Field>
        <Field label="Compare" htmlFor="experiment-filter-compare">
          <select
            id="experiment-filter-compare"
            value={props.compareOutcomeFilter}
            onChange={(event) => props.onCompareOutcomeFilterChange(event.target.value as CompareOutcome | "")}
          >
            <option value="">All compare outcomes</option>
            {COMPARE_OUTCOME_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </Field>
      </div>
      {props.runsPending ? <Notice>Loading experiment runs...</Notice> : null}
      <TableShell>
        <table>
          <thead>
            <tr>
              <th>Sample</th>
              <th>Status</th>
              <th>Judgement</th>
              <th>Compare</th>
              <th>Phoenix</th>
              <th>Curation</th>
            </tr>
          </thead>
          <tbody>
            {props.filteredRuns.map((run) => (
              <tr key={run.runId}>
                <td>
                  <strong>{run.datasetSampleId}</strong>
                  <p className="muted-note">{run.input}</p>
                </td>
                <td>
                  <StatusPill tone={experimentTone(run.runStatus)}>{run.runStatus}</StatusPill>
                </td>
                <td>
                  <StatusPill tone={judgementTone(run.judgement)}>{run.judgement ?? "pending"}</StatusPill>
                </td>
                <td>
                  {props.compareLookup.get(run.datasetSampleId) ? (
                    <StatusPill tone={compareTone(props.compareLookup.get(run.datasetSampleId) as CompareOutcome)}>
                      {props.compareLookup.get(run.datasetSampleId) as CompareOutcome}
                    </StatusPill>
                  ) : (
                    <span className="muted-note">n/a</span>
                  )}
                </td>
                <td>
                  {run.traceUrl ? (
                    <Button href={run.traceUrl} variant="ghost">
                      Open Phoenix <ArrowUpRight size={14} />
                    </Button>
                  ) : (
                    <span className="muted-note">No deeplink</span>
                  )}
                </td>
                <td>
                  <div className={props.styles.curationActions}>
                    <Button
                      variant={run.curationStatus === "include" ? "primary" : "ghost"}
                      disabled={!canCurateRun(run) || props.patchPending}
                      title={curationDisabledReason(run, props.patchPending)}
                      onClick={() => props.onPatchRun(run, { curationStatus: "include" })}
                    >
                      Include
                    </Button>
                    <Button
                      variant={run.curationStatus === "review" ? "primary" : "ghost"}
                      disabled={!canCurateRun(run) || props.patchPending}
                      title={curationDisabledReason(run, props.patchPending)}
                      onClick={() => props.onPatchRun(run, { curationStatus: "review" })}
                    >
                      Review
                    </Button>
                    <Button
                      variant={run.curationStatus === "exclude" ? "primary" : "ghost"}
                      disabled={!canCurateRun(run) || props.patchPending}
                      title={curationDisabledReason(run, props.patchPending)}
                      onClick={() => props.onPatchRun(run, { curationStatus: "exclude" })}
                    >
                      Exclude
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
            {!props.runsPending && !props.filteredRuns.length ? (
              <tr>
                <td colSpan={6}>
                  <Notice>No runs match the current filters.</Notice>
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </TableShell>
    </Panel>
  );
}
