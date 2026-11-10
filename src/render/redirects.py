"""WordPress-URL-Redirects (Welle 8.D).

Generates ``<meta http-equiv="refresh">`` stub pages at the old
WordPress paths so external links from the live ride.i-d-e.de era
keep landing on the correct new pages after the domain switches.

Four URL families need redirecting:

1. **Per-review URLs.** ``/issues/issue-{N}/{slug}/`` →
   ``/issues/{N}/{review_id}/``. The old addresses come from three
   sources (:func:`review_legacy_paths`): the WordPress path recorded from
   the live sitemap per DOI (``config/legacy-urls.json``), the path of
   ``publicationStmt/idno[@type='URI']``, and the TEI filename stem. The
   stem alone missed every review whose WordPress slug differs from its
   file name (``carolingian-scholarship`` versus
   ``carolingian_scholarship``), which the parity check of 2026-11-10
   measured. The legacy factsheet sub-page ``…/factsheet`` redirects to
   ``/issues/{N}/{review_id}/factsheet/`` (R18).
2. **Per-issue URLs.** ``/issues/issue-{N}/`` → ``/issues/{N}/``.
3. **Tag archives.** ``/tag/{wp-slug}/`` → ``/tags/{slug}/``
   (:func:`tag_redirects`).
4. **Editorial URLs.** A static map under
   :data:`EDITORIAL_REDIRECTS` covers the legacy menu paths whose slug
   actually changed (e.g. ``/about/copyright/`` → ``/imprint/``). Paths
   the new section hierarchy already matches (``/about/team/`` …) need
   no stub.

Per requirements R17 the URL contract is the static path under
``docs/url-scheme.md``; the redirects keep the legacy paths working
without polluting the new URL space.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote, urlsplit

from src.model.review import Review
from src.render.html import slugify

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
# Recorded from the live WordPress sitemap by scripts/parity.py --write-legacy-urls.
LEGACY_URLS = REPO_ROOT / "config" / "legacy-urls.json"
LEGACY_HOST = "ride.i-d-e.de"

# Editorial paths from the live WordPress menu mapping to new slugs.
#
# The new editorial URLs mirror the old WordPress section hierarchy
# (/about/…, /reviewers/…), so most legacy paths now EQUAL their target
# and get NO entry: a stub there would overwrite the real page with one
# pointing to itself (endless reload). Only paths whose slug genuinely
# changed remain below. The self-redirect guard in write_at enforces this
# at runtime; test_no_editorial_redirect_points_to_itself enforces it on
# the data. The same guard also drops the unchanged top-level slugs
# (/about/, /ethical-code/, /data/) that already serve a real page.
EDITORIAL_REDIRECTS: dict[str, str] = {
    # Dynamically generated WP listing pages -> their static replacements.
    # The two charts pages merged into one page with per-set anchors; the
    # anchor slugs come from charts.CRITERIA_LABELS (pinned by test).
    "data/charts-scholarly-editions": "/data/charts/#chart-digital-editions-1.1",
    "data/charts-text-collections": "/data/charts/#chart-text-collections-1.0",
    "data/by-tag": "/tags/",
    "data/reviewed-resources": "/resources/",
    "reviewers/list-of-reviewers": "/reviewers/",
    "about/copyright": "/imprint/",
    "publishing-policies": "/about/publishing-policy/",
    "reviewers/submission": "/reviewers/submitting-a-review/",
    "reviewers/suggested-projects-for-review": "/reviewers/projects-for-review/",
    # The submission-guidelines / suggested-projects-for-review TEI pages were
    # consolidated onto the /reviewers/…/ URLs the navigation uses (twin
    # Markdown retired, 2026-07-17). The flat slugs those TEI pages formerly
    # rendered at keep landing on the new canonical URL.
    "submission-guidelines": "/reviewers/submitting-a-review/",
    "suggested-projects-for-review": "/reviewers/projects-for-review/",
    "reviewers/ride-award-for-best-review": "/reviewers/ride-award/",
    "reviewers/catalogue-criteria-for-reviewing-digital-editions-and-resources": "/criteria/",
}


def _redirect_html(target: str) -> str:
    """Minimal HTML 5 stub with meta-refresh + canonical link.

    Browsers honour the meta-refresh (delay 0 counts as a permanent
    redirect for Google and is the WCAG-2.2.1-conformant case); crawlers
    follow the canonical link. location.replace() is additive speed-up
    for JS clients and keeps the stub out of the back-button history;
    the manual link is the way out when everything else is ignored.
    """
    return (
        "<!doctype html>\n"
        '<html lang="en">\n<head>\n'
        '  <meta charset="utf-8">\n'
        f'  <meta http-equiv="refresh" content="0; url={target}">\n'
        f'  <link rel="canonical" href="{target}">\n'
        f'  <script>location.replace("{target}")</script>\n'
        f"  <title>Moved — {target}</title>\n"
        "</head>\n<body>\n"
        f'  <p>This page has moved to <a href="{target}">{target}</a>.</p>\n'
        "</body>\n</html>\n"
    )


def write_redirects(
    reviews: Iterable[Review],
    out_root: Path,
    base_url: str = "",
    legacy_urls: LegacyUrls | None = None,
) -> int:
    """Write all WordPress-style redirect stubs under ``out_root``.

    Returns the number of stubs written. ``base_url`` is prepended to
    every target so the redirect lands on the correct GitHub-Pages
    project path (e.g. ``/ride-static/issues/22/...``).
    """
    prefix = base_url.rstrip("/")
    written = 0

    def write_at(legacy_path: str, target: str) -> None:
        nonlocal written
        legacy = legacy_path.strip("/")
        if not legacy:
            return
        # A redirect whose legacy path equals its target would overwrite the
        # real page at that path with a stub that points to itself (endless
        # reload). Never emit one — independent of base_url, since both sides
        # carry the same prefix on the deployed site.
        if f"/{legacy}/" == target:
            return
        target_full = f"{prefix}{target}" if prefix else target
        out = out_root / legacy / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(_redirect_html(target_full), encoding="utf-8")
        written += 1

    # Editorial redirects.
    for legacy, target in EDITORIAL_REDIRECTS.items():
        write_at(legacy, target)

    # Per-review and per-issue redirects.
    table = load_legacy_urls() if legacy_urls is None else legacy_urls
    reviews = tuple(reviews)
    seen_issues: set[str] = set()
    for review in reviews:
        if not review.issue or not review.id:
            continue
        seen_issues.add(review.issue)
        for old in review_legacy_paths(review, table.reviews):
            write_at(old, f"/issues/{review.issue}/{review.id}/")
            # Legacy factsheet URL (R18) → new factsheet sub-page.
            write_at(f"{old}/factsheet", f"/issues/{review.issue}/{review.id}/factsheet/")

    # WordPress tag archives (/tag/{slug}/) -> the static tag pages.
    for old, target in tag_redirects(reviews, table.tags).items():
        write_at(old, target)

    for issue_no in seen_issues:
        write_at(f"issues/issue-{issue_no}", f"/issues/{issue_no}/")

    return written


@dataclass(frozen=True)
class LegacyUrls:
    """Addresses recorded from the live WordPress site (``config/legacy-urls.json``).

    ``reviews`` maps a lower-case DOI to the WordPress paths of that review;
    ``tags`` maps a WordPress tag path (``tag/{slug}``) to its tag label.
    """

    reviews: dict[str, list[str]] = field(default_factory=dict)
    tags: dict[str, str] = field(default_factory=dict)


def load_legacy_urls(path: Path = LEGACY_URLS) -> LegacyUrls:
    if not path.is_file():
        return LegacyUrls()
    data = json.loads(path.read_text(encoding="utf-8"))
    return LegacyUrls(
        reviews={doi.lower(): paths for doi, paths in data.get("reviews", {}).items()},
        tags=dict(data.get("tags", {})),
    )


def wordpress_slug(label: str) -> str:
    """Approximate WordPress ``sanitize_title`` for labels the live table lacks.

    Accents are folded, everything but ASCII letters and digits becomes a
    hyphen. The recorded table takes precedence because WordPress also
    de-duplicates slugs, which no function of the label alone can reproduce.
    """
    folded = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", folded.lower()).strip("-")


def tag_redirects(reviews: Iterable[Review], recorded: dict[str, str]) -> dict[str, str]:
    """``tag/{wp-slug}`` -> ``/tags/{slug}/`` for every tag WordPress served.

    Tags of published reviews redirect to their static tag page. A recorded
    WordPress tag that no TEI keyword carries (the consolidation of WordPress
    tags into TEI under specification A2 is still open) lands on the tag
    overview rather than on a 404.
    """
    by_label: dict[str, str] = {}
    for review in reviews:
        for kw in review.keywords:
            if slugify(kw):
                by_label.setdefault(kw.casefold(), f"/tags/{slugify(kw)}/")
    out: dict[str, str] = {}
    for label, target in by_label.items():
        out[f"tag/{wordpress_slug(label)}"] = target
    for path, label in recorded.items():
        out[path.strip("/")] = by_label.get(label.casefold(), "/tags/")
    return {k: v for k, v in out.items() if k != "tag/"}


def review_legacy_paths(review: Review, table: dict[str, list[str]]) -> list[str]:
    """Every old address of a review that must keep landing on its new page.

    Three sources, in order: the path the live WordPress sitemap lists for the
    review's DOI (``config/legacy-urls.json``, the evidence of what readers and
    links actually used); the path of ``publicationStmt/idno[@type='URI']``,
    which OAI records and DOI metadata print and which differs from the live
    path for some reviews; and the TEI file stem, the historical default the
    previous stubs used. Bundles fall back to their directory name.
    """
    paths: list[str] = []
    for p in table.get((review.doi or "").lower(), []):
        paths.append(p.strip("/"))
    if review.publication_uri:
        parts = urlsplit(review.publication_uri.strip())
        if parts.netloc.lower() == LEGACY_HOST and parts.path.strip("/"):
            paths.append(unquote(parts.path).strip("/"))
    if review.source_file:
        name = review.source_file
        if name.endswith("/review.xml"):
            slug = name[: -len("/review.xml")].rsplit("/", 1)[-1]
        else:
            stem = name.rsplit(".", 1)[0]
            slug = stem[:-4] if stem.endswith("-tei") else stem
    else:
        slug = review.id  # fallback — should not happen in normal builds
    paths.append(f"issues/issue-{review.issue}/{slug}")
    return list(dict.fromkeys(paths))
