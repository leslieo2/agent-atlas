# Schemas

`schemas/` is the neutral schema source of truth for cross-plane contracts.

Use:

- `jsonschema/` for contract schemas
- `openapi/` for external HTTP APIs
- `protobuf/` for boundaries that later need gRPC or protobuf generation

The canonical internal execution contracts are defined in
`packages/contracts/python/src/agent_atlas_contracts/execution.py` and mirrored here as
versioned JSON Schema files so the control plane, runtimes, workers, and future plane services
share the same boundary definitions.

Current mirrored execution contracts:

- `RunSpec` -> `jsonschema/run-spec.v1.schema.json`
- `RunnerRunSpec` -> `jsonschema/runner-run-spec.v1.schema.json`
- `EventEnvelope` -> `jsonschema/runner-event.v1.schema.json`
- `ArtifactManifest` -> `jsonschema/runner-artifact-manifest.v1.schema.json`
- `EvalResult` -> `jsonschema/eval-result.v1.schema.json`
- `ExportManifest` -> `jsonschema/export-manifest.v1.schema.json`
