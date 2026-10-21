import uuid
from .policy import build_response
from .evaluations import evaluate_run


def reconstruct(envelope: dict):
    return {
        "mode": "historical_reconstruction",
        "session_id": envelope["session_id"],
        "trace_id": envelope["trace_id"],
        "timeline": [
            {
                "sequence": e["sequence_number"],
                "event": e["event_type"],
                "component": e["component_name"],
                "status": e["status"],
                "duration_ms": e["duration_ms"],
            }
            for e in envelope["events"]
        ],
        "outcome": envelope["final_outcome"],
        "external_services_called": False,
    }


def controlled_replay(envelope: dict, policy_version: str):
    customer = envelope["recorded_state"]["customer_profile"]
    risk_result = envelope["recorded_state"].get("risk_assessment")
    failure_reason = envelope["recorded_state"].get("failure_reason")
    outcome, response = build_response(policy_version, risk_result, customer, failure_reason)
    evaluations = evaluate_run(risk_result is not None, outcome, response, failure_reason or "none")
    original = envelope["final_outcome"]
    comparison = {
        "original": original,
        "replay": {"status": outcome, "response": response, "policy_version": policy_version},
        "changed": {
            "policy_version": [envelope["policy"]["version"], policy_version],
            "status": [original["status"], outcome],
            "task_completion_score": [envelope["evaluations"]["task_completion"]["score"], evaluations["task_completion"]["score"]],
        },
        "same_recorded_tool_outcomes": True,
        "external_services_called": False,
    }
    return f"replay-{uuid.uuid4().hex[:12]}", outcome, evaluations, comparison
