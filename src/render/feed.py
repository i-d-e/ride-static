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


_FALLBACK_DATE = (2014, 6, 1)  # first RIDE issue


def _date_parts(publication_date: str) -> tuple[int, int, int]:
    """Widen a corpus date (``YYYY`` / ``YYYY-MM`` / ``YYYY-MM-DD``) to a
    ``(year, month, day)`` tuple.

    Single source for the corpus date-widening rule shared by all three
    feed renderers: missing granularity is pinned to the first of the
    month/year, empty or unparseable values fall back to the earliest
    issue date so a reader always sees a sortable value.
    """
    if publication_date:
        parts = publication_date.split("T")[0].split("-")
        if all(p.isdigit() for p in parts):
            if len(parts) == 3:
                return int(parts[0]), int(parts[1]), int(parts[2])
            if len(parts) == 2:
                return int(parts[0]), int(parts[1]), 1
            if len(parts) == 1 and len(parts[0]) == 4:
                return int(parts[0]), 1, 1
    return _FALLBACK_DATE


def _rfc3339(publication_date: str) -> str:
    """Corpus date as RFC 3339 UTC datetime — Atom's ``atom:updated`` is an
    ``xsd:dateTime``, so a bare date is not enough."""
    year, month, day = _date_parts(publication_date)
    return f"{year:04d}-{month:02d}-{day:02d}T00:00:00Z"


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


# Legacy WordPress feed URL -> which feed XML serves it. /feed/ is the
# canonical WP feed URL (live probe 2026-07-10: /feed/rss 301s there),
# so it is the path existing subscriptions most likely point at.
LEGACY_FEED_ALIASES: dict[str, str] = {
    "feed/index.html": "feed/rss.xml",
    "feed/rss/index.html": "feed/rss.xml",
    "feed/atom/index.html": "feed/atom.xml",
    "feed/rdf/index.html": "feed/rdf.xml",
}


def write_legacy_feed_aliases(out_root: Path) -> int:
    """Copy the feed XML to the legacy WordPress feed paths.

    Feed readers fetch XML and ignore HTML meta-refresh stubs, so the only
    static way to keep old subscriptions alive is serving the XML itself at
    the old paths. Deliberate shortcut with a known ceiling: GitHub Pages
    types the copies text/html (extension-based), which most readers sniff
    past but none is guaranteed to; real 301s need the server layer at the
    domain switch (see knowledge/redirects-feeds.md). Returns the number of
    aliases written; sources missing (dev build without base_url) are
    skipped silently.
    """
    written = 0
    for alias, source in LEGACY_FEED_ALIASES.items():
        src = out_root / source
        if not src.is_file():
            continue
        dest = out_root / alias
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        written += 1
    return written


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
