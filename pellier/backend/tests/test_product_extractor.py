"""Product-envelope regression coverage for streamed specialist results."""

import json

import pytest

from services.chat import (
    EnhancedChatService,
    ProductExtractor,
    _is_incomplete_router_preface,
    _mentions_returned_product,
    _new_unique_products,
    _specialist_prose,
)


PRODUCT = {
    "productId": 7,
    "name": "Italian Linen Camp Shirt",
    "brand": "Pellier",
    "price": 228,
    "category": "Shirts",
    "imgUrl": "/products/italian-linen-camp-shirt.png",
}


def test_extracts_direct_tool_product_envelope():
    products = ProductExtractor.extract(json.dumps({"products": [PRODUCT]}))

    assert products == [
        {
            "productId": 7,
            "name": "Italian Linen Camp Shirt",
            "brand": "Pellier",
            "color": "",
            "price": 228.0,
            "rating": 0.0,
            "reviews": 0,
            "category": "Shirts",
            "imgUrl": "/products/italian-linen-camp-shirt.png",
            "badge": None,
            "tags": [],
        }
    ]


def test_extracts_products_forwarded_by_agents_as_tools_specialist():
    result = (
        "The indigo camp shirt is the strongest warm-weather option."
        "\n\n```json\n"
        f"{json.dumps([PRODUCT])}"
        "\n```"
    )

    products = ProductExtractor.extract(result)

    assert [product["productId"] for product in products] == [7]
    assert products[0]["imgUrl"] == "/products/italian-linen-camp-shirt.png"


def test_ignores_non_product_json_markers_and_duplicate_products():
    result = (
        "A grounded result."
        "\n\n```json\n"
        '{"type": "escalation", "reason": "human requested"}'
        "\n```\n"
        "```json\n"
        f"{json.dumps([PRODUCT, PRODUCT, {'status': 'success'}])}"
        "\n```"
    )

    products = ProductExtractor.extract(result)

    assert [product["productId"] for product in products] == [7]


def test_deduplicates_forwarded_batch_against_existing_and_itself():
    existing = [{"id": "7", "name": "Italian Linen Camp Shirt"}]
    candidates = [
        {"id": 7, "name": "Italian Linen Camp Shirt"},
        {"id": "16", "name": "Linen Overshirt"},
        {"id": 16, "name": "Linen Overshirt"},
        {"name": "Cotton-Linen Crew Tee"},
        {"name": "cotton-linen crew tee"},
    ]

    assert _new_unique_products(existing, candidates) == [
        {"id": "16", "name": "Linen Overshirt"},
        {"name": "Cotton-Linen Crew Tee"},
    ]


def test_extracts_specialist_prose_without_forwarded_product_payload():
    result = (
        "Lead with the Italian Linen Camp Shirt at $228."
        "\n\n```json\n"
        f"{json.dumps([PRODUCT])}"
        "\n```"
    )

    assert _specialist_prose(result) == (
        "Lead with the Italian Linen Camp Shirt at $228."
    )


def test_only_short_trailing_colon_copy_is_an_incomplete_router_preface():
    assert _is_incomplete_router_preface(
        "Here's a resort edit built around your linen wardrobe:"
    )
    assert not _is_incomplete_router_preface(
        "Lead with the Italian Linen Camp Shirt, then add the overshirt."
    )
    assert not _is_incomplete_router_preface("")


def test_detects_product_grounding_by_returned_name():
    products = [{"name": "Italian Linen Camp Shirt"}, {"name": ""}]

    assert _mentions_returned_product(
        "Lead with the Italian Linen Camp Shirt.",
        products,
    )
    assert not _mentions_returned_product("Here are some great options!", products)


@pytest.mark.asyncio
async def test_parser_preserves_grounded_editorial_price_sentence():
    service = EnhancedChatService.__new__(EnhancedChatService)
    prose = (
        "The Cotton-Linen Crew Tee at $68 is the closest match for a "
        "linen top under $150."
    )

    parsed = await service._parse_agent_response(
        prose,
        "Find a linen shirt under $150",
        has_tool_products=True,
    )

    assert parsed["text"] == prose
