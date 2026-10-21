# Validation report

Validated in the build environment:

- Python syntax compilation: passed
- Unit tests: 4 passed
- Policy v1 safe-degradation behavior: passed
- Policy v2 provisional counterfactual behavior: passed
- Reconstruction external-call assertion: passed
- Counterfactual recorded-outcome reuse assertion: passed

Not executed in the build environment:

- Docker image pulls/builds
- Live Docker Compose startup
- OTLP transmission to Collector
- Jaeger UI inspection
- PostgreSQL integration flow

Reason: Docker is unavailable inside the artifact-generation container. Run the documented acceptance criteria in your Ubuntu/KodeKloud environment.
