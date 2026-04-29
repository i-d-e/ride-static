"""Tests for ``src.render.corpus_dump`` — Phase 12 R15 / A5.

The serialiser is a pure recursive transformation over the domain
dataclasses. Tests:

* Pin the top-level dump shape (version, review_count, base_url,
  build_date, reviews list).
* Pin the discriminated-union ``__type`` rule for blocks and inlines.
* Pin the tuple-to-list conversion and ``None`` passthrough.
* End-to-end round-trip: parse a real corpus review, dump it, reload
  the JSON, and verify the load-bearing structure survives.

Synthetic fixtures are appropriate per the pure-formatter exception in
``CLAUDE.md`` — the function signature ``Sequence[Review] → dict`` is
the only data form richer than the input.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.model.block import Paragraph
from src.model.inline import Emphasis, Reference, Text
from src.model.review import Review
from src.model.section import Section
from src.render.corpus_dump import (
    LICENCE_NAME,
    LICENCE_URL,
    VERSION,
    to_corpus_dump,
    to_corpus_dump_string,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO_ROOT.parent / "ride" / "tei_all"


# ── Fixture helpers ──────────────────────────────────────────────────


def _minimal_review(**overrides) -> Review:
    base = dict(
        id="ride.13.7",
        issue="13",
        title="A Test Review",
        publication_date="2024-06-01",
        language="en",
        licence="http://creativecommons.org/licenses/by/4.0/",
    )
    base.update(overrides)
    return Review(**base)


# ── Top-level shape ──────────────────────────────────────────────────


def test_empty_corpus_emits_envelope_with_zero_reviews():
    dump = to_corpus_dump([], base_url="https://x.de", build_date="2024-08-01")
    assert dump == {
        "version": VERSION,
        "generated_at": "2024-08-01",
        "base_url": "https://x.de",
        "licence": {"name": LICENCE_NAME, "url": LICENCE_URL},
        "review_count": 0,
        "reviews": [],
    }


def test_dump_carries_top_level_licence_for_consumer_clarity():
    """N6: every machine-readable artefact names its licence explicitly.

    The CC-BY-4.0 statement at the top of corpus.json mirrors the
    per-review ``licence`` field in the TEI source so consumers do not
    have to scan 107 records to discover the terms of use.
    """
    dump = to_corpus_dump([_minimal_review()])
    assert dump["licence"]["name"] == "CC-BY-4.0"
    assert dump["licence"]["url"].startswith("https://creativecommons.org/licenses/by/4.0")


def test_review_count_matches_input_length():
    reviews = [_minimal_review(id=f"ride.{i}", issue="13") for i in range(5)]
    dump = to_corpus_dump(reviews)
    assert dump["review_count"] == 5
    assert len(dump["reviews"]) == 5


def test_review_field_names_pass_through():
    """Top-level Review fields land as JSON keys without renaming."""
    review = _minimal_review(keywords=("a", "b"))
    [r] = to_corpus_dump([review])["reviews"]
    assert r["id"] == "ride.13.7"
    assert r["issue"] == "13"
    assert r["title"] == "A Test Review"
    assert r["language"] == "en"
    assert r["keywords"] == ["a", "b"]


def test_tuples_become_lists():
    """All tuple sequences serialise as JSON arrays."""
    review = _minimal_review(keywords=("digital editions", "TEI"))
    [r] = to_corpus_dump([review])["reviews"]
    assert isinstance(r["keywords"], list)
    assert r["keywords"] == ["digital editions", "TEI"]


def test_none_fields_pass_through_as_null():
    review = _minimal_review()  # source_file omitted → None
    [r] = to_corpus_dump([review])["reviews"]
    assert r["source_file"] is None


# ── Discriminated unions ─────────────────────────────────────────────


def test_paragraph_block_carries_type_discriminator():
    section = Section(
        xml_id="s1",
        type=None,
        heading=None,
        level=1,
        blocks=(Paragraph(inlines=(Text(text="hello"),)),),
        subsections=(),
    )
    review = _minimal_review(body=(section,))
    [r] = to_corpus_dump([review])["reviews"]
    [block] = r["body"][0]["blocks"]
    assert block["__type"] == "Paragraph"


def test_inline_text_carries_type_discriminator():
    section = Section(
        xml_id="s1",
        type=None,
        heading=None,
        level=1,
        blocks=(Paragraph(inlines=(Text(text="hello"),)),),
        subsections=(),
    )
    review = _minimal_review(body=(section,))
    [r] = to_corpus_dump([review])["reviews"]
    [inline] = r["body"][0]["blocks"][0]["inlines"]
    assert inline == {"__type": "Text", "text": "hello"}


def test_inline_reference_carries_type_and_bucket():
    section = Section(
        xml_id="s1",
        type=None,
        heading=None,
        level=1,
        blocks=(
            Paragraph(
                inlines=(
                    Reference(
                        children=(Text(text="see §2"),),
                        target="#sec-2",
                        bucket="local",
                    ),
                )
            ),
        ),
        subsections=(),
    )
    review = _minimal_review(body=(section,))
    [r] = to_corpus_dump([review])["reviews"]
    [inline] = r["body"][0]["blocks"][0]["inlines"]
    assert inline["__type"] == "Reference"
    assert inline["target"] == "#sec-2"
    assert inline["bucket"] == "local"
    [child] = inline["children"]
    assert child == {"__type": "Text", "text": "see §2"}


def test_emphasis_inline_carries_type():
    section = Section(
        xml_id="s1",
        type=None,
        heading=None,
        level=1,
        blocks=(
            Paragraph(
                inlines=(
                    Emphasis(children=(Text(text="bold"),)),
                ),
            ),
        ),
        subsections=(),
    )
    review = _minimal_review(body=(section,))
    [r] = to_corpus_dump([review])["reviews"]
    [inline] = r["body"][0]["blocks"][0]["inlines"]
    assert inline["__type"] == "Emphasis"
    assert inline["children"][0]["__type"] == "Text"


def test_section_does_not_carry_type_discriminator():
    """Section is not a polymorphic union — no __type added."""
    section = Section(
        xml_id="s1", type=None, heading=None, level=1, blocks=(), subsections=()
    )
    review = _minimal_review(body=(section,))
    [r] = to_corpus_dump([review])["reviews"]
    assert "__type" not in r["body"][0]


def test_review_does_not_carry_type_discriminator():
    """Review is the document root, no need to discriminate."""
    [r] = to_corpus_dump([_minimal_review()])["reviews"]
    assert "__type" not in r


# ── String serialisation ─────────────────────────────────────────────


def test_to_corpus_dump_string_returns_loadable_json():
    s = to_corpus_dump_string([_minimal_review()])
    assert json.loads(s)["version"] == VERSION


def test_compact_indent_works():
    s = to_corpus_dump_string([_minimal_review()], indent=None)
    assert "\n  " not in s  # no pretty-print whitespace
    assert json.loads(s)["review_count"] == 1


def test_unicode_passes_through_unescaped():
    review = _minimal_review(title="Über das Münster")
    s = to_corpus_dump_string([review])
    assert "Über das Münster" in s
    assert json.loads(s)["reviews"][0]["title"] == "Über das Münster"


# ── Real-corpus integration ──────────────────────────────────────────


@pytest.mark.skipif(not CORPUS_DIR.exists(), reason="../ride/ corpus not checked out")
def test_real_corpus_review_round_trips_through_json():
    """Parse a real review, dump it, reload the JSON, verify shape.

    Uses 1641-tei.xml as the rich-metadata reference fixture (matches
    the JSON-LD smoke test) so any drift in the model's field set
    surfaces in both modules at once.
    """
    from src.parser.review import parse_review

    review = parse_review(CORPUS_DIR / "1641-tei.xml")
    dump = to_corpus_dump([review], base_url="https://ride.i-d-e.de")

    # Round-trip through JSON.
    reloaded = json.loads(json.dumps(dump))
    [r] = reloaded["reviews"]
    assert r["id"] == review.id
    assert r["issue"] == review.issue
    assert r["title"] == review.title
    assert isinstance(r["body"], list)
    assert isinstance(r["bibliography"], list)

    # Sanity: at least one block in body is a Paragraph (rich review).
    blocks = [b for sec in r["body"] for b in sec["blocks"]]
    assert any(b["__type"] == "Paragraph" for b in blocks)
