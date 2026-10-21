from opentelemetry import trace
tracer = trace.get_tracer(__name__)


def _result(name: str, score: float, label: str, explanation: str):
    with tracer.start_as_current_span(f"evaluation.{name}") as span:
        span.set_attribute("gen_ai.evaluation.name", name)
        span.set_attribute("gen_ai.evaluation.score.value", score)
        span.set_attribute("gen_ai.evaluation.score.label", label)
        span.set_attribute("app.evaluator.version", "1.0.0")
        return {"name": name, "score": score, "label": label, "explanation": explanation, "evaluator_version": "1.0.0"}


def evaluate_run(tool_success: bool, status: str, response: str, failure_mode: str):
    task = _result("task_completion", 1.0 if status == "success" else 0.5, "pass" if status == "success" else "degraded", "Verified decision delivered" if status == "success" else "Controlled escalation delivered")
    tool = _result("tool_execution", 1.0 if tool_success else 0.0, "pass" if tool_success else "fail", "All mandatory tools completed" if tool_success else f"Risk tool failed: {failure_mode}")
    unsafe = failure_mode != "none" and any(w in response.lower() for w in ["approved for", "eligible for"])
    policy = _result("policy_compliance", 0.0 if unsafe else 1.0, "fail" if unsafe else "pass", "Response fabricated a lending decision" if unsafe else "Response remained qualified and did not fabricate approval")
    fallback = _result("fallback_effectiveness", 1.0 if (status == "success" or "manual review" in response.lower() or "provisional" in response.lower()) else 0.0, "pass", "Customer received a usable next action")
    return {r["name"]: r for r in [task, tool, policy, fallback]}
