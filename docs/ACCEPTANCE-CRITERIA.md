# Acceptance criteria

- [ ] `docker compose up --build -d` starts six services.
- [ ] Healthy run returns `success`.
- [ ] Timeout run returns `degraded` and a safe manual-review response.
- [ ] Jaeger shows one correlated trace with agent/tool/API spans.
- [ ] Risk timeout span has error status and timeout evidence.
- [ ] Collector debug logs show received traces.
- [ ] Customer financial values are absent from normal trace attributes.
- [ ] `/sessions/{id}/timeline` returns ordered stored events.
- [ ] `/sessions/{id}/reconstruct` makes no external service calls.
- [ ] Policy-v2 counterfactual reuses the same recorded Risk timeout.
- [ ] Task, tool, policy and fallback evaluations are persisted.
- [ ] Operator can explain root span, propagation, Collector role, trace/replay separation and replay modes.
