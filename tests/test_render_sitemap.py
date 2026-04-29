"""Tests for ``src.render.sitemap`` — Phase 12 R15 / A5.

The sitemap module has two layers; the tests follow that split:

* :func:`build_sitemap` is a pure XML formatter — it takes
  :class:`SitemapEntry` records. Tests use synthetic entries to pin the
  output shape (xmlns, ``<url>`` rows, ``<lastmod>`` filtering).
* :func:`collect_entries` walks the build's domain inputs. Pure-formatter
  tests (synthetic Reviews and aggregates) verify the URL scheme; one
  real-corpus integration test walks ``../ride/`` end-to-end so any
  drift in actual aggregator output surfaces here.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from src.model.review import Person, Review
from src.parser.datasets import ReviewerAggregate, TagAggregate
from src.render.editorial import EditorialPage
from src.render.sitemap import (
    SITEMAP_XMLNS,
    SitemapEntry,
    build_sitemap,
    collect_entries,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO_ROOT.parent / "ride" / "tei_all"


# ── Pure formatter ───────────────────────────────────────────────────


def test_empty_entries_produce_well_formed_urlset():
    xml = build_sitemap([])
    root = ET.fromstring(xml)
    assert root.tag == f"{{{SITEMAP_XMLNS}}}urlset"
    assert list(root) == []


def test_single_entry_emits_loc_and_lastmod():
    xml = build_sitemap([SitemapEntry(loc="https://x.de/", lastmod="2024-06-01")])
    root = ET.fromstring(xml)
    [url] = root
    assert url.find(f"{{{SITEMAP_XMLNS}}}loc").text == "https://x.de/"
    assert url.find(f"{{{SITEMAP_XMLNS}}}lastmod").text == "2024-06-01"


def test_lastmod_omitted_when_none():
    xml = build_sitemap([SitemapEntry(loc="https://x.de/")])
    root = ET.fromstring(xml)
    [url] = root
    assert url.find(f"{{{SITEMAP_XMLNS}}}lastmod") is None


def test_lastmod_omitted_when_not_w3c_date():
    """Freeform publication_date strings ('forthcoming') must not break the XML."""
    xml = build_sitemap([SitemapEntry(loc="https://x.de/", lastmod="forthcoming")])
    root = ET.fromstring(xml)
    [url] = root
    assert url.find(f"{{{SITEMAP_XMLNS}}}lastmod") is None


def test_lastmod_accepts_year_only_year_month_year_month_day_iso():
    """W3C datetime formats permitted by sitemap.org all pass through."""
    cases = ["2024", "2024-06", "2024-06-01", "2024-06-01T12:00:00Z"]
    for value in cases:
        xml = build_sitemap([SitemapEntry(loc="https://x.de/", lastmod=value)])
        root = ET.fromstring(xml)
        [url] = root
        assert url.find(f"{{{SITEMAP_XMLNS}}}lastmod").text == value


def test_special_characters_are_xml_escaped():
    xml = build_sitemap(
        [SitemapEntry(loc="https://x.de/?q=a&b=c<d>", lastmod=None)]
    )
    # Must parse cleanly even with ampersands and angle brackets in loc.
    root = ET.fromstring(xml)
    [url] = root
    assert url.find(f"{{{SITEMAP_XMLNS}}}loc").text == "https://x.de/?q=a&b=c<d>"


def test_entry_order_is_preserved():
    entries = [
        SitemapEntry(loc=f"https://x.de/p{i}/") for i in range(5)
    ]
    xml = build_sitemap(entries)
    root = ET.fromstring(xml)
    locs = [u.find(f"{{{SITEMAP_XMLNS}}}loc").text for u in root]
    assert locs == [f"https://x.de/p{i}/" for i in range(5)]


# ── collect_entries ──────────────────────────────────────────────────


def _review(rid: str, issue: str, *, pub_date: str = "2024-01-01") -> Review:
    return Review(
        id=rid,
        issue=issue,
        title=f"Review {rid}",
        publication_date=pub_date,
        language="en",
        licence="http://creativecommons.org/licenses/by/4.0/",
    )


def test_collect_requires_absolute_base_url():
    with pytest.raises(ValueError):
        collect_entries([], base_url="")


def test_collect_emits_top_level_indices_even_for_empty_corpus():
    entries = collect_entries([], base_url="https://x.de", build_date="2024-06-01")
    locs = [e.loc for e in entries]
    assert "https://x.de/" in locs
    assert "https://x.de/issues/" in locs
    assert "https://x.de/tags/" in locs
    assert "https://x.de/reviewers/" in locs
    assert "https://x.de/resources/" in locs


def test_collect_emits_one_entry_per_review_with_publication_date():
    reviews = [
        _review("ride.13.1", "13", pub_date="2024-06-01"),
        _review("ride.13.2", "13", pub_date="2024-07-15"),
    ]
    entries = collect_entries(
        reviews, base_url="https://x.de", build_date="2024-08-01"
    )
    by_loc = {e.loc: e.lastmod for e in entries}
    assert by_loc["https://x.de/issues/13/ride.13.1/"] == "2024-06-01"
    assert by_loc["https://x.de/issues/13/ride.13.2/"] == "2024-07-15"


def test_collect_skips_review_with_missing_id_or_issue():
    review = Review(
        id="",
        issue="",
        title="Fragment",
        publication_date="2024-06-01",
        language="en",
        licence="http://creativecommons.org/licenses/by/4.0/",
    )
    entries = collect_entries([review], base_url="https://x.de", build_date="2024-08-01")
    locs = [e.loc for e in entries]
    # Top-level indices still there, but no review URL was added.
    assert not any("/issues//" in loc for loc in locs)


def test_collect_emits_per_issue_index():
    entries = collect_entries(
        [], base_url="https://x.de", issues=["13", "14"], build_date="2024-08-01"
    )
    locs = [e.loc for e in entries]
    assert "https://x.de/issues/13/" in locs
    assert "https://x.de/issues/14/" in locs


def test_collect_emits_tag_detail_with_slugified_name():
    tag = TagAggregate(name="digital editions", display_name="Digital Editions",
                       review_ids=("ride.13.1",))
    entries = collect_entries(
        [], base_url="https://x.de", tag_aggregates=[tag], build_date="2024-08-01"
    )
    assert any(e.loc == "https://x.de/tags/digital-editions/" for e in entries)


def test_collect_emits_reviewer_detail_with_reviewer_slug():
    reviewer = ReviewerAggregate(
        person=Person(full_name="Jane Doe", forename="Jane", surname="Doe"),
        review_ids=("ride.13.1",),
    )
    entries = collect_entries(
        [], base_url="https://x.de", reviewer_aggregates=[reviewer],
        build_date="2024-08-01"
    )
    assert any(e.loc == "https://x.de/reviewers/doe-jane/" for e in entries)


def test_collect_emits_editorial_pages_with_last_updated_when_set():
    page = EditorialPage(
        slug="about", title="About", language="en",
        last_updated="2024-05-01", body_md="# About"
    )
    entries = collect_entries(
        [], base_url="https://x.de", editorials=[page], build_date="2024-08-01"
    )
    by_loc = {e.loc: e.lastmod for e in entries}
    assert by_loc["https://x.de/about/"] == "2024-05-01"


def test_collect_falls_back_to_build_date_when_editorial_has_no_last_updated():
    page = EditorialPage(
        slug="imprint", title="Imprint", language="en",
        last_updated=None, body_md="# Imprint"
    )
    entries = collect_entries(
        [], base_url="https://x.de", editorials=[page], build_date="2024-08-01"
    )
    by_loc = {e.loc: e.lastmod for e in entries}
    assert by_loc["https://x.de/imprint/"] == "2024-08-01"


# ── Real-corpus integration ──────────────────────────────────────────


@pytest.mark.skipif(not CORPUS_DIR.exists(), reason="../ride/ corpus not checked out")
def test_real_corpus_sitemap_round_trips_through_xml():
    """Walk the real corpus, build a sitemap, parse it back, sanity-check.

    Smoke verifies that the formatter handles every actual
    ``Review.publication_date`` string in the corpus without crashing,
    and that the resulting XML is well-formed.
    """
    from src.parser.datasets import aggregate_reviewers, aggregate_tags
    from src.parser.review import parse_review

    reviews = tuple(
        parse_review(p)
        for p in sorted(CORPUS_DIR.glob("*.xml"))[:20]
    )
    issues = sorted({r.issue for r in reviews if r.issue})
    entries = collect_entries(
        reviews,
        base_url="https://ride.i-d-e.de",
        issues=issues,
        tag_aggregates=aggregate_tags(reviews),
        reviewer_aggregates=aggregate_reviewers(reviews),
        build_date="2024-08-01",
    )

    xml = build_sitemap(entries)
    root = ET.fromstring(xml)  # raises if malformed
    assert root.tag == f"{{{SITEMAP_XMLNS}}}urlset"

    locs = [
        u.find(f"{{{SITEMAP_XMLNS}}}loc").text
        for u in root
    ]
    # Top-level indices.
    assert "https://ride.i-d-e.de/" in locs
    assert "https://ride.i-d-e.de/issues/" in locs
    # At least one per-review URL in the deployed scheme.
    assert any(
        loc.startswith("https://ride.i-d-e.de/issues/")
        and loc.count("/") == 6  # https:, '', host, issues, N, id, ''
        for loc in locs
    )
