import re
from typing import Dict, Any, Tuple


INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|above)\s+instructions?",
    r"disregard\s+(all\s+)?instructions?",
    r"you\s+are\s+now\s+(in\s+)?developer\s+mode",
    r"bypass\s+all\s+(guardrails|safety)",
    r"show\s+me\s+your\s+system\s+prompt",
    r"what\s+are\s+your\s+(internal\s+)?instructions?",
    r"print\s+database\s+passwords?",
    r"drop\s+table",
    r"delete\s+from\s+reservations",
    r"select\s+\*\s+from\s+users",
    r"union\s+select",
    r"leak\s+(other\s+)?customers?(\s+info)?",
    r"act\s+as\s+an\s+unfiltered\s+ai"
]


class PromptSafetyGuardrail:
    """Guardrail to intercept prompt injection, adversarial commands, and SQL manipulation in voice speech."""

    def __init__(self):
        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]

    def inspect(self, text: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Evaluates input text against known jailbreak/injection patterns.
        Returns (is_safe, sanitized_or_replacement_text, violation_meta).
        """
        for pattern in self.compiled_patterns:
            match = pattern.search(text)
            if match:
                violation_type = "PROMPT_INJECTION_OR_MANIPULATION"
                matched_fragment = match.group(0)
                safe_fallback = "I would be happy to assist you with restaurant reservations, table availability, or dietary information. How may I help you with your booking today?"
                
                return False, safe_fallback, {
                    "violation": violation_type,
                    "fragment": matched_fragment,
                    "risk_level": "HIGH",
                    "action": "BLOCKED_AND_REDIRECTED"
                }

        return True, text, {}

