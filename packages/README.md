# Packages

`packages/` is reserved for cross-plane shared libraries.

The key long-term boundary is `packages/contracts/`, which should own neutral contracts such as
run specs, event envelopes, artifact manifests, eval results, and export manifests.

In the current checkout, `packages/contracts/` is the concrete package in use. Other shared package
names referenced in architecture docs are planned landing zones until their directories exist.
