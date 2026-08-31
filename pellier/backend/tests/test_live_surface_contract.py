"""Guard the live-data contract for the participant-facing surfaces.

The storefront and Observatory may display an explicit unavailable/empty
state, but they must never replace a failed Aurora/API read with browser
fixtures or locally fabricated persona data.
"""

from __future__ import annotations

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[3]
FRONTEND = ROOT / "pellier" / "frontend" / "src"
BACKEND = ROOT / "pellier" / "backend"


def test_observatory_data_hook_is_api_only() -> None:
    body = (FRONTEND / "observatory" / "hooks" / "useObservatoryData.ts").read_text()

    assert "const apiEndpoints" in body
    assert "fixtureImporters" not in body
    assert "allowFixtureFallback" not in body


def test_persona_runtime_has_no_file_or_process_memory_fallback() -> None:
    body = (BACKEND / "app.py").read_text()

    assert "personas-config.json" not in body
    assert "/api/observatory/personas/reload" not in body
    assert "_session_persona" not in body
    assert "pellier.persona_profiles" in body
    assert "pellier.shopper_sessions" in body


def test_persona_membership_comes_from_the_customer_record() -> None:
    """Profile presentation is seeded; membership is a current customer fact."""
    source = (BACKEND / "app.py").read_text()
    persona_query = source[
        source.index("async def _persona_rows") : source.index("def _persona_payload")
    ]

    assert "JOIN pellier.customers c" in persona_query
    assert "c.membership" in persona_query
    assert "pp.membership," not in persona_query


def test_live_surface_migration_provisions_profiles_sessions_and_scenarios() -> None:
    body = (ROOT / "scripts" / "migrations" / "029_live_surface_data.sql").read_text()

    for relation in (
        "pellier.persona_profiles",
        "pellier.shopper_sessions",
        "pellier.workshop_scenarios",
    ):
        assert relation in body
    assert "regexp_replace(\"imgUrl\", '\\.png$', '.webp')" in body


def test_storefront_persona_edits_are_durable_aurora_merchandising() -> None:
    migration = (
        ROOT / "scripts" / "migrations" / "030_storefront_editorial_order.sql"
    ).read_text()
    products_route = (BACKEND / "routes" / "products.py").read_text()

    assert "storefront_rank" in migration
    assert "count(*) <> 9" in migration
    assert "storefront_rank IS NOT NULL" in products_route
    assert "ORDER BY {order}" in products_route


def test_unsigned_edit_and_default_guided_turn_keep_the_house_merchandising() -> None:
    """The runner stays searchable but cannot set the guest-facing house edit."""
    initial_edit = (
        ROOT / "scripts" / "migrations" / "030_storefront_editorial_order.sql"
    ).read_text()
    refinement = (
        ROOT / "scripts" / "migrations" / "031_refine_fresh_storefront_edit.sql"
    ).read_text()
    scenarios = (ROOT / "scripts" / "migrations" / "029_live_surface_data.sql").read_text()
    curations = (FRONTEND / "data" / "personaCurations.ts").read_text()

    assert "('fresh', '10', 9)" in initial_edit
    assert "('fresh', '9', 9)" not in initial_edit
    assert 'WHEN "productId" = \'10\' THEN 9' in refinement
    assert "'A considered carry-all for a long weekend.', '10'" in scenarios
    assert "A considered carry-all for a long weekend." in curations


def test_voice_transcription_is_not_shipped_when_no_voice_control_exists() -> None:
    app = (BACKEND / "app.py").read_text()
    chat = (FRONTEND / "components" / "ChatDrawer.tsx").read_text()
    hero = (FRONTEND / "components" / "PellierHero.tsx").read_text()

    assert "transcribe_router" not in app
    assert "useVoiceSearch" not in chat
    assert "useVoiceSearch" not in hero
    assert not (BACKEND / "routes" / "transcribe.py").exists()
    assert not (FRONTEND / "hooks" / "useVoiceSearch.ts").exists()


def test_observatory_never_substitutes_browser_or_hardcoded_data() -> None:
    """A failed live read is visible; it is never simulated in the browser."""
    settings = (FRONTEND / "observatory" / "surfaces" / "Settings.tsx").read_text()
    tool_discovery = (
        FRONTEND / "observatory" / "hooks" / "useToolDiscovery.ts"
    ).read_text()
    skills = (
        FRONTEND / "observatory" / "surfaces" / "understand" / "Skills.tsx"
    ).read_text()
    session_chat = (
        FRONTEND / "observatory" / "surfaces" / "observe" / "ChatTab.tsx"
    ).read_text()

    assert "FALLBACK_PERSONAS" not in settings
    assert "discoverToolsLocally" not in tool_discovery
    assert "routeSkillsOffline" not in skills
    assert "SHOWCASE_PRODUCTS" not in session_chat
    assert "searchCatalog" not in session_chat
    assert "ComposerBar" not in session_chat
    assert "PERSONA_STRIP_META" not in session_chat
