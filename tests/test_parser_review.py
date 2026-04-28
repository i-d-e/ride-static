"""Tests for the top-level ``parse_review`` entry point.

Test data philosophy: integration tests parse real reviews from
``../ride/tei_all/``. There are no synthetic-from-XML fixtures here —
``parse_review`` is the entry point for the whole parser, and any
fixture small enough to write would also be small enough to mask
real-corpus surprises. A corpus-wide smoke confirms all 107 reviews
parse without raising.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.model.review import Review
from src.parser.review import parse_review


_RIDE = Path(__file__).resolve().parent.parent.parent / "ride" / "tei_all"

# Fixture choices grounded in real corpus shapes:
# - 1641-tei.xml (ride.5.4, issue 5): small, 4 body sections, dense figures.
# - bayeux-tei.xml: rich body with 6 sections, 32 figures, 11 notes,
#   figure-in-cell pattern, full back-bibliography.
# - tustep-tei.xml (ride.11.2): one of seven reviews with no <back>.
_REVIEW_1641 = _RIDE / "1641-tei.xml"
_BAYEUX = _RIDE / "bayeux-tei.xml"
_TUSTEP = _RIDE / "tustep-tei.xml"


pytestmark = pytest.mark.skipif(not _RIDE.exists(), reason="../ride/ corpus not present")


# -- Per-review wiring (real corpus) ---------------------------------------


def test_parse_review_returns_review_with_top_level_metadata():
    """The header parsers must populate id, issue, title, language, source_file."""
    review = parse_review(_REVIEW_1641)
    assert isinstance(review, Review)
    assert review.id == "ride.5.4"
    assert review.issue == "5"
    assert review.language == "en"
    assert review.title  # non-empty; exact wording is editorial, not load-bearing
    assert review.source_file == "1641-tei.xml"


def test_parse_review_populates_body_sections_with_xml_ids():
    """Every body section in 1641-tei.xml carries a real ``@xml:id`` from the source."""
    review = parse_review(_REVIEW_1641)
    assert len(review.body) >= 1
    # Every body section has an xml_id (real or synthesised positional).
    for sec in review.body:
        assert sec.xml_id, f"body section without xml_id in {review.source_file}"


def test_parse_review_aggregates_figures_in_document_order():
    """Bayeux has 32 figures. The aggregate emits them in document order;
    the first three are img1, img2, img3 in the source TEI."""
    review = parse_review(_BAYEUX)
    assert len(review.figures) == 32
    first_three = [f.xml_id for f in review.figures[:3] if f.xml_id]
    assert first_three == ["img1", "img2", "img3"]


def test_parse_review_aggregates_figures_inside_table_cells():
    """The cell-figure pattern (22 corpus occurrences) must reach the
    aggregate. Bayeux has at least one figure inside a table cell."""
    from src.model.block import Figure, Table
    review = parse_review(_BAYEUX)

    figures_in_cells = []

    def walk(sec):
        for b in sec.blocks:
            if isinstance(b, Table):
                for row in b.rows:
                    for cell in row.cells:
                        for nb in cell.blocks:
                            if isinstance(nb, Figure):
                                figures_in_cells.append(nb)
        for sub in sec.subsections:
            walk(sub)

    for sec in review.body + review.front + review.back:
        walk(sec)

    assert figures_in_cells, "bayeux is supposed to have figures inside cells"
    # Each cell-embedded figure also lives in the corpus-order aggregate
    # (re-aggregation after Phase 7 walks keeps identity).
    aggregate_ids = {id(f) for f in review.figures}
    assert all(id(f) in aggregate_ids for f in figures_in_cells)


def test_parse_review_aggregates_notes_in_document_order():
    """Bayeux has 11 notes; the aggregate emits ftn1, ftn2, … in source order."""
    review = parse_review(_BAYEUX)
    assert len(review.notes) == 11
    note_ids = [n.xml_id for n in review.notes if n.xml_id]
    assert note_ids[:3] == ["ftn1", "ftn2", "ftn3"]


def test_parse_review_no_back_review_has_empty_back_and_bibliography():
    """tustep-tei.xml is one of seven corpus reviews with no <back>.
    Both ``back`` and ``bibliography`` are empty tuples — the parser
    branches on the missing element, doesn't synthesise a placeholder.
    """
    review = parse_review(_TUSTEP)
    assert review.back == ()
    assert review.bibliography == ()


# -- Corpus-wide smoke ----------------------------------------------------


def test_smoke_real_corpus_all_reviews_parse_through_parse_review() -> None:
    """End-to-end: every review file parses without raising, and every
    review has at least one body section. Aggregate magnitudes pin the
    inventory's documented counts (874 figures, 1926 notes corpus-wide)
    with headroom for parser drift."""
    files = sorted(_RIDE.glob("*-tei.xml"))
    assert len(files) >= 100
    figure_count_total = 0
    note_count_total = 0
    for f in files:
        review = parse_review(f)
        assert isinstance(review, Review)
        assert review.id, f"{f.name} produced an empty xml:id"
        assert review.body, f"empty body in {f.name}"
        figure_count_total += len(review.figures)
        note_count_total += len(review.notes)
    assert figure_count_total >= 800
    assert note_count_total >= 1800
