"""Product transport across the Pattern I specialist boundary."""

from agents.specialist_hooks import (
    forward_or_append_products,
    reset_product_collector,
    reset_specialist_reply_collector,
    set_product_collector,
    set_specialist_reply_collector,
)


PRODUCT = {
    "productId": 7,
    "name": "Italian Linen Camp Shirt",
    "price": 228,
}


def test_bound_collector_keeps_product_json_out_of_router_context():
    collector = []
    token = set_product_collector(collector)
    try:
        result = forward_or_append_products(
            'The indigo camp shirt is the strongest option.\n\n```json\n[]\n```',
            [PRODUCT],
        )
    finally:
        reset_product_collector(token)

    assert result == "The indigo camp shirt is the strongest option."
    assert collector == [PRODUCT]


def test_direct_specialist_call_preserves_fenced_product_fallback():
    result = forward_or_append_products("A grounded result.", [PRODUCT])

    assert result.startswith("A grounded result.\n\n```json\n[")
    assert '"productId": 7' in result
    assert result.endswith("\n```")


def test_bound_reply_collector_preserves_completed_specialist_prose():
    products = []
    replies = []
    product_token = set_product_collector(products)
    reply_token = set_specialist_reply_collector(replies)
    try:
        result = forward_or_append_products(
            "Lead with the Italian Linen Camp Shirt.",
            [PRODUCT],
        )
    finally:
        reset_specialist_reply_collector(reply_token)
        reset_product_collector(product_token)

    assert result == "Lead with the Italian Linen Camp Shirt."
    assert replies == ["Lead with the Italian Linen Camp Shirt."]
