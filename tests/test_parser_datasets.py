"""Tests for the cross-corpus aggregation datasets."""
from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree

from src.model.review import Affiliation, Author, Person, RelatedItem, Review
from src.parser.datasets import (
    ReviewerAggregate,
    ReviewedResourceAggregate,
    TagAggregate,
    aggregate_reviewed_resources,
    aggregate_reviewers,
    aggregate_tags,
)
from src.parser.review import parse_review


_RIDE = Path(__file__).resolve().parent.parent.parent / "ride" / "tei_all"


def _r(rid: str, **kw) -> Review:
    """Build a minimal Review with the fields the aggregator inspects."""
    return Review(
        id=rid,
        issue=kw.get("issue", "1"),
        title=kw.get("title", "T"),
        publication_date="2026",
        language="en",
        licence="cc-by",
        keywords=tuple(kw.get("keywords", ())),
        authors=tuple(kw.get("authors", ())),
        related_items=tuple(kw.get("related_items", ())),
    )


# -- Tags -----------------------------------------------------------------


def test_aggregate_tags_groups_case_insensitive():
    reviews = (
        _r("ride.1.1", keywords=("TEI", "edition")),
        _r("ride.1.2", keywords=("tei", "review")),
    )
    out = aggregate_tags(reviews)
    by_name = {t.name: t for t in out}
    assert by_name["tei"].count == 2
    assert set(by_name["tei"].review_ids) == {"ride.1.1", "ride.1.2"}
    assert by_name["edition"].count == 1
    assert by_name["review"].count == 1


def test_aggregate_tags_preserves_first_display_form():
    reviews = (
        _r("a", keywords=("TEI",)),
        _r("b", keywords=("tei",)),
    )
    out = aggregate_tags(reviews)
    by_name = {t.name: t for t in out}
    # First-encountered form survives as display_name.
    assert by_name["tei"].display_name == "TEI"


def test_aggregate_tags_skips_empty_keywords():
    reviews = (_r("a", keywords=("", "  ", "valid")),)
    out = aggregate_tags(reviews)
    assert len(out) == 1
    assert out[0].name == "valid"


def test_aggregate_tags_sorted_alphabetically():
    reviews = (_r("a", keywords=("zebra", "apple", "mango")),)
    out = aggregate_tags(reviews)
    assert [t.name for t in out] == ["apple", "mango", "zebra"]


# -- Reviewers ------------------------------------------------------------


def test_aggregate_reviewers_dedupes_by_orcid():
    """Same person via two different name spellings, same ORCID — one entry."""
    p1 = Person(full_name="Anna Smith", forename="Anna", surname="Smith",
                orcid="https://orcid.org/0000-0000-0000-0001")
    p2 = Person(full_name="A. Smith", forename="A.", surname="Smith",
                orcid="https://orcid.org/0000-0000-0000-0001")
    reviews = (
        _r("a", authors=(Author(person=p1),)),
        _r("b", authors=(Author(person=p2),)),
    )
    out = aggregate_reviewers(reviews)
    assert len(out) == 1
    assert out[0].count == 2
    assert set(out[0].review_ids) == {"a", "b"}


def test_aggregate_reviewers_falls_back_to_name_when_no_orcid():
    p = Person(full_name="No Orcid", forename="No", surname="Orcid", orcid=None)
    reviews = (_r("a", authors=(Author(person=p),)), _r("b", authors=(Author(person=p),)))
    out = aggregate_reviewers(reviews)
    assert len(out) == 1
    assert out[0].count == 2


def test_aggregate_reviewers_sorted_by_surname():
    pa = Person(full_name="Anne Adams", forename="Anne", surname="Adams")
    pz = Person(full_name="Zoe Zonder", forename="Zoe", surname="Zonder")
    pm = Person(full_name="Max Mueller", forename="Max", surname="Mueller")
    reviews = (
        _r("a", authors=(Author(person=pz),)),
        _r("b", authors=(Author(person=pa),)),
        _r("c", authors=(Author(person=pm),)),
    )
    out = aggregate_reviewers(reviews)
    assert [r.person.surname for r in out] == ["Adams", "Mueller", "Zonder"]


