"""Build CLI — ``python -m src.build``.

Walks the in-repo ``issues/*/reviews/`` corpus, parses every TEI file
into a :class:`~src.model.review.Review`, and writes the full static
site tree under ``site/``: per-review HTML at
``issues/{issue}/{review_id}/index.html`` plus the original TEI as a
download sibling, optional WeasyPrint PDF (``--pdf``), editorial pages
from ``pages/*.xml`` (TEI; ``content/*.md`` as fallback), aggregation pages (issues, tags, reviewers,
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
from src.parser.page import discover_pages
from src.parser.review import parse_review
from src.render.aggregations import (
    render_explore,
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
from src.render.explorer import to_explorer_dump_string
from src.render.editorial import discover_editorials, discover_home_widgets, render_editorial
from src.render.factsheet import render_factsheet
from src.render.html import REPO_ROOT, BuildInfo, SiteConfig, make_env, render_review, slugify
from src.render.issues_config import (
    IssueConfigError,
    discover_issue_configs,
    find_duplicate_review_dois,
    validate_issue_configs,
    validate_review_ids,
    validate_review_locations,
)
from src.render.navigation import load_navigation, resolve_navigation
from src.render.oai_pmh import write_oai_pmh
from src.render.page import render_page
from src.render.redirects import write_redirects
from src.render.sitemap import build_sitemap, collect_entries
from src.validate import validate_corpus

CORPUS_DIR = REPO_ROOT / "issues"
# Issue-Bilder bleiben (vorerst) im Schwester-Repo ../ride/. Die Asset-Pipeline
# degradiert sauber, wenn der Pfad fehlt — fehlende Bilder erscheinen im
# Build-Report, brechen den Build aber nicht ab.
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


def _build_date(site: SiteConfig) -> Optional[str]:
    """The build commit date, or None when no BuildInfo is attached."""
    return site.build_info.date if site.build_info else None


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

    # Factsheet full page (R18) — /issues/{N}/{id}/factsheet/index.html.
    factsheet_dir = page_dir / "factsheet"
    factsheet_dir.mkdir(parents=True, exist_ok=True)
    (factsheet_dir / "index.html").write_text(
        render_factsheet(review, site=site, env=env), encoding="utf-8"
    )

    # Drop the original TEI alongside, per specification.md R3 (download).
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
    tei_editorials: bool = False,
) -> int:
    """Render the editorial pages to ``site/{slug}/index.html``.

    Two editorial source sets coexist. With ``tei_editorials`` (the
    deployed default — ``build()`` passes ``True``) the build renders the
    TEI editorial set under ``pages/*.xml`` via :func:`discover_pages` /
    :func:`render_page`: each TEI page takes precedence at its slug, and
    any Markdown editorial whose slug no TEI page produces is rendered as
    a fallback so no page disappears — the generator-native ``about``,
    ``data/charts``, ``data/questionnaires``, plus the rename-orphans
    (``projects-for-review``, ``submitting-a-review``). Passing
    ``--no-tei-editorials`` falls back to the legacy Markdown-only build.

    ``parsed`` is the build's ``[(path, review), …]`` list. When given
    and the editorial page is the Data-Charts placeholder
    (``data/charts``), the chart marker is substituted by inline SVG bar
    charts derived from the parsed corpus (R9)."""
    from src.render.charts import render_charts_block

    written = 0
    chart_html = ""

    def _chart_for(slug: str) -> str:
        nonlocal chart_html
        if slug == "data/charts" and parsed and not chart_html:
            chart_html = render_charts_block(
                tuple(r for _, r in parsed), parsed_paths=parsed
            )
        return chart_html if slug == "data/charts" else ""

    def _write(slug: str, html: str) -> None:
        nonlocal written
        page_dir = out_root / slug
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "index.html").write_text(html, encoding="utf-8")
        written += 1

    if tei_editorials:
        covered: set[str] = set()
        for page in discover_pages():
            _write(page.slug, render_page(page, site=site, env=env))
            covered.add(page.slug)
        for page in discover_editorials():
            if page.slug in covered:
                continue  # TEI page wins at this slug
            _write(
                page.slug,
                render_editorial(page, site=site, env=env, chart_html=_chart_for(page.slug)),
            )
        return written

    for page in discover_editorials():
        _write(
            page.slug,
            render_editorial(page, site=site, env=env, chart_html=_chart_for(page.slug)),
        )
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

    # Interactive data exploration (knowledge/exploration.md View 1).
    build_date = _build_date(site)
    data_dir = out_root / "data"
    explore_dir = data_dir / "explore"
    explore_dir.mkdir(parents=True, exist_ok=True)
    (explore_dir / "index.html").write_text(
        render_explore(reviews, site=site, env=env, build_date=build_date),
        encoding="utf-8",
    )
    pages += 1
    # The same payload as a reusable artefact next to the page.
    (data_dir / "explorer.json").write_text(
        to_explorer_dump_string(reviews, base_url=site.base_url, build_date=build_date),
        encoding="utf-8",
    )

    return pages


def _iter_corpus(corpus_dir: Path, limit: Optional[int]) -> Iterable[Path]:
    files = sorted(corpus_dir.glob("**/*-tei.xml"))
    return files[:limit] if limit else files


