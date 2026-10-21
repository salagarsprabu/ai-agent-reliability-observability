# Architecture

## Runtime path

```text
Client -> Loan Agent -> Customer Profile API -> Risk Assessment API -> Policy -> Response
```

## Telemetry path

```text
Python OTel SDK -> OTLP/HTTP -> OTel Collector -> privacy processor -> batch -> Jaeger OTLP
```

## Evidence path

```text
Agent -> PostgreSQL
        |- Session metadata
        |- Ordered execution events
        |- Recorded tool outcomes
        |- Evaluations
        `- Replay comparisons
```

## Key boundaries

- **Jaeger is diagnostic telemetry storage**, not the replay system of record.
- **PostgreSQL is the evidence/replay store** and contains the data needed for controlled reconstruction.
- `agent.run` is the logical root span. Tool spans are children, and HTTPX instrumentation propagates W3C trace context to both APIs.
- Financial/customer values are intentionally excluded from trace attributes. A stable salted hash is used for correlation.
- Historical reconstruction performs no external calls.
- Controlled and counterfactual replay rerun decision policy using recorded tool outcomes. They are not claims of fully deterministic model replay.
