# Roadmap

## Product Direction

Agent Atlas is narrowing into an RL data control plane.

The target product loop is:

```text
Published Agent -> Dataset -> Eval Job -> Curation -> Export
```

Atlas should get stronger at producing governed RL-ready data and weaker at features that Phoenix
already owns well.

## Boundary

### Atlas keeps

- repository-local agent discovery and publish gate
- published snapshot, artifact, image, and runner provenance
- dataset and sample identity
- eval job orchestration
- sample-level outcomes and compare views that support curation
- RL-ready offline export

### Atlas removes or downscopes

- standalone tracing workflows
- raw trace browsing UX
- playground and manual run as product centers
- prompt management
- evaluator authoring
- experiment analysis UI
- Phoenix-like dataset experimentation surfaces

### Phoenix owns

- raw traces
- trace exploration
- prompts
- evaluators
- playground
- experiment analysis

## Current Baseline

What exists today:

- repository-local discovery and publish / unpublish workflow
- worker-backed run execution and run lifecycle tracking
- legacy run, trajectory, and playground surfaces from the old workbench story
- dataset CRUD and dataset-driven eval jobs
- artifact export for downstream analysis
- Phoenix-backed raw trace integration

What still needs to become product-sharp:

- better distinction between Atlas-owned data workflows and Phoenix-owned debugging workflows
- first-class RL curation and export semantics
- stronger provenance through publication, execution, eval, and export
- removal of overlapping workbench UX

## Priority Roadmap

### 1. Product subtraction and IA simplification

Priority: High

Goal:
- remove or downscope product surfaces that duplicate Phoenix

Scope:
- remove `Playground` as a first-class workflow
- remove `Runs` as a primary navigation destination
- remove Atlas-native raw trace browsing as a primary experience
- keep only Phoenix deep links and lightweight observability summaries where needed
- converge the primary navigation on `Agents`, `Datasets`, `Evals`, and `Exports`

Acceptance direction:
- Atlas no longer presents itself as a general agent workbench
- debugging heavy flows clearly route to Phoenix

### 2. RL dataset model and curation

Priority: High

Goal:
- make datasets and samples formal RL data assets instead of generic eval inputs only

Scope:
- strengthen dataset sample identity and slice metadata
- attach curation-oriented labels and export eligibility to samples or sample results
- make Atlas datasets the source of truth and Phoenix datasets mirrors when needed
- support filtering by source, slice, tag, and failure class

Acceptance direction:
- operators can decide which dataset slices and sample outcomes should move toward export without
  relying on Phoenix as the source of truth

### 3. Eval jobs as the production engine

Priority: High

Goal:
- make eval jobs the primary way Atlas produces RL candidate data

Scope:
- treat runs as supporting internal records under eval workflows
- support comparing published agent snapshots against the same dataset or slice
- expose sample-level outcomes, failure buckets, and regression slices
- keep orchestration focused on batch production, not manual experimentation

Acceptance direction:
- Atlas can answer which agent versions on which dataset slices produced the candidate data worth
  exporting

### 4. RL-ready export contract

Priority: High

Goal:
- make exports the main product output

Scope:
- extend export rows with agent snapshot, eval job, dataset sample, artifact, image, runner, and
  failure provenance
- support export filtering by success, failure type, slice, and compare outcome
- keep the export endpoint stable while expanding row richness

Acceptance direction:
- a training team can consume exported rows without reconstructing lineage across Atlas and Phoenix

### 5. Publication and execution provenance hardening

Priority: Medium

Goal:
- keep the provenance chain stable from publication to export

Scope:
- strengthen published artifact and image metadata
- preserve runner backend through execution and export
- keep Phoenix trace pointers and deep links attached without making Atlas a trace browser

Acceptance direction:
- every exported row and eval result can be attributed to a governed published snapshot and its
  execution carrier

## Supporting Work

### Documentation and language cleanup

Priority: Medium

Goal:
- keep product language aligned with the narrowed scope

Scope:
- align PRD, README, roadmap, and architecture docs
- remove workbench-first phrasing
- describe Phoenix as the analysis plane and Atlas as the RL data control plane

### Frontend control-plane focus

Priority: Medium

Goal:
- keep the frontend centered on Atlas-owned workflows

Scope:
- push heavy observability workflows out to Phoenix
- show only the provenance and export context that Atlas owns
- bias new UI work toward dataset, eval, curation, and export flows

## Deferred Tracks

### Multi-language agent runtime

Priority: Medium

Deferred because:
- the current priority is narrowing the product and improving RL data workflows, not broadening the
  runtime matrix

What belongs here later:
- TypeScript or other non-Python agent support
- language-aware discovery and publication contracts
- command or artifact-based launch specs

### Docker and remote runners

Priority: Medium

Deferred because:
- provenance and product-surface simplification matter more right now than adding another carrier

What belongs here later:
- Docker-backed runner execution
- remote or sandboxed runners
- image distribution and isolation semantics

### Direct RL ingestion

Priority: Medium

Deferred because:
- the near-term handoff is offline export, not training orchestration

What belongs here later:
- direct handoff into internal RL ingestion pipelines
- training-task submission integration
- automated feedback loops from export to training
