import re
from typing import Dict, Any, List, Tuple


ALLERGEN_KEYWORDS = {
    "peanuts": ["peanut", "peanuts", "groundnut", "peanut butter", "peanut oil"],
    "tree_nuts": ["tree nut", "nuts", "almond", "walnut", "cashew", "pecan", "pistachio", "hazelnut", "praline", "macadamia"],
    "dairy": ["dairy", "milk", "cheese", "butter", "cream", "lactose", "yogurt", "parmesan", "gelato"],
    "gluten": ["gluten", "celiac", "coeliac", "wheat", "barley", "rye", "bread", "crouton", "pasta", "flour"],
    "shellfish": ["shellfish", "crustacean", "shrimp", "prawn", "crab", "lobster", "calamari", "squid", "clam", "mussel", "oyster"],
    "fish": ["fish", "salmon", "tuna", "cod", "anchovy", "halibut", "bass"],
    "eggs": ["egg", "eggs", "aioli", "mayonnaise", "mayo"],
    "soy": ["soy", "soya", "soy sauce", "tofu", "edamame"],
    "sesame": ["sesame", "tahini"]
}

SEVERE_INDICATORS = [
    "anaphylaxis", "anaphylactic", "severe", "epipen", "epi-pen", 
    "life-threatening", "hospital", "deadly", "deathly", "throat closing", "critical"
]

MODERATE_INDICATORS = [
    "allergic", "allergy", "intolerant", "intolerance", "celiac", "reaction"
]


class AllergenSafetyGuardrail:
    """Specialized safety guardrail for health and dietary allergen protection."""

    def analyze_dietary_input(self, text: str) -> Dict[str, Any]:
        """
        Parses user dietary statements, classifies severity, and extracts allergen list.
        """
        text_lower = text.lower()
        identified_allergens = set()
        
        for allergen, keywords in ALLERGEN_KEYWORDS.items():
            for kw in keywords:
                pattern = r'\b' + re.escape(kw) + r'\b'
                if re.search(pattern, text_lower):
                    identified_allergens.add(allergen)
                    break

        # Check severity level
        has_severe = any(re.search(r'\b' + re.escape(ind) + r'\b', text_lower) for ind in SEVERE_INDICATORS)
        has_moderate = any(re.search(r'\b' + re.escape(ind) + r'\b', text_lower) for ind in MODERATE_INDICATORS)

        if identified_allergens:
            if has_severe:
                severity = "SEVERE_ANAPHYLAXIS"
                risk_level = "CRITICAL"
            elif has_moderate:
                severity = "MODERATE"
                risk_level = "HIGH"
            else:
                severity = "MILD"
                risk_level = "MEDIUM"
        else:
            if "vegan" in text_lower or "vegetarian" in text_lower or "halal" in text_lower or "kosher" in text_lower:
                severity = "PREFERENCE"
                risk_level = "LOW"
            else:
                severity = "NONE"
                risk_level = "LOW"

        allergen_list = sorted(list(identified_allergens))
        
        kitchen_alert = ""
        customer_disclaimer = ""
        
        if severity == "SEVERE_ANAPHYLAXIS":
            kitchen_alert = (
                f"🚨 RED ALERT: GUEST HAS SEVERE/LIFE-THREATENING ALLERGY TO {', '.join(allergen_list).upper()}. "
                f"Mandatory sanitized cookware, separate prep station, and manager sign-off required."
            )
            customer_disclaimer = (
                f"⚠️ Health Notice: We have flagged a SEVERE {', '.join(allergen_list)} allergy for our Executive Chef. "
                f"While we enforce strict sanitization, our kitchen handles various ingredients, so please confirm with your server upon arrival."
            )
        elif severity == "MODERATE":
            kitchen_alert = f"⚠️ ALLERGY WARNING: Guest is allergic to {', '.join(allergen_list)}. Modify dish and clean utensils."
            customer_disclaimer = f"Notice: We have marked your {', '.join(allergen_list)} allergy in the reservation for our kitchen team."

        return {
            "has_allergy": len(identified_allergens) > 0,
            "allergy_level": severity,
            "risk_level": risk_level,
            "identified_allergens": allergen_list,
            "allergen_flags_str": ",".join(allergen_list) if allergen_list else None,
            "kitchen_alert_note": kitchen_alert,
            "customer_disclaimer": customer_disclaimer
        }

    def check_dish_conflict(self, dish_allergens_str: str, customer_allergens: List[str]) -> Tuple[bool, List[str]]:
        """
        Determines whether a dish contains any allergens conflicting with the customer's allergy profile.
        """
        if not dish_allergens_str or dish_allergens_str == "none":
            return False, []
        
        dish_allergens = [a.strip().lower() for a in dish_allergens_str.split(",")]
        conflicts = [a for a in customer_allergens if a.lower() in dish_allergens]
        return len(conflicts) > 0, conflicts

