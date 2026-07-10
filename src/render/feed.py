"""Atom 1.0 syndication feed — RFC 4287.

OAI-PMH harvests metadata and the sitemap feeds crawlers; this feed is the
one interface aimed at a *human* who wants to follow new reviews in a feed
reader. Like the sitemap and the OAI snapshot it is a static file built
once per build and served as-is. Entry links need an absolute origin, so a
dev build without a deploy ``base_url`` skips the feed.

Element choice follows RFC 4287: the feed carries ``id`` / ``title`` /
``updated``, each entry ``id`` / ``title`` / ``updated`` plus a link,
author and summary. Feed and entry ids are ``tag:`` URIs (RFC 4151) so
they stay stable regardless of host and need no absolute origin — the same
spirit as the OAI identifier scheme ``oai:ride.i-d-e.de:{id}``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence
from xml.sax.saxutils import escape

from src.model.review import Review
from src.render.html import abstract_first_paragraph_text, review_url

FEED_PATH = "feed/atom.xml"
TAG_AUTHORITY = "ride.i-d-e.de"
TAG_DATE = "2014"  # first RIDE issue — the date component of the tag: URIs
JOURNAL_TITLE = "RIDE — Reviews in Digital Editions"
DEFAULT_LIMIT = 20
_FALLBACK_DATETIME = f"{TAG_DATE}-06-01T00:00:00Z"


def _rfc3339(publication_date: str) -> str:
    """Widen a corpus date (``YYYY`` / ``YYYY-MM`` / ``YYYY-MM-DD``) to an
    RFC 3339 UTC datetime.

    Atom's ``atom:updated`` is an ``xsd:dateTime``, so a bare date is not
    enough; the missing granularity is pinned to midnight UTC on the first
    of the month/year. Unparseable values fall back to the earliest issue
    date so a reader always sees a sortable value.
    """
    if not publication_date:
        return _FALLBACK_DATETIME
    parts = publication_date.split("T")[0].split("-")
    if len(parts) == 3 and all(p.isdigit() for p in parts):
        return f"{parts[0]}-{parts[1]}-{parts[2]}T00:00:00Z"
    if len(parts) == 2 and all(p.isdigit() for p in parts):
        return f"{parts[0]}-{parts[1]}-01T00:00:00Z"
    if len(parts) == 1 and parts[0].isdigit() and len(parts[0]) == 4:
        return f"{parts[0]}-01-01T00:00:00Z"
    return _FALLBACK_DATETIME


def _recent(reviews: Sequence[Review], limit: int) -> list[Review]:
    """The ``limit`` newest reviews by publication date, newest first."""
    ordered = sorted(
        (r for r in reviews if r.id and r.issue),
        key=lambda r: _rfc3339(r.publication_date),
        reverse=True,
    )
    return ordered[:limit]


def _entry_xml(review: Review, base_url: str) -> str:
    url = review_url(review, base_url)
    entry_id = f"tag:{TAG_AUTHORITY},{TAG_DATE}:{review.id}"
    lines = [
        "  <entry>",
        f"    <id>{escape(entry_id)}</id>",
        f"    <title>{escape(review.title or review.id or '')}</title>",
        f'    <link href="{escape(url)}"/>',
        f"    <updated>{_rfc3339(review.publication_date)}</updated>",
    ]
    for author in review.authors:
        lines.append(
            f"    <author><name>{escape(author.person.full_name or '')}</name></author>"
        )
    abstract = abstract_first_paragraph_text(review)
    if abstract:
        lines.append(f"    <summary>{escape(abstract)}</summary>")
    lines.append("  </entry>")
    return "\n".join(lines)


def build_atom_feed(
    reviews: Sequence[Review],
    base_url: str,
    build_date: Optional[str] = None,
    limit: int = DEFAULT_LIMIT,
) -> str:
    """Render the Atom feed XML string for the most recent reviews."""
    recent = _recent(reviews, limit)
    feed_id = f"tag:{TAG_AUTHORITY},{TAG_DATE}:feed/atom"
    feed_url = f"{base_url}/{FEED_PATH}"
    site_url = f"{base_url}/" if base_url else "/"
    updated = (
        max(_rfc3339(r.publication_date) for r in recent)
        if recent
        else (build_date or _FALLBACK_DATETIME)
    )
    entries = "\n".join(_entry_xml(r, base_url) for r in recent)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<feed xmlns="http://www.w3.org/2005/Atom">\n'
        f"  <id>{escape(feed_id)}</id>\n"
        f"  <title>{escape(JOURNAL_TITLE)}</title>\n"
        "  <subtitle>Latest reviews</subtitle>\n"
        f'  <link rel="self" href="{escape(feed_url)}"/>\n'
        f'  <link rel="alternate" href="{escape(site_url)}"/>\n'
        f"  <updated>{updated}</updated>\n"
        f"  <author><name>{escape(JOURNAL_TITLE)}</name></author>\n"
        f"{entries}\n"
        "</feed>\n"
    )


def write_atom_feed(
    reviews: Sequence[Review],
    base_url: str,
    out_root: Path,
    build_date: Optional[str] = None,
    limit: int = DEFAULT_LIMIT,
) -> int:
    """Write the Atom feed to ``out_root/feed/atom.xml``.

    Returns 1 if written, 0 if skipped. Like the sitemap and OAI snapshot
    the feed needs an absolute ``base_url`` for its entry links, so it is a
    deploy-only artefact — dev builds without a prefix skip it cleanly.
    """
    if not base_url:
        return 0
    xml = build_atom_feed(reviews, base_url, build_date=build_date, limit=limit)
    feed_file = out_root / "feed" / "atom.xml"
    feed_file.parent.mkdir(parents=True, exist_ok=True)
    feed_file.write_text(xml, encoding="utf-8")
    return 1
