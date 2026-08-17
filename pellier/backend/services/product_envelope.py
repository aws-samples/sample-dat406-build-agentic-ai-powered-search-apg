"""Normalize product records observed in tool-result envelopes."""

from __future__ import annotations

import json
import re
from typing import Any


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


class ProductExtractor:
    """Extract products from direct JSON or fenced JSON tool results."""

    @staticmethod
    def extract(tool_result: Any) -> list[dict[str, Any]]:
        candidates: list[Any] = [tool_result]
        if isinstance(tool_result, str):
            candidates.extend(
                match.group(1)
                for match in re.finditer(
                    r"```json\s*(.*?)\s*```",
                    tool_result,
                    re.DOTALL | re.IGNORECASE,
                )
            )

        products: list[Any] = []
        for candidate in candidates:
            data = candidate
            if isinstance(candidate, str):
                try:
                    data = json.loads(candidate)
                except (json.JSONDecodeError, TypeError):
                    continue
            if isinstance(data, dict) and isinstance(data.get("products"), list):
                products.extend(data["products"])
            elif isinstance(data, list):
                products.extend(data)

        normalized: list[dict[str, Any]] = []
        seen: set[str] = set()
        for product in products:
            if not isinstance(product, dict):
                continue
            item = ProductExtractor.normalize(product)
            identity = str(item["productId"] or item["name"]).strip().casefold()
            if not identity or identity in seen:
                continue
            seen.add(identity)
            normalized.append(item)
        return normalized

    @staticmethod
    def normalize(product: dict[str, Any]) -> dict[str, Any]:
        """Project known catalog aliases onto the storefront wire contract."""
        return {
            "productId": product.get("productId") or product.get("product_id", ""),
            "name": str(
                product.get("name") or product.get("product_description", "")
            )[:80],
            "brand": product.get("brand", ""),
            "color": product.get("color", ""),
            "price": _safe_float(product.get("price", 0)),
            "rating": _safe_float(product.get("rating") or product.get("stars", 0)),
            "reviews": _safe_int(product.get("reviews", 0)),
            "category": (
                product.get("category") or product.get("category_name", "")
            ),
            "imgUrl": (
                product.get("imgUrl")
                or product.get("img_url")
                or product.get("image_url")
                or product.get("image")
                or ""
            ),
            "badge": product.get("badge"),
            "tags": list(product.get("tags") or []),
        }
