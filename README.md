# AI Agent Reliability, Observability, Replay and Evaluation

A production-oriented reference implementation demonstrating how an enterprise AI agent can be **observed, diagnosed, evaluated, reconstructed, and tested for resilience** using distributed tracing and persisted execution evidence.

The reference scenario is a banking loan-support agent that invokes Customer Profile and Risk Assessment services. The platform captures the complete execution path, introduces controlled failures, attributes faults to the responsible dependency, evaluates agent behavior, reconstructs historical sessions, and compares outcomes under an alternative resilience policy.

> **Project status:** Hands-on reference implementation for learning and architecture validation. It is not a production banking platform.

---

## Table of Contents

- [Problem Statement](#problem-statement)
- [Reference Scenario](#reference-scenario)
- [Architecture](#architecture)
- [Architecture Principles](#architecture-principles)
- [Runtime Components](#runtime-components)
- [Technology Stack](#technology-stack)
- [Repository Structure](#repository-structure)
- [Getting Started](#getting-started)
- [Start the Platform](#start-the-platform)
- [Verify Service Health](#verify-service-health)
- [Scenario 1: Healthy Agent Execution](#scenario-1-healthy-agent-execution)
- [Inspect the Distributed Trace](#inspect-the-distributed-trace)
- [Scenario 2: Risk Assessment Timeout](#scenario-2-risk-assessment-timeout)
- [Reliability Insight](#reliability-insight)
- [Inspect Stored Evidence](#inspect-stored-evidence)
- [Historical Reconstruction](#historical-reconstruction)
- [Controlled and Counterfactual Replay](#controlled-and-counterfactual-replay)
- [Agent Evaluations](#agent-evaluations)
- [Telemetry Privacy](#telemetry-privacy)
- [Automated Tests](#automated-tests)
- [Troubleshooting](#troubleshooting)
- [Acceptance Criteria](#acceptance-criteria)
- [Current Limitations](#current-limitations)
- [Roadmap](#roadmap)
- [Why This Project Exists](#why-this-project-exists)

---

## Problem Statement

Traditional application monitoring can identify infrastructure and API failures, but AI agents introduce additional operational questions:

- What customer request initiated the interaction?
- What execution plan did the agent create?
- Which tools and APIs were invoked?
- Which model, tool, API, or policy caused the failure?
- Did the agent handle the failure safely?
- Was the requested business task completed?
- Can the historical interaction be reconstructed?
- Would a different resilience policy have produced a better outcome?

This implementation explores those questions through a controlled banking loan-assessment workflow.

---

## Reference Scenario

A customer asks:

> “Can I increase my personal-loan limit from $20,000 to $45,000?”

The Loan Support Agent performs the following workflow:

1. Classifies the customer intent.
2. Creates an execution plan.
3. Retrieves the customer profile.
4. Calls the Risk Assessment service.
5. Applies the lending-response policy.
6. Generates a verified or degraded customer response.
7. Evaluates the interaction.
8. Persists evidence for reconstruction and replay.

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

### Failure path

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
Risk Assessment API        TIMEOUT / 504-style failure
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
                           Test Client
                               |
                               v
                    +-----------------------+
                    | Loan Support Agent    |
                    | Port 8000             |
                    +-----------+-----------+
                                |
                 +--------------+--------------+
                 |                             |
                 v                             v
      +----------------------+      +----------------------+
      | Customer Profile API |      | Risk Assessment API  |
      | Port 8001            |      | Port 8002            |
      | HTTP 200             |      | HTTP 200 / timeout   |
      +----------------------+      +----------------------+

                    BUSINESS EXECUTION PATH


                    OBSERVABILITY PATH

     Agent + Customer API + Risk API
                    |
             OpenTelemetry SDK
                    |
                OTLP/HTTP
                    v
          +-----------------------+
          | OTel Collector        |
          | Ports 4317 / 4318     |
          | Redact / Batch / Route|
          +-----------+-----------+
                      |
                      v
              +---------------+
              | Jaeger        |
              | UI Port 16686 |
              +---------------+


                    EVIDENCE PATH

              Loan Support Agent
                      |
                      v
              +----------------+
              | PostgreSQL     |
              | Port 5432      |
              +-------+--------+
                      |
       +--------------+----------------+
       |              |                |
       v              v                v
    Sessions        Events         Evaluations
                      |
                      v
         Reconstruction and Replay
```

---

## Architecture Principles

The implementation deliberately separates three concerns.

### Business execution

- Agent orchestration
- Tool and API invocation
- Policy enforcement
- Fallback handling
- Customer response generation

### Observability

- Distributed traces
- Parent-child span relationships
- Latency and errors
- Tool and API dependencies
- Failure attribution
- Hashed correlation identifiers

### Replay and evaluation evidence

- Session state
- Ordered execution events
- Recorded tool outcomes
- Agent and policy versions
- Evaluation results
- Replay runs and comparisons

**Jaeger is used for operational trace investigation. PostgreSQL is the evidence store used for reconstruction and controlled replay.** A trace can show what happened technically, but it does not automatically contain all the state required to reproduce a historical decision path.

---

## Runtime Components

### 1. Loan Support Agent

**Container:** `agent`  
**Port:** `8000`

Responsibilities:

- Accept customer requests
- Create session and trace context
- Classify customer intent
- Generate an execution plan
- Invoke downstream tools
- Apply lending-response policies
- Produce fallback behavior
- Run rule-based evaluations
- Persist replay evidence

### 2. Customer Profile API

**Container:** `customer-api`  
**Port:** `8001`

Represents a healthy downstream banking dependency. It returns the customer information required by the loan-assessment workflow.

### 3. Risk Assessment API

**Container:** `risk-api`  
**Port:** `8002`

Performs the simulated underwriting decision and supports controlled failure modes:

- `none`: healthy response
- `risk_timeout`: response delay exceeding the agent timeout
- `malformed`: HTTP success with an invalid response schema

This service is the primary fault-injection point for reliability testing.

### 4. OpenTelemetry Collector

**Container:** `otel-collector`  
**Ports:** `4317` for OTLP/gRPC, `4318` for OTLP/HTTP, `13133` for health

Responsibilities:

- Receive OTLP telemetry
- Apply configured privacy filtering
- Protect memory usage
- Batch spans
- Export traces to Jaeger
- Emit development debug telemetry

### 5. Jaeger

**Container:** `jaeger`  
**UI port:** `16686`

Provides investigation of:

- Distributed traces
- Parent-child span relationships
- Tool and API calls
- Latency and error evidence
- Execution waterfalls

### 6. PostgreSQL

**Container:** `postgres`  
**Port:** `5432`

Persists:

- Sessions
- Ordered execution events
- Evaluations
- Replay envelopes
- Policy versions
- Replay runs
- Before-and-after comparisons

---

## Technology Stack

- **Application language:** Python 3.12
- **API framework:** FastAPI
- **HTTP client:** httpx
- **Tracing:** OpenTelemetry Python SDK
- **Telemetry protocol:** OTLP/HTTP
- **Telemetry gateway:** OpenTelemetry Collector Contrib
- **Trace backend:** Jaeger
- **Evidence store:** PostgreSQL 16
- **ORM:** SQLAlchemy
- **Database driver:** psycopg
- **Testing:** pytest
- **Runtime:** Docker and Docker Compose

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
|       `-- config.py
|-- customer-api/
|   |-- Dockerfile
|   |-- requirements.txt
|   `-- app/
|       |-- main.py
|       `-- telemetry.py
|-- risk-api/
|   |-- Dockerfile
|   |-- requirements.txt
|   `-- app/
|       |-- main.py
|       `-- telemetry.py
|-- otel-collector/
|   `-- config.yaml
|-- scripts/
|   |-- healthy-run.sh
|   |-- timeout-run.sh
|   |-- reconstruct.sh
|   `-- counterfactual.sh
|-- tests/
|   |-- requirements.txt
|   `-- test_policy_and_replay.py
|-- docs/
|   |-- ARCHITECTURE.md
|   `-- ACCEPTANCE-CRITERIA.md
|-- docker-compose.yml
|-- .env.example
|-- Makefile
|-- SECURITY.md
|-- VALIDATION.md
`-- README.md
```

---

## Getting Started

### Prerequisites

- Ubuntu 22.04 or later, or a compatible Linux environment
- Docker Engine
- Docker Compose v2
- `curl`
- Git
- Python 3 for JSON formatting and local tests

### Clone the repository

```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/ai-agent-observability-replay.git
cd ai-agent-observability-replay
```

### Create local configuration

```bash
cp .env.example .env
```

The `.env` file is excluded by `.gitignore`. Do not commit passwords, tokens, private keys, or real customer data.

### Ensure utility scripts are executable

Files copied from Windows may not retain Linux executable permissions.

```bash
chmod +x scripts/*.sh
```

### Ubuntu Python command

The scripts should use `python3 -m json.tool`. If they contain `python -m json.tool`, update them:

```bash
sed -i 's/python -m json.tool/python3 -m json.tool/g' scripts/*.sh
```

---

## Start the Platform

### Validate the Compose definition

```bash
docker compose config
```

### Build application images

```bash
docker compose build
```

### Start all six containers

```bash
docker compose up -d
```

### Verify the runtime

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

PostgreSQL should eventually report `healthy`.

### View startup logs

```bash
docker compose logs --tail=50 agent
docker compose logs --tail=50 customer-api
docker compose logs --tail=50 risk-api
docker compose logs --tail=50 otel-collector
docker compose logs --tail=50 jaeger
docker compose logs --tail=50 postgres
```

---

## Verify Service Health

### Loan Support Agent

```bash
curl -sS http://localhost:8000/health | python3 -m json.tool
```

### Customer Profile API

```bash
curl -sS http://localhost:8001/health | python3 -m json.tool
```

### Risk Assessment API

```bash
curl -sS http://localhost:8002/health | python3 -m json.tool
```

Expected structure:

```json
{
  "status": "ok",
  "service": "service-name"
}
```

---

## Scenario 1: Healthy Agent Execution

Execute the predefined healthy request:

```bash
./scripts/healthy-run.sh
```

Expected high-level outcome:

```text
Agent outcome            SUCCESS
Customer Profile API     PASS
Risk Assessment API      PASS
Task completion          PASS
Tool execution           PASS
Policy compliance        PASS
Fallback effectiveness   PASS
```

Example response structure:

```json
{
  "session_id": "sess-generated-id",
  "conversation_id": "conv-healthy-001",
  "trace_id": "generated-otel-trace-id",
  "status": "success",
  "response": "Your request is eligible for a loan limit up to $45,000, subject to final verification.",
  "evaluations": {
    "task_completion": {
      "score": 1.0,
      "label": "pass"
    },
    "tool_execution": {
      "score": 1.0,
      "label": "pass"
    },
    "policy_compliance": {
      "score": 1.0,
      "label": "pass"
    },
    "fallback_effectiveness": {
      "score": 1.0,
      "label": "pass"
    }
  }
}
```

---

## Inspect the Distributed Trace

Open Jaeger locally:

```text
http://localhost:16686
```

If the platform runs on a remote VM, create an SSH tunnel from your local workstation:

```bash
ssh -L 16686:localhost:16686 USER@REMOTE_HOST
```

Then open:

```text
http://localhost:16686
```

In Jaeger:

1. Select `loan-support-agent`.
2. Search for recent traces.
3. Open the latest trace.
4. Inspect the agent, tool, HTTP, policy, evaluation, and response spans.

Expected logical hierarchy:

```text
agent.run
|-- agent.intent.classify
|-- agent.plan
|-- tool.customer_profile
|   `-- HTTP GET
|-- tool.risk_assessment
|   `-- HTTP POST
|-- guardrail.lending_response
|-- evaluation.task_completion
|-- evaluation.tool_execution
|-- evaluation.policy_compliance
|-- evaluation.fallback_effectiveness
`-- agent.response
```

Additional FastAPI and HTTP spans may appear because framework-level auto-instrumentation is enabled.

---

## Scenario 2: Risk Assessment Timeout

Before running the scenario, predict the expected behavior:

```text
Customer Profile API     PASS
Risk Assessment API      FAIL
Fallback                 ACTIVATED
Task completion          DEGRADED
Tool execution           FAIL
Policy compliance        PASS
Customer outcome         DEGRADED BUT SAFE
```

Execute:

```bash
./scripts/timeout-run.sh
```

Expected response characteristics:

- Overall status is `degraded`.
- Risk Assessment fails because the configured client timeout is exceeded.
- The customer receives a manual-review response.
- Tool execution evaluates to `fail`.
- Task completion evaluates to `degraded`.
- Policy compliance remains `pass`.

In Jaeger, inspect `tool.risk_assessment` and verify:

- Error status
- Timeout duration
- Error type
- Healthy Customer Profile span
- Agent fallback span
- Safe final response

---

## Reliability Insight

A technical dependency failure does not automatically mean the agent behaved unsafely.

```text
Risk API                    FAILED
Tool execution              FAILED
Task completion             DEGRADED
Policy compliance           PASSED
Fallback effectiveness      PASSED
Customer outcome            SAFE ESCALATION
```

This project treats reliability as more than infrastructure availability:

> **AI agent reliability = system reliability + agent behavior + quality evaluation + safe business outcome.**

---

## Inspect Stored Evidence

### List sessions

```bash
curl -sS http://localhost:8000/sessions | python3 -m json.tool
```

### Retrieve one session

```bash
curl -sS http://localhost:8000/sessions/SESSION_ID | python3 -m json.tool
```

### Retrieve the execution timeline

```bash
curl -sS \
  http://localhost:8000/sessions/SESSION_ID/timeline \
  | python3 -m json.tool
```

### Retrieve evaluation results

```bash
curl -sS \
  http://localhost:8000/sessions/SESSION_ID/evaluations \
  | python3 -m json.tool
```

Replace `SESSION_ID` with the identifier returned by `/agent/run`.

This evidence is persisted independently from Jaeger.

---

## Historical Reconstruction

Run:

```bash
./scripts/reconstruct.sh SESSION_ID
```

Historical reconstruction reads recorded execution evidence and presents the ordered timeline:

```text
Customer Request
      |
      v
Intent Classification
      |
      v
Agent Plan
      |
      v
Customer Profile API
      |
      v
Risk Assessment API
      |
      v
Failure or Success
      |
      v
Fallback and Policy
      |
      v
Final Response
```

Historical reconstruction does **not** call external services again. It answers:

> What happened during the recorded interaction?

It should not be confused with deterministic model re-execution.

---

## Controlled and Counterfactual Replay

### Controlled replay

```bash
curl -sS -X POST \
  http://localhost:8000/sessions/SESSION_ID/replay \
  -H 'Content-Type: application/json' \
  -d '{"policy_version":"1.0.0"}' \
  | python3 -m json.tool
```

Controlled replay re-applies the selected decision policy using recorded tool outcomes. It does not invoke the live Customer or Risk APIs.

### Counterfactual replay

```bash
./scripts/counterfactual.sh SESSION_ID
```

The counterfactual compares:

```text
ORIGINAL

Policy v1
   |
Risk API timeout
   |
Manual review
   |
DEGRADED


COUNTERFACTUAL

Policy v2
   |
Same recorded Risk API timeout
   |
Permitted cached classification
   |
Provisional response + mandatory review
   |
DEGRADED_SUCCESS
```

The original request and tool outcomes remain the same. Only the policy changes, enabling a controlled comparison of customer outcomes.

---

## Agent Evaluations

The initial implementation uses transparent rule-based evaluators.

### Task completion

Answers:

> Did the customer receive a verified decision or an approved escalation path?

Possible labels:

- `pass`
- `degraded`
- `fail`

### Tool execution

Answers:

> Did the required downstream tools complete successfully?

### Policy compliance

Answers:

> Did the agent avoid fabricating a lending decision when risk evidence was unavailable?

### Fallback effectiveness

Answers:

> Did degraded execution still provide a usable next action?

Every evaluation includes:

- Name
- Numeric score
- Label
- Explanation
- Evaluator version

---

## Telemetry Privacy

Raw customer financial data is deliberately excluded from normal trace attributes.

Traces use a stable salted reference:

```text
app.customer.ref_hash
```

The Collector also removes configured sensitive attribute names, including examples such as:

```text
customer.name
customer.account_number
customer.annual_income
customer.credit_score
gen_ai.input.messages
gen_ai.output.messages
```

### Trace backend versus replay store

**Jaeger contains operational telemetry:**

- Trace ID
- Span names
- Services
- Duration
- Error category
- Tool name
- HTTP status
- Hashed correlation ID

**PostgreSQL contains controlled replay evidence:**

- Session and conversation references
- Agent and policy versions
- Ordered execution events
- Recorded tool outcomes
- Evaluation evidence
- Historical outcome
- Replay comparisons

The current lab database is not production hardened. A production implementation requires encryption, RBAC, key management, purpose-based access, data classification, retention, and deletion controls.

---

## Automated Tests

The repository includes lightweight unit tests for policy and replay behavior.

Create a local virtual environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r tests/requirements.txt
```

Run:

```bash
pytest -q
```

The tests currently validate:

- Policy v1 produces safe degradation after a timeout.
- Policy v2 produces a qualified provisional response.
- Historical reconstruction performs no external calls.
- Counterfactual replay reuses recorded tool outcomes.

---

## Troubleshooting

### Script permission denied

Files copied from Windows may not retain executable permissions.

```bash
chmod +x scripts/*.sh
```

### `python: command not found`

Use `python3` on Ubuntu:

```bash
sed -i 's/python -m json.tool/python3 -m json.tool/g' scripts/*.sh
```

### JSON formatter reports `Expecting value`

This usually means the upstream HTTP request returned an empty or non-JSON error response.

Check service health:

```bash
curl -i http://localhost:8000/health
```

Inspect agent logs:

```bash
docker compose logs agent --tail=100
```

Run the request without JSON formatting to see the raw HTTP response:

```bash
curl -i -X POST http://localhost:8000/agent/run \
  -H 'Content-Type: application/json' \
  -d '{
    "customer_reference":"CUST-98421",
    "conversation_id":"conv-debug-001",
    "query":"Please check whether I can increase my personal loan limit from 20000 to 45000.",
    "requested_limit":45000,
    "failure_mode":"none",
    "policy_version":"1.0.0"
  }'
```

### PostgreSQL foreign-key violation while inserting evaluations

If evaluations are inserted before the parent session becomes visible, PostgreSQL can reject the transaction.

The session must be added and flushed before inserting dependent events and evaluations:

```python
db.add(session_record)
db.flush()

# Insert execution events and evaluations after the parent row exists.
```

After changing agent code, rebuild only the agent container:

```bash
docker compose up -d --build agent
```

### Risk service unavailable

Stop the service:

```bash
docker compose stop risk-api
```

Execute a request and inspect whether the agent distinguishes dependency unavailability from timeout behavior.

Restart:

```bash
docker compose start risk-api
```

### Collector unavailable

```bash
docker compose stop otel-collector
./scripts/healthy-run.sh
docker compose start otel-collector
```

The business transaction should remain independent from telemetry availability, although trace delivery may be lost in this development configuration.

### View all runtime logs

```bash
docker compose logs -f agent customer-api risk-api otel-collector jaeger postgres
```

---

## Acceptance Criteria

The initial implementation is complete when:

- [ ] All six containers start successfully.
- [ ] PostgreSQL reports healthy.
- [ ] All three application health endpoints return HTTP 200.
- [ ] A healthy request returns `success`.
- [ ] One request produces one correlated distributed trace.
- [ ] The Collector receives and exports telemetry.
- [ ] Jaeger displays agent, tool, and API spans.
- [ ] A controlled Risk timeout produces an error span.
- [ ] The customer receives a safe degraded response.
- [ ] Task, tool, policy, and fallback evaluations are persisted.
- [ ] The timeline can be reconstructed without calling live tools.
- [ ] Policy v2 can be compared against the original Policy v1 result.
- [ ] Raw customer financial data is absent from normal trace attributes.
- [ ] The operator can explain the complete architecture without reading the code.

See `docs/ACCEPTANCE-CRITERIA.md` for the shorter project checklist.

---

## Current Limitations

- The initial agent is deterministic and rule-based rather than LLM-driven.
- All banking data and services are simulated.
- Authentication and authorization are not implemented.
- Replay artifacts are not encrypted with production key management.
- High availability and horizontal scaling are not implemented.
- Production retention and deletion policies are not enforced.
- Replay is policy re-execution using captured state, not full deterministic model replay.
- RCA is evidence-driven and operator-led rather than AI-generated.
- Fault injection is application-controlled rather than managed by a chaos-engineering platform.
- Deployment uses Docker Compose rather than Kubernetes.
- Telemetry buffering and delivery guarantees are development-grade.

This project should be described as a **production-oriented reference architecture and hands-on implementation**, not as a production-ready banking platform.

---

## Roadmap

### Phase 2: Real model integration

- Add a real or local LLM provider
- Trace model invocation and token usage
- Record model and prompt versions
- Add output grounding and response-quality evaluations
- Define token and cost SLIs

### Phase 3: Evaluation release gate

- Build a version-controlled golden dataset
- Compare Agent v17 and v18
- Add deterministic and model-assisted evaluators
- Add DeepEval
- Integrate evaluation checks with CI/CD
- Generate automated PASS/BLOCK release decisions

### Phase 4: RAG reliability

- Add retrieval and vector-search components
- Trace query, retrieval, context, and generation
- Measure retrieval relevance and groundedness
- Add Ragas-based evaluation
- Introduce controlled retrieval degradation
- Correlate quality regressions with version changes

### Phase 5: Enterprise hardening

- Authentication and role-based access
- TLS and mTLS
- Secret management
- Encrypted replay storage
- Retention and deletion controls
- Kubernetes deployment
- Scalable Collector gateway pattern
- Production alerting and incident integration

---

## Why This Project Exists

The goal is not to demonstrate another AI chatbot.

The objective is to explore the operational engineering required to run AI agents reliably in enterprise environments:

- How do we observe what an agent actually did?
- How do we identify the component responsible for failure?
- How do we distinguish technical success from business-task success?
- How do we evaluate agent behavior independently from infrastructure health?
- How do we reconstruct historical interactions?
- How do we test whether a proposed policy improves the outcome?
- How do we prevent observability from becoming another repository of sensitive enterprise data?

The operating lifecycle demonstrated by this repository is:

```text
Observe
   |
Evaluate
   |
Diagnose
   |
Reconstruct
   |
Improve
   |
Verify
```

This reference implementation explores the intersection of:

- Enterprise Architecture
- Site Reliability Engineering
- OpenTelemetry
- Distributed tracing
- AI Agent Reliability
- Agent Observability
- AI Evaluation
- Replay and counterfactual analysis

---

## License

This project is licensed under the MIT License. See `LICENSE` for details.
