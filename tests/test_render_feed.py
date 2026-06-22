"""Tests for the Atom syndication feed (RFC 4287).

Per CLAUDE.md test philosophy, the feed-shape tests are real-corpus
integration: they parse actual TEI reviews and assert the resulting Atom
document. ``_rfc3339`` is a pure function (date string in, date string
out), so its unit test uses synthetic inputs documented as such.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from src.parser.review import parse_review
from src.render.feed import (
    _rfc3339,
    build_atom_feed,
    write_atom_feed,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS = REPO_ROOT / "issues"
BASE = "/ride-static"

needs_corpus = pytest.mark.skipif(not CORPUS.is_dir(), reason="corpus not present")


def _reviews(n: int = 8):
    files = sorted(CORPUS.glob("**/*-tei.xml"))[:n]
    return [parse_review(f) for f in files]


@needs_corpus
def test_feed_has_required_feed_level_elements():
    xml = build_atom_feed(_reviews(), BASE)
    assert '<feed xmlns="http://www.w3.org/2005/Atom">' in xml
    assert "<id>tag:ride.i-d-e.de,2014:feed/atom</id>" in xml
    assert "<title>" in xml and "</title>" in xml
    assert "<updated>" in xml
    assert '<link rel="self" href="/ride-static/feed/atom.xml"/>' in xml


@needs_corpus
def test_every_entry_carries_id_title_link_updated():
    reviews = _reviews()
    valid = [r for r in reviews if r.id and r.issue]
    xml = build_atom_feed(reviews, BASE)
    assert xml.count("<entry>") == len(valid)
    assert "tag:ride.i-d-e.de,2014:" in xml
    assert "/ride-static/issues/" in xml
    # feed-level updated plus one per entry
    assert xml.count("<updated>") == len(valid) + 1


@needs_corpus
def test_feed_respects_limit_and_orders_newest_first():
    xml = build_atom_feed(_reviews(40), BASE, limit=5)
    assert xml.count("<entry>") == 5
    entry_dates = re.findall(r"<entry>.*?<updated>(.*?)</updated>", xml, re.DOTALL)
    assert entry_dates == sorted(entry_dates, reverse=True)


@needs_corpus
def test_write_atom_feed_writes_file(tmp_path: Path):
    n = write_atom_feed(_reviews(), BASE, tmp_path)
    assert n == 1
    feed = tmp_path / "feed" / "atom.xml"
    assert feed.exists()
    assert feed.read_text(encoding="utf-8").startswith("<?xml")


def test_write_atom_feed_skips_without_base_url(tmp_path: Path):
    """Deploy-only artefact — no base_url means no feed, like the sitemap."""
    assert write_atom_feed([], "", tmp_path) == 0
    assert not (tmp_path / "feed" / "atom.xml").exists()


def test_rfc3339_widens_partial_dates():
    """Pure function — synthetic inputs are the only data form (CLAUDE.md)."""
    assert _rfc3339("2026-03-15") == "2026-03-15T00:00:00Z"
    assert _rfc3339("2026-03") == "2026-03-01T00:00:00Z"
    assert _rfc3339("2020") == "2020-01-01T00:00:00Z"
    assert _rfc3339("").endswith("T00:00:00Z")  # empty fallback
    assert _rfc3339("n.d.").endswith("T00:00:00Z")  # unparseable fallback
