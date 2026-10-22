import sys
from app.evaluations import evaluate_task_completion
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / "agent"))

from app.policy import build_response
from app.replay import reconstruct, controlled_replay


def test_policy_v1_timeout_is_safe_degraded():
    customer = {"credit_score": 780}
    status, response = build_response("1.0.0", None, customer, "risk_timeout")
    assert status == "degraded"
    assert "manual review" in response.lower()
    assert "approved for" not in response.lower()


def test_policy_v2_counterfactual_is_provisional():
    customer = {"credit_score": 780}
    status, response = build_response("2.0.0", None, customer, "risk_timeout")
    assert status == "degraded_success"
    assert "provisionally" in response.lower()
    assert "manual review" in response.lower()


def sample_envelope():
    return {
        "session_id": "sess-1", "trace_id": "trace-1",
        "policy": {"version": "1.0.0"},
        "recorded_state": {"customer_profile": {"credit_score": 780}, "risk_assessment": None, "failure_reason": "risk_timeout"},
        "events": [{"sequence_number": 1, "event_type": "tool_call", "component_name": "risk-assessment", "status": "failed", "duration_ms": 2000}],
        "evaluations": {"task_completion": {"score": 0.5}},
        "final_outcome": {"status": "degraded", "response": "Manual review"},
    }


def test_reconstruction_does_not_call_services():
    result = reconstruct(sample_envelope())
    assert result["external_services_called"] is False
    assert result["timeline"][0]["status"] == "failed"


def test_counterfactual_reuses_recorded_outcomes():
    _, outcome, _, comparison = controlled_replay(sample_envelope(), "2.0.0")
    assert outcome == "degraded_success"
    assert comparison["same_recorded_tool_outcomes"] is True
    assert comparison["external_services_called"] is False
def test_degraded_success_has_higher_task_score():
    result = evaluate_task_completion("degraded_success")

    assert result["score"] == 0.8
    assert result["label"] == "degraded_success"
    assert result["evaluator_version"] == "1.1.0"


def test_degraded_has_partial_task_score():
    result = evaluate_task_completion("degraded")

    assert result["score"] == 0.5
    assert result["label"] == "degraded"
