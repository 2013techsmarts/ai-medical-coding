import re

# Redaction patterns
SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
PHONE_PATTERN = re.compile(r'\b(?:\+?\d{1,3}[-.●]?)?\(?\d{3}\)?[-.●]?\d{3}[-.●]?\d{4}\b')
ZIP_PATTERN = re.compile(r'\b\d{5}(?:-\d{4})?\b')

# Simple patterns for prompt injection
INJECTION_KEYWORDS = [
    "ignore previous instructions",
    "ignore above instructions",
    "bypass",
    "jailbreak",
    "you are now an admin",
    "system command",
    "override security"
]

def redact_phi(text: str) -> str:
    """
    Redacts standard PHI elements from clinical notes to protect privacy.
    """
    text = SSN_PATTERN.sub("[REDACTED SSN]", text)
    text = EMAIL_PATTERN.sub("[REDACTED EMAIL]", text)
    text = PHONE_PATTERN.sub("[REDACTED PHONE]", text)
    # Be careful redacting zip codes as they can occasionally match ICD codes, but let's redact 5-digit zip patterns safely.
    # To prevent overlap with codes, we only do it if clearly labeled or as a general regex check
    text = ZIP_PATTERN.sub("[REDACTED ZIP]", text)
    
    # Redact common names indicator
    text = re.sub(r'((?:patient|doctor|dr\.)\s+)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', r'\1[REDACTED NAME]', text)
    return text

def detect_prompt_injection(text: str) -> bool:
    """
    Checks if a clinical note contains malicious formatting/commands designed to hijack the model.
    """
    text_lower = text.lower()
    for kw in INJECTION_KEYWORDS:
        if kw in text_lower:
            return True
            
    # Check for split combinations (e.g. "Ignore all previous instructions")
    if "ignore" in text_lower and "instructions" in text_lower:
        return True
        
    return False

OFF_TOPIC_KEYWORDS = [
    "recipe",
    "cookie",
    "spaghetti",
    "weather",
    "poem",
    "capital of",
    "who are you",
    "favorite movie",
    "tell me a joke"
]

def detect_off_topic(text: str) -> bool:
    """
    Checks if a query is off-topic (e.g. general knowledge, recipes, creative writing)
    to protect the agent from non-medical tasks.
    """
    text_lower = text.lower()
    for kw in OFF_TOPIC_KEYWORDS:
        if kw in text_lower:
            return True
    return False

