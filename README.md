# AI Agent Observability, Replay and Evaluation Platform

A runnable reference implementation for one banking loan-support agent, two downstream APIs, real OpenTelemetry traces, Collector-to-Jaeger export, persisted replay evidence, rule-based evaluations, historical reconstruction, and counterfactual policy comparison.

This repository implements the scope in the supplied design document. It intentionally uses a deterministic agent first so that tracing, context propagation, failure attribution, replay boundaries, and evaluations remain transparent.

## Architecture

```text
Test Client
    |
    v
Loan Agent API (8000)
    |-- Customer Profile API (8001)
    |-- Risk Assessment API (8002: healthy / timeout / malformed)
    |-- Policy v1/v2
    |-- Rule-based evaluators
    `-- PostgreSQL replay/evidence store

All services -> OTLP/HTTP -> OTel Collector -> Jaeger (16686)
```

## What is real

- Three running HTTP services
- Real W3C trace-context propagation
- Real OTel spans and OTLP/HTTP export
- Real Collector processing and OTLP export to Jaeger
- Controlled timeout and malformed-response failures
- PostgreSQL session, event, evaluation and replay persistence
- Historical reconstruction without external calls
- Controlled/counterfactual policy replay using recorded tool outcomes

## What is deliberately not claimed

- No production banking integration
- No real LLM in v0.1
- No exact deterministic re-execution of a model
- No AI-generated RCA
- No production authentication, HA, encryption/KMS or retention enforcement
- No claim that Jaeger is the replay store

## Quick start

Prerequisites: Docker Engine, Docker Compose v2, curl and Python for pretty-printing JSON.

```bash
cp .env.example .env
docker compose up --build -d
docker compose ps
```

Open Jaeger: `http://localhost:16686`

### Healthy run

```bash
./scripts/healthy-run.sh
```

Expected: `status=success`, all evaluations pass.

### Timeout run

```bash
./scripts/timeout-run.sh
```

Expected:

- overall status `degraded`
- Risk tool execution fails
- task completion is degraded
- policy compliance passes
- customer receives manual-review escalation

Copy the returned `session_id`, then run:

```bash
./scripts/reconstruct.sh SESSION_ID
./scripts/counterfactual.sh SESSION_ID
```

The counterfactual uses policy `2.0.0`, the original query and the same recorded Risk timeout. It makes no external tool calls.

## API endpoints

```text
POST /agent/run
GET  /sessions
GET  /sessions/{session_id}
GET  /sessions/{session_id}/timeline
GET  /sessions/{session_id}/evaluations
POST /sessions/{session_id}/reconstruct
POST /sessions/{session_id}/replay
POST /sessions/{session_id}/counterfactual
GET  /replays/{replay_id}/comparison
GET  /health
```

Interactive API documentation: `http://localhost:8000/docs`

## Jaeger investigation

1. Run a healthy and timeout request.
2. Wait a few seconds for batching.
3. Open Jaeger and select `loan-support-agent`.
4. Search for recent traces.
5. Open the timeout trace and inspect `tool.risk_assessment`.
6. Confirm its error status, duration and child HTTP call.
7. Confirm `customer-profile-api` remained healthy.

## Privacy design

Normal trace attributes contain only a stable salted customer reference hash. Raw income, debt, credit score, full customer ID, prompt content and tool payloads are not deliberately added as trace attributes. The Collector also removes a defined denylist of sensitive attribute names as defense in depth.

The replay store contains business evidence needed for the lab. It is not production hardened. A production implementation requires encryption, RBAC, key management, data-classification controls, purpose-based access and retention enforcement.

## Evaluations

- `task_completion`
- `tool_execution`
- `policy_compliance`
- `fallback_effectiveness`

Each result contains a score, label, explanation and evaluator version.

## Failure experiments

```bash
# Risk service unavailable
docker compose stop risk-api
./scripts/timeout-run.sh
docker compose start risk-api

# Collector unavailable: business request should still execute
docker compose stop otel-collector
./scripts/healthy-run.sh
docker compose start otel-collector

# Malformed Risk response
curl -sS -X POST http://localhost:8000/agent/run \
  -H 'Content-Type: application/json' \
  -d '{"conversation_id":"conv-malformed-001","query":"Increase my loan limit","failure_mode":"malformed","policy_version":"1.0.0"}' | python -m json.tool
```

## Tests

Local lightweight tests:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r tests/requirements.txt
pytest -q
```

## Definition of done

See `docs/ACCEPTANCE-CRITERIA.md`.