def test_aggregate_reviewers_captures_first_affiliation():
    p = Person(full_name="X Y", surname="Y", orcid="orc:1")
    reviews = (
        _r("a", authors=(Author(person=p, affiliation=Affiliation(org_name="Univ A")),)),
        _r("b", authors=(Author(person=p, affiliation=Affiliation(org_name="Univ B")),)),
    )
    out = aggregate_reviewers(reviews)
    assert out[0].affiliation_hint == "Univ A"


# -- Reviewed resources ---------------------------------------------------


def test_aggregate_reviewed_resources_dedupes_by_target():
    ri1 = RelatedItem(type="reviewed_resource", bibl_text="Edition X (v1)",
                     bibl_targets=("https://example.org/x",))
    ri2 = RelatedItem(type="reviewed_resource", bibl_text="Edition X (v2)",
                     bibl_targets=("https://example.org/x",))
    reviews = (_r("a", related_items=(ri1,)), _r("b", related_items=(ri2,)))
    out = aggregate_reviewed_resources(reviews)
    assert len(out) == 1
    assert out[0].count == 2


def test_aggregate_reviewed_resources_filters_other_related_item_types():
    """`reviewing_criteria` and other types must not appear in the resource list."""
    ri_resource = RelatedItem(type="reviewed_resource", bibl_text="The Edition")
    ri_criteria = RelatedItem(type="reviewing_criteria", bibl_text="The Criteria")
    reviews = (_r("a", related_items=(ri_resource, ri_criteria)),)
    out = aggregate_reviewed_resources(reviews)
    assert len(out) == 1
    assert out[0].title == "The Edition"


def test_aggregate_reviewed_resources_sorted_by_title():
    reviews = (
        _r("a", related_items=(RelatedItem(type="reviewed_resource", bibl_text="Zebra"),)),
        _r("b", related_items=(RelatedItem(type="reviewed_resource", bibl_text="Apple"),)),
    )
    out = aggregate_reviewed_resources(reviews)
    assert [r.title for r in out] == ["Apple", "Zebra"]


def test_aggregate_reviewed_resources_no_related_items_yields_empty():
    out = aggregate_reviewed_resources((_r("a"), _r("b")))
    assert out == ()


# -- Real-corpus smoke ----------------------------------------------------


@pytest.mark.skipif(not _RIDE.exists(), reason="../ride/ corpus not present")
def test_smoke_real_corpus_aggregates() -> None:
    """The full corpus aggregates to plausible magnitudes:
    - ~107 reviewers (one per review, with some reuse)
    - ~107 reviewed resources (one per review)
    - hundreds of tags after dedup."""
    files = sorted(_RIDE.glob("*-tei.xml"))
    reviews = tuple(parse_review(f) for f in files)

    tags = aggregate_tags(reviews)
    reviewers = aggregate_reviewers(reviews)
    resources = aggregate_reviewed_resources(reviews)

    assert isinstance(tags, tuple) and all(isinstance(t, TagAggregate) for t in tags)
    assert isinstance(reviewers, tuple) and all(isinstance(r, ReviewerAggregate) for r in reviewers)
    assert isinstance(resources, tuple) and all(isinstance(r, ReviewedResourceAggregate) for r in resources)

    # Bounds for sanity
    assert 50 <= len(tags) <= 1000, f"unexpected tag count: {len(tags)}"
    assert 30 <= len(reviewers) <= 200, f"unexpected reviewer count: {len(reviewers)}"
    assert 80 <= len(resources) <= 200, f"unexpected resource count: {len(resources)}"

    # Sums must equal corpus totals
    total_reviewer_attributions = sum(r.count for r in reviewers)
    assert total_reviewer_attributions >= len(files), (
        "every review should attribute at least one reviewer"
    )

    # Sort invariants
    assert [t.name for t in tags] == sorted(t.name for t in tags)