def _run_parse_pass(
    corpus_dir: Path,
    limit: Optional[int],
    out_root: Path,
) -> tuple[list[tuple[Path, Review]], list[AssetReport], list[tuple[Path, Exception]]]:
    """Walk every TEI under ``issues/{N}/reviews/``, parse it, and copy
    its referenced figures. Per-file failures are collected, not raised,
    so one broken TEI does not block the rest of the build.

    Returns ``(parsed, asset_reports, failed)`` where ``parsed`` is a
    list of ``(path, Review)`` pairs in corpus-iteration order.
    """
    parsed: list[tuple[Path, Review]] = []
    asset_reports: list[AssetReport] = []
    failed: list[tuple[Path, Exception]] = []
    for path in _iter_corpus(corpus_dir, limit):
        try:
            review, report = _parse_one(path, out_root, ride_root=RIDE_ROOT)
            parsed.append((path, review))
            asset_reports.append(report)
        except Exception as exc:  # noqa: BLE001 — keep building on per-file failure
            failed.append((path, exc))
            print(f"parse failed: {path.name}: {exc}", file=sys.stderr)
    return parsed, asset_reports, failed


def _check_corpus_consistency(
    parsed: list[tuple[Path, Review]],
    rendered: tuple[Review, ...],
) -> dict:
    """Validate that the parsed corpus is self-consistent and return the
    loaded issue YAML configs.

    Three hard checks plus one soft (warning) check:

    - **Folder ↔ ``biblScope @n``.** The TEI header is the canonical
      source for issue membership; the folder layout is convenience. A
      mismatch means an editor dropped a TEI in the wrong
      ``issues/{N}/`` folder — the build would otherwise quietly render
      it under the header's issue, surprising the editor.
    - **xml:id ↔ review DOI.** The DOI is the registered identifier; the
      xml:id must be its local form. A copied header bearing a foreign id
      (e.g. an issue-21 review still carrying ``ride.1.1``) misroutes the
      page URL and collides downstream — a hard error.
    - **Issue YAML ↔ corpus** (R11). Per-issue ``metadata.yaml`` must
      agree with what the TEI corpus actually contains.
    - **Duplicate review DOIs** (warning). Two reviews claiming one DOI is
      a mis-registration only the editors can resolve against the DOI
      registry, so the build warns rather than blocks.
    """
    location_errors = validate_review_locations(parsed)
    if location_errors:
        raise IssueConfigError(
            "TEI file location does not match its biblScope @n:\n  - "
            + "\n  - ".join(location_errors)
        )

    id_errors = validate_review_ids(parsed)
    if id_errors:
        raise IssueConfigError(
            "review xml:id does not match its registered DOI:\n  - "
            + "\n  - ".join(id_errors)
        )

    duplicate_dois = find_duplicate_review_dois(parsed)
    if duplicate_dois:
        print(
            "WARNING: reviews share a DOI — editorial fix needed "
            "(one page is overwritten if the issue also matches):\n  - "
            + "\n  - ".join(duplicate_dois),
            file=sys.stderr,
        )

    issue_configs = discover_issue_configs()
    issue_errors = validate_issue_configs(issue_configs, rendered)
    if issue_errors:
        raise IssueConfigError(
            "issue YAML and TEI corpus disagree:\n  - "
            + "\n  - ".join(issue_errors)
        )
    return issue_configs


