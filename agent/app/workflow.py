import hashlib
import time
import uuid
import httpx
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from .config import CUSTOMER_API_URL, RISK_API_URL, RISK_CLIENT_TIMEOUT_SECONDS, CUSTOMER_HASH_SALT, AGENT_NAME, AGENT_VERSION
from .policy import build_response
from .evaluations import evaluate_run

tracer = trace.get_tracer(__name__)


def hash_customer(value: str) -> str:
    return hashlib.sha256(f"{CUSTOMER_HASH_SALT}:{value}".encode()).hexdigest()[:20]


def event(seq, etype, component, status, started, payload=None):
    return {
        "sequence_number": seq,
        "event_type": etype,
        "component_name": component,
        "status": status,
        "duration_ms": round((time.perf_counter() - started) * 1000),
        "payload": payload or {},
    }


async def execute(req, session_id: str):
    events = []
    customer_ref_hash = hash_customer(req.customer_reference)
    with tracer.start_as_current_span("agent.intent.classify") as span:
        started = time.perf_counter()
        intent = "credit_limit_increase" if "limit" in req.query.lower() else "unknown"
        span.set_attribute("app.intent", intent)
        events.append(event(1, "intent_classification", "agent", "success", started, {"intent": intent}))

    with tracer.start_as_current_span("agent.plan") as span:
        started = time.perf_counter()
        plan = ["customer-profile", "risk-assessment", "lending-policy"]
        span.set_attribute("app.plan.tool_count", len(plan))
        events.append(event(2, "agent_plan", "agent", "success", started, {"plan": plan}))

    async with httpx.AsyncClient() as client:
        with tracer.start_as_current_span("tool.customer_profile") as span:
            started = time.perf_counter()
            span.set_attribute("gen_ai.tool.name", "customer-profile")
            span.set_attribute("gen_ai.tool.call.id", f"tool-{uuid.uuid4().hex[:12]}")
            span.set_attribute("app.customer.ref_hash", customer_ref_hash)
            response = await client.get(f"{CUSTOMER_API_URL}/customers/{req.customer_reference}", timeout=5)
            response.raise_for_status()
            customer = response.json()
            span.set_attribute("app.tool.outcome", "success")
            events.append(event(3, "tool_call", "customer-profile", "success", started, {"http_status": response.status_code, "recorded_output": customer}))

        risk_result = None
        failure_reason = None
        with tracer.start_as_current_span("tool.risk_assessment") as span:
            started = time.perf_counter()
            span.set_attribute("gen_ai.tool.name", "risk-assessment")
            span.set_attribute("gen_ai.tool.call.id", f"tool-{uuid.uuid4().hex[:12]}")
            span.set_attribute("app.customer.ref_hash", customer_ref_hash)
            risk_payload = {
                "customer_ref_hash": customer_ref_hash,
                "current_limit": customer["current_limit"],
                "requested_limit": req.requested_limit,
                "annual_income": customer["annual_income"],
                "total_debt": customer["total_debt"],
                "credit_score": customer["credit_score"],
            }
            try:
                risk_response = await client.post(
                    f"{RISK_API_URL}/risk/evaluate",
                    json=risk_payload,
                    headers={"X-Failure-Mode": req.failure_mode},
                    timeout=RISK_CLIENT_TIMEOUT_SECONDS,
                )
                risk_response.raise_for_status()
                candidate = risk_response.json()
                required = {"decision", "risk_score", "approved_limit", "reason_codes"}
                if not required.issubset(candidate):
                    raise ValueError("Malformed risk response")
                risk_result = candidate
                span.set_attribute("app.tool.outcome", "success")
                events.append(event(4, "tool_call", "risk-assessment", "success", started, {"http_status": risk_response.status_code, "recorded_output": risk_result}))
            except (httpx.TimeoutException, httpx.RequestError, httpx.HTTPStatusError, ValueError) as exc:
                failure_reason = "risk_timeout" if isinstance(exc, httpx.TimeoutException) else ("risk_unavailable" if isinstance(exc, httpx.RequestError) else "invalid_or_error_response")
                status_code = 504 if failure_reason == "risk_timeout" else (503 if failure_reason == "risk_unavailable" else 502)
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                span.set_attribute("error.type", type(exc).__name__)
                span.set_attribute("http.response.status_code", status_code)
                span.set_attribute("app.tool.outcome", "failed")
                events.append(event(4, "tool_call", "risk-assessment", "failed", started, {"http_status": status_code, "error": failure_reason}))

    if risk_result is None:
        with tracer.start_as_current_span("agent.fallback") as span:
            started = time.perf_counter()
            span.set_attribute("app.policy.version", req.policy_version)
            events.append(event(5, "fallback", "agent", "success", started, {"policy_version": req.policy_version, "reason": failure_reason}))

    with tracer.start_as_current_span("guardrail.lending_response") as span:
        started = time.perf_counter()
        outcome, final_response = build_response(req.policy_version, risk_result, customer, failure_reason)
        span.set_attribute("app.policy.version", req.policy_version)
        span.set_attribute("app.guardrail.result", "pass")
        events.append(event(6, "policy_check", "lending-policy", "pass", started, {"policy_version": req.policy_version}))

    evaluations = evaluate_run(risk_result is not None, outcome, final_response, failure_reason or "none")
    with tracer.start_as_current_span("agent.response") as span:
        started = time.perf_counter()
        span.set_attribute("app.agent.outcome", outcome)
        span.set_attribute("app.session.id", session_id)
        events.append(event(7, "agent_response", "agent", outcome, started, {"response": final_response}))

    return {
        "customer_ref_hash": customer_ref_hash,
        "intent": intent,
        "status": outcome,
        "response": final_response,
        "events": events,
        "evaluations": evaluations,
        "recorded_customer": customer,
        "recorded_risk": risk_result,
        "failure_reason": failure_reason,
        "agent": {"name": AGENT_NAME, "version": AGENT_VERSION},
    }
