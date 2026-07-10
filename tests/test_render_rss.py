"""Tests for the RSS 2.0 syndication feed.

Per CLAUDE.md test philosophy, the feed-shape tests are real-corpus
integration: they parse actual TEI reviews and assert the resulting RSS
document. ``_rfc822`` is a pure function (date string in, date string
out), so its unit test uses synthetic inputs documented as such.

Spec references: RSS 2.0 (rssboard.org) plus the RSS Best Practices
Profile — channel needs title/link/description, items carry guid with
explicit isPermaLink, pubDate is an RFC-822 date-time with timezone, and
the channel carries an ``atom:link rel="self"`` (W3C Feed Validator
warns without it).
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from src.render.rss import (
    _rfc822,
    build_rss_feed,
    write_rss_feed,
)

BASE = "/ride-static"

ATOM = "{http://www.w3.org/2005/Atom}"
# RFC-822 date-time as RSS requires it: english day/month names, four-digit
# year, full time, universally compatible timezone (+0000 / GMT).
_RFC822_RE = re.compile(
    r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun), \d{2} "
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) "
    r"\d{4} \d{2}:\d{2}:\d{2} (\+0000|-0000|GMT)$"
)


def _reviews(corpus_reviews, n: int = 8):
    """A slice of the shared real-corpus fixture (order-independent: the
    feed sorts newest-first internally)."""
    return list(corpus_reviews[:n])


def test_channel_has_required_and_recommended_elements(corpus_reviews):
    xml = build_rss_feed(_reviews(corpus_reviews), BASE)
    root = ET.fromstring(xml)
    assert root.tag == "rss"
    assert root.get("version") == "2.0"
    channel = root.find("channel")
    assert channel is not None
    # RSS 2.0 required trio.
    assert channel.findtext("title")
    assert channel.findtext("link") == "/ride-static/"
    assert channel.findtext("description")
    # Best-practice extras.
    assert channel.findtext("language") == "en"
    assert _RFC822_RE.match(channel.findtext("lastBuildDate"))
    self_link = channel.find(f"{ATOM}link")
    assert self_link is not None
    assert self_link.get("rel") == "self"
    assert self_link.get("href") == "/ride-static/feed/rss.xml"
    assert self_link.get("type") == "application/rss+xml"


def test_every_item_carries_title_link_guid_pubdate(corpus_reviews):
    reviews = _reviews(corpus_reviews)
    valid = [r for r in reviews if r.id and r.issue]
    xml = build_rss_feed(reviews, BASE)
    channel = ET.fromstring(xml).find("channel")
    items = channel.findall("item")
    assert len(items) == len(valid)
    for item in items:
        assert item.findtext("title")
        assert item.findtext("link", "").startswith("/ride-static/issues/")
        guid = item.find("guid")
        # Stable tag: URI as identifier, so isPermaLink must be false.
        assert guid is not None
        assert guid.get("isPermaLink") == "false"
        assert guid.text.startswith("tag:ride.i-d-e.de,2014:")
        assert _RFC822_RE.match(item.findtext("pubDate"))


def test_guid_matches_atom_entry_id(corpus_reviews):
    """RSS guid and Atom entry id use the same tag: URI, so a reader
    subscribed to both feeds deduplicates entries."""
    from src.render.feed import build_atom_feed

    reviews = _reviews(corpus_reviews, 5)
    rss = build_rss_feed(reviews, BASE)
    atom = build_atom_feed(reviews, BASE)
    guids = set(re.findall(r"<guid[^>]*>(.*?)</guid>", rss))
    atom_ids = set(re.findall(r"<id>(tag:[^<]*)</id>", atom)) - {
        "tag:ride.i-d-e.de,2014:feed/atom"
    }
    assert guids == atom_ids


def test_feed_respects_limit_and_orders_newest_first(corpus_reviews):
    xml = build_rss_feed(_reviews(corpus_reviews, 40), BASE, limit=5)
    channel = ET.fromstring(xml).find("channel")
    items = channel.findall("item")
    assert len(items) == 5
    # Same ordering contract as the Atom feed: the guid sequence must equal
    # the Atom entry-id sequence for the same input.
    from src.render.feed import build_atom_feed

    atom = build_atom_feed(_reviews(corpus_reviews, 40), BASE, limit=5)
    rss_guids = [g.findtext("guid") for g in items]
    atom_ids = re.findall(r"<entry>\s*<id>(.*?)</id>", atom)
    assert rss_guids == atom_ids


def test_feed_escapes_special_characters(corpus_reviews):
    """The document must be well-formed XML end to end — ET.fromstring in
    the other tests proves it, this one pins that raw ampersands never
    survive (the most common hand-built-feed validator error)."""
    xml = build_rss_feed(_reviews(corpus_reviews, 40), BASE, limit=40)
    text_content = re.sub(r"<[^>]+>", "", xml)
    assert not re.search(r"&(?!amp;|lt;|gt;|quot;|apos;|#)", text_content)


def test_write_rss_feed_writes_file(corpus_reviews, tmp_path: Path):
    n = write_rss_feed(_reviews(corpus_reviews), BASE, tmp_path)
    assert n == 1
    feed = tmp_path / "feed" / "rss.xml"
    assert feed.exists()
    assert feed.read_text(encoding="utf-8").startswith("<?xml")


def test_write_rss_feed_skips_without_base_url(tmp_path: Path):
    """Deploy-only artefact — no base_url means no feed, like Atom."""
    assert write_rss_feed([], "", tmp_path) == 0
    assert not (tmp_path / "feed" / "rss.xml").exists()


def test_rfc822_widens_partial_dates():
    """Pure function — synthetic inputs are the only data form (CLAUDE.md).

    Corpus dates come as YYYY / YYYY-MM / YYYY-MM-DD; RSS requires a full
    RFC-822 date-time, so missing granularity is pinned to midnight UTC on
    the first of the month/year (artificial precision, documented in the
    renderer)."""
    assert _rfc822("2026-03-15") == "Sun, 15 Mar 2026 00:00:00 +0000"
    assert _rfc822("2026-03") == "Sun, 01 Mar 2026 00:00:00 +0000"
    assert _rfc822("2020") == "Wed, 01 Jan 2020 00:00:00 +0000"
    assert _rfc822("") == "Sun, 01 Jun 2014 00:00:00 +0000"  # fallback
    assert _rfc822("n.d.") == "Sun, 01 Jun 2014 00:00:00 +0000"  # unparseable
