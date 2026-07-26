import json
import re


def extract_json(raw_text: str) -> dict:
    """
    Extracts a JSON object from raw LLM output, tolerating markdown code
    fences and leading/trailing prose that models sometimes add despite
    being told to return JSON only.

    Raises ValueError if no valid JSON object can be parsed.
    """
    text = raw_text.strip()

    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
    if fence_match:
        text = fence_match.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start:end + 1]

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Could not parse JSON from LLM output: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ValueError(f"Expected a JSON object, got {type(parsed).__name__}")

    return parsed
