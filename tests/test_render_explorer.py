"""Tests for ``src.render.explorer`` — the ``/data/explore/`` data basis.

Real-corpus drive per the CLAUDE.md hard rule: the explorer dump is a
denormalised measurement table over the whole corpus, so its invariants
(one row per review, set-internal yes-ratio, per-row schema) can only be
proven against the reviews the parser actually produces. The
``corpus_*`` fixtures (``conftest.py``) parse once per session and skip
cleanly when the corpus is absent.

A second layer freezes the row *schema* (field names, types, value
ranges) as the pipeline → ``static/js/explore.js`` interface contract, so
a rename or type drift on either side fails here instead of silently
breaking the interactive page.
"""
from __future__ import annotations

import json

from src.render.explorer import (
    VERSION,
    review_row,
    to_explorer_dump,
    to_explorer_dump_string,
)
from src.render.html import SiteConfig, make_env


# ── Row-schema contract (pipeline → explore.js) ──────────────────────

# The full set of keys every explorer row must carry. Frozen so a field
# rename in explorer.py or a new consumer in explore.js is a conscious,
# reviewed change rather than a silent break.
ROW_KEYS = {
    "id", "issue", "title", "year", "date", "language", "url",
    "set_slug", "set_label", "yes", "answered", "yes_pct",
    "chars", "paragraphs", "figures", "notes", "bibl",
    "code", "code_present", "external_refs",
    "resource_title", "resource_year", "resource_age",
    "resource_has_doi", "resource_host",
}

# Fields static/js/explore.js reads directly (facets, beeswarm axes,
# timeline, table columns, tooltip). Pinned so the frontend never loses
# a field out from under it.
FRONTEND_FIELDS = {
    "id", "title", "issue", "year", "language", "url",
    "set_slug", "yes_pct", "chars", "figures", "notes",
    "external_refs", "resource_age",
}

# int-typed fields; None allowed only where noted below.
_INT_FIELDS = {"yes", "answered", "chars", "paragraphs", "figures", "notes", "bibl", "code", "external_refs"}
_NULLABLE_INT = {"year", "resource_year", "resource_age"}
_BOOL_FIELDS = {"code_present", "resource_has_doi"}


def test_frontend_fields_are_a_subset_of_the_row_schema():
    """The interface pin only holds if every consumed field is emitted."""
    assert FRONTEND_FIELDS <= ROW_KEYS


def test_review_row_carries_exactly_the_contract_keys(corpus_review):
    row = review_row(corpus_review)
    assert set(row.keys()) == ROW_KEYS


def test_every_row_matches_the_frozen_schema(corpus_reviews):
    """Field types and value ranges are stable across the whole corpus."""
    rows = [review_row(r) for r in corpus_reviews]
    for row in rows:
        assert set(row.keys()) == ROW_KEYS
        for f in FRONTEND_FIELDS:
            assert f in row
        # id / issue / url are always present, non-empty strings.
        assert isinstance(row["id"], str) and row["id"]
        assert isinstance(row["issue"], str) and row["issue"]
        assert row["url"].endswith(f"/issues/{row['issue']}/{row['id']}/")
        for f in _INT_FIELDS:
            assert isinstance(row[f], int), f"{f} must be int"
            assert row[f] >= 0
        for f in _BOOL_FIELDS:
            assert isinstance(row[f], bool)
        for f in _NULLABLE_INT:
            assert row[f] is None or isinstance(row[f], int)
        # yes-ratio is a bounded percentage or None (no questionnaire).
        assert row["yes_pct"] is None or 0.0 <= row["yes_pct"] <= 100.0


def test_yes_ratio_is_set_internal_and_consistent(corpus_reviews):
    """The yes-ratio is computed per review over its own criteria set —
    never a global mean across taxonomy sets. Each row carries its
    ``set_slug`` so the consumer keeps comparisons set-internal, and the
    ratio equals yes/answered for that row alone."""
    for row in (review_row(r) for r in corpus_reviews):
        assert row["yes"] <= row["answered"] or row["answered"] == 0
        if row["answered"]:
            assert row["yes_pct"] == round(100.0 * row["yes"] / row["answered"], 1)
            # A row with answers must name the set it belongs to.
            assert row["set_slug"] is not None
        else:
            assert row["yes_pct"] is None


def test_dump_has_one_row_per_corpus_review(corpus_reviews):
    """Row count tracks the loader, not a hardcoded 111."""
    dump = to_explorer_dump(corpus_reviews)
    assert dump["review_count"] == len(corpus_reviews)
    assert len(dump["reviews"]) == len(corpus_reviews)
    # No global yes-ratio leaks into the envelope — the ratio is per row.
    assert "yes_pct" not in dump
    assert "yes" not in dump


def test_dump_envelope_and_set_legend(corpus_reviews):
    dump = to_explorer_dump(corpus_reviews, base_url="https://ride.i-d-e.de")
    assert dump["version"] == VERSION
    assert dump["base_url"] == "https://ride.i-d-e.de"
    assert dump["licence"]["name"] == "CC-BY-4.0"
    # Every set_slug used by a row is labelled in the legend.
    used = {row["set_slug"] for row in dump["reviews"] if row["set_slug"]}
    assert used <= set(dump["sets"].keys())
    for slug, label in dump["sets"].items():
        assert isinstance(label, str) and label


def test_dump_string_is_loadable_json(corpus_reviews):
    s = to_explorer_dump_string(corpus_reviews, indent=None)
    assert "\n  " not in s  # compact
    reloaded = json.loads(s)
    assert reloaded["review_count"] == len(corpus_reviews)


def test_render_explore_and_dump_write_exact_target_paths(corpus_reviews, tmp_path):
    """The build writes the explorer at two exact paths next to each
    other: the page island and the reusable JSON artefact."""
    from src.build import _render_aggregations

    site = SiteConfig(title="RIDE", base_url="", default_language="en")
    env = make_env()
    _render_aggregations(corpus_reviews, env, site, tmp_path)

    page = tmp_path / "data" / "explore" / "index.html"
    dump = tmp_path / "data" / "explorer.json"
    assert page.is_file()
    assert dump.is_file()
    # The page embeds the JSON island explore.js reads.
    assert 'id="ride-explore-data"' in page.read_text(encoding="utf-8")
    # The sidecar dump has one row per corpus review.
    payload = json.loads(dump.read_text(encoding="utf-8"))
    assert payload["review_count"] == len(corpus_reviews)
    assert len(payload["reviews"]) == len(corpus_reviews)