def _run_render_pass(
    parsed: list[tuple[Path, Review]],
    env,
    site: SiteConfig,
    out_root: Path,
    failed: list[tuple[Path, Exception]],
) -> None:
    """Render every parsed Review to its per-review page. Per-file render
    failures are appended to ``failed`` (mutated in place) so the build
    finishes and reports them rather than aborting on one bad TEI.
    """
    for path, review in parsed:
        try:
            _render_review(path, review, env, site, out_root)
        except Exception as exc:  # noqa: BLE001
            failed.append((path, exc))
            print(f"render failed: {path.name}: {exc}", file=sys.stderr)


def _run_validation_layer(
    corpus_dir: Path,
    reviews: tuple[Review, ...],
    validate: bool,
    linkcheck: bool,
):
    """Run the optional pre-build validation (RelaxNG against
    ``schema/ride.rng``) and post-build link probe. Either can be off;
    both return report objects that are fed into ``build-info.json``.
    """
    validation_report = None
    if validate:
        try:
            validation_report = validate_corpus(corpus_dir, RIDE_ROOT / "schema" / "ride.rng")
        except FileNotFoundError as exc:
            print(f"validation skipped: {exc}", file=sys.stderr)

    link_report = None
    if linkcheck:
        from src.linkcheck import probe_links

        link_report = probe_links(reviews)
    return validation_report, link_report


def _print_build_summary(
    *,
    failed: list,
    editorials: int,
    aggregations: int,
    sitemap_written: bool,
    feed_written: bool,
    rss_written: bool,
    rdf_written: bool,
    feed_aliases: int,
    oai_files: int,
    redirect_count: int,
    validation_report,
    link_report,
    pdf: bool,
    pdf_count: int,
    pdf_failed: list,
    asset_reports: list,
) -> None:
    """Print the one-line-per-artefact summary to stdout, plus per-review
    failure detail to stderr. All files are already written; this only
    reports what happened.
    """
    if failed:
        print(f"\n{len(failed)} files failed to render", file=sys.stderr)

    if editorials:
        print(f"Wrote {editorials} editorial pages")
    print(f"Wrote {aggregations} aggregation pages")
    if sitemap_written:
        print("Wrote sitemap.xml")
    if feed_written:
        print("Wrote feed/atom.xml")
    if rss_written:
        print("Wrote feed/rss.xml")
    if rdf_written:
        print("Wrote feed/rdf.xml")
    if feed_aliases:
        print(f"Wrote {feed_aliases} legacy feed aliases")
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
        print(
            f"Linkcheck: {link_report.alive} alive, {link_report.dead} dead "
            f"({link_report.probed} probed)"
        )
    if pdf:
        print(f"PDF: {pdf_count} rendered, {len(pdf_failed)} failed")
    print("Wrote api/build-info.json")

    _print_asset_summary(asset_reports)


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
    tei_editorials: bool = True,
) -> int:
    """Run the build. Returns the number of review pages written.

    The flow is parse → consistency-check → render → aux-pages →
    machine-artefacts → optional-PDF → validation-layer → summary. Each
    step is a named helper so this function reads as a sequence and not
    as a script.
    """
    if not corpus_dir.exists():
        raise FileNotFoundError(
            f"Corpus directory not found: {corpus_dir}. "
            "Expected issues/{N}/reviews/*.xml in the repo."
        )

    out_root.mkdir(parents=True, exist_ok=True)
    site = _site_config(
        base_url=base_url,
        matomo_url=matomo_url,
        matomo_site_id=matomo_site_id,
    )
    env = make_env()

    # Parse every TEI; collect Reviews, asset reports, and parse failures.
    parsed, asset_reports, failed = _run_parse_pass(corpus_dir, limit, out_root)
    rendered = tuple(r for _, r in parsed)

    # Consistency: folder ↔ biblScope @n; issue YAML ↔ corpus. Hard errors.
    issue_configs = _check_corpus_consistency(parsed, rendered)

    # Navigation YAML resolved against the parsed corpus, then re-bound
    # onto site so every subsequent render call sees the populated Issues
    # dropdown.
    site = _site_with_navigation(site, rendered)

    # Per-review HTML — render failures append to `failed`.
    _run_render_pass(parsed, env, site, out_root, failed)

    # Editorial pages, aggregation pages, static asset tree.
    editorials = _render_editorials(
        env, site, out_root, parsed=parsed, tei_editorials=tei_editorials
    )
    home_widgets = discover_home_widgets()
    aggregations = _render_aggregations(
        rendered, env, site, out_root,
        issue_configs=issue_configs,
        home_widgets=home_widgets,
    )
    _copy_static(out_root)

    # Machine-readable artefacts and legacy-URL redirects.
    sitemap_written = _write_sitemap(rendered, site, out_root)
    feed_written = _write_atom_feed(rendered, site, out_root)
    rss_written = _write_rss_feed(rendered, site, out_root)
    rdf_written = _write_rdf_feed(rendered, site, out_root)
    feed_aliases = _write_legacy_feed_aliases(out_root)
    _write_corpus_dump(rendered, site, out_root)
    oai_files = _write_oai_pmh_snapshot(rendered, site, out_root)
    redirect_count = write_redirects(rendered, out_root, base_url=site.base_url)

    # Optional PDF pass (Phase 14). Skipped silently when WeasyPrint is
    # unavailable on the host (typical Windows dev).
    pdf_count, pdf_failed = _render_pdfs(parsed, out_root) if pdf else (0, [])

    # Validation + linkcheck + aggregated build-info.json (Phase 13).
    validation_report, link_report = _run_validation_layer(
        corpus_dir, rendered, validate, linkcheck
    )
    _write_build_info(
        out_root=out_root,
        site=site,
        reviews=rendered,
        asset_reports=asset_reports,
        failed=failed,
        validation_report=validation_report,
        link_report=link_report,
    )

    _print_build_summary(
        failed=failed,
        editorials=editorials,
        aggregations=aggregations,
        sitemap_written=sitemap_written,
        feed_written=feed_written,
        rss_written=rss_written,
        rdf_written=rdf_written,
        feed_aliases=feed_aliases,
        oai_files=oai_files,
        redirect_count=redirect_count,
        validation_report=validation_report,
        link_report=link_report,
        pdf=pdf,
        pdf_count=pdf_count,
        pdf_failed=pdf_failed,
        asset_reports=asset_reports,
    )

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
            "date": _build_date(site),
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
    build_date = _build_date(site)
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
    build_date = _build_date(site)
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
    build_date = _build_date(site)

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


