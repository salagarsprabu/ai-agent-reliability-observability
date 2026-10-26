# AI Agent Reliability, Observability, Replay and Evaluation

A production-oriented reference implementation showing how an enterprise AI agent can be **observed, diagnosed, evaluated, reconstructed, replayed, and tested for resilience**.

We implemented an end-to-end AI Reliability reference architecture that separates agent execution, observability, evaluation and replay concerns. Each agent transaction is correlated through OpenTelemetry, investigated through distributed tracing, evaluated independently for business and policy outcomes, and persisted with sufficient evidence for reconstruction and controlled replay. Historical failures can be replayed under alternative policies to determine whether a proposed resilience change improves the customer outcome without re-invoking production dependencies. The design establishes the foundation for AI-specific SLIs/SLOs, auditability, release-quality gates and enterprise AI operations.”

> **Project status:** Hands-on reference implementation for learning and architecture validation. This is not a production banking platform.

---

## What This Project Demonstrates

- A real multi-service loan-support agent workflow
- Healthy, timeout, unavailable-service, and malformed-response scenarios
- OpenTelemetry instrumentation and W3C trace-context propagation
- OTLP telemetry routing through the OpenTelemetry Collector
- Distributed trace investigation in Jaeger
- Persisted sessions, events, evaluations, and replay evidence in PostgreSQL
- Historical reconstruction without calling live tools
- Controlled replay using recorded tool outcomes
- Counterfactual replay using an alternative policy
- Rule-based agent evaluations with evaluator versioning
- A web-based AI Reliability Operations Console
- Initial safe-outcome SLI and provisional SLO views

---

## Reference Scenario

A customer asks:

> “Can I increase my personal-loan limit from $20,000 to $45,000?”

The Loan Support Agent:

1. Classifies the customer intent.
2. Creates an execution plan.
3. Retrieves the customer profile.
4. Calls the Risk Assessment service.
5. Applies the lending-response policy.
6. Generates a verified or degraded response.
7. Runs agent-specific evaluations.
8. Persists evidence needed for reconstruction and replay.

### Healthy path

```text
Customer Request
      |
      v
Loan Agent
      |
      v
Customer Profile API       HTTP 200
      |
      v
Risk Assessment API        HTTP 200
      |
      v
Policy Check               PASS
      |
      v
Customer Response          SUCCESS
```

### Timeout path

```text
Customer Request
      |
      v
Loan Agent
      |
      v
Customer Profile API       HTTP 200
      |
      v
Risk Assessment API        TIMEOUT
      |
      v
Fallback                   ACTIVATED
      |
      v
Policy Check               PASS
      |
      v
Customer Response          DEGRADED BUT SAFE
```

---

## Architecture

```text
                         Windows Browser
                               |
                        SSH local tunnels
                     8000              16686
                       |                  |
                       v                  v
              AI Reliability UI        Jaeger UI
                       |                  ^
                       | REST APIs        | OTLP
                       v                  |
                Loan Support Agent       |
                    Port 8000            |
                       |                 |
             +---------+---------+       |
             |                   |       |
             v                   v       |
   Customer Profile API   Risk Assessment API
        Port 8001              Port 8002
             |                   |
             +---------+---------+
                       |
                Business outcome

All application services
          |
   OpenTelemetry SDK
          |
      OTLP/HTTP
          v
OpenTelemetry Collector
   Ports 4317 / 4318
          |
          v
        Jaeger

Loan Support Agent
          |
          v
      PostgreSQL
          |
  Sessions / Events / Evaluations
          |
 Reconstruction / Replay / Comparison
```

---

## Three Architectural Paths

### Business execution path

```text
Customer → Agent → Customer API → Risk API → Policy → Response
```

### Observability path

```text
Services → OpenTelemetry SDK → OTLP → Collector → Jaeger
```

### Evidence and replay path

```text
Agent → PostgreSQL → Reconstruction / Replay / Counterfactual analysis
```

