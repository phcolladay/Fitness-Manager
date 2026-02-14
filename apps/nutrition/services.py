import os
from typing import Any

import requests
import logging

USDA_BASE_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

logger = logging.getLogger(__name__)


def _extract_nutrients(nutrients: list[dict[str, Any]]) -> dict[str, float]:
    mapped = {
        "calories": 0.0,
        "protein_g": 0.0,
        "carbs_g": 0.0,
        "fat_g": 0.0,
        "fiber_g": 0.0,
        "sugar_g": 0.0,
        "sodium_mg": 0.0,
    }
    for nutrient in nutrients:
        name = (nutrient.get("nutrientName") or "").lower()
        value = nutrient.get("value")
        if value is None:
            continue
        if "energy" in name:
            mapped["calories"] = float(value)
        elif "protein" in name:
            mapped["protein_g"] = float(value)
        elif "carbohydrate" in name:
            mapped["carbs_g"] = float(value)
        elif name == "total lipid (fat)":
            mapped["fat_g"] = float(value)
        elif "fiber" in name:
            mapped["fiber_g"] = float(value)
        elif "sugars" in name:
            mapped["sugar_g"] = float(value)
        elif "sodium" in name:
            mapped["sodium_mg"] = float(value)
    return mapped


def search_usda_foods(query: str) -> list[dict[str, Any]]:
    api_key = os.getenv("USDA_API_KEY")
    if not api_key:
        return []
    try:
        response = requests.get(
            USDA_BASE_URL,
            params={"api_key": api_key, "query": query, "pageSize": 5},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException:
        logger.exception("USDA lookup failed")
        return []
    results = []
    for food in payload.get("foods", []):
        nutrients = _extract_nutrients(food.get("foodNutrients", []))
        results.append(
            {
                "description": food.get("description", ""),
                "brand": food.get("brandName") or "",
                "nutrients": nutrients,
            }
        )
    return results
