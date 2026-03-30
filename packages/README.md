# Packages

`packages/` is reserved for cross-plane shared libraries.

The key long-term boundary is `packages/contracts/`, which should own neutral contracts such as
run specs, event envelopes, artifact manifests, eval results, and export manifests.
