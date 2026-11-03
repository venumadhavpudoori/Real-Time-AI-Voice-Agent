from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class SafetyAuditLog(Base):
    __tablename__ = "safety_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)  # PII_REDACTION, SEVERE_ALLERGY_DETECTED, PROMPT_INJECTION_ATTEMPT, TOOL_ERROR, INTERRUPTION
    raw_text_preview = Column(Text, nullable=True)               # Safe preview with high risk strings partially masked
    sanitized_text = Column(Text, nullable=True)
    risk_level = Column(String(20), nullable=False)              # LOW, MEDIUM, HIGH, CRITICAL
    action_taken = Column(String(100), nullable=False)           # REDACTED, WARNED_CUSTOMER, BLOCKED, ESCALATED_TO_KITCHEN
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    def __repr__(self):
        return f"<SafetyAuditLog {self.event_type} [{self.risk_level}]: {self.action_taken}>"
