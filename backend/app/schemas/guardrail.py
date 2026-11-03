from datetime import datetime
from typing import Optional, Dict
from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    id: int
    event_type: str
    raw_text_preview: Optional[str]
    sanitized_text: Optional[str]
    risk_level: str
    action_taken: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GuardrailStatsResponse(BaseModel):
    total_events: int
    pii_redactions: int
    allergy_escalations: int
    prompt_injections: int
    interruptions: int
    risk_breakdown: Dict[str, int]
