"""Tests for storefront session ownership checks."""

from __future__ import annotations

import pytest

from services.session_ownership import session_actor_id


def test_session_actor_id_prefers_authenticated_identity() -> None:
    assert session_actor_id({"sub": "user-123"}, "x" * 64) == "user-123"


def test_session_actor_id_hashes_anonymous_token() -> None:
    first = session_actor_id(None, "a" * 64)
    second = session_actor_id(None, "b" * 64)

    assert first.startswith("anonymous:")
    assert len(first) == len("anonymous:") + 64
    assert first != second


@pytest.mark.parametrize("token", [None, "", "too-short"])
def test_session_actor_id_rejects_missing_or_weak_anonymous_token(
    token: str | None,
) -> None:
    with pytest.raises(ValueError):
        session_actor_id(None, token)
