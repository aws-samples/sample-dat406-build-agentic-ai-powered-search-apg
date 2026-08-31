"""Live catalog filters must treat shopper text as literal LIKE input."""

from __future__ import annotations

from typing import Any

import pytest

from services import business_logic
from services.business_logic import BusinessLogic


class _CaptureDB:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    async def fetch_all(self, query: str, *params: Any) -> list[dict[str, Any]]:
        self.calls.append((query, params))
        return []

    async def fetch_one(self, query: str, *params: Any) -> dict[str, Any]:
        self.calls.append((query, params))
        return {}


def test_prepare_like_pattern_escapes_every_postgres_metacharacter() -> None:
    prepare = getattr(business_logic, "prepare_like_pattern", lambda _value: None)

    assert prepare(r"50%_\\") == r"%50\%\_\\\\%"


@pytest.mark.asyncio
async def test_every_live_category_or_product_filter_escapes_literal_input() -> None:
    db = _CaptureDB()
    logic = BusinessLogic(db)
    literal = "50%_"
    expected = r"%50\%\_%"

    await logic.get_trending_products(category=literal)
    trending_query, trending_params = db.calls[-1]

    await logic._check_inventory_by_product(literal)
    inventory_query, inventory_params = db.calls[-1]

    await logic.get_price_analysis(category=literal)
    price_query, price_params = db.calls[-2]

    logic._embedding_service = type(
        "_Embeddings",
        (),
        {"embed_query": staticmethod(lambda _query: [0.1, 0.2])},
    )()
    await logic.search_products("linen", category=literal)
    search_query, search_params = db.calls[-1]

    await logic.get_products_by_category(literal)
    browse_query, browse_params = db.calls[-1]

    assert [
        trending_params[0],
        inventory_params[0],
        price_params[0],
        search_params[1],
        browse_params[0],
    ] == [expected] * 5
    assert all(
        "ESCAPE '\\'" in query
        for query in (
            trending_query,
            inventory_query,
            price_query,
            search_query,
            browse_query,
        )
    )
