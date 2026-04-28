"""Build CLI — ``python -m src.build``.

Walks the sibling ``../ride/tei_all/`` corpus, parses every TEI file
into a :class:`~src.model.review.Review`, and renders an HTML page per
review under ``site/issues/{issue}/{review_id}/``. Copies the static
asset tree and the original TEI file alongside each rendered page.

This is the Phase 8 entry point. The asset pipeline for embedded figures
(rewriting ``<graphic @url>`` to a deployed path and copying the image
file) belongs to Phase 7 and lands in the parser/render bridge — until
then, ``Figure.graphic_url`` carries the raw corpus path and broken
image links are an accepted v0 limitation.

Usage:

    python -m src.build               # build every review into site/
    python -m src.build --pdf         # also run the WeasyPrint pass (Phase 14)
    python -m src.build --reviews 5   # build only the first N reviews — for quick iteration
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Iterable, Optional

from src.model.review import Review
from src.parser.datasets import (
    aggregate_reviewed_resources,
    aggregate_reviewers,
    aggregate_tags,
)
from src.parser.review import parse_review
from src.render.aggregations import (
    render_index,
    render_issue,
    render_issues_overview,
    render_resources,
    render_reviewer,
    render_reviewers_overview,
    render_tag,
    render_tags_overview,
    reviewer_slug,
)
from src.render.editorial import discover_editorials, render_editorial
from src.render.html import REPO_ROOT, BuildInfo, SiteConfig, make_env, render_review, slugify
from src.render.issues_config import (
    IssueConfigError,
    discover_issue_configs,
    validate_issue_configs,
)

CORPUS_DIR = REPO_ROOT.parent / "ride" / "tei_all"
SITE_DIR = REPO_ROOT / "site"
STATIC_DIR = REPO_ROOT / "static"


def _build_info() -> BuildInfo:
    """Read the current commit from git if available; harmless dev fallback otherwise."""
    try:
        import subprocess

        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
        ).strip()
        date = subprocess.check_output(
            ["git", "show", "-s", "--format=%cI", "HEAD"], cwd=REPO_ROOT, text=True
        ).strip()
        return BuildInfo(commit=commit, commit_short=commit[:7], date=date)
    except Exception:
        return BuildInfo()


def _site_config(base_url: str = "") -> SiteConfig:
    return SiteConfig(
        title="RIDE — Reviews in Digital Editions",
        default_language="en",
        base_url=base_url,
        strings={},  # localised UI strings — Phase 9 wires them from content/
        build_info=_build_info(),
    )


def _render_one(path: Path, env, site: SiteConfig, out_root: Path) -> Review:
    """Parse one TEI file and write its rendered HTML page. Returns the Review."""
    review = parse_review(path)
    page_dir = out_root / "issues" / (review.issue or "0") / (review.id or path.stem)
    page_dir.mkdir(parents=True, exist_ok=True)

    html = render_review(review, site=site, env=env)
    (page_dir / "index.html").write_text(html, encoding="utf-8")

    # Drop the original TEI alongside, per requirements.md R3 (download).
    target_xml = page_dir / f"{review.id or path.stem}.xml"
    shutil.copyfile(path, target_xml)

    return review


def _render_editorials(env, site: SiteConfig, out_root: Path) -> int:
    """Render every ``content/*.md`` page to ``site/{slug}/index.html``."""
    written = 0
    for page in discover_editorials():
        page_dir = out_root / page.slug
        page_dir.mkdir(parents=True, exist_ok=True)
        html = render_editorial(page, site=site, env=env)
        (page_dir / "index.html").write_text(html, encoding="utf-8")
        written += 1
    return written


def _copy_static(out_root: Path) -> None:
    """Mirror static/ into site/static/ — CSS, JS, fonts."""
    target = out_root / "static"
    if target.exists():
        shutil.rmtree(target)
    if STATIC_DIR.exists():
        shutil.copytree(STATIC_DIR, target)


def _render_aggregations(
    reviews: tuple[Review, ...],
    env,
    site: SiteConfig,
    out_root: Path,
    issue_configs: Optional[dict] = None,
) -> int:
    """Build every aggregation page — home, issues, tags, reviewers, resources.

    Each page is written under ``site/<slug>/index.html`` so URLs end in
    a trailing slash and match the URL-Schema in ``docs/url-scheme.md``.
    Returns the number of pages written (informational).
    """
    pages = 0

    # Site root.
    (out_root / "index.html").write_text(
        render_index(reviews, site=site, env=env), encoding="utf-8"
    )
    pages += 1

    # Heftübersicht and per-issue.
    configs = issue_configs or {}
    issues_dir = out_root / "issues"
    issues_dir.mkdir(parents=True, exist_ok=True)
    (issues_dir / "index.html").write_text(
        render_issues_overview(reviews, site=site, env=env, issue_configs=configs),
        encoding="utf-8",
    )
    pages += 1

    seen_issues = sorted({r.issue for r in reviews if r.issue})
    for issue_no in seen_issues:
        d = issues_dir / issue_no
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(
            render_issue(issue_no, reviews, site=site, env=env, config=configs.get(issue_no)),
            encoding="utf-8",
        )
        pages += 1

    # Tags.
    tags_dir = out_root / "tags"
    tags_dir.mkdir(parents=True, exist_ok=True)
    (tags_dir / "index.html").write_text(
        render_tags_overview(reviews, site=site, env=env), encoding="utf-8"
    )
    pages += 1
    for tag in aggregate_tags(reviews):
        d = tags_dir / slugify(tag.name)
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(
            render_tag(tag, reviews, site=site, env=env), encoding="utf-8"
        )
        pages += 1

    # Reviewers.
    reviewers_dir = out_root / "reviewers"
    reviewers_dir.mkdir(parents=True, exist_ok=True)
    (reviewers_dir / "index.html").write_text(
        render_reviewers_overview(reviews, site=site, env=env), encoding="utf-8"
    )
    pages += 1
    for r in aggregate_reviewers(reviews):
        d = reviewers_dir / reviewer_slug(r)
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(
            render_reviewer(r, reviews, site=site, env=env), encoding="utf-8"
        )
        pages += 1

    # Reviewed resources.
    resources_dir = out_root / "resources"
    resources_dir.mkdir(parents=True, exist_ok=True)
    (resources_dir / "index.html").write_text(
        render_resources(reviews, site=site, env=env), encoding="utf-8"
    )
    pages += 1

    return pages


def _iter_corpus(corpus_dir: Path, limit: Optional[int]) -> Iterable[Path]:
    files = sorted(corpus_dir.glob("*.xml"))
    return files[:limit] if limit else files


def build(
    corpus_dir: Path = CORPUS_DIR,
    out_root: Path = SITE_DIR,
    limit: Optional[int] = None,
    base_url: str = "",
) -> int:
    """Run the build. Returns the number of review pages written."""
    if not corpus_dir.exists():
        raise FileNotFoundError(
            f"Corpus directory not found: {corpus_dir}. "
            f"In CI, ride is checked out as a sibling at ../ride."
        )

    out_root.mkdir(parents=True, exist_ok=True)
    site = _site_config(base_url=base_url)
    env = make_env()

    rendered: list[Review] = []
    failed: list[tuple[Path, Exception]] = []
    for path in _iter_corpus(corpus_dir, limit):
        try:
            rendered.append(_render_one(path, env, site, out_root))
        except Exception as exc:  # noqa: BLE001 — we want to keep building on per-file failure
            failed.append((path, exc))
            print(f"render failed: {path.name}: {exc}", file=sys.stderr)

    # Issue YAML configs — loaded once, validated against the parsed corpus.
    # R11: inconsistencies break the build with a clear error.
    issue_configs = discover_issue_configs()
    issue_errors = validate_issue_configs(issue_configs, tuple(rendered))
    if issue_errors:
        raise IssueConfigError(
            "issue YAML and TEI corpus disagree:\n  - "
            + "\n  - ".join(issue_errors)
        )

    editorials = _render_editorials(env, site, out_root)
    aggregations = _render_aggregations(
        tuple(rendered), env, site, out_root, issue_configs=issue_configs
    )

    _copy_static(out_root)

    if failed:
        print(f"\n{len(failed)} files failed to render", file=sys.stderr)

    if editorials:
        print(f"Wrote {editorials} editorial pages")
    print(f"Wrote {aggregations} aggregation pages")

    return len(rendered)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build the ride.i-d-e.de static site.")
    parser.add_argument("--reviews", type=int, default=None, help="Limit to first N reviews (for iteration)")
    parser.add_argument("--base-url", default="", help="Deploy URL prefix; empty for relative paths")
    parser.add_argument("--pdf", action="store_true", help="Also run the WeasyPrint PDF pass (Phase 14)")
    args = parser.parse_args(argv)

    if args.pdf:
        print("--pdf is a Phase 14 placeholder; no PDF rendered yet.", file=sys.stderr)

    written = build(limit=args.reviews, base_url=args.base_url)
    print(f"Wrote {written} review pages to {SITE_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
