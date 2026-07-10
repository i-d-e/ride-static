"""RSS 1.0 (RDF Site Summary) syndication feed — third sibling next to
Atom (``feed.py``) and RSS 2.0 (``rss.py``).

Adversarial research (2026-07-10, see the redirects-feeds knowledge
document) found no active consumer that requires RSS 1.0 specifically;
the feed exists as a deliberate full-parity decision for a journal
publication, the WordPress predecessor served one and the cost is one
more static file. All three feeds share ordering, limit and data
sources.

Element choice follows the RSS 1.0 spec (web.resource.org/rss/1.0/):
the channel carries an ``rdf:about`` of the feed URL and lists its
items in an ``rdf:Seq`` whose ``rdf:li`` resources mirror the items'
``rdf:about`` URIs (the review URLs). Metadata uses the Dublin Core
module — the same vocabulary as the OAI-PMH snapshot — and dates are
W3CDTF, i.e. the RFC-3339 form the Atom feed already produces.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence
from xml.sax.saxutils import escape

from src.model.review import Review
from src.render.feed import (
    JOURNAL_TITLE,
    DEFAULT_LIMIT,
    _recent,
    _rfc3339,
)
from src.render.html import abstract_first_paragraph_text, review_url

FEED_PATH = "feed/rdf.xml"


def _item_xml(review: Review, base_url: str) -> str:
    url = review_url(review, base_url)
    lines = [
        f'  <item rdf:about="{escape(url)}">',
        f"    <title>{escape(review.title or review.id or '')}</title>",
        f"    <link>{escape(url)}</link>",
        f"    <dc:date>{_rfc3339(review.publication_date)}</dc:date>",
    ]
    for author in review.authors:
        name = author.person.full_name or ""
        if name:
            lines.append(f"    <dc:creator>{escape(name)}</dc:creator>")
    abstract = abstract_first_paragraph_text(review)
    if abstract:
        lines.append(f"    <description>{escape(abstract)}</description>")
    lines.append("  </item>")
    return "\n".join(lines)


def build_rdf_feed(
    reviews: Sequence[Review],
    base_url: str,
    build_date: Optional[str] = None,
    limit: int = DEFAULT_LIMIT,
) -> str:
    """Render the RSS 1.0 feed XML string for the most recent reviews."""
    recent = _recent(reviews, limit)
    feed_url = f"{base_url}/{FEED_PATH}"
    site_url = f"{base_url}/" if base_url else "/"
    updated = (
        max(_rfc3339(r.publication_date) for r in recent)
        if recent
        else _rfc3339(build_date or "")
    )
    seq = "\n".join(
        f'        <rdf:li rdf:resource="{escape(review_url(r, base_url))}"/>'
        for r in recent
    )
    items = "\n".join(_item_xml(r, base_url) for r in recent)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"'
        ' xmlns="http://purl.org/rss/1.0/"'
        ' xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
        f'  <channel rdf:about="{escape(feed_url)}">\n'
        f"    <title>{escape(JOURNAL_TITLE)}</title>\n"
        f"    <link>{escape(site_url)}</link>\n"
        "    <description>Latest reviews</description>\n"
        "    <dc:language>en</dc:language>\n"
        f"    <dc:date>{updated}</dc:date>\n"
        "    <items>\n"
        "      <rdf:Seq>\n"
        f"{seq}\n"
        "      </rdf:Seq>\n"
        "    </items>\n"
        "  </channel>\n"
        f"{items}\n"
        "</rdf:RDF>\n"
    )


def write_rdf_feed(
    reviews: Sequence[Review],
    base_url: str,
    out_root: Path,
    build_date: Optional[str] = None,
    limit: int = DEFAULT_LIMIT,
) -> int:
    """Write the RSS 1.0 feed to ``out_root/feed/rdf.xml``.

    Returns 1 if written, 0 if skipped. Deploy-only artefact like its
    siblings: item links need an absolute prefix, so dev builds without
    a ``base_url`` skip it cleanly.
    """
    if not base_url:
        return 0
    xml = build_rdf_feed(reviews, base_url, build_date=build_date, limit=limit)
    feed_file = out_root / "feed" / "rdf.xml"
    feed_file.parent.mkdir(parents=True, exist_ok=True)
    feed_file.write_text(xml, encoding="utf-8")
    return 1
