"""Tests for the RSS 1.0 (RDF) syndication feed.

Per CLAUDE.md test philosophy, the feed-shape tests are real-corpus
integration: they parse actual TEI reviews and assert the resulting RDF
document.

Spec reference: RDF Site Summary (RSS) 1.0 — the channel carries an
``rdf:about``, lists its items in an ``rdf:Seq`` whose ``rdf:li``
resources match the ``rdf:about`` of the item elements, and dates use
W3CDTF (``dc:date``), the same RFC-3339 form as the Atom feed.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from src.render.rdf import build_rdf_feed, write_rdf_feed

BASE = "/ride-static"

RDF = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}"
RSS1 = "{http://purl.org/rss/1.0/}"
DC = "{http://purl.org/dc/elements/1.1/}"
_W3CDTF_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def _reviews(corpus_reviews, n: int = 8):
    """A slice of the shared real-corpus fixture (order-independent: the
    feed sorts newest-first internally)."""
    return list(corpus_reviews[:n])


def test_channel_carries_about_title_link_description(corpus_reviews):
    xml = build_rdf_feed(_reviews(corpus_reviews), BASE)
    root = ET.fromstring(xml)
    assert root.tag == f"{RDF}RDF"
    channel = root.find(f"{RSS1}channel")
    assert channel is not None
    assert channel.get(f"{RDF}about") == "/ride-static/feed/rdf.xml"
    assert channel.findtext(f"{RSS1}title")
    assert channel.findtext(f"{RSS1}link") == "/ride-static/"
    assert channel.findtext(f"{RSS1}description")
    assert channel.findtext(f"{DC}language") == "en"


def test_seq_resources_match_item_abouts(corpus_reviews):
    """RSS 1.0 structural invariant: the channel's rdf:Seq lists exactly
    the rdf:about URIs of the item elements, in the same order."""
    xml = build_rdf_feed(_reviews(corpus_reviews), BASE)
    root = ET.fromstring(xml)
    seq = root.find(f"{RSS1}channel/{RSS1}items/{RDF}Seq")
    assert seq is not None
    resources = [li.get(f"{RDF}resource") for li in seq.findall(f"{RDF}li")]
    abouts = [item.get(f"{RDF}about") for item in root.findall(f"{RSS1}item")]
    assert resources == abouts
    assert resources, "feed must carry items"


def test_every_item_carries_title_link_date(corpus_reviews):
    reviews = _reviews(corpus_reviews)
    valid = [r for r in reviews if r.id and r.issue]
    xml = build_rdf_feed(reviews, BASE)
    root = ET.fromstring(xml)
    items = root.findall(f"{RSS1}item")
    assert len(items) == len(valid)
    for item in items:
        assert item.findtext(f"{RSS1}title")
        link = item.findtext(f"{RSS1}link")
        assert link and link.startswith("/ride-static/issues/")
        assert item.get(f"{RDF}about") == link
        assert _W3CDTF_RE.match(item.findtext(f"{DC}date"))


def test_item_order_matches_the_atom_feed(corpus_reviews):
    """All three feeds share the same ordering contract (newest first)."""
    from src.render.feed import build_atom_feed

    reviews = _reviews(corpus_reviews, 40)
    rdf = build_rdf_feed(reviews, BASE, limit=5)
    atom = build_atom_feed(reviews, BASE, limit=5)
    rdf_links = [
        i.findtext(f"{RSS1}link") for i in ET.fromstring(rdf).findall(f"{RSS1}item")
    ]
    atom_links = re.findall(r'<entry>\s*<id>.*?</id>\s*<title>.*?</title>\s*<link href="(.*?)"/>', atom)
    assert rdf_links == atom_links


def test_write_rdf_feed_writes_file(corpus_reviews, tmp_path: Path):
    n = write_rdf_feed(_reviews(corpus_reviews), BASE, tmp_path)
    assert n == 1
    feed = tmp_path / "feed" / "rdf.xml"
    assert feed.exists()
    assert feed.read_text(encoding="utf-8").startswith("<?xml")


def test_write_rdf_feed_skips_without_base_url(tmp_path: Path):
    """Deploy-only artefact — no base_url means no feed, like Atom/RSS."""
    assert write_rdf_feed([], "", tmp_path) == 0
    assert not (tmp_path / "feed" / "rdf.xml").exists()
