import os
import time
from typing import Any

import requests
import logging

USDA_BASE_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

logger = logging.getLogger(__name__)


def _to_mg(value: Any, unit_name: str) -> float:
    amount = float(value)
    unit = (unit_name or "").strip().lower()
    if unit in {"g", "gram", "grams"}:
        return amount * 1000.0
    if unit in {"ug", "µg", "mcg", "microgram", "micrograms"}:
        return amount / 1000.0
    return amount


def _extract_nutrients(nutrients: list[dict[str, Any]]) -> dict[str, Any]:
    mapped = {
        "calories": 0.0,
        "protein_g": 0.0,
        "carbs_g": 0.0,
        "fat_g": 0.0,
        "fiber_g": 0.0,
        "sugar_g": 0.0,
        "sodium_mg": 0.0,
        "micronutrients": {},
    }
    micros = mapped["micronutrients"]
    for nutrient in nutrients:
        name = (nutrient.get("nutrientName") or "").lower()
        value = nutrient.get("value")
        unit_name = nutrient.get("unitName") or ""
        if value is None:
            continue
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            continue
        if "energy" in name:
            mapped["calories"] = numeric_value
        elif "protein" in name:
            mapped["protein_g"] = numeric_value
        elif "carbohydrate" in name:
            mapped["carbs_g"] = numeric_value
        elif name == "total lipid (fat)":
            mapped["fat_g"] = numeric_value
        elif "fiber" in name:
            mapped["fiber_g"] = numeric_value
        elif "sugars" in name:
            mapped["sugar_g"] = numeric_value
        elif "sodium" in name:
            mapped["sodium_mg"] = _to_mg(numeric_value, unit_name)

        if "iron" in name:
            micros["iron_mg"] = _to_mg(numeric_value, unit_name)
        elif "calcium" in name:
            micros["calcium_mg"] = _to_mg(numeric_value, unit_name)
        elif "vitamin c" in name or "ascorbic" in name:
            micros["vitamin_c_mg"] = _to_mg(numeric_value, unit_name)
        elif "potassium" in name:
            micros["potassium_mg"] = _to_mg(numeric_value, unit_name)

    if mapped["fiber_g"]:
        micros["fiber_g"] = float(mapped["fiber_g"])
    if mapped["sodium_mg"]:
        micros["sodium_mg"] = float(mapped["sodium_mg"])
    return mapped


def search_usda_foods(query: str) -> list[dict[str, Any]]:
    api_key = os.getenv("USDA_API_KEY")
    if not api_key:
        return []
    payload = {}
    for attempt in range(2):
        try:
            response = requests.get(
                USDA_BASE_URL,
                params={"api_key": api_key, "query": query, "pageSize": 5},
                timeout=10,
            )
            if response.status_code >= 500 and attempt == 0:
                time.sleep(0.4)
                continue
            response.raise_for_status()
            payload = response.json()
            break
        except (requests.Timeout, requests.ConnectionError):
            if attempt == 0:
                time.sleep(0.4)
                continue
            logger.exception("USDA lookup failed after retry")
            return []
        except requests.HTTPError:
            logger.warning("USDA lookup HTTP error status=%s", getattr(response, "status_code", "unknown"))
            return []
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
