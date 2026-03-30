FROM python:3.12-slim

WORKDIR /workspace

COPY packages/contracts/python /workspace/packages/contracts/python
COPY runtimes/runner-base /workspace/runtimes/runner-base
COPY runtimes/runner-openai-agents /workspace/runtimes/runner-openai-agents
COPY runtimes/runner-langgraph /workspace/runtimes/runner-langgraph
COPY apps/control-plane /workspace/apps/control-plane

WORKDIR /workspace/apps/control-plane

RUN pip install --no-cache-dir uv
RUN uv pip install --system . \
  /workspace/packages/contracts/python \
  /workspace/runtimes/runner-base \
  /workspace/runtimes/runner-openai-agents \
  /workspace/runtimes/runner-langgraph

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
