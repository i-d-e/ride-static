"""RSS 2.0 syndication feed — sibling of the Atom feed in ``feed.py``.

Atom (RFC 4287) covers the technically strict readers; RSS 2.0 remains
the more widely assumed format among simple aggregators and legacy
clients, and the WordPress predecessor served one, so keeping it costs
little and preserves subscriber continuity. Both feeds share the same
data sources, ordering, limit and identifiers, a reader subscribed to
both deduplicates on the shared ``tag:`` URI.

Element choice follows the RSS 2.0 spec plus the RSS Best Practices
Profile (rssboard.org): channel carries the required title/link/
description plus ``language``, ``lastBuildDate`` and an
``atom:link rel="self"`` (the W3C Feed Validator warns without it);
items carry title/link/description, ``pubDate`` in RFC-822 form and a
``guid isPermaLink="false"`` holding the stable ``tag:`` URI. Escaping
is entity-based throughout (no CDATA), the same regime as the Atom
renderer.
"""
from __future__ import annotations

from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from typing import Optional, Sequence
from xml.sax.saxutils import escape

from src.model.review import Review
from src.render.feed import (
    JOURNAL_TITLE,
    TAG_AUTHORITY,
    TAG_DATE,
    DEFAULT_LIMIT,
    _FALLBACK_DATE,
    _date_parts,
    _recent,
    _rfc3339,
)
from src.render.html import abstract_first_paragraph_text, review_url

FEED_PATH = "feed/rss.xml"


def _rfc822(publication_date: str) -> str:
    """Corpus date as an RFC-822 date-time, the form RSS ``pubDate``
    requires (widening rule shared via ``feed._date_parts``).

    The pinned midnight is artificial precision forced by the format, not
    real knowledge. ``email.utils.format_datetime`` guarantees english
    day/month names regardless of locale and emits the universally
    compatible ``+0000`` timezone.
    """
    year, month, day = _date_parts(publication_date)
    try:
        dt = datetime(year, month, day, tzinfo=timezone.utc)
    except ValueError:  # out-of-range corpus value, e.g. month 13
        dt = datetime(*_FALLBACK_DATE, tzinfo=timezone.utc)
    return format_datetime(dt)


def _item_xml(review: Review, base_url: str) -> str:
    url = review_url(review, base_url)
    guid = f"tag:{TAG_AUTHORITY},{TAG_DATE}:{review.id}"
    lines = [
        "    <item>",
        f"      <title>{escape(review.title or review.id or '')}</title>",
        f"      <link>{escape(url)}</link>",
        f'      <guid isPermaLink="false">{escape(guid)}</guid>',
        f"      <pubDate>{_rfc822(review.publication_date)}</pubDate>",
    ]
    for author in review.authors:
        name = author.person.full_name or ""
        if name:
            lines.append(f"      <dc:creator>{escape(name)}</dc:creator>")
    abstract = abstract_first_paragraph_text(review)
    if abstract:
        lines.append(f"      <description>{escape(abstract)}</description>")
    lines.append("    </item>")
    return "\n".join(lines)


def build_rss_feed(
    reviews: Sequence[Review],
    base_url: str,
    build_date: Optional[str] = None,
    limit: int = DEFAULT_LIMIT,
) -> str:
    """Render the RSS 2.0 feed XML string for the most recent reviews."""
    recent = _recent(reviews, limit)
    feed_url = f"{base_url}/{FEED_PATH}"
    site_url = f"{base_url}/" if base_url else "/"
    # _rfc3339 is the sortable form both feeds agree on for "newest".
    last_build = (
        max((r.publication_date for r in recent), key=_rfc3339)
        if recent
        else (build_date or "")
    )
    items = "\n".join(_item_xml(r, base_url) for r in recent)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0"'
        ' xmlns:atom="http://www.w3.org/2005/Atom"'
        ' xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
        "  <channel>\n"
        f"    <title>{escape(JOURNAL_TITLE)}</title>\n"
        f"    <link>{escape(site_url)}</link>\n"
        "    <description>Latest reviews</description>\n"
        "    <language>en</language>\n"
        f"    <lastBuildDate>{_rfc822(last_build)}</lastBuildDate>\n"
        f'    <atom:link rel="self" type="application/rss+xml"'
        f' href="{escape(feed_url)}"/>\n'
        f"{items}\n"
        "  </channel>\n"
        "</rss>\n"
    )


def write_rss_feed(
    reviews: Sequence[Review],
    base_url: str,
    out_root: Path,
    build_date: Optional[str] = None,
    limit: int = DEFAULT_LIMIT,
) -> int:
    """Write the RSS feed to ``out_root/feed/rss.xml``.

    Returns 1 if written, 0 if skipped. Deploy-only artefact like the
    Atom feed: item links need an absolute prefix, so dev builds without
    a ``base_url`` skip it cleanly.
    """
    if not base_url:
        return 0
    xml = build_rss_feed(reviews, base_url, build_date=build_date, limit=limit)
    feed_file = out_root / "feed" / "rss.xml"
    feed_file.parent.mkdir(parents=True, exist_ok=True)
    feed_file.write_text(xml, encoding="utf-8")
    return 1
