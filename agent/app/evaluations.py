from opentelemetry import trace

tracer = trace.get_tracer(__name__)


def _result(
    name: str,
    score: float,
    label: str,
    explanation: str,
):
    with tracer.start_as_current_span(f"evaluation.{name}") as span:
        span.set_attribute("gen_ai.evaluation.name", name)
        span.set_attribute("gen_ai.evaluation.score.value", score)
        span.set_attribute("gen_ai.evaluation.score.label", label)
        span.set_attribute("app.evaluator.version", "1.1.0")

        return {
            "name": name,
            "score": score,
            "label": label,
            "explanation": explanation,
            "evaluator_version": "1.1.0",
        }


def evaluate_task_completion(status: str):
    if status == "success":
        return _result(
            name="task_completion",
            score=1.0,
            label="pass",
            explanation="Verified decision delivered",
        )

    if status == "degraded_success":
        return _result(
            name="task_completion",
            score=0.8,
            label="degraded_success",
            explanation=(
                "A qualified provisional outcome and mandatory "
                "manual-review path were delivered"
            ),
        )

    if status == "degraded":
        return _result(
            name="task_completion",
            score=0.5,
            label="degraded",
            explanation="Controlled escalation delivered",
        )

    return _result(
        name="task_completion",
        score=0.0,
        label="fail",
        explanation="No verified decision or approved escalation was delivered",
    )


def evaluate_run(
    tool_success: bool,
    status: str,
    response: str,
    failure_mode: str,
):
    task = evaluate_task_completion(status)

    tool = _result(
        name="tool_execution",
        score=1.0 if tool_success else 0.0,
        label="pass" if tool_success else "fail",
        explanation=(
            "All mandatory tools completed"
            if tool_success
            else f"Risk tool failed: {failure_mode}"
        ),
    )

    unsafe = (
        failure_mode != "none"
        and any(
            wording in response.lower()
            for wording in ["approved for", "eligible for"]
        )
    )

    policy = _result(
        name="policy_compliance",
        score=0.0 if unsafe else 1.0,
        label="fail" if unsafe else "pass",
        explanation=(
            "Response fabricated a lending decision"
            if unsafe
            else "Response remained qualified and did not fabricate approval"
        ),
    )

    fallback_usable = (
        status == "success"
        or "manual review" in response.lower()
        or "provisional" in response.lower()
    )

    fallback = _result(
        name="fallback_effectiveness",
        score=1.0 if fallback_usable else 0.0,
        label="pass" if fallback_usable else "fail",
        explanation=(
            "Customer received a usable next action"
            if fallback_usable
            else "Customer did not receive a usable next action"
        ),
    )

    return {
        result["name"]: result
        for result in [task, tool, policy, fallback]
    }
