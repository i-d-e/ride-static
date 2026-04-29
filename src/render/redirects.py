"""WordPress-URL-Redirects (Welle 8.D).

Generates ``<meta http-equiv="refresh">`` stub pages at the old
WordPress paths so external links from the live ride.i-d-e.de era
keep landing on the correct new pages after the domain switches.

Three URL families need redirecting:

1. **Per-review URLs.** ``/issues/issue-{N}/{slug}/`` →
   ``/issues/{N}/{review_id}/``. The slug is the TEI filename stem
   (``arendt`` for ``arendt-tei.xml``); review-id is parsed from
   ``<TEI/@xml:id>``.
2. **Per-issue URLs.** ``/issues/issue-{N}/`` → ``/issues/{N}/``.
3. **Editorial URLs.** A static map under
   :data:`EDITORIAL_REDIRECTS` covers the live menu's stable paths
   (e.g. ``/about/team/`` → ``/team/``).

Per requirements R17 the URL contract is the static path under
``docs/url-scheme.md``; the redirects keep the legacy paths working
without polluting the new URL space.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from src.model.review import Review

# Editorial paths from the live WordPress menu mapping to new slugs.
# Both with and without trailing slash so either form redirects cleanly.
EDITORIAL_REDIRECTS: dict[str, str] = {
    "about": "/about/",
    "about/team": "/team/",
    "about/copyright": "/imprint/",
    "about/peer-reviewers": "/peer-reviewers/",
    "about/editorial": "/editorial/",
    "publishing-policies": "/publishing-policy/",
    "ethical-code": "/ethical-code/",
    "reviewers/call-for-reviews": "/call-for-reviews/",
    "reviewers/submission": "/submitting-a-review/",
    "reviewers/suggested-projects-for-review": "/projects-for-review/",
    "reviewers/ride-award-for-best-review": "/ride-award/",
    "reviewers/catalogue-criteria-for-reviewing-digital-editions-and-resources": "/criteria/",
    "data": "/data/",
}


def _redirect_html(target: str) -> str:
    """Minimal HTML 5 stub with meta-refresh + canonical link.

    Browsers honour the meta-refresh; crawlers follow the canonical
    link. Both belt and braces because some screen readers ignore
    meta-refresh and a manual link gives users a way out.
    """
    return (
        "<!doctype html>\n"
        '<html lang="en">\n<head>\n'
        '  <meta charset="utf-8">\n'
        f'  <meta http-equiv="refresh" content="0; url={target}">\n'
        f'  <link rel="canonical" href="{target}">\n'
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
        target_full = f"{prefix}{target}" if prefix else target
        legacy = legacy_path.strip("/")
        if not legacy:
            return
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

    for issue_no in seen_issues:
        write_at(f"issues/issue-{issue_no}", f"/issues/{issue_no}/")

    return written
