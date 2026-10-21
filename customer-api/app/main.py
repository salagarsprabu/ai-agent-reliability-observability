import hashlib
import os
from fastapi import FastAPI, HTTPException
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from .telemetry import configure_tracing

configure_tracing("customer-profile-api")
app = FastAPI(title="Customer Profile API", version="0.1.0")
FastAPIInstrumentor.instrument_app(app)
tracer = trace.get_tracer(__name__)

CUSTOMERS = {
    "CUST-98421": {
        "customer_reference": "CUST-98421",
        "current_limit": 20000,
        "annual_income": 115000,
        "total_debt": 18000,
        "credit_score": 780,
        "relationship_tier": "gold",
    }
}


def customer_hash(value: str) -> str:
    salt = os.getenv("CUSTOMER_HASH_SALT", "local")
    return hashlib.sha256(f"{salt}:{value}".encode()).hexdigest()[:20]


@app.get("/health")
def health():
    return {"status": "ok", "service": "customer-profile-api"}


@app.get("/customers/{customer_reference}")
def get_customer(customer_reference: str):
    with tracer.start_as_current_span("customer.profile.lookup") as span:
        span.set_attribute("app.customer.ref_hash", customer_hash(customer_reference))
        customer = CUSTOMERS.get(customer_reference)
        if not customer:
            span.set_attribute("app.tool.outcome", "not_found")
            raise HTTPException(404, "Customer not found")
        span.set_attribute("app.tool.outcome", "success")
        span.set_attribute("app.customer.relationship_tier", customer["relationship_tier"])
        return customer
