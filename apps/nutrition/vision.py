import base64
from io import BytesIO
import json
import logging
import os

import requests


logger = logging.getLogger(__name__)


def _image_to_jpeg_b64(image_path: str) -> str:
    # Normalize any supported image to a reasonably-sized JPEG to control payload size/cost.
    from PIL import Image

    with Image.open(image_path) as img:
        img = img.convert("RGB")
        img.thumbnail((1024, 1024))
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=85, optimize=True)
        return base64.b64encode(buf.getvalue()).decode("ascii")


def _extract_output_text(payload: dict) -> str:
    for item in payload.get("output", []) or []:
        for content in item.get("content", []) or []:
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                return text
    # Fallbacks for slightly different response shapes.
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
        raise ValueError("Model output was JSON but not an object")
    except json.JSONDecodeError:
        # Best-effort salvage if the model wrapped the JSON in extra text.
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            obj = json.loads(text[start : end + 1])
            if isinstance(obj, dict):
                return obj
        raise ValueError("Model returned invalid JSON")


def recognize_food(image_path: str) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    image_b64 = _image_to_jpeg_b64(image_path)

    # Responses API request shape:
    # - inputs use {"type":"input_text"} / {"type":"input_image","image_url":"..."} items
    # - structured output is configured via text.format (not response_format)
    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Identify the food in the image and return ONLY a JSON object with keys: "
                                "name, calories, protein_g, carbs_g, fat_g, fiber_g, sugar_g, sodium_mg. "
                                "Use numbers for all *_g, calories, sodium_mg. Use best effort estimates."
                            ),
                        },
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{image_b64}",
                        },
                    ],
                }
            ],
            "text": {"format": {"type": "json_object"}},
            "temperature": 0.2,
        },
        timeout=30,
    )
    try:
        response.raise_for_status()
    except requests.HTTPError:
        # Log enough to debug in server logs; never return this to the user directly.
        request_id = response.headers.get("x-request-id") or response.headers.get("x-request-id".upper())
        body = (response.text or "")[:1200]
        logger.error(
            "OpenAI /v1/responses failed status=%s request_id=%s body=%s",
            response.status_code,
            request_id,
            body,
        )
        raise

    payload = response.json()
    output_text = _extract_output_text(payload)
    return _coerce_json_object(output_text)
