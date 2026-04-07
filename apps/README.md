# Apps

`apps/` holds the app entrypoints that exist in the current checkout.

Current implementations:

- `web/`: Next.js operator UI
- `control-plane/`: FastAPI control plane and worker

The current checkout does not contain any additional top-level `apps/*` services.

Planned future split candidates:

- `executor-gateway/`: execution entrypoint and scheduler adapters
- `data-plane-api/`: data-plane read and write API
- `data-ingestion/`: event and trace normalization pipeline
- `eval-worker/`: evaluator and batch scoring worker
- `export-worker/`: offline export and manifest generation worker

Treat the list above as directional architecture notes, not as a map of directories that already
exist in this repository.
