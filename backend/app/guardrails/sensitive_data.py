import re
from typing import Tuple, List, Dict, Any


def luhn_checksum(card_number: str) -> bool:
    """Validate credit card number using Luhn algorithm."""
    digits = [int(c) for c in card_number if c.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        if i % 2 == 1:
            doubled = d * 2
            checksum += doubled - 9 if doubled > 9 else doubled
        else:
            checksum += d
    return checksum % 10 == 0


class SensitiveDataGuardrail:
    """Guardrail to detect, mask, and redact sensitive customer data (PII, cards, IDs)."""

    # Credit card regex (Visa, MC, Amex, Discover, standard formats with hyphens/spaces)
    CARD_REGEX = re.compile(r'\b(?:\d[ -]*?){13,19}\b')

    # Social Security / National ID regex (e.g., 000-00-0000 or 9 digits)
    SSN_REGEX = re.compile(r'\b\d{3}[- ]?\d{2}[- ]?\d{4}\b')

    # CVV pattern (3 or 4 digits near security/cvv keywords)
    CVV_REGEX = re.compile(r'\b(?:cvv|cvc|security code|pin)[:\s]+(\d{3,4})\b', re.IGNORECASE)

    # Email pattern
    EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b')

    def sanitize_input(self, text: str) -> Tuple[str, List[Dict[str, Any]], str]:
        """
        Scans input text, redacts sensitive PII, and returns:
        (sanitized_text, detections, overall_risk_level)
        """
        detections = []
        sanitized = text
        risk_level = "LOW"

        # 1. Detect and redact Credit Card numbers
        for match in self.CARD_REGEX.finditer(text):
            candidate = match.group(0).replace(" ", "").replace("-", "")
            if luhn_checksum(candidate):
                last_four = candidate[-4:]
                masked = f"[CARD_REDACTED_*{last_four}]"
                sanitized = sanitized.replace(match.group(0), masked)
                detections.append({
                    "type": "PAYMENT_CARD",
                    "matched": f"****{last_four}",
                    "risk": "CRITICAL"
                })
                risk_level = "CRITICAL"

        # 2. Detect and redact SSN / National IDs
        for match in self.SSN_REGEX.finditer(sanitized):
            masked = "[NATIONAL_ID_REDACTED]"
            sanitized = sanitized.replace(match.group(0), masked)
            detections.append({
                "type": "NATIONAL_ID",
                "matched": "[SSN]",
                "risk": "HIGH"
            })
            if risk_level != "CRITICAL":
                risk_level = "HIGH"

        # 3. Detect and redact CVV / PINs
        for match in self.CVV_REGEX.finditer(sanitized):
            masked = "cvv: [REDACTED_CVV]"
            sanitized = sanitized.replace(match.group(0), masked)
            detections.append({
                "type": "SECURITY_CODE",
                "matched": "[CVV]",
                "risk": "HIGH"
            })
            if risk_level != "CRITICAL":
                risk_level = "HIGH"

        return sanitized, detections, risk_level

