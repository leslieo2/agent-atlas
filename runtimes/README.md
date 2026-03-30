# Runtimes

`runtimes/` holds execution-side adapters that consume shared contracts and run agents inside a
specific framework or carrier.

`runner-base/` now owns the shared bootstrap, launcher, and standardized output-writing primitives
used by the control plane and future runtime families.

`runner-openai-agents/` and `runner-langgraph/` now own the framework-specific runtime execution
and trace-mapping code for those adapters.

`runner-inspect/` and `runner-custom/` remain scaffolded landing zones for future runtime families.
