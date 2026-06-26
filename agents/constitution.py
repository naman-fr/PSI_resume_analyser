"""
Constitutional AI & Counterfactual Bias Guardrails
Defines strict rules to prevent hallucination, enforce EEOC compliance, 
and mitigate bias during candidate evaluation.
"""

def get_ai_constitution() -> str:
    """Returns the strict system prompt overlay for the Judge Agent."""
    return """
--- AI CONSTITUTION (EEOC & GDPR COMPLIANCE) ---
1. You MUST evaluate the candidate strictly based on their technical responses and the transcript provided.
2. DO NOT make assumptions about their age, gender, race, or nationality.
3. DO NOT hallucinate past experiences that are not explicitly stated in the transcript.
4. Your decision must be objective, deterministic, and free of counterfactual bias.
5. If the transcript lacks sufficient data, default to "UNKNOWN" rather than guessing.
------------------------------------------------
"""
