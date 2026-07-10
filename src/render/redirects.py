"""WordPress-URL-Redirects (Welle 8.D).

Generates ``<meta http-equiv="refresh">`` stub pages at the old
WordPress paths so external links from the live ride.i-d-e.de era
keep landing on the correct new pages after the domain switches.

Three URL families need redirecting:

1. **Per-review URLs.** ``/issues/issue-{N}/{slug}/`` →
   ``/issues/{N}/{review_id}/``. The slug is the TEI filename stem
   (``arendt`` for ``arendt-tei.xml``); review-id is parsed from
   ``<TEI/@xml:id>``. The legacy factsheet sub-page
   ``/issues/issue-{N}/{slug}/factsheet`` redirects to its new
   ``/issues/{N}/{review_id}/factsheet/`` (R18).
2. **Per-issue URLs.** ``/issues/issue-{N}/`` → ``/issues/{N}/``.
3. **Editorial URLs.** A static map under
   :data:`EDITORIAL_REDIRECTS` covers the legacy menu paths whose slug
   actually changed (e.g. ``/about/copyright/`` → ``/imprint/``). Paths
   the new section hierarchy already matches (``/about/team/`` …) need
   no stub.

Per requirements R17 the URL contract is the static path under
``docs/url-scheme.md``; the redirects keep the legacy paths working
without polluting the new URL space.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from src.model.review import Review

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
    seen_issues: set[str] = set()
    for review in reviews:
        if not review.issue or not review.id:
            continue
        seen_issues.add(review.issue)
        # Slug from source filename: arendt-tei.xml → arendt.
        # source_file is a basename string (e.g. "arendt-tei.xml").
        if review.source_file:
            stem = review.source_file.rsplit(".", 1)[0]
            slug = stem[:-4] if stem.endswith("-tei") else stem
        else:
            slug = review.id  # fallback — should not happen in normal builds
        write_at(
            f"issues/issue-{review.issue}/{slug}",
            f"/issues/{review.issue}/{review.id}/",
        )
        # Legacy factsheet URL (R18) → new factsheet sub-page.
        write_at(
            f"issues/issue-{review.issue}/{slug}/factsheet",
            f"/issues/{review.issue}/{review.id}/factsheet/",
        )

    for issue_no in seen_issues:
        write_at(f"issues/issue-{issue_no}", f"/issues/{issue_no}/")

    return written
