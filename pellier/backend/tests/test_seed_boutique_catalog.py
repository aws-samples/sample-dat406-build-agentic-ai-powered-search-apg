"""Tests for the workshop catalog seed generator.

The governed workshop uses 40 curated story products plus generated archive
distractors for retrieval evaluation. These tests keep that split explicit so
inventory, order, and policy exercises keep their stable product IDs.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_seed_module():
    module_name = "seed_boutique_catalog_for_tests"
    if module_name in sys.modules:
        return sys.modules[module_name]

    script_path = (
        Path(__file__).resolve().parents[3] / "scripts" / "seed_boutique_catalog.py"
    )
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def test_default_catalog_keeps_curated_ids_and_adds_archive_distractors():
    seed = _load_seed_module()

    catalog = seed.build_catalog()
    curated = [p for p in catalog if not p.is_distractor]
    distractors = [p for p in catalog if p.is_distractor]

    assert len(curated) == seed.CURATED_PRODUCT_COUNT == 40
    assert len(distractors) == seed.DEFAULT_DISTRACTOR_COUNT == 960
    assert len(catalog) == 1000
    assert [p.productId for p in curated] == list(range(1, 41))
    assert distractors[0].productId == seed.DISTRACTOR_ID_START
    assert (
        distractors[-1].productId
        == seed.DISTRACTOR_ID_START + seed.DEFAULT_DISTRACTOR_COUNT - 1
    )
    assert all(
        seed.DISTRACTOR_ID_START <= p.productId <= seed.DISTRACTOR_ID_END
        for p in distractors
    )
    assert all(1 <= int(p.source_product_id or 0) <= 40 for p in distractors)
    assert all("archive" in p.tags for p in distractors)
    assert all("archive" not in p.tags for p in curated)


def test_catalog_can_still_seed_only_the_40_curated_story_products():
    seed = _load_seed_module()

    catalog = seed.build_catalog(include_distractors=False)

    assert len(catalog) == 40
    assert all(not p.is_distractor for p in catalog)
    assert [p.productId for p in catalog] == list(range(1, 41))


def test_distractor_embeddings_are_derived_from_cache_and_deterministic(monkeypatch):
    seed = _load_seed_module()
    monkeypatch.setenv("BEDROCK_EMBED_MODEL_ID", "us.cohere.embed-v4:0")

    def _embedded_catalog():
        catalog = seed.build_catalog(distractor_count=5)
        curated = [p for p in catalog if not p.is_distractor]
        assert seed.load_embeddings_cache(curated, seed.EMBED_CACHE) == 40
        assert seed.derive_distractor_embeddings(catalog) == 5
        return catalog

    first = _embedded_catalog()
    second = _embedded_catalog()
    first_distractors = [p for p in first if p.is_distractor]
    second_distractors = [p for p in second if p.is_distractor]

    assert len(first_distractors) == 5
    assert all(
        p.embedding and len(p.embedding) == seed.EMBED_DIM
        for p in first_distractors
    )
    assert first_distractors[0].embedding == second_distractors[0].embedding
    assert first_distractors[-1].embedding == second_distractors[-1].embedding
    assert first_distractors[0].embedding != first[0].embedding
