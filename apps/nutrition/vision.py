import base64
from io import BytesIO
import json
import os

import requests


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


def recognize_food(image_path: str) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    image_b64 = _image_to_jpeg_b64(image_path)

    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Identify the food in the image and return JSON with keys "
                                "name, calories, protein_g, carbs_g, fat_g, fiber_g, sugar_g, sodium_mg."
                            ),
                        },
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{image_b64}",
                        },
                    ],
                }
            ],
            "response_format": {"type": "json_object"},
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    output_text = _extract_output_text(payload)
    try:
        return json.loads(output_text)
    except json.JSONDecodeError as exc:
        raise ValueError("Model returned invalid JSON") from exc
