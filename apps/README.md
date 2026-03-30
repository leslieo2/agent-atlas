# Apps

`apps/` holds product-facing services.

Current implementations:

- `web/`: Next.js operator UI
- `control-plane/`: FastAPI control plane and worker

Scaffolded next-stage services:

- `executor-gateway/`: execution entrypoint and scheduler adapters
- `data-plane-api/`: data-plane read and write API
- `data-ingestion/`: event and trace normalization pipeline
- `eval-worker/`: evaluator and batch scoring worker
- `export-worker/`: offline export and manifest generation worker
