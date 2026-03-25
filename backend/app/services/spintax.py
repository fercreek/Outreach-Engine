"""Spintax processor for message template variations."""

import random
import re

# Pattern: {option1|option2|option3}
SPINTAX_PATTERN = re.compile(r"\{([^{}]+)\}")


def spin(text: str) -> str:
    """
    Resolve a single layer of spintax in the text.
    Example: "Hi {there|buddy}!" → "Hi buddy!"
    """
    def _pick(match: re.Match) -> str:
        options = match.group(1).split("|")
        return random.choice(options).strip()

    return SPINTAX_PATTERN.sub(_pick, text)


def spin_multiple(text: str, count: int = 5) -> list[str]:
    """Generate multiple unique variations from a spintax template."""
    results: set[str] = set()
    max_attempts = count * 10
    attempts = 0
    while len(results) < count and attempts < max_attempts:
        results.add(spin(text))
        attempts += 1
    return list(results)


def personalize(template: str, lead_data: dict) -> str:
    """
    Replace {{variable}} placeholders with lead-specific data.
    Example: "Hola {{business_name}}!" → "Hola Salsa MTY!"
    """
    result = template
    for key, value in lead_data.items():
        placeholder = "{{" + key + "}}"
        if placeholder in result and value:
            result = result.replace(placeholder, str(value))
    return result
