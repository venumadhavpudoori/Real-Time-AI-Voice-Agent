from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models.audit_log import SafetyAuditLog
from app.schemas.guardrail import AuditLogResponse, GuardrailStatsResponse
from app.guardrails import safety_pipeline

router = APIRouter(prefix="/guardrails", tags=["Safety Guardrails"])


class GuardrailTestRequest(BaseModel):
    text: str


@router.get("/logs", response_model=List[AuditLogResponse])
async def get_audit_logs(
    limit: int = Query(50, le=200),
    event_type: str = Query(None),
    risk_level: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """View recent safety audit events (PII redactions, allergen escalations, interruptions)."""
    stmt = select(SafetyAuditLog).order_by(SafetyAuditLog.created_at.desc()).limit(limit)
    if event_type:
        stmt = stmt.where(SafetyAuditLog.event_type == event_type)
    if risk_level:
        stmt = stmt.where(SafetyAuditLog.risk_level == risk_level.upper())

    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/stats", response_model=GuardrailStatsResponse)
async def get_guardrail_stats(db: AsyncSession = Depends(get_db)):
    """Aggregate statistics on safety guardrail interventions."""
    stmt = select(SafetyAuditLog)
    result = await db.execute(stmt)
    logs = result.scalars().all()

    total = len(logs)
    pii = sum(1 for l in logs if l.event_type == "PII_REDACTION")
    allergy = sum(1 for l in logs if "ALLERGY" in l.event_type)
    injections = sum(1 for l in logs if "INJECTION" in l.event_type)
    interruptions = sum(1 for l in logs if l.event_type == "INTERRUPTION")

    risk_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    for l in logs:
        if l.risk_level in risk_counts:
            risk_counts[l.risk_level] += 1

    return GuardrailStatsResponse(
        total_events=total,
        pii_redactions=pii,
        allergy_escalations=allergy,
        prompt_injections=injections,
        interruptions=interruptions,
        risk_breakdown=risk_counts
    )


@router.post("/test")
async def test_guardrails(
    payload: GuardrailTestRequest,
    db: AsyncSession = Depends(get_db)
):
    """Test string against active safety guardrails."""
    return await safety_pipeline.process_input(payload.text, db=db)

