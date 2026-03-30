# Observability Infra

`infra/observability/` owns collector and backend wiring for the observability plane.

Boundary rule:

- runtimes and control-plane exporters should target OTLP
- collector and backend routing belongs in infrastructure
- Phoenix may be wired here for trace inspection, but it is not the runtime contract
