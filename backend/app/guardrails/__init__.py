import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.guardrails.sensitive_data import SensitiveDataGuardrail
from app.guardrails.allergen_safety import AllergenSafetyGuardrail
from app.guardrails.prompt_safety import PromptSafetyGuardrail
from app.models.audit_log import SafetyAuditLog

logger = logging.getLogger("voice_agent.guardrails")


class SafetyPipeline:
    def __init__(self):
        self.sensitive_guard = SensitiveDataGuardrail()
        self.allergen_guard = AllergenSafetyGuardrail()
        self.prompt_guard = PromptSafetyGuardrail()

    async def process_input(
        self, 
        text: str, 
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Runs full pre-processing guardrails on incoming user voice transcript:
        1. Prompt Injection & Malicious Pattern Check
        2. Sensitive Data & PII Redaction
        3. Dietary & Allergen Safety Analysis
        4. Audit Log Persistence
        """
        result = {
            "original_text": text,
            "processed_text": text,
            "is_blocked": False,
            "guardrail_events": [],
            "allergy_analysis": None,
            "highest_risk": "LOW"
        }

        # 1. Prompt Injection Check
        is_safe, replacement, injection_info = self.prompt_guard.inspect(text)
        if not is_safe:
            result["is_blocked"] = True
            result["processed_text"] = replacement
            result["highest_risk"] = "HIGH"
            result["guardrail_events"].append({
                "type": "PROMPT_INJECTION_ATTEMPT",
                "risk": "HIGH",
                "action": "BLOCKED",
                "details": injection_info
            })
            if db:
                await self._log_event(
                    db,
                    event_type="PROMPT_INJECTION_ATTEMPT",
                    raw_text=text[:200],
                    sanitized_text=replacement,
                    risk_level="HIGH",
                    action_taken="BLOCKED_AND_REDIRECTED"
                )
            return result

        # 2. PII / Sensitive Data Sanitization
        sanitized, pii_detections, pii_risk = self.sensitive_guard.sanitize_input(text)
        result["processed_text"] = sanitized
        if pii_detections:
            if pii_risk == "CRITICAL" or (pii_risk == "HIGH" and result["highest_risk"] != "CRITICAL"):
                result["highest_risk"] = pii_risk

            result["guardrail_events"].append({
                "type": "PII_REDACTION",
                "risk": pii_risk,
                "action": "REDACTED",
                "details": pii_detections
            })
            if db:
                await self._log_event(
                    db,
                    event_type="PII_REDACTION",
                    raw_text=text[:150] + "...",
                    sanitized_text=sanitized[:150] + "...",
                    risk_level=pii_risk,
                    action_taken="REDACTED_BEFORE_PROCESSING"
                )

        # 3. Dietary & Allergen Analysis
        allergy_data = self.allergen_guard.analyze_dietary_input(sanitized)
        result["allergy_analysis"] = allergy_data
        if allergy_data["has_allergy"]:
            allergy_risk = allergy_data["risk_level"]
            if allergy_risk == "CRITICAL" or (allergy_risk == "HIGH" and result["highest_risk"] != "CRITICAL"):
                result["highest_risk"] = allergy_risk

            result["guardrail_events"].append({
                "type": "SEVERE_ALLERGY_DETECTED" if allergy_data["allergy_level"] == "SEVERE_ANAPHYLAXIS" else "ALLERGY_LOGGED",
                "risk": allergy_risk,
                "action": "ESCALATED_TO_KITCHEN" if allergy_data["allergy_level"] == "SEVERE_ANAPHYLAXIS" else "TAGGED",
                "details": allergy_data
            })
            if db and allergy_data["allergy_level"] in ("SEVERE_ANAPHYLAXIS", "MODERATE"):
                await self._log_event(
                    db,
                    event_type="SEVERE_ALLERGY_DETECTED" if allergy_data["allergy_level"] == "SEVERE_ANAPHYLAXIS" else "MODERATE_ALLERGY_DETECTED",
                    raw_text=sanitized[:200],
                    sanitized_text=allergy_data["kitchen_alert_note"],
                    risk_level=allergy_risk,
                    action_taken="ESCALATED_TO_KITCHEN_ALERT"
                )

        return result

    async def log_interruption(self, db: Optional[AsyncSession], stage: str, details: str = ""):
        """Logs user interruption / barge-in event for observability."""
        if db:
            await self._log_event(
                db,
                event_type="INTERRUPTION",
                raw_text=f"User interrupted agent during {stage}",
                sanitized_text=details[:200],
                risk_level="LOW",
                action_taken="HALTED_AUDIO_AND_RESCHEDULED"
            )

    async def _log_event(
        self,
        db: AsyncSession,
        event_type: str,
        raw_text: str,
        sanitized_text: str,
        risk_level: str,
        action_taken: str
    ):
        try:
            log_entry = SafetyAuditLog(
                event_type=event_type,
                raw_text_preview=raw_text,
                sanitized_text=sanitized_text,
                risk_level=risk_level,
                action_taken=action_taken
            )
            db.add(log_entry)
            await db.commit()
        except Exception as err:
            logger.error(f"Failed to record safety audit log: {err}")


safety_pipeline = SafetyPipeline()

__all__ = [
    "SensitiveDataGuardrail",
    "AllergenSafetyGuardrail",
    "PromptSafetyGuardrail",
    "SafetyPipeline",
    "safety_pipeline"
]

