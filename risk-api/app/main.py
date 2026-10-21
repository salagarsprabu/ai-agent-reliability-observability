import asyncio
import os
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from .telemetry import configure_tracing

configure_tracing("risk-assessment-api")
app = FastAPI(title="Risk Assessment API", version="0.1.0")
FastAPIInstrumentor.instrument_app(app)
tracer = trace.get_tracer(__name__)


class RiskRequest(BaseModel):
    customer_ref_hash: str
    current_limit: int
    requested_limit: int
    annual_income: int
    total_debt: int
    credit_score: int


@app.get("/health")
def health():
    return {"status": "ok", "service": "risk-assessment-api"}


@app.post("/risk/evaluate")
async def evaluate(request: RiskRequest, x_failure_mode: str = Header(default="none")):
    with tracer.start_as_current_span("risk.evaluate") as span:
        span.set_attribute("app.customer.ref_hash", request.customer_ref_hash)
        span.set_attribute("app.risk.policy_version", "risk-model-1.0.0")
        if x_failure_mode == "risk_timeout":
            await asyncio.sleep(float(os.getenv("RISK_TIMEOUT_SECONDS", "3")))
            span.set_attribute("http.response.status_code", 504)
            span.set_attribute("error.type", "RiskAssessmentTimeout")
            span.set_attribute("app.tool.outcome", "failed")
            span.set_status(Status(StatusCode.ERROR, "Controlled risk-assessment timeout"))
            raise HTTPException(504, "RISK_ASSESSMENT_TIMEOUT")
        if x_failure_mode == "malformed":
            return {"unexpected": "shape"}

        debt_ratio = request.total_debt / max(request.annual_income, 1)
        eligible = request.credit_score >= 720 and debt_ratio < 0.35
        approved = request.requested_limit if eligible else request.current_limit
        result = {
            "decision": "eligible" if eligible else "manual_review",
            "risk_score": round((1 - min(request.credit_score / 850, 1)) + debt_ratio, 3),
            "approved_limit": approved,
            "reason_codes": ["HIGH_CREDIT_SCORE", "LOW_DEBT_TO_INCOME"] if eligible else ["MANUAL_REVIEW_REQUIRED"],
        }
        span.set_attribute("app.tool.outcome", "success")
        span.set_attribute("app.risk.decision", result["decision"])
        return result
