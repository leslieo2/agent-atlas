# Model Boundary Reset

This frontend now treats the product model as:

`AgentAsset -> ExecutionProfile -> Run -> Evidence -> Export`

## What Stays First-Class

- `AgentAsset`: the governed asset operators intake, validate, and hand into experiments
- `ExecutionProfile`: the thin execution contract attached to a governed asset
- `Run`: the active or historical execution record created from a governed asset
- `Evidence`: validation summaries, traces, artifacts, and outcome projections attached to a run
- `Export`: offline handoff files produced from curated evidence-backed rows

## What Stays Supporting

- runner adapters
- providers
- credential bindings
- carrier or image details
- tracing vendors

These details can appear inside execution-profile summaries, evidence drill-downs, or provenance fields, but they should not become primary navigation, top-level product nouns, or the default explanatory frame for the UI.

## Frontend Inventory Cut

This inventory is the actionable cut for follow-up task splitting. Each residue point includes the required treatment:

- `keep`: preserve as a first-class product object or IA choice
- `demote`: keep the data, but move it behind execution-profile, provenance, or evidence summaries
- `migrate`: rename or remap the current shape so the product reads through the canonical model
- `delete`: remove the residue from default product framing or automation

## Residue Inventory

### Schema

- `apps/web/src/shared/api/contract.ts`
  Residue: wire fields such as `default_runtime_profile`, `executor_config`, `executor_backend`, `runner_image`, `runner_backend`, and `provider` still speak in execution-plane terms.
  Treatment: `demote` for current frontend consumption, then `migrate` behind product-facing types as backend contracts evolve.
  Guidance: these fields can remain on the wire, but they should not define top-level frontend nouns. Frontend entity models should expose `executionProfile`, `run`, and `evidence` records instead.

- `apps/web/src/entities/agent/model.ts`
  Residue: the old frontend-facing `defaultRuntimeProfile` name exposed wire language inside the product model.
  Treatment: `migrate`.
  Guidance: this slice already remaps the frontend field to `executionProfile`; future frontend additions should use canonical product names even when the API payload still uses legacy wire names.

### API

- `apps/web/src/entities/agent/mapper.ts`
  Residue: the backend still emits `default_runtime_profile`.
  Treatment: `migrate`.
  Guidance: keep the mapper boundary as the canonical translation seam. Product code after mapping should not read or reintroduce wire-native runner/provider naming.

- `apps/web/src/entities/experiment/model.ts`
  Residue: experiment records still expose `executorBackend` as a direct field because the backend response is execution-oriented.
  Treatment: `demote`.
  Guidance: keep it available for provenance or diagnostics, but do not make it a headline experiment concept. If this field gains UI value later, surface it as execution provenance, not as a new product object.

- `apps/web/src/shared/api/provenance.ts`
  Residue: provenance still carries `runnerBackend`, `executorBackend`, and `traceBackend`.
  Treatment: `demote`.
  Guidance: these are acceptable only as secondary provenance fields under runs or evidence. They should never drive primary navigation, CTA gating, or default page copy.

### UI Copy

- `apps/web/src/widgets/workbench-shell/WorkbenchShell.tsx`
  Residue: shell framing previously described Atlas through runner adapters and runner internals.
  Treatment: `migrate`.
  Guidance: shell copy should teach `AgentAsset -> ExecutionProfile -> Run -> Evidence -> Export` and reserve execution systems for boundary notes only.

- `apps/web/src/widgets/agents-workspace/AgentsWorkspace.tsx`
  Residue: agents can easily drift back into runtime-first language because they expose validation, provenance, and execution-profile metadata in one place.
  Treatment: `keep` the surface, `demote` execution detail.
  Guidance: keep the product center on governed assets, validation state, and next handoff. Execution-profile detail may appear only as a thin summary, with deeper execution facts treated as metadata.

- `apps/web/src/widgets/experiments-workspace/ExperimentsWorkspace.tsx`
  Residue: experiment creation and summary copy previously centered the neutral runner seam and adapter detail.
  Treatment: `migrate`.
  Guidance: experiments should talk about converting governed assets into runs, evidence, compare, curation, and export. Execution details belong inside the inherited execution profile or evidence drill-downs.

- Phoenix wording across shell, agents, and experiments
  Residue: trace links can accidentally become a second product center.
  Treatment: `keep` as deeplink-only, `delete` any wording that presents Phoenix as a peer workspace.
  Guidance: Phoenix remains evidence drill-down, never a first-class Atlas navigation object.

### IA

- Primary navigation in `apps/web/src/widgets/workbench-shell/WorkbenchShell.tsx`
  Residue: none in the current four-surface layout.
  Treatment: `keep`.
  Guidance: `Agents / Datasets / Experiments / Exports` remains the stable product IA. Do not add top-level `Runners`, `Providers`, `Credentials`, or `Tracing` pages from the current residue.

- Validation as a separate product center
  Residue: older task framing and automation often treated validation as if it were its own workspace.
  Treatment: `demote`.
  Guidance: validation is a lifecycle and evidence state on governed assets and runs, not a separate first-class navigation object. Follow-up lifecycle work like `#71` should align projections within the existing surfaces instead of growing new IA.

- Execution-profile detail depth
  Residue: raw backend, adapter, image, and credential details can sprawl into default cards and selectors.
  Treatment: `demote`.
  Guidance: default surfaces get one thin execution-profile summary. Deeper execution facts belong in metadata rows, provenance panels, or evidence drill-downs, not in page titles, hero copy, or selectors.

### Automation Mental Model

- `apps/web/e2e/live-smoke.spec.ts`
  Residue: the filename and surrounding task history still encode starter/smoke language even though the assertions now describe the governed asset path in product terms.
  Treatment: `migrate`.
  Guidance: future automation should describe the main path in product terms (`Agents -> Validation -> Datasets -> Experiments -> Exports`) and stop teaching a starter- or smoke-first mental model. This is follow-up automation work, not part of the current doc-only framing gate.

- `apps/web/e2e/evals.spec.ts`
  Residue: automation assertions can accidentally freeze runner-first copy or old headings.
  Treatment: `migrate`.
  Guidance: tests should assert the canonical product-language boundary, not adapter-heavy wording. This slice already updates the current assertions accordingly.

- Top-level task language and acceptance criteria
  Residue: previous task names and checks often grouped work around starter residue, runner residue, or provider/credential-first semantics.
  Treatment: `delete` as the default framing, then `migrate` future tasks to the canonical model.
  Guidance: follow-up work should now split by product-model concern:
  `ExecutionProfile` translation and thin-summary rules, lifecycle projection coherence, evidence/provenance drill-down boundaries, and automation/main-path wording.

## Next Task Split Guidance

- Schema/API follow-up: keep wire compatibility, but continue wrapping execution-plane fields in product-facing frontend models instead of leaking generated contract names into widgets.
- UI/IA follow-up: guard thin execution-profile summaries and keep Phoenix, provider, credential, and backend details out of headline copy or top-level navigation.
- Automation follow-up: rename and reframe remaining starter/smoke residue so tests teach the canonical user path rather than legacy infrastructure history.
- UI copy follow-up: keep starter/reference bridges framed as thin beginner paths under governed asset intake instead of as standalone product mechanisms.