Jaeger is the technical trace-investigation backend. PostgreSQL is the evidence store used for reconstruction, evaluator results, and controlled replay. The Operations Console brings the business and reliability evidence together without attempting to replace Jaeger.

---

## Runtime Components

### Loan Support Agent

- Container: `agent`
- Port: `8000`
- Accepts agent requests
- Creates sessions and spans
- Calls downstream tools
- Applies policies and fallbacks
- Runs evaluations
- Persists replay evidence
- Hosts the Operations Console under `/ui/`

### Customer Profile API

- Container: `customer-api`
- Port: `8001`
- Returns simulated customer information
- Produces server-side OpenTelemetry spans

### Risk Assessment API

- Container: `risk-api`
- Port: `8002`
- Produces healthy lending decisions
- Supports controlled timeout and malformed-response modes

### OpenTelemetry Collector

- Container: `otel-collector`
- OTLP/gRPC: `4317`
- OTLP/HTTP: `4318`
- Health check: `13133`
- Receives, processes, filters, batches, and exports telemetry

### Jaeger

- Container: `jaeger`
- UI port: `16686`
- Displays distributed traces, spans, latency, dependencies, and errors

### PostgreSQL

- Container: `postgres`
- Port: `5432`
- Stores sessions, events, evaluations, replay envelopes, and comparisons

---

## AI Reliability Operations Console

The repository includes a web UI inspired by enterprise observability consoles but connected to the real backend APIs in this project.

### UI capabilities

#### Overview

- Total persisted sessions
- Successful interactions
- Degraded and degraded-success outcomes
- Dependency/tool-failure count
- Safe-outcome rate
- Recent sessions
- Outcome distribution

#### Session Explorer

Search and inspect sessions using:

- Session ID
- Conversation ID
- Agent status
- Failure mode
- Agent version
- Policy version

#### Session Detail

- Session and trace IDs
- Agent, policy, and evaluator lineage
- Ordered execution timeline
- Tool failures and durations
- Task, tool, policy, and fallback evaluations
- Final customer response
- Link to Jaeger for detailed trace investigation

#### Replay Studio

- Historical reconstruction
- Controlled replay with Policy v1
- Counterfactual replay with Policy v2
- Raw replay evidence
- Original-versus-replay comparison
- Verification that recorded tool outcomes were reused
- Verification that external services were not called

#### Reliability and SLO

- Safe-outcome SLI
- Verified-success rate
- Dependency-failure exposure
- Provisional 97% safe-outcome target
- Insufficient-sample warning for small datasets

### Important UI boundary

```text
Operations Console
  ├── Sessions
  ├── Evaluations
  ├── Reconstruction
  ├── Replay
  ├── Counterfactual comparison
  └── Reliability scorecard

Jaeger
  └── Detailed distributed trace investigation
```

The UI does not claim capabilities that are not implemented. It does not display synthetic RAG, ChromaDB, LLM token-cost, or golden-dataset benchmark data.

---

## Technology Stack

- Python 3.12
- FastAPI
- httpx
- SQLAlchemy
- psycopg
- PostgreSQL 16
- OpenTelemetry Python SDK
- OpenTelemetry Collector Contrib
- OTLP/HTTP and OTLP/gRPC
- Jaeger
- Docker and Docker Compose
- HTML, CSS, and JavaScript Operations Console
- pytest

---

## Repository Structure

