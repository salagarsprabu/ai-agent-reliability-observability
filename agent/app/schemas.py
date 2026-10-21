from typing import Literal, Any
from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    customer_reference: str = "CUST-98421"
    conversation_id: str
    query: str
    requested_limit: int = Field(default=45000, gt=0)
    failure_mode: Literal["none", "risk_timeout", "malformed"] = "none"
    policy_version: Literal["1.0.0", "2.0.0"] = "1.0.0"


class ReplayRequest(BaseModel):
    policy_version: Literal["1.0.0", "2.0.0"] = "1.0.0"


class AgentRunResponse(BaseModel):
    session_id: str
    conversation_id: str
    trace_id: str
    status: str
    response: str
    evaluations: dict[str, Any]
