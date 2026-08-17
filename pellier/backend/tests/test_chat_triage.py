"""Tests for ``services.chat.classify_triage`` — deterministic small-talk short-circuit.

The triage classifier runs before any orchestrator dispatch so
greetings/meta/thanks queries never depend on an LLM roll. These
tests pin the bucket mapping so a workshop demo that opens with "hi"
is guaranteed to produce a reply.
"""

from __future__ import annotations

import pytest

from services.chat import classify_intent, classify_triage, _TRIAGE_REPLIES


class TestTriageGreetings:
    @pytest.mark.parametrize(
        "query",
        [
            "hi",
            "Hi",
            "HI!",
            "hello",
            "Hello.",
            "hey",
            "hey there",
            "howdy",
            "yo",
            "good morning",
            "Good Afternoon",
            "good evening",
            "hi there",
            "hello, can you help me out",  # short-enough greeting prefix
        ],
    )
    def test_recognises_common_greetings(self, query: str) -> None:
        assert classify_triage(query) == "greeting"


class TestTriageMeta:
    @pytest.mark.parametrize(
        "query",
        [
            "what can you do",
            "What can you do?",
            "who are you",
            "what are you",
            "how do you work",
            "what are your capabilities",
            "help",
            "how can you help",
            "what can I ask",
        ],
    )
    def test_recognises_meta_queries(self, query: str) -> None:
        assert classify_triage(query) == "meta"


class TestTriageThanks:
    @pytest.mark.parametrize(
        "query",
        ["thanks", "thank you", "thanks!", "thx", "ty", "appreciate it"],
    )
    def test_recognises_thanks(self, query: str) -> None:
        assert classify_triage(query) == "thanks"


class TestTriageFallsThrough:
    @pytest.mark.parametrize(
        "query",
        [
            "find me a linen shirt under $150",
            "what's low on stock right now",
            "compare two mens shirts",
            "return policy?",
            "best linen shirt for travel",
            "",  # empty query
            "    ",  # whitespace
        ],
    )
    def test_real_queries_are_not_triaged(self, query: str) -> None:
        assert classify_triage(query) is None

    def test_long_query_starting_with_hi_is_not_triaged(self) -> None:
        """Long queries that happen to start with 'hi' are real
        questions, not greetings. The 60-char ceiling is what
        separates 'hi!' from 'hi, can you find me a linen shirt
        under $150 in a travel-friendly fabric?'"""
        long_q = (
            "hi, can you find me a linen shirt under $150 in a "
            "travel-friendly fabric please"
        )
        assert len(long_q) > 60
        assert classify_triage(long_q) is None


class TestTriageRepliesShape:
    def test_every_bucket_has_a_reply(self) -> None:
        for bucket in ("greeting", "meta", "thanks"):
            assert bucket in _TRIAGE_REPLIES
            assert _TRIAGE_REPLIES[bucket]
            # On-brand: should not start with generic "I can help"
            assert len(_TRIAGE_REPLIES[bucket]) > 20


class TestIntentPairing:
    @pytest.mark.parametrize(
        "query",
        [
            "What would go with the Hadley shirt?",
            "What pairs with the Ecru overshirt?",
            "What goes well with the pour-over set?",
        ],
    )
    def test_pairing_turns_route_to_search_for_style_match(self, query: str) -> None:
        assert classify_intent(query) == "search"


class TestIntentInventory:
    @pytest.mark.parametrize(
        "query",
        [
            "Is the Hadley shirt in Brooklyn?",
            "Do you have the linen overshirt in Austin?",
            "Can the camp shirt ship from Portland?",
        ],
    )
    def test_city_stock_questions_route_to_inventory(self, query: str) -> None:
        assert classify_intent(query) == "inventory"


class TestCanonicalPersonaIntentRoutes:
    @pytest.mark.parametrize(
        "query,expected",
        [
            ("Browse linen for a Goa carry-on", "search"),
            ("Pair something with the Hadley shirt", "search"),
            ("Compare Hadley with the Italian Linen Camp Shirt", "search"),
            ("Linen shirt price range", "pricing"),
            ("Hadley availability in Brooklyn", "inventory"),
            ("Housewarming gift under $200 for a ceramics lover", "recommendation"),
            ("Anniversary gift using past orders", "recommendation"),
            ("Trending home gifts", "recommendation"),
            ("Latest receipt for find_pieces_hybrid", "recommendation"),
            ("A sensitive sympathy gift that needs a human touch", "recommendation"),
            ("Hand-thrown pieces for a morning ritual", "search"),
            ("Care and return window for the linen throw", "customer_support"),
            ("File a damaged Wabi-Sabi Bowl return", "customer_support"),
            ("Prove the return was recorded", "customer_support"),
            (
                "Out-of-window durability exception for the linen throw",
                "customer_support",
            ),
            ("Which pieces are running low?", "inventory"),
            ("Restock product 37 by 12 units.", "inventory"),
        ],
    )
    def test_canonical_turn_reaches_expected_specialist(
        self,
        query: str,
        expected: str,
    ) -> None:
        assert classify_intent(query) == expected
