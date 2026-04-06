# Product Requirements Document

This document narrows the current product contract behind the repository README. It is not a
second public entrypoint.

## Product Definition

Agent Atlas is the control plane for turning governed assets, datasets, and runs into
evidence-backed offline RL data.

The shortest useful product model is:

`governed intake -> governed asset -> run -> evidence -> export`

Atlas is not a runner console and not a tracing product. Its value is governed asset lifecycle,
dataset identity, evidence-backed orchestration, and exportable data.

## Architecture Stance

Atlas should be described as a layered platform:

- `Control Plane`
- `Execution Plane`
- `Observability / Eval Plane`
- `Data Plane`
- `Training Plane`

Hexagonal architecture still applies inside control-plane business services, but it is not the
top-level description for execution runtime, telemetry pipelines, or data-processing systems.

## Problem

Training and eval teams need a reliable way to answer:

- which governed asset produced this run
- which dataset sample and experiment generated this evidence
- which artifact, image, and runner were involved
- which outcomes are worth exporting for downstream RL or post-training workflows

Existing tooling is strong at debugging and experimentation, but weaker at governed data
production, curation, provenance, and export handoff. Atlas exists to own that layer.

## Target Users

- platform engineers who intake, validate, and govern runnable assets
- eval and data engineers who run batch jobs across datasets and slices
- training pipeline owners who need export-ready offline data with provenance

## Product Goals

### 1. Govern intake into runnable assets

Atlas must keep a stable governed record of what is allowed to run.

Required outcomes:

- governed intake and validation follow-through
- asset identity plus execution provenance
- clear readiness state before experiments start

### 2. Treat datasets as formal RL data assets

Datasets are controlled inputs for evidence production and export, not loose experiment scratchpads.

Required outcomes:

- dataset and sample identity
- slice, tag, and source metadata
- export eligibility and curation state
- linkage from sample to run evidence and export rows

### 3. Orchestrate batch production through experiments

Experiments should be the primary way Atlas turns governed assets and datasets into evidence-backed
results.

Required outcomes:

- batch job creation and lifecycle tracking
- sample-level outcomes
- baseline and candidate comparison
- evidence summaries that support curation

### 4. Export RL-ready offline data

Exports are the main product handoff.

Required outcomes:

- offline export first
- stable export schema
- embedded provenance per row
- filters that support curation by success, failure type, regression, and slice

## Product Non-Goals

Atlas should not become the primary place for:

- raw trace browsing
- trace search and filtering UX
- prompt management
- evaluator authoring
- experiment analysis UI
- rich playground or manual run workflows
- direct training-job orchestration

Those belong in Phoenix or other downstream tooling. Atlas can hold links and summaries, but it
should not recreate those products.

## Core Product Objects

First-class product objects:

- governed asset
- dataset
- experiment
- run evidence
- export artifact

Supporting internal records:

- run
- trace pointer
- observability metadata

Runs still matter for provenance and execution state, but they are supporting records beneath
experiments and exports, not the center of the product.

## Product Boundary With Phoenix

Atlas owns:

- governed asset lifecycle
- dataset identity and curation state
- experiment orchestration
- run provenance and evidence association
- export eligibility and offline export

Phoenix owns:

- raw traces
- deep trace inspection
- prompts
- evaluators
- playground
- trace-centric experiment analysis

Relationship model:

- Atlas is the source of truth for governed assets, datasets, experiments, evidence, and exports.
- Phoenix is the analysis plane.
- Atlas stores Phoenix pointers and deep links where useful.
- Atlas should not maintain a second product-level trace browser or experiment workbench.

## Information Architecture

The first-class product surfaces are:

- `Agents`
- `Datasets`
- `Experiments`
- `Exports`

Supporting drill-downs:

- run detail inside experiment workflows
- Phoenix deep links for trace inspection

Surfaces to remove or keep downscoped:

- standalone `Runs` as a primary navigation item
- standalone `Playground` or manual run console
- Atlas-native tracing workspace

## Success Criteria

The product is succeeding when:

- every exported row can be traced back to a governed asset, dataset sample, and experiment
- training teams can filter and select export slices without leaving Atlas
- operators use Phoenix for debugging, not Atlas-native trace tooling
- Atlas stays narrow and does not regrow a second observability or experiment product

## Deferred Work

Important but not required for the current product definition:

- multi-language agent runtime support such as TypeScript agents
- broader remote runner coverage beyond the current local and external-runner paths
- direct integration with RL ingestion or training-job scheduling systems
- full publication history and rollback UX
