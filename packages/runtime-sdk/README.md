# Runtime SDK

`runtime-sdk/` is the shared landing zone for runtime bootstrap helpers that should remain neutral
across frameworks and languages.

Current direction:

- shared runtime bootstrap contracts belong in `packages/contracts/`
- runtime-side helpers for OTLP export and other neutral execution concerns belong here
- vendor-specific observability clients should not become the runtime contract
