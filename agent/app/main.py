from datetime import datetime, timezone
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from opentelemetry import trace
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from sqlalchemy import select

from .config import AGENT_NAME, AGENT_VERSION
from .db import init_db, SessionLocal, SessionRecord, EventRecord, EvaluationRecord, ReplayRun
from .schemas import AgentRunRequest, AgentRunResponse, ReplayRequest
from .telemetry import configure_tracing, current_trace_id
from .workflow import execute
from .replay import reconstruct, controlled_replay

configure_tracing("loan-support-agent")
HTTPXClientInstrumentor().instrument()
tracer = trace.get_tracer(__name__)
app = FastAPI(title="AI Agent Observability, Replay and Evaluation Platform", version="0.1.0")


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok", "service": "loan-support-agent"}


@app.post("/agent/run", response_model=AgentRunResponse)
async def run_agent(req: AgentRunRequest):
    session_id = f"sess-{uuid.uuid4().hex[:12]}"
    started = datetime.now(timezone.utc)
    with tracer.start_as_current_span("agent.run") as span:
        span.set_attribute("gen_ai.agent.name", AGENT_NAME)
        span.set_attribute("gen_ai.agent.version", AGENT_VERSION)
        span.set_attribute("gen_ai.conversation.id", req.conversation_id)
        span.set_attribute("app.session.id", session_id)
        span.set_attribute("app.policy.version", req.policy_version)
        span.set_attribute("app.failure_mode", req.failure_mode)
        result = await execute(req, session_id)
        trace_id = current_trace_id()
        span.set_attribute("app.agent.outcome", result["status"])

        envelope = {
            "schema_version": "1.0",
            "session_id": session_id,
            "trace_id": trace_id,
            "conversation_id": req.conversation_id,
            "created_at": started.isoformat(),
            "agent": result["agent"],
            "model": {"provider": "rule-based-initial", "model": "none", "temperature": 0},
            "prompt": {"template_id": "loan-limit-assessment", "template_version": "1.0.0", "content": req.query},
            "policy": {"name": "loan-response-policy", "version": req.policy_version},
            "recorded_state": {
                "customer_profile": result["recorded_customer"],
                "risk_assessment": result["recorded_risk"],
                "failure_reason": result["failure_reason"],
            },
            "events": result["events"],
            "evaluations": result["evaluations"],
            "final_outcome": {"status": result["status"], "response": result["response"]},
        }

        with SessionLocal.begin() as db:
            db.add(SessionRecord(
                session_id=session_id, trace_id=trace_id, conversation_id=req.conversation_id,
                customer_ref_hash=result["customer_ref_hash"], query=req.query,
                agent_name=AGENT_NAME, agent_version=AGENT_VERSION, policy_version=req.policy_version,
                failure_mode=req.failure_mode, status=result["status"], final_response=result["response"],
                replay_envelope=envelope, started_at=started, completed_at=datetime.now(timezone.utc),
            ))
            db.flush()
            for item in result["events"]:
                db.add(EventRecord(session_id=session_id, **item))
            for item in result["evaluations"].values():
                db.add(EvaluationRecord(
                    session_id=session_id, evaluation_name=item["name"], score=item["score"],
                    label=item["label"], explanation=item["explanation"], evaluator_version=item["evaluator_version"],
                ))

    return AgentRunResponse(
        session_id=session_id, conversation_id=req.conversation_id, trace_id=trace_id,
        status=result["status"], response=result["response"], evaluations=result["evaluations"],
    )


@app.get("/sessions")
def list_sessions():
    with SessionLocal() as db:
        rows = db.scalars(select(SessionRecord).order_by(SessionRecord.started_at.desc())).all()
        return [{
            "session_id": r.session_id, "trace_id": r.trace_id, "conversation_id": r.conversation_id,
            "agent_version": r.agent_version, "policy_version": r.policy_version,
            "failure_mode": r.failure_mode, "status": r.status, "started_at": r.started_at,
        } for r in rows]


def get_session_or_404(db, session_id: str):
    row = db.get(SessionRecord, session_id)
    if not row:
        raise HTTPException(404, "Session not found")
    return row


@app.get("/sessions/{session_id}")
def get_session(session_id: str):
    with SessionLocal() as db:
        row = get_session_or_404(db, session_id)
        return row.replay_envelope


@app.get("/sessions/{session_id}/timeline")
def get_timeline(session_id: str):
    with SessionLocal() as db:
        get_session_or_404(db, session_id)
        rows = db.scalars(select(EventRecord).where(EventRecord.session_id == session_id).order_by(EventRecord.sequence_number)).all()
        return [{"sequence": r.sequence_number, "event": r.event_type, "component": r.component_name, "status": r.status, "duration_ms": r.duration_ms, "payload": r.payload} for r in rows]


@app.get("/sessions/{session_id}/evaluations")
def get_evaluations(session_id: str):
    with SessionLocal() as db:
        get_session_or_404(db, session_id)
        rows = db.scalars(select(EvaluationRecord).where(EvaluationRecord.session_id == session_id)).all()
        return [{"name": r.evaluation_name, "score": r.score, "label": r.label, "explanation": r.explanation, "evaluator_version": r.evaluator_version} for r in rows]


@app.post("/sessions/{session_id}/reconstruct")
def reconstruct_session(session_id: str):
    with SessionLocal() as db:
        row = get_session_or_404(db, session_id)
        return reconstruct(row.replay_envelope)


@app.post("/sessions/{session_id}/replay")
def replay_session(session_id: str, request: ReplayRequest):
    return _run_replay(session_id, request.policy_version, "controlled")


@app.post("/sessions/{session_id}/counterfactual")
def counterfactual_session(session_id: str, request: ReplayRequest):
    return _run_replay(session_id, request.policy_version, "counterfactual")


def _run_replay(session_id: str, policy_version: str, replay_type: str):
    with SessionLocal.begin() as db:
        row = get_session_or_404(db, session_id)
        replay_id, outcome, evaluations, comparison = controlled_replay(row.replay_envelope, policy_version)
        db.add(ReplayRun(replay_id=replay_id, source_session_id=session_id, replay_type=replay_type, policy_version=policy_version, outcome=outcome, comparison_result=comparison))
        return {"replay_id": replay_id, "outcome": outcome, "evaluations": evaluations, "comparison": comparison}


@app.get("/replays/{replay_id}/comparison")
def replay_comparison(replay_id: str):
    with SessionLocal() as db:
        row = db.get(ReplayRun, replay_id)
        if not row:
            raise HTTPException(404, "Replay not found")
        return row.comparison_result


@app.get("/", include_in_schema=False)
def root_ui():
    return RedirectResponse(url="/ui/")


app.mount("/ui", StaticFiles(directory="app/static", html=True), name="ui")
