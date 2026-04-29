"""sitemap.xml generation — Phase 12 R15 / A5.

The deployed site has six page-type families that crawlers should know
about: review pages, issue pages (overview + per-issue), tag pages,
reviewer pages, the resources table, and editorial Markdown pages.
Every URL goes into ``site/sitemap.xml`` per the protocol at
https://www.sitemaps.org/protocol.html so search engines can prioritise
crawling and surface lastmod hints.

Two layers:

* :func:`build_sitemap` is the pure XML formatter — takes
  :class:`SitemapEntry` records and returns the xmlns-stamped urlset.
  No model imports, no IO — easy to test in isolation.
* :func:`collect_entries` is the aggregator that translates the build's
  computed inputs (reviews, tag aggregates, reviewer aggregates, issue
  numbers, editorial pages) into entries. It owns the URL scheme and
  the per-entry ``lastmod`` rules.

The renderer in ``src.build`` calls :func:`collect_entries` once it has
all the inputs ready and writes the resulting XML to ``sitemap.xml``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence
from xml.sax.saxutils import escape

from src.model.review import Review
from src.parser.datasets import ReviewerAggregate, TagAggregate
from src.render.aggregations import reviewer_slug
from src.render.editorial import EditorialPage
from src.render.html import slugify


SITEMAP_XMLNS = "http://www.sitemaps.org/schemas/sitemap/0.9"

# W3C datetime: YYYY, YYYY-MM, YYYY-MM-DD, or full ISO 8601 with offset.
# Per https://www.w3.org/TR/NOTE-datetime — sitemaps accept any of these.
_W3C_DATE = re.compile(
    r"^\d{4}(-\d{2}(-\d{2}(T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+\-]\d{2}:\d{2}))?)?)?$"
)


@dataclass(frozen=True)
class SitemapEntry:
    """One ``<url>`` row in the sitemap."""

    loc: str
    lastmod: Optional[str] = None


def build_sitemap(entries: Iterable[SitemapEntry]) -> str:
    """Render entries to a sitemap XML string.

    The output is deterministic and stable for a fixed input — useful for
    diffing build artifacts in CI. Entries are emitted in the order
    received; sort upstream if a canonical order matters.
    """
    lines: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<urlset xmlns="{SITEMAP_XMLNS}">',
    ]
    for entry in entries:
        lines.append("  <url>")
        lines.append(f"    <loc>{escape(entry.loc)}</loc>")
        if entry.lastmod and _W3C_DATE.match(entry.lastmod):
            lines.append(f"    <lastmod>{escape(entry.lastmod)}</lastmod>")
        lines.append("  </url>")
    lines.append("</urlset>")
    lines.append("")  # trailing newline
    return "\n".join(lines)


def collect_entries(
    reviews: Sequence[Review],
    base_url: str,
    *,
    issues: Sequence[str] = (),
    tag_aggregates: Sequence[TagAggregate] = (),
    reviewer_aggregates: Sequence[ReviewerAggregate] = (),
    editorials: Sequence[EditorialPage] = (),
    build_date: Optional[str] = None,
) -> list[SitemapEntry]:
    """Walk the build's outputs and return one :class:`SitemapEntry` per page.

    ``base_url`` must be set; sitemaps require absolute URLs. The
    ``build_date`` is used as the fallback ``lastmod`` for pages without
    a per-entity date (aggregations, home). Per-review ``lastmod`` comes
    from ``Review.publication_date`` when it is a parsable W3C date.
    """
    if not base_url:
        raise ValueError("sitemap requires an absolute base_url; got empty string")

    entries: list[SitemapEntry] = []

    # Home + top-level aggregation indices.
    entries.append(SitemapEntry(loc=f"{base_url}/", lastmod=build_date))
    entries.append(SitemapEntry(loc=f"{base_url}/issues/", lastmod=build_date))
    entries.append(SitemapEntry(loc=f"{base_url}/tags/", lastmod=build_date))
    entries.append(SitemapEntry(loc=f"{base_url}/reviewers/", lastmod=build_date))
    entries.append(SitemapEntry(loc=f"{base_url}/resources/", lastmod=build_date))

    # Per-issue pages.
    for issue_no in issues:
        entries.append(
            SitemapEntry(loc=f"{base_url}/issues/{issue_no}/", lastmod=build_date)
        )

    # Per-review pages.
    for review in reviews:
        if not review.issue or not review.id:
            continue
        entries.append(
            SitemapEntry(
                loc=f"{base_url}/issues/{review.issue}/{review.id}/",
                lastmod=review.publication_date or build_date,
            )
        )

    # Tag detail pages.
    for tag in tag_aggregates:
        entries.append(
            SitemapEntry(
                loc=f"{base_url}/tags/{slugify(tag.name)}/",
                lastmod=build_date,
            )
        )

    # Reviewer detail pages.
    for reviewer in reviewer_aggregates:
        entries.append(
            SitemapEntry(
                loc=f"{base_url}/reviewers/{reviewer_slug(reviewer)}/",
                lastmod=build_date,
            )
        )

    # Editorial Markdown pages — last_updated wins over build_date when set.
    for page in editorials:
        entries.append(
            SitemapEntry(
                loc=f"{base_url}/{page.slug}/",
                lastmod=page.last_updated or build_date,
            )
        )

    return entries