def _write_atom_feed(reviews: tuple[Review, ...], site: SiteConfig, out_root: Path) -> bool:
    """Write the Atom feed (``site/feed/atom.xml``) when a base_url is set.

    Like the sitemap, the feed's entry links need an absolute prefix, so
    dev builds without ``--base-url`` skip it. Returns whether a file was
    written.
    """
    from src.render.feed import write_atom_feed

    build_date = _build_date(site)
    return bool(
        write_atom_feed(
            reviews, base_url=site.base_url, out_root=out_root, build_date=build_date
        )
    )


def _write_rss_feed(reviews: tuple[Review, ...], site: SiteConfig, out_root: Path) -> bool:
    """Write the RSS 2.0 feed (``site/feed/rss.xml``) when a base_url is
    set — same deploy-only rule as the Atom feed."""
    from src.render.rss import write_rss_feed

    build_date = _build_date(site)
    return bool(
        write_rss_feed(
            reviews, base_url=site.base_url, out_root=out_root, build_date=build_date
        )
    )


def _write_rdf_feed(reviews: tuple[Review, ...], site: SiteConfig, out_root: Path) -> bool:
    """Write the RSS 1.0 feed (``site/feed/rdf.xml``) when a base_url is
    set — same deploy-only rule as its siblings."""
    from src.render.rdf import write_rdf_feed

    build_date = _build_date(site)
    return bool(
        write_rdf_feed(
            reviews, base_url=site.base_url, out_root=out_root, build_date=build_date
        )
    )


def _write_legacy_feed_aliases(out_root: Path) -> int:
    """Copy the feed XML to the legacy WP feed paths (no-op when the
    deploy-only feeds were skipped)."""
    from src.render.feed import write_legacy_feed_aliases

    return write_legacy_feed_aliases(out_root)


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
    parser.add_argument("--no-tei-editorials", action="store_false", dest="tei_editorials", help="Fall back to the legacy content/*.md Markdown editorials. By default the build renders the pages/*.xml TEI editorials with precedence (Markdown remains the fallback for slugs no TEI page covers).")
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
        tei_editorials=args.tei_editorials,
    )
    print(f"Wrote {written} review pages to {SITE_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
