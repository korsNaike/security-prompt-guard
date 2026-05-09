from app.infrastructure.ml.common.preprocessing import normalize_text

PROMPT_INJECTION_PATTERNS = (
    "ignore previous instructions",
    "ignore all previous instructions",
    "reveal your system prompt",
    "show the system prompt",
    "developer message",
    "system instructions",
)

JAILBREAK_PATTERNS = (
    "dan mode",
    "do anything now",
    "jailbreak",
    "bypass safety",
    "disable guardrails",
)

DATA_EXFILTRATION_PATTERNS = (
    "api key",
    "access token",
    "secret key",
    "private key",
    "environment variables",
)


def classify_prompt_by_rules(text: str) -> tuple[str, float, str]:
    normalized = normalize_text(text)
    if any(pattern in normalized for pattern in DATA_EXFILTRATION_PATTERNS):
        return "data_exfiltration", 0.82, "Mentions secret or credential extraction patterns."
    if any(pattern in normalized for pattern in PROMPT_INJECTION_PATTERNS):
        return (
            "prompt_injection",
            0.86,
            "Attempts to override instructions or reveal hidden content.",
        )
    if any(pattern in normalized for pattern in JAILBREAK_PATTERNS):
        return "jailbreak", 0.84, "Contains common jailbreak phrasing."
    if any(word in normalized for word in ("hack", "malware", "exploit")):
        return "harmful", 0.7, "Contains potentially harmful cybersecurity intent."
    return "safe", 0.62, "No high-risk prompt safety pattern was matched."
