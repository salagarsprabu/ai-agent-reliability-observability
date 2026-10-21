from datetime import datetime, timezone
from sqlalchemy import create_engine, String, Integer, Float, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .config import DATABASE_URL


class Base(DeclarativeBase):
    pass


class SessionRecord(Base):
    __tablename__ = "sessions"
    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(128), index=True)
    customer_ref_hash: Mapped[str] = mapped_column(String(64), index=True)
    query: Mapped[str] = mapped_column(Text)
    agent_name: Mapped[str] = mapped_column(String(100))
    agent_version: Mapped[str] = mapped_column(String(32))
    policy_version: Mapped[str] = mapped_column(String(32))
    failure_mode: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32))
    final_response: Mapped[str] = mapped_column(Text)
    replay_envelope: Mapped[dict] = mapped_column(JSON)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EventRecord(Base):
    __tablename__ = "execution_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.session_id"), index=True)
    sequence_number: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(64))
    component_name: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32))
    duration_ms: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class EvaluationRecord(Base):
    __tablename__ = "evaluations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.session_id"), index=True)
    evaluation_name: Mapped[str] = mapped_column(String(100))
    score: Mapped[float] = mapped_column(Float)
    label: Mapped[str] = mapped_column(String(32))
    explanation: Mapped[str] = mapped_column(Text)
    evaluator_version: Mapped[str] = mapped_column(String(32), default="1.0.0")


class ReplayRun(Base):
    __tablename__ = "replay_runs"
    replay_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_session_id: Mapped[str] = mapped_column(ForeignKey("sessions.session_id"), index=True)
    replay_type: Mapped[str] = mapped_column(String(32))
    policy_version: Mapped[str] = mapped_column(String(32))
    outcome: Mapped[str] = mapped_column(String(32))
    comparison_result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db():
    Base.metadata.create_all(engine)