```text
ai-agent-observability-replay/
|-- agent/
|   |-- Dockerfile
|   |-- requirements.txt
|   `-- app/
|       |-- main.py
|       |-- workflow.py
|       |-- telemetry.py
|       |-- evaluations.py
|       |-- policy.py
|       |-- replay.py
|       |-- db.py
|       |-- schemas.py
|       |-- config.py
|       `-- static/
|           `-- index.html
|-- customer-api/
|-- risk-api/
|-- otel-collector/
|-- scripts/
|   |-- healthy-run.sh
|   |-- timeout-run.sh
|   |-- reconstruct.sh
|   `-- counterfactual.sh
|-- tests/
|-- docs/
|-- docker-compose.yml
|-- .env.example
|-- SECURITY.md
|-- VALIDATION.md
`-- README.md
```

---

## Prerequisites

- Ubuntu 22.04 or later, or a compatible Linux environment
- Docker Engine
- Docker Compose v2
- Git
- curl
- Python 3
- SSH access when running on a remote VM

---

## Clone and Configure

```bash
git clone https://github.com/salagarsprabu/ai-agent-reliability-observability.git
cd ai-agent-reliability-observability
cp .env.example .env
chmod +x scripts/*.sh
```

If scripts contain `python -m json.tool`, update them for Ubuntu:

```bash
sed -i 's/python -m json.tool/python3 -m json.tool/g' scripts/*.sh
```

---

## Build and Start

Validate Compose:

```bash
docker compose config
```

Build and start all services:

```bash
docker compose up -d --build
```

Check the runtime:

```bash
docker compose ps
```

Expected services:

```text
agent
customer-api
risk-api
otel-collector
jaeger
postgres
```

---

## Verify Health

Agent:

```bash
curl -sS http://localhost:8000/health | python3 -m json.tool
```

Customer Profile API:

```bash
curl -sS http://localhost:8001/health | python3 -m json.tool
```

Risk Assessment API:

```bash
curl -sS http://localhost:8002/health | python3 -m json.tool
```

Collector:

```bash
curl -i http://localhost:13133/
```

A successful health response proves that a component is responding. It does not by itself prove that the complete business and telemetry flows are working.

---

## Access the UI and Jaeger from Windows

Do not expose the application or Jaeger ports publicly. Use SSH local forwarding:

```powershell
ssh `
  -L 8000:localhost:8000 `
  -L 16686:localhost:16686 `
  azureuser@salagarsvm1.eastus.cloudapp.azure.com
```

Keep the PowerShell window open.

Open the Operations Console:

```text
http://localhost:8000/ui/
```

The root URL also redirects to the UI:

```text
http://localhost:8000
```

Open Jaeger:

```text
http://localhost:16686
```

Open FastAPI Swagger:

```text
http://localhost:8000/docs
```

---

## Scenario 1: Healthy Agent Execution

```bash
./scripts/healthy-run.sh
```

Expected result:

```text
Agent outcome            SUCCESS
Customer Profile API     PASS
Risk Assessment API      PASS
Task completion          PASS
Tool execution           PASS
Policy compliance        PASS
Fallback effectiveness   PASS
```

Refresh the Operations Console and verify that the session appears with the generated session and trace IDs.

---

## Scenario 2: Risk Assessment Timeout

```bash
./scripts/timeout-run.sh
```

Expected result:

```text
Customer Profile API     SUCCESS
Risk Assessment API      TIMEOUT
Tool execution           FAIL
Fallback                 SUCCESS
Policy compliance        PASS
Task completion          DEGRADED
Customer outcome         SAFE ESCALATION
```

In the Operations Console:

1. Open **Sessions**.
2. Select the timeout session.
3. Review the execution timeline.
4. Review the mixed evaluation outcome.
5. Use the trace ID to correlate the session with Jaeger.

In Jaeger, inspect the Risk Assessment tool span and identify the critical latency and error evidence.

---

## Inspect Stored Evidence

List sessions:

```bash
curl -sS http://localhost:8000/sessions | python3 -m json.tool
```

Retrieve the session timeline:

```bash
curl -sS \
  http://localhost:8000/sessions/SESSION_ID/timeline \
  | python3 -m json.tool
```

Retrieve evaluations:

```bash
curl -sS \
  http://localhost:8000/sessions/SESSION_ID/evaluations \
  | python3 -m json.tool
```

---

## Reconstruction, Replay, and Counterfactual Analysis

### Historical reconstruction

Question answered:

> What happened?

```bash
./scripts/reconstruct.sh SESSION_ID
```

Historical reconstruction reads persisted events and does not call external services.

### Controlled replay

Question answered:

> Can the decision be reproduced from captured evidence using the original policy?

```bash
curl -sS -X POST \
  http://localhost:8000/sessions/SESSION_ID/replay \
  -H 'Content-Type: application/json' \
  -d '{"policy_version":"1.0.0"}' \
  | python3 -m json.tool
```

### Counterfactual replay

Question answered:

> What would have happened if the policy had been different?

```bash
./scripts/counterfactual.sh SESSION_ID
```

A meaningful timeout comparison is:

```text
Original Policy v1
Risk timeout → Manual review → DEGRADED

Counterfactual Policy v2
Same Risk timeout → Qualified provisional result + mandatory review
→ DEGRADED_SUCCESS
```

Expected control evidence:

```text
same_recorded_tool_outcomes = true
external_services_called    = false
```

---

## Agent Evaluations

### Task completion

Did the customer receive a verified result or approved escalation?

Suggested scoring model:

```text
success             1.0
Degraded success    0.8
degraded            0.5
failure             0.0
```

### Tool execution

Did required downstream tools complete successfully?

### Policy compliance

Did the agent avoid fabricating approval or presenting an unverified outcome as final?

### Fallback effectiveness

Did degraded execution still provide a usable next action?

Each result includes:

- Evaluation name
- Numeric score
- Label
- Explanation
- Evaluator version

Evaluator versioning is important because a changed score may result from a changed evaluator rather than a changed agent.

---

## OpenTelemetry and Jaeger Validation

Check Collector status:

```bash
docker compose ps otel-collector
```

Check OTLP listeners:

```bash
sudo ss -lntp | grep -E ':(4317|4318|13133)\b'
```

Generate telemetry:

```bash
./scripts/healthy-run.sh
sleep 3
docker compose logs otel-collector --since=30s
```

The strongest validation is:

```text
Generate transaction
       ↓
Collector receives spans
       ↓
Jaeger displays the same trace
```

---

## Reliability and SLO Notes

The UI calculates an initial safe-outcome SLI:

```text
Success + Approved Degraded Outcomes
------------------------------------
Total Stored Sessions
```

The draft lab SLO is:

> 97% of eligible loan-support interactions should produce either a verified decision or an approved safe escalation within the agreed latency threshold, with zero critical policy violations.

This remains provisional because the current repository does not yet persist a complete measurement-window model or full request-latency SLI.

---

## Privacy Design

Raw customer financial data is deliberately excluded from normal trace attributes. Traces use a stable salted customer-reference hash.

The Collector also removes configured sensitive attribute names before exporting telemetry.

### Jaeger should contain

- Trace and span identifiers
- Service and operation names
- Duration
- Error type
- Tool name
- HTTP status
- Hashed correlation reference

### PostgreSQL replay evidence may contain

- Session and conversation references
- Agent and policy versions
- Ordered execution events
- Recorded tool outcomes
- Evaluation evidence
- Historical outcome
- Replay comparisons

The replay store is not production hardened. A real implementation needs encryption, RBAC, key management, data classification, retention, and deletion controls.

---

## Automated Tests

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r tests/requirements.txt
pytest -q
```

Syntax-only validation:

```bash
python3 -m compileall -q agent && echo "Python syntax: PASS"
```

---

## Troubleshooting

### Script permission denied

```bash
chmod +x scripts/*.sh
```

### `python: command not found`

```bash
sed -i 's/python -m json.tool/python3 -m json.tool/g' scripts/*.sh
```

### JSON formatter reports `Expecting value`

Inspect the unformatted HTTP response:

```bash
curl -i http://localhost:8000/health
```

Inspect agent logs:

```bash
docker compose logs agent --tail=100
```

### PostgreSQL foreign-key violation for evaluations

The parent session must be flushed before inserting child event and evaluation records:

```python
db.add(session_record)
db.flush()
```

Rebuild the agent after changing application code:

```bash
docker compose up -d --build agent
```

### UI does not open

Verify the static file:

```bash
ls -lh agent/app/static/index.html
```

Verify the route:

```bash
curl -I http://localhost:8000/ui/
```

Inspect logs:

```bash
docker compose logs agent --tail=100
```

Rebuild:

```bash
docker compose up -d --build agent
```

### UI loads but contains no data

Generate sessions:

```bash
./scripts/healthy-run.sh
./scripts/timeout-run.sh
```

Then refresh the UI.

---

## Acceptance Criteria

- [ ] All six containers start successfully.
- [ ] PostgreSQL reports healthy.
- [ ] The application health endpoints return HTTP 200.
- [ ] The Operations Console loads from `/ui/`.
- [ ] The Session Explorer shows persisted sessions.
- [ ] A healthy run returns `success`.
- [ ] A timeout run returns `degraded` safely.
- [ ] Jaeger displays a correlated distributed trace.
- [ ] The Risk timeout appears as a failed tool span.
- [ ] Evaluations are shown in the UI.
- [ ] Reconstruction does not call external services.
- [ ] Controlled replay uses recorded tool outcomes.
- [ ] Counterfactual Policy v2 produces a comparison.
- [ ] Raw customer financial data is absent from normal trace attributes.
- [ ] The operator can explain the architecture and evidence flow without reading the code.

---

## Current Limitations

- The initial agent is deterministic and rule-based rather than LLM-driven.
- Banking data and services are simulated.
- Authentication and authorization are not implemented.
- The UI is intended for a trusted lab environment.
- Replay artifacts are not encrypted with production key management.
- High availability and horizontal scaling are not implemented.
- Production retention and deletion policies are not enforced.
- Replay is policy re-execution using captured state, not full deterministic model replay.
- RCA is operator-led rather than AI-generated.
- Deployment uses Docker Compose rather than Kubernetes.
- The SLO view is provisional and based on the current stored session set.

---

## Roadmap

### Phase 2: Deeper reliability evidence

- Store end-to-end transaction latency
- Add fixed SLI measurement windows
- Aggregate policy-compliance evaluations
- Add error-budget calculation
- Add filters by agent, policy, evaluator, and failure mode

### Phase 3: Real model integration

- Add an LLM provider
- Trace model invocation and token usage
- Record model and prompt versions
- Add groundedness and response-quality evaluations
- Measure cost per successful task

### Phase 4: Evaluation release gate

- Build a golden dataset
- Compare agent versions
- Add deterministic and model-assisted evaluators
- Integrate CI/CD PASS/BLOCK gates
- Retain release evidence

### Phase 5: Enterprise hardening

- Authentication and RBAC
- TLS and mTLS
- Secret management
- Encrypted replay storage
- Retention and deletion controls
- Kubernetes deployment
- Scalable regional Collector gateways
- Production alerting and incident integration

---

## Git Workflow

Review changes:

```bash
git status
git diff
```

Validate:

```bash
python3 -m compileall -q agent
pytest -q
```

Stage and commit:

```bash
git add README.md agent/app/main.py agent/app/static/index.html
git diff --cached
git commit -m "Add AI reliability operations console and documentation"
```

Synchronize safely:

```bash
git pull --rebase origin main
git push origin main
```

Do not use `git push --force` merely to bypass a non-fast-forward rejection.

---

## Why This Project Exists

The goal is not to demonstrate another AI chatbot.

The objective is to explore the operational engineering required to make enterprise AI systems observable, evaluable, diagnosable, replayable, and reliable:

```text
Observe
   ↓
Evaluate
   ↓
Diagnose
   ↓
Reconstruct
   ↓
Replay
   ↓
Test a remediation
   ↓
Measure improvement
   ↓
Decide whether reliability is acceptable
```

This project explores the intersection of Enterprise Architecture, SRE, OpenTelemetry, distributed tracing, AI Agent Reliability, AI Evaluation, and counterfactual analysis.

---

## License

This project is licensed under the MIT License. See `LICENSE` for details.
