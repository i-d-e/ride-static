"""Build CLI — ``python -m src.build``.

Walks the sibling ``../ride/tei_all/`` corpus, parses every TEI file
into a :class:`~src.model.review.Review`, and writes the full static
site tree under ``site/``: per-review HTML at
``issues/{issue}/{review_id}/index.html`` plus the original TEI as a
download sibling, optional WeasyPrint PDF (``--pdf``), editorial pages
from ``content/*.md``, aggregation pages (issues, tags, reviewers,
resources), the static asset tree, the OAI-PMH snapshot, the corpus
JSON dump, the sitemap, the redirect stubs, and the build report at
``site/api/build-info.json``.

The build runs in two passes: parse all reviews first (so the navigation
YAML can resolve its data-driven Issues dropdown against the full
corpus), then render every page. RelaxNG validation runs by default
before the build report is written; ``--no-validate`` skips it.

Usage:

    python -m src.build                           # build every review into site/
    python -m src.build --pdf                     # also produce a per-review PDF via WeasyPrint
    python -m src.build --linkcheck               # probe external bibliography URLs (slow, off by default)
    python -m src.build --matomo-url … --matomo-site-id …   # emit the cookieless tracker snippet
    python -m src.build --reviews 5               # build only the first N reviews — for quick iteration
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Iterable, Optional

from src.model.review import Review
from src.parser.assets import AssetReport, rewrite_figure_assets
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
from src.render.corpus_dump import LICENCE_NAME, LICENCE_URL, to_corpus_dump_string
from src.render.editorial import discover_editorials, discover_home_widgets, render_editorial
from src.render.html import REPO_ROOT, BuildInfo, SiteConfig, make_env, render_review, slugify
from src.render.issues_config import (
    IssueConfigError,
    discover_issue_configs,
    validate_issue_configs,
)
from src.render.navigation import load_navigation, resolve_navigation
from src.render.oai_pmh import write_oai_pmh
from src.render.redirects import write_redirects
from src.render.sitemap import build_sitemap, collect_entries
from src.validate import validate_corpus

CORPUS_DIR = REPO_ROOT.parent / "ride" / "tei_all"
RIDE_ROOT = REPO_ROOT.parent / "ride"
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


def _site_config(
    base_url: str = "",
    matomo_url: str = "",
    matomo_site_id: str = "",
) -> SiteConfig:
    return SiteConfig(
        title="RIDE — Reviews in Digital Editions",
        default_language="en",
        base_url=base_url,
        strings={},  # localised UI strings — Phase 9 wires them from content/
        build_info=_build_info(),
        matomo_url=matomo_url,
        matomo_site_id=matomo_site_id,
    )


def _parse_one(
    path: Path,
    out_root: Path,
    ride_root: Path,
) -> tuple[Review, AssetReport]:
    """Parse one TEI file and copy its figures.

    Splitting parse from render lets the build resolve the navigation
    YAML against the full corpus before any HTML is written, so every
    page sees the populated Issues dropdown.
    """
    review = parse_review(path)
    review, report = rewrite_figure_assets(review, ride_root=ride_root, site_root=out_root)
    return review, report


def _render_review(
    path: Path,
    review: Review,
    env,
    site: SiteConfig,
    out_root: Path,
) -> None:
    """Write a parsed Review to ``site/issues/{N}/{id}/`` plus its TEI."""
    page_dir = out_root / "issues" / (review.issue or "0") / (review.id or path.stem)
    page_dir.mkdir(parents=True, exist_ok=True)

    html = render_review(review, site=site, env=env)
    (page_dir / "index.html").write_text(html, encoding="utf-8")

    # Drop the original TEI alongside, per requirements.md R3 (download).
    target_xml = page_dir / f"{review.id or path.stem}.xml"
    shutil.copyfile(path, target_xml)


def _site_with_navigation(site: SiteConfig, reviews: tuple[Review, ...]) -> SiteConfig:
    """Re-bind ``site`` with the resolved navigation tuple.

    SiteConfig is frozen, so we materialise a copy. Failure to load the
    YAML is fatal — the navigation file is part of the build contract.
    """
    items = load_navigation()
    resolved = resolve_navigation(items, reviews)
    return SiteConfig(
        title=site.title,
        default_language=site.default_language,
        base_url=site.base_url,
        strings=site.strings,
        build_info=site.build_info,
        navigation=resolved,
        matomo_url=site.matomo_url,
        matomo_site_id=site.matomo_site_id,
    )


def _render_editorials(
    env,
    site: SiteConfig,
    out_root: Path,
    parsed: Optional[list] = None,
) -> int:
    """Render every ``content/*.md`` page to ``site/{slug}/index.html``.

    ``parsed`` is the build's ``[(path, review), …]`` list. When given
    and the editorial page is the Data-Charts placeholder
    (``data/charts``), the chart marker is substituted by inline SVG
    bar charts derived from the parsed corpus (R9). All other pages
    render unchanged."""
    from src.render.charts import render_charts_block

    written = 0
    chart_html = ""
    for page in discover_editorials():
        if page.slug == "data/charts" and parsed and not chart_html:
            chart_html = render_charts_block(
                tuple(r for _, r in parsed), parsed_paths=parsed
            )
        page_dir = out_root / page.slug
        page_dir.mkdir(parents=True, exist_ok=True)
        html = render_editorial(
            page,
            site=site,
            env=env,
            chart_html=chart_html if page.slug == "data/charts" else "",
        )
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
    home_widgets: Optional[list] = None,
) -> int:
    """Build every aggregation page — home, issues, tags, reviewers, resources.

    Each page is written under ``site/<slug>/index.html`` so URLs end in
    a trailing slash and match the URL-Schema in ``docs/url-scheme.md``.
    Returns the number of pages written (informational).
    """
    pages = 0

    # Site root.
    (out_root / "index.html").write_text(
        render_index(reviews, site=site, env=env, home_widgets=home_widgets or []),
        encoding="utf-8",
    )
    pages += 1

    # Issue-Übersicht and per-issue.
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
    validate: bool = True,
    linkcheck: bool = False,
    matomo_url: str = "",
    matomo_site_id: str = "",
    pdf: bool = False,
) -> int:
    """Run the build. Returns the number of review pages written."""
    if not corpus_dir.exists():
        raise FileNotFoundError(
            f"Corpus directory not found: {corpus_dir}. "
            f"In CI, ride is checked out as a sibling at ../ride."
        )

    out_root.mkdir(parents=True, exist_ok=True)
    site = _site_config(
        base_url=base_url,
        matomo_url=matomo_url,
        matomo_site_id=matomo_site_id,
    )
    env = make_env()

    parsed: list[tuple[Path, Review]] = []
    asset_reports: list[AssetReport] = []
    failed: list[tuple[Path, Exception]] = []
    for path in _iter_corpus(corpus_dir, limit):
        try:
            review, report = _parse_one(path, out_root, ride_root=RIDE_ROOT)
            parsed.append((path, review))
            asset_reports.append(report)
        except Exception as exc:  # noqa: BLE001 — we want to keep building on per-file failure
            failed.append((path, exc))
            print(f"parse failed: {path.name}: {exc}", file=sys.stderr)

    rendered = [r for _, r in parsed]

    # Issue YAML configs — loaded once, validated against the parsed corpus.
    # R11: inconsistencies break the build with a clear error.
    issue_configs = discover_issue_configs()
    issue_errors = validate_issue_configs(issue_configs, tuple(rendered))
    if issue_errors:
        raise IssueConfigError(
            "issue YAML and TEI corpus disagree:\n  - "
            + "\n  - ".join(issue_errors)
        )

    # Navigation YAML resolved against the corpus so the Issues dropdown
    # carries the most recent issues. Re-bind site so all subsequent
    # render calls see the populated navigation tuple.
    site = _site_with_navigation(site, tuple(rendered))

    # Render pass — every HTML write happens after navigation is resolved.
    for path, review in parsed:
        try:
            _render_review(path, review, env, site, out_root)
        except Exception as exc:  # noqa: BLE001
            failed.append((path, exc))
            print(f"render failed: {path.name}: {exc}", file=sys.stderr)

    editorials = _render_editorials(env, site, out_root, parsed=parsed)
    home_widgets = discover_home_widgets()
    aggregations = _render_aggregations(
        tuple(rendered), env, site, out_root,
        issue_configs=issue_configs,
        home_widgets=home_widgets,
    )

    _copy_static(out_root)
    sitemap_written = _write_sitemap(tuple(rendered), site, out_root)
    _write_corpus_dump(tuple(rendered), site, out_root)
    oai_files = _write_oai_pmh_snapshot(tuple(rendered), site, out_root)
    redirect_count = write_redirects(tuple(rendered), out_root, base_url=site.base_url)

    pdf_count = 0
    pdf_failed: list[tuple[str, str]] = []
    if pdf:
        pdf_count, pdf_failed = _render_pdfs(parsed, out_root)

    # Phase 13 / Welle 10: validation + link-probe + aggregated build report.
    validation_report = None
    if validate:
        try:
            validation_report = validate_corpus(corpus_dir, RIDE_ROOT / "schema" / "ride.rng")
        except FileNotFoundError as exc:
            print(f"validation skipped: {exc}", file=sys.stderr)
    link_report = None
    if linkcheck:
        from src.linkcheck import probe_links

        link_report = probe_links(tuple(rendered))
    _write_build_info(
        out_root=out_root,
        site=site,
        reviews=tuple(rendered),
        asset_reports=asset_reports,
        failed=failed,
        validation_report=validation_report,
        link_report=link_report,
    )

    if failed:
        print(f"\n{len(failed)} files failed to render", file=sys.stderr)

    if editorials:
        print(f"Wrote {editorials} editorial pages")
    print(f"Wrote {aggregations} aggregation pages")
    if sitemap_written:
        print("Wrote sitemap.xml")
    print("Wrote api/corpus.json")
    if oai_files:
        print(f"Wrote {oai_files} OAI-PMH snapshot files")
    print(f"Wrote {redirect_count} legacy-URL redirect stubs")
    if validation_report:
        print(
            f"Validation: {validation_report.files_checked} files checked, "
            f"{validation_report.files_with_errors} with errors, "
            f"{len(validation_report.findings)} findings"
        )
    if link_report:
        print(f"Linkcheck: {link_report.alive} alive, {link_report.dead} dead "
              f"({link_report.probed} probed)")
    if pdf:
        print(f"PDF: {pdf_count} rendered, {len(pdf_failed)} failed")
    print("Wrote api/build-info.json")

    _print_asset_summary(asset_reports)

    return len(rendered)


def _render_pdfs(
    parsed: list,
    out_root: Path,
) -> tuple[int, list[tuple[str, str]]]:
    """Render every parsed review's HTML to a sibling PDF.

    Returns ``(success_count, failures)`` where ``failures`` is a list
    of ``(review_id, error_message)`` pairs. The whole pass surfaces
    cleanly (count = 0) when WeasyPrint or its system libraries
    cannot be loaded, so a missing GTK install on a developer machine
    does not block the rest of the build.

    Phase 14 / Welle 11. The HTML is read from disk so the print
    output reflects exactly what was deployed to the static tree —
    no separate template, no second render pass.
    """
    try:
        from src.render.pdf import render_review_pdf
    except (ImportError, OSError) as exc:
        print(
            "PDF: WeasyPrint unavailable, skipping. "
            f"Install instructions: https://doc.courtbouillon.org/weasyprint/  ({exc})",
            file=sys.stderr,
        )
        return 0, []

    count = 0
    failed: list[tuple[str, str]] = []
    for path, review in parsed:
        review_id = review.id or path.stem
        page_dir = out_root / "issues" / (review.issue or "0") / review_id
        html_path = page_dir / "index.html"
        if not html_path.exists():
            continue  # render pass skipped this review (already in `failed`)
        pdf_path = page_dir / f"{review_id}.pdf"
        try:
            render_review_pdf(html_path, pdf_path)
            count += 1
        except Exception as exc:  # noqa: BLE001 — keep building on per-file failure
            failed.append((review_id, str(exc)))
            print(f"PDF failed: {review_id}: {exc}", file=sys.stderr)
    return count, failed


def _write_build_info(
    *,
    out_root: Path,
    site: SiteConfig,
    reviews: tuple,
    asset_reports: list,
    failed: list,
    validation_report=None,
    link_report=None,
) -> None:
    """Write ``site/api/build-info.json`` — N7 aggregated build report.

    Captures:
      - build commit, date, base-URL
      - per-review counts (parsed, rendered, failed)
      - asset-pipeline summary (copied / missing / unparseable)
      - validation report (per-file warnings) if validation ran
      - link-probe report (dead URLs + Wayback snapshots) if linkcheck ran

    Phase 13 will surface this as a downloadable artefact in CI.
    """
    import json

    data = {
        "schema_version": 1,
        "licence": {"name": LICENCE_NAME, "url": LICENCE_URL},
        "site": {
            "title": site.title,
            "base_url": site.base_url,
            "default_language": site.default_language,
        },
        "build": {
            "commit": site.build_info.commit if site.build_info else None,
            "commit_short": site.build_info.commit_short if site.build_info else None,
            "date": site.build_info.date if site.build_info else None,
        },
        "reviews": {
            "rendered": len(reviews),
            "failed": [
                {"file": str(p.name), "error": str(exc)} for p, exc in failed
            ],
        },
        "assets": {
            "copied": sum(len(r.copied) for r in asset_reports),
            "missing": sum(len(r.missing) for r in asset_reports),
            "unparseable": sum(len(r.unparseable) for r in asset_reports),
        },
        "validation": validation_report.to_dict() if validation_report else None,
        "linkcheck": link_report.to_dict() if link_report else None,
    }
    api_dir = out_root / "api"
    api_dir.mkdir(parents=True, exist_ok=True)
    (api_dir / "build-info.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _write_oai_pmh_snapshot(
    reviews: tuple[Review, ...], site: SiteConfig, out_root: Path
) -> int:
    """Write the OAI-PMH snapshot under ``site/oai/`` if ``base_url`` is set.

    Like the sitemap, OAI-PMH identifiers and ``baseURL`` need an
    absolute origin, so dev builds without a deploy prefix skip silently.
    Returns the number of XML files written (0 when skipped).
    """
    if not site.base_url:
        return 0
    build_date = site.build_info.date if site.build_info else None
    return write_oai_pmh(
        reviews, base_url=site.base_url, out_root=out_root, build_date=build_date
    )


def _write_corpus_dump(reviews: tuple[Review, ...], site: SiteConfig, out_root: Path) -> None:
    """Write the full-corpus JSON dump to ``site/api/corpus.json``.

    Per requirements R15 / A5 the dump is always written — unlike
    sitemap.xml it does not require an absolute base_url. Consumers
    receive the corpus as one self-describing file.
    """
    api_dir = out_root / "api"
    api_dir.mkdir(parents=True, exist_ok=True)
    build_date = site.build_info.date if site.build_info else None
    payload = to_corpus_dump_string(
        reviews,
        base_url=site.base_url,
        build_date=build_date,
        indent=None,  # compact production dump
    )
    (api_dir / "corpus.json").write_text(payload, encoding="utf-8")


def _write_sitemap(reviews: tuple[Review, ...], site: SiteConfig, out_root: Path) -> bool:
    """Build and write ``site/sitemap.xml`` if a base_url is configured.

    Sitemaps require absolute URLs, so dev builds without a deploy prefix
    skip silently. CI passes ``--base-url`` and gets a real sitemap.
    Returns whether a file was written.
    """
    if not site.base_url:
        return False

    issues = sorted({r.issue for r in reviews if r.issue})
    tag_aggregates = aggregate_tags(reviews)
    reviewer_aggregates = aggregate_reviewers(reviews)
    editorials = discover_editorials()
    build_date = site.build_info.date if site.build_info else None

    entries = collect_entries(
        reviews,
        base_url=site.base_url,
        issues=issues,
        tag_aggregates=tag_aggregates,
        reviewer_aggregates=reviewer_aggregates,
        editorials=editorials,
        build_date=build_date,
    )
    (out_root / "sitemap.xml").write_text(build_sitemap(entries), encoding="utf-8")
    return True


def _print_asset_summary(reports: list[AssetReport]) -> None:
    """Aggregate per-review AssetReports into one build-summary line.

    Per-review missing/unparseable lists go to stderr so CI surfaces them
    without polluting the success output. Phase 13 will turn this into
    structured warnings tied to the validation pipeline.
    """
    total_copied = sum(len(r.copied) for r in reports)
    total_missing = sum(len(r.missing) for r in reports)
    total_unparseable = sum(len(r.unparseable) for r in reports)
    print(
        f"Assets: copied {total_copied}, "
        f"missing {total_missing}, unparseable {total_unparseable}"
    )
    for report in reports:
        if report.missing or report.unparseable:
            for url in report.missing:
                print(f"  asset missing: {report.review_id}: {url}", file=sys.stderr)
            for url in report.unparseable:
                print(f"  asset url-unparseable: {report.review_id}: {url}", file=sys.stderr)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build the ride.i-d-e.de static site.")
    parser.add_argument("--reviews", type=int, default=None, help="Limit to first N reviews (for iteration)")
    parser.add_argument("--base-url", default="", help="Deploy URL prefix; empty for relative paths")
    parser.add_argument("--pdf", action="store_true", help="Render a PDF next to every review's HTML via WeasyPrint")
    parser.add_argument("--no-validate", action="store_true", help="Skip the RelaxNG validation pre-check")
    parser.add_argument("--linkcheck", action="store_true", help="Probe external bibliography URLs (slow ~5min, off by default)")
    parser.add_argument("--matomo-url", default="", help="Matomo tracker URL (e.g. https://matomo.example.org/); empty disables tracking")
    parser.add_argument("--matomo-site-id", default="", help="Matomo site id; required when --matomo-url is set")
    args = parser.parse_args(argv)

    if bool(args.matomo_url) != bool(args.matomo_site_id):
        parser.error("--matomo-url and --matomo-site-id must be set together")

    written = build(
        limit=args.reviews,
        base_url=args.base_url,
        validate=not args.no_validate,
        linkcheck=args.linkcheck,
        matomo_url=args.matomo_url,
        matomo_site_id=args.matomo_site_id,
        pdf=args.pdf,
    )
    print(f"Wrote {written} review pages to {SITE_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
