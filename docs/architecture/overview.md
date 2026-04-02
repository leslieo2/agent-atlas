# Architecture Overview

This is the compact architecture view for Agent Atlas.

Use it as the first-stop mental model before reading the more detailed docs:

- [repository-layout.md](repository-layout.md)
- [platform-boundaries.md](platform-boundaries.md)
- [../../apps/control-plane/ARCHITECTURE.md](../../apps/control-plane/ARCHITECTURE.md)
- [../../apps/web/ARCHITECTURE.md](../../apps/web/ARCHITECTURE.md)

The goal is to make one thing clear:

- Atlas is a layered product platform
- the control plane is the product center
- execution, observability, and training systems integrate around Atlas-owned contracts instead of defining them

## Platform Diagram

```text
                                     Web UI
                            (Agents / Datasets / Experiments / Exports)
                                                |
                                           HTTPS / JSON
                                                v
    +---------------------------------------------------------------------------------------+
    |                                     Control Plane                                      |
    |      FastAPI + worker + Atlas-owned product semantics + neutral run/evidence APIs      |
    |                                                                                       |
    |  Product modules: agents / datasets / experiments / exports / runs / policies         |
    +---------------------------------------------------------------------------------------+
              |                                  |                                  |
              | run intent + control             | evidence / query projection      | product-owned records
              v                                  v                                  v
    +---------------------------+      +-----------------------------+      +----------------------------+
    |      Execution Plane      |      | Observability / Eval Plane  |      |         Data Plane         |
    | launcher selection, queue,|      | OTLP ingest, trace linking, |      | trajectories, artifacts,   |
    | worker lifecycle, carrier |      | Phoenix deeplinks, eval     |      | lineage, labels, exports   |
    | adapters, K8s / local     |      | comparison + trace storage  |      | and training-ready records |
    +---------------------------+      +-----------------------------+      +----------------------------+
              |                                  ^                                  |
              | run spec / carrier request       | OTLP + trace metadata             | export manifests + URIs
              v                                  |                                  v
    +---------------------------------------------------------------------------------------+
    |                           Runner / Agent Runtime Plane                                 |
    |  framework adapter + agent loop + bootstrap + terminal result + artifact manifest      |
    +---------------------------------------------------------------------------------------+
              |                                  |                                  |
              | tool / MCP calls                 | model API                         | telemetry
              v                                  v                                  v
         Tool Gateway                       Model Gateway                    Phoenix / OTEL backend

    Data Plane ---------------------------------------------------------------> Training Plane
                         offline export manifests, object refs, curated datasets
```

## How To Read This Diagram

### 1. Atlas owns the product truth in the control plane

The control plane is where Atlas-owned semantics live:

- published agent governance
- dataset identity
- experiment orchestration
- run and evidence projection
- export and curation contracts

This is why the UI talks to the control plane first, not to Phoenix, Kubernetes, or a framework SDK.

### 2. Execution is a carrier, not the product center

The execution plane exists to take Atlas run intent and deliver it into a runnable carrier:

- local worker
- docker/container path
- Kubernetes job path
- future adapter-backed carriers

Execution infrastructure can change without redefining Atlas product objects.

### 3. Runners consume neutral contracts

Runner packages should only need:

- the shared contracts
- runner bootstrap helpers
- framework-specific SDK code

They must not import the control-plane application directly. A runner emits neutral outputs such as:

- runtime events
- terminal result
- artifact manifest
- trace metadata

### 4. Observability is read-side support, not product truth

Phoenix is important, but it is not the domain center of Atlas.

The rule is:

- Atlas owns `RunEvidence`
- observability backends project into that evidence
- deeplinks are product-facing conveniences, not the source of truth for Atlas state

### 5. The data plane is where evidence becomes training-usable

The control plane owns operator intent and governance.

The data plane owns the long-lived normalization path for:

- trajectories
- artifacts
- labels
- lineage
- export manifests
- training-usable records

That means Atlas can stay centered on governed RL data production instead of becoming a generic trace UI.

## Architecture Red Lines

Use these rules when deciding where new code belongs.

### Product surfaces

- Atlas owns `Agents`, `Datasets`, `Experiments`, and `Exports`
- Phoenix owns raw trace analysis and trace-native debugging workflows
- runner/carrier consoles should not become first-class Atlas pages

### Backend layering

- HTTP/API -> application -> domain
- infrastructure may depend on module ports and domain models
- feature modules must not reach into other feature use cases directly
- `app/execution/` is orchestration infrastructure, not a second product-control layer

### Frontend layering

- `app -> widgets -> features -> entities -> shared`
- UI should consume Atlas-owned records, evidence, and deeplinks
- frontend should not become a Phoenix workbench or runner console

### Shared contract boundary

Long-lived Atlas contracts stay neutral:

- run submission
- cancel / status / heartbeat
- event ingest
- terminal result
- artifact manifest

External systems map into those contracts. They do not redefine them.

## Where To Go Next

- Read [repository-layout.md](repository-layout.md) for repository placement rules.
- Read [platform-boundaries.md](platform-boundaries.md) for plane ownership and dependency rules.
- Read [../../apps/control-plane/ARCHITECTURE.md](../../apps/control-plane/ARCHITECTURE.md) for the control-plane modular-monolith rules.
- Read [../../apps/web/ARCHITECTURE.md](../../apps/web/ARCHITECTURE.md) for the frontend layering rules.
