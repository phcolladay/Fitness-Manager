import json
import logging
import os
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)


def _extract_output_text(payload: dict) -> str:
    for item in payload.get("output", []) or []:
        for content in item.get("content", []) or []:
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                return text
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text
    raise ValueError("No output text found in response payload")


def _coerce_json_object(text: str) -> dict:
    text = (text or "").strip()
    if not text:
        raise ValueError("Empty model output")
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            obj = json.loads(text[start : end + 1])
            if isinstance(obj, dict):
                return obj
    raise ValueError("Model returned invalid JSON")


def estimate_exercise_calories_ai(
    *,
    exercise_name: str,
    duration_minutes: int,
    category: str = "",
    muscle_group: str = "",
    weight_kg: Optional[float] = None,
) -> Optional[float]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    if not exercise_name or not duration_minutes:
        return None

    prompt = (
        "Estimate calories burned for this exercise session and return ONLY JSON with keys "
        "calories_burned and reasoning_short. calories_burned must be a number.\n"
        f"exercise_name: {exercise_name}\n"
        f"duration_minutes: {duration_minutes}\n"
        f"category: {category or 'unknown'}\n"
        f"muscle_group: {muscle_group or 'unknown'}\n"
        f"user_weight_kg: {weight_kg if weight_kg is not None else 'unknown'}"
    )

    response = None
    for attempt in range(2):
        try:
            response = requests.post(
                "https://api.openai.com/v1/responses",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    "input": [{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
                    "text": {"format": {"type": "json_object"}},
                    "temperature": 0.1,
                },
                timeout=20,
            )
            if response.status_code >= 500 and attempt == 0:
                time.sleep(0.4)
                continue
            response.raise_for_status()
            payload = response.json()
            output_text = _extract_output_text(payload)
            obj = _coerce_json_object(output_text)
            value = float(obj.get("calories_burned"))
            if value < 0:
                return None
            return round(value, 2)
        except (requests.Timeout, requests.ConnectionError):
            if attempt == 0:
                time.sleep(0.4)
                continue
            logger.exception("Exercise calorie AI estimate failed after retry")
            return None
        except (requests.RequestException, ValueError, TypeError):
            logger.exception("Exercise calorie AI estimate failed")
            return None
    return None
