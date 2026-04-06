# Roadmap

This document is for sequencing, not for redefining the public product contract. The root
`README.md` remains the public authority.

## Current Direction

Atlas is narrowing into an RL data control plane organized around:

`governed intake -> governed asset -> run -> evidence -> export`

The platform still spans:

- control plane
- execution plane
- observability / eval plane
- data plane
- training plane

Hexagonal design applies locally inside control-plane business services, not as the top-level
description for the whole stack.

## What The Roadmap Is Optimizing For

- less overlapping product authority beside the root README
- fewer Phoenix-duplicate surfaces inside Atlas
- stronger governed asset, dataset, evidence, and export semantics
- cleaner execution/runtime boundaries behind Atlas-owned contracts

## Near-Term Tracks

### 1. Product subtraction and boundary enforcement

Goal:
- keep Atlas centered on `Agents / Datasets / Experiments / Exports`

Scope:
- continue downscoping standalone run, playground, and trace-first surfaces
- keep Phoenix as the deep-debug backend rather than a peer Atlas workspace
- keep runner, provider, carrier, and credential detail behind provenance or execution-profile
  summaries instead of elevating them into product nouns

Success looks like:
- Atlas no longer reads like a general agent workbench
- debugging-heavy flows route to Phoenix

### 2. Governed asset and dataset hardening

Goal:
- make governed assets and datasets the stable production inputs for evidence and export

Scope:
- strengthen governed asset readiness and provenance
- strengthen dataset sample identity, slice metadata, and export eligibility
- keep dataset-driven execution centered on repeatable batch workflows

Success looks like:
- operators can clearly answer which governed asset on which dataset slice produced the evidence
  they care about

### 3. Experiments and evidence as the production engine

Goal:
- make experiment batches the default production path for evidence-backed results

Scope:
- keep runs as supporting records under experiment workflows
- improve compare, curation, and evidence summaries
- preserve trace and execution provenance without turning those systems into first-class product
  centers

Success looks like:
- Atlas can identify which governed assets and dataset slices produced export-worthy evidence

### 4. Export contract strengthening

Goal:
- make exports the main product handoff

Scope:
- preserve stable export rows while enriching provenance
- support curation-friendly filtering by success, failure type, slice, and compare outcome
- keep exports consumable without downstream teams reconstructing lineage across Atlas and Phoenix

Success looks like:
- training teams can consume offline exports as the durable product output

### 5. Execution and runtime separation

Goal:
- keep execution carriers and external tools downstream of Atlas-owned semantics

Scope:
- continue tightening execution-control, runner, and evidence boundaries
- keep external runtimes such as Claude Code CLI, Inspect AI, and E2B behind adapters
- let execution/runtime improvements increase realism without reopening new product lanes

Success looks like:
- Atlas can swap execution or evidence adapters without redefining its product model

## Supporting Work

### Documentation and language cleanup

Goal:
- keep all surviving docs aligned to the README-reset contract

Scope:
- rewrite or demote stale top-level and app-entry docs that still teach superseded product
  authority
- keep subsystem docs only where they narrow cleanly to local contributor or architecture rules

### Frontend control-plane focus

Goal:
- keep the frontend centered on Atlas-owned workflows

Scope:
- keep execution details demoted behind execution-profile, provenance, and evidence summaries
- keep Phoenix as deeplink-only inside the product UI
- bias automation and walkthroughs toward the canonical governed asset path instead of starter- or
  runtime-first residue

## Deferred Tracks

Deferred because they are not on the critical path for the current product shape:

- multi-language agent runtime support such as TypeScript agents
- broader remote runner coverage and image distribution
- direct RL ingestion or training-job scheduling
- full publication history and rollback UX
