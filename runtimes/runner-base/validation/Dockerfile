FROM node:20-bookworm-slim AS claude-code

ARG CLAUDE_CODE_NPM_VERSION=2.1.89

RUN npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_NPM_VERSION}

FROM python:3.12-slim

WORKDIR /workspace

COPY --from=claude-code /usr/local/bin/claude /usr/local/bin/claude
COPY --from=claude-code /usr/local/bin/node /usr/local/bin/node
COPY --from=claude-code /usr/local/lib/node_modules /usr/local/lib/node_modules

COPY packages/contracts/python /workspace/packages/contracts/python
COPY runtimes/runner-base /workspace/runtimes/runner-base
COPY runtimes/runner-base/validation/sample-project /opt/atlas-validation/sample-project

RUN pip install --no-cache-dir uv \
 && uv pip install --system /workspace/packages/contracts/python /workspace/runtimes/runner-base

RUN python - <<'PY'
import tarfile
from pathlib import Path

root = Path("/opt/atlas-validation")
source = root / "sample-project"
bundle = root / "project-bundle.tar.gz"
with tarfile.open(bundle, "w:gz") as archive:
    archive.add(source, arcname="sample-project")
PY

ENV HOME=/home/atlas

RUN useradd --create-home --uid 1000 atlas \
 && chown -R atlas:atlas /opt/atlas-validation /workspace

USER atlas

WORKDIR /workspace
