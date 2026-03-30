# Runner Base

`runner-base/` owns shared runner bootstrap and launcher concerns for the execution-side runtime
layer.

Current ownership:

- local bootstrap workspace materialization for `RunnerRunSpec`
- file and directory layout derived from `RunnerBootstrapPaths`
- Kubernetes Job launch request generation for runner payloads
- neutral observability handoff carried in `RunnerRunSpec.observability`
- standardized runtime-side emission of events, terminal results, and artifact manifests
- local artifact file registration helpers for runner-produced outputs

Control-plane code should consume these primitives through thin adapters rather than owning the
bootstrap implementation itself.
