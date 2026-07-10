"""Tests for the Atom syndication feed (RFC 4287).

Per CLAUDE.md test philosophy, the feed-shape tests are real-corpus
integration: they parse actual TEI reviews and assert the resulting Atom
document. ``_rfc3339`` is a pure function (date string in, date string
out), so its unit test uses synthetic inputs documented as such.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from src.render.feed import (
    _rfc3339,
    build_atom_feed,
    write_atom_feed,
)

BASE = "/ride-static"

ATOM = "{http://www.w3.org/2005/Atom}"
# RFC 3339 date-time, the form Atom requires for atom:updated.
_RFC3339_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})$")


def _reviews(corpus_reviews, n: int = 8):
    """A slice of the shared real-corpus fixture (order-independent: the
    feed sorts newest-first internally)."""
    return list(corpus_reviews[:n])


def test_feed_has_required_feed_level_elements(corpus_reviews):
    xml = build_atom_feed(_reviews(corpus_reviews), BASE)
    assert '<feed xmlns="http://www.w3.org/2005/Atom">' in xml
    assert "<id>tag:ride.i-d-e.de,2014:feed/atom</id>" in xml
    assert "<title>" in xml and "</title>" in xml
    assert "<updated>" in xml
    assert '<link rel="self" href="/ride-static/feed/atom.xml"/>' in xml


def test_every_entry_carries_id_title_link_updated(corpus_reviews):
    reviews = _reviews(corpus_reviews)
    valid = [r for r in reviews if r.id and r.issue]
    xml = build_atom_feed(reviews, BASE)
    assert xml.count("<entry>") == len(valid)
    assert "tag:ride.i-d-e.de,2014:" in xml
    assert "/ride-static/issues/" in xml
    # feed-level updated plus one per entry
    assert xml.count("<updated>") == len(valid) + 1


def test_feed_respects_limit_and_orders_newest_first(corpus_reviews):
    xml = build_atom_feed(_reviews(corpus_reviews, 40), BASE, limit=5)
    assert xml.count("<entry>") == 5
    entry_dates = re.findall(r"<entry>.*?<updated>(.*?)</updated>", xml, re.DOTALL)
    assert entry_dates == sorted(entry_dates, reverse=True)


def test_feed_conforms_to_rfc4287_required_rules(corpus_reviews):
    """Algorithmic conformance check. Parse the feed (proving it is
    well-formed and namespaced) and assert the RFC 4287 MUST rules for the
    elements we emit: exactly one id/title/updated on the feed and on each
    entry, RFC 3339 datestamps, non-empty ids, and at least one entry link
    with an href. This encodes the spec rules rather than matching strings."""
    xml = build_atom_feed(_reviews(corpus_reviews, 12), BASE, limit=12)
    root = ET.fromstring(xml)

    assert root.tag == f"{ATOM}feed"
    assert len(root.findall(f"{ATOM}id")) == 1
    assert len(root.findall(f"{ATOM}title")) == 1
    assert len(root.findall(f"{ATOM}updated")) == 1
    assert root.findtext(f"{ATOM}id")
    assert _RFC3339_RE.match(root.findtext(f"{ATOM}updated"))

    entries = root.findall(f"{ATOM}entry")
    assert entries
    for e in entries:
        assert len(e.findall(f"{ATOM}id")) == 1
        assert len(e.findall(f"{ATOM}title")) == 1
        assert len(e.findall(f"{ATOM}updated")) == 1
        assert e.findtext(f"{ATOM}id")
        assert e.findtext(f"{ATOM}title")
        assert _RFC3339_RE.match(e.findtext(f"{ATOM}updated"))
        links = e.findall(f"{ATOM}link")
        assert links and all(link.get("href") for link in links)


def test_write_atom_feed_writes_file(corpus_reviews, tmp_path: Path):
    n = write_atom_feed(_reviews(corpus_reviews), BASE, tmp_path)
    assert n == 1
    feed = tmp_path / "feed" / "atom.xml"
    assert feed.exists()
    assert feed.read_text(encoding="utf-8").startswith("<?xml")


def test_write_atom_feed_skips_without_base_url(tmp_path: Path):
    """Deploy-only artefact — no base_url means no feed, like the sitemap."""
    assert write_atom_feed([], "", tmp_path) == 0
    assert not (tmp_path / "feed" / "atom.xml").exists()


def test_legacy_feed_aliases_copy_the_xml(corpus_reviews, tmp_path: Path):
    """The legacy WordPress feed URLs get the feed XML itself (readers
    fetch XML and ignore HTML redirect stubs): /feed/ (the canonical WP
    feed URL) and /feed/rss serve the RSS document, /feed/atom/ the Atom
    document."""
    from src.render.feed import write_legacy_feed_aliases
    from src.render.rdf import write_rdf_feed
    from src.render.rss import write_rss_feed

    write_atom_feed(_reviews(corpus_reviews), BASE, tmp_path)
    write_rss_feed(_reviews(corpus_reviews), BASE, tmp_path)
    write_rdf_feed(_reviews(corpus_reviews), BASE, tmp_path)
    n = write_legacy_feed_aliases(tmp_path)
    assert n == 4
    rss = (tmp_path / "feed" / "rss.xml").read_text(encoding="utf-8")
    atom = (tmp_path / "feed" / "atom.xml").read_text(encoding="utf-8")
    rdf = (tmp_path / "feed" / "rdf.xml").read_text(encoding="utf-8")
    assert (tmp_path / "feed" / "index.html").read_text(encoding="utf-8") == rss
    assert (tmp_path / "feed" / "rss" / "index.html").read_text(encoding="utf-8") == rss
    assert (tmp_path / "feed" / "atom" / "index.html").read_text(encoding="utf-8") == atom
    assert (tmp_path / "feed" / "rdf" / "index.html").read_text(encoding="utf-8") == rdf


def test_legacy_feed_aliases_skip_when_feeds_absent(tmp_path: Path):
    """Dev builds without base_url write no feeds, so no aliases either."""
    from src.render.feed import write_legacy_feed_aliases

    assert write_legacy_feed_aliases(tmp_path) == 0
    assert not (tmp_path / "feed").exists()


def test_rfc3339_widens_partial_dates():
    """Pure function — synthetic inputs are the only data form (CLAUDE.md)."""
    assert _rfc3339("2026-03-15") == "2026-03-15T00:00:00Z"
    assert _rfc3339("2026-03") == "2026-03-01T00:00:00Z"
    assert _rfc3339("2020") == "2020-01-01T00:00:00Z"
    assert _rfc3339("").endswith("T00:00:00Z")  # empty fallback
    assert _rfc3339("n.d.").endswith("T00:00:00Z")  # unparseable fallback
