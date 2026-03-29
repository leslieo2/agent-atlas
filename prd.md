# Product Requirements Document

## Product Definition

Agent Atlas is the control plane for collecting, curating, and exporting RL-ready agent execution
data.

Atlas is not an observability product and should not compete with Phoenix on tracing,
experimentation, prompt workflows, evaluator authoring, or playground UX. Its value is the
governed data path from published agents to offline training exports.

## Problem

Training teams need a reliable way to answer these questions:

- which published agent version produced this data
- which dataset and sample produced this outcome
- which eval job generated it
- which artifact, image, and runner were involved
- which outcomes are useful for downstream RL or fine-tuning workflows

Existing agent tooling is strong at debugging and experimentation, but weaker at governed data
production, curation, provenance, and export handoff. Atlas exists to own that layer.

## Target Users

- agent platform engineers who publish and govern runnable agent snapshots
- eval and data engineers who run batch jobs across datasets and slices
- training pipeline owners who need RL-ready offline exports with provenance

## Product Goals

### 1. Govern published agent snapshots

Atlas must keep a stable record of which agent version was used to generate data.

Required outcomes:

- repository-local discovery
- validation and publish gate
- published snapshot metadata
- artifact, image, and runner provenance attached to publication

### 2. Treat datasets as formal RL data assets

Atlas datasets are not experiment workspaces. They are controlled data assets used to generate,
filter, and export training data.

Required outcomes:

- dataset and sample identity
- slice, tag, and source metadata
- linkage from sample to eval result and export row
- export eligibility and curation state

### 3. Orchestrate batch production through eval jobs

Atlas should make it easy to run one or more published agent snapshots across one or more dataset
slices and collect sample-level outcomes.

Required outcomes:

- batch job creation
- batch execution tracking
- sample-level result aggregation
- baseline and candidate comparison that helps decide what to export

### 4. Export RL-ready offline data

Atlas should produce data files that a training team can consume without reconstructing lineage from
multiple systems.

Required outcomes:

- offline export first
- stable export schema
- critical provenance embedded in each row
- filters that support curation by success, failure type, regression, and slice

## Product Non-Goals

Atlas should not be the primary place for:

- raw trace browsing
- trace search and filtering UX
- prompt management
- evaluator authoring
- experiment analysis UI
- rich playground or manual run workflows
- direct training-job orchestration

These belong in Phoenix or other vendor tooling. Atlas can hold links and summaries, but it should
not recreate those products.

## Core Product Objects

### First-class Atlas objects

- `PublishedAgent`
- `Dataset`
- `DatasetSample`
- `EvalJob`
- `EvalSampleResult`
- `ExportArtifact`

### Supporting internal objects

- `Run`
- `TracePointer`
- `ObservabilityMetadata`

Runs still matter for provenance and execution state, but they are supporting records beneath evals
and exports, not the center of the product.

## Product Boundary With Phoenix

### Atlas owns

- published agent identity and governance
- dataset identity and curation state
- eval job orchestration
- run provenance
- export eligibility
- RL-ready offline export

### Phoenix owns

- raw traces
- deep trace inspection
- prompts
- evaluators
- playground
- experiments and analysis

### Relationship model

- Atlas is the source of truth for datasets, samples, eval jobs, and exports.
- Phoenix is the analysis plane.
- Atlas stores Phoenix pointers and deep links where useful.
- Atlas should not maintain a second product-level trace browser or experiment workbench.

## Information Architecture

The target first-class product surfaces are:

- `Agents`
- `Datasets`
- `Evals`
- `Exports`

Supporting drill-downs:

- run detail as a child view within eval workflows
- Phoenix deep links for trace inspection

Surfaces to remove or downscope:

- standalone `Runs` as a primary navigation item
- standalone `Playground` or manual run console
- Atlas-native tracing workspace

## Primary Workflow

```text
Published Agent
  -> Dataset / Slice
  -> Eval Job
  -> Sample-level Results
  -> Curation / Compare
  -> RL-ready Export
```

Phoenix supports debugging and inspection around that loop, but Atlas owns the loop itself.

## Success Criteria

The product is succeeding when:

- every exported row can be traced back to a published agent snapshot, dataset sample, and eval job
- training teams can filter or select export slices without leaving Atlas
- operators use Phoenix for debugging, not Atlas-native trace tooling
- Atlas remains narrow and does not grow a second observability or experiment product

## Deferred Work

Important but not required for the current product definition:

- multi-language agent runtime support such as TypeScript agents
- Docker-backed and remote runners beyond the current local-first path
- direct integration with RL ingestion or training-job scheduling systems
- full publication history and rollback UX
