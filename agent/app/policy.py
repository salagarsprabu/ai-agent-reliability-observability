def build_response(policy_version: str, risk_result: dict | None, customer: dict, failure_reason: str | None):
    if risk_result:
        if risk_result["decision"] == "eligible":
            return "success", f"Your request is eligible for a loan limit up to ${risk_result['approved_limit']:,}, subject to final verification."
        return "degraded", "Your request requires manual review. A lending specialist will contact you with the next steps."

    if policy_version == "2.0.0" and customer.get("credit_score", 0) >= 760:
        return "degraded_success", "The automated risk service is temporarily unavailable. Based on the permitted cached risk classification, your request is provisionally eligible and has been sent for mandatory manual review."

    return "degraded", "The automated risk service is temporarily unavailable. Your request has been recorded for manual review."
