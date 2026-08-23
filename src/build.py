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

import yaml

from src._corpus import is_review_bundle, iter_tei_files
from src.model.review import Review
from src.parser.assets import AssetReport, rewrite_figure_assets
from src.parser.datasets import (
    aggregate_reviewers,
    aggregate_tags,
)
from src.parser.page import discover_pages
from src.parser.review import parse_review
from src.render.aggregations import (
    render_drafts,
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
from src.render.bibexport import write_bibliography_exports
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
from src.validate import ValidationReport, validate_corpus

CONTENT_DIR = REPO_ROOT / "content"
STRINGS_PATH = CONTENT_DIR / "strings.yaml"


class BuildFailure(RuntimeError):
    """Raised after the build report records one or more hard failures."""


# Vocabulary of localisable UI-string keys the templates consume via
# ``site.strings.<key> | default('…')`` or ``strings.get('<key>', '…')``.
# An override in content/strings.yaml for any other key is a typo and
# fails the build. Regenerate after adding/renaming a template label:
#   grep -rhoE "strings\.get\('[a-z_]+'|strings\.[a-z_]+" templates/html
# and reconcile; tests/test_strings_config.py greps the real templates
# and fails if this constant drifts from them.
STRING_KEYS: frozenset[str] = frozenset(
    {
        "abstract",
        "accessed",
        "amendment_original",
        "amendments",
        "apparate",
        "back_to_review",
        "cite",
        "cite_note",
        "contact",
        "copy_bibtex",
        "copy_csl",
        "criteria",
        "doi",
        "edited_by",
        "editors",
        "explanation",
        "factsheet",
        "answer",
        "figure_default",
        "figures",
        "full_factsheet",
        "imprint",
        "issue",
        "last_accessed",
        "last_updated",
        "licence",
        "licence_short",
        "main_navigation",
        "meta",
        "not_answered",
        "not_evaluated",
        "notes",
        "people",
        "published",
        "questionnaire",
        "references",
        "reviewed_by",
        "reviewed_resource",
        "sidebar",
        "skip_to_content",
        "tags",
        "title",
        "toc",
        "uri",
    }
)


def _load_strings(path: Path = STRINGS_PATH) -> dict:
    """Load the editorial UI-string overrides from ``content/strings.yaml``.

    Returns ``{}`` when the file is absent, empty, or all-commented — the
    override layer is optional and the shipped file carries every key as a
    comment, so the deployed output stays byte-identical. Any active key
    outside :data:`STRING_KEYS` fails the build (typo protection).
    """
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(
            f"{path.name}: expected a YAML mapping of string keys to labels, "
            f"got {type(data).__name__}"
        )
    unknown = set(data) - STRING_KEYS
    if unknown:
        raise ValueError(
            f"{path.name}: unknown UI-string key(s) {sorted(unknown)}. "
            f"Valid keys are the vocabulary in src.build.STRING_KEYS "
            f"({len(STRING_KEYS)} keys, mirrored from templates/html/)."
        )
    return data


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
        strings=_load_strings(),  # UI-string overrides from content/strings.yaml (empty when all-commented)
        build_info=_build_info(),
        matomo_url=matomo_url,
        matomo_site_id=matomo_site_id,
    )


def _parse_one(
    path: Path,
    out_root: Path,
    ride_root: Path,
    include_drafts: bool,
) -> tuple[Review, AssetReport]:
    """Parse one TEI file and copy its figures.

    Splitting parse from render lets the build resolve the navigation
    YAML against the full corpus before any HTML is written, so every
    page sees the populated Issues dropdown.
    """
    review = parse_review(path)
    review, report = rewrite_figure_assets(
        review,
        ride_root=ride_root,
        site_root=out_root,
        copy=include_drafts or not review.is_draft,
        source_path=path,
    )
    return review, report


def _render_review(
    path: Path,
    review: Review,
    env,
    site: SiteConfig,
    out_root: Path,
    pdf_available: bool,
) -> None:
    """Write a parsed Review to ``site/issues/{N}/{id}/`` plus its TEI."""
    page_dir = out_root / "issues" / (review.issue or "0") / (review.id or path.stem)
    page_dir.mkdir(parents=True, exist_ok=True)

    html = render_review(
        review,
        site=site,
        env=env,
        pdf_available=pdf_available,
    )
    (page_dir / "index.html").write_text(html, encoding="utf-8")

    # Factsheet full page (R18) — /issues/{N}/{id}/factsheet/index.html.
    factsheet_dir = page_dir / "factsheet"
    factsheet_dir.mkdir(parents=True, exist_ok=True)
    (factsheet_dir / "index.html").write_text(
        render_factsheet(
            review,
            site=site,
            env=env,
            pdf_available=pdf_available,
        ),
        encoding="utf-8",
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

    ``parsed`` is the build's ``[(path, review), …]`` list. When given,
    the Data-Charts page (``data/charts``) has its chart marker
    substituted by inline SVG bar charts (R9), and the Data-Questionnaires
    page (``data/questionnaires``) has its marker substituted by the
    per-question aggregate tables, both derived from the parsed corpus."""
    from src.render.charts import render_charts_block
    from src.render.questionnaires import render_questionnaires_html

    written = 0
    chart_html = ""
    quest_html = ""

    def _chart_for(slug: str) -> str:
        nonlocal chart_html
        if slug == "data/charts" and parsed and not chart_html:
            chart_html = render_charts_block(tuple(r for _, r in parsed), parsed_paths=parsed)
        return chart_html if slug == "data/charts" else ""

    def _questionnaires_for(slug: str) -> str:
        nonlocal quest_html
        if slug == "data/questionnaires" and parsed and not quest_html:
            quest_html = render_questionnaires_html(tuple(r for _, r in parsed))
        return quest_html if slug == "data/questionnaires" else ""

    def _write(slug: str, html: str) -> None:
        nonlocal written
        page_dir = out_root / slug
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "index.html").write_text(html, encoding="utf-8")
        written += 1

    def _render_md(page) -> str:
        return render_editorial(
            page,
            site=site,
            env=env,
            chart_html=_chart_for(page.slug),
            questionnaires_html=_questionnaires_for(page.slug),
        )

    if tei_editorials:
        covered: set[str] = set()
        for page in discover_pages():
            _write(page.slug, render_page(page, site=site, env=env))
            covered.add(page.slug)
        for page in discover_editorials():
            if page.slug in covered:
                continue  # TEI page wins at this slug
            _write(page.slug, _render_md(page))
        return written

    for page in discover_editorials():
        _write(page.slug, _render_md(page))
    return written


def _copy_static(out_root: Path) -> None:
    """Mirror static/ into site/static/ — CSS, JS, fonts."""
    target = out_root / "static"
    if target.exists():
        shutil.rmtree(target)
    if STATIC_DIR.exists():
        shutil.copytree(STATIC_DIR, target)


def _remove_excluded_draft_outputs(
    parsed: list[tuple[Path, Review]],
    out_root: Path,
) -> None:
    """Remove stale local draft pages and generated assets before publication."""
    resolved_root = out_root.resolve()
    for _, review in parsed:
        if not review.is_draft:
            continue
        targets = (
            out_root / "issues" / review.issue / review.id,
            out_root / "static" / "images" / "wordclouds" / f"{review.id}.png",
            out_root / "drafts",
        )
        for target in targets:
            resolved_target = target.resolve()
            try:
                resolved_target.relative_to(resolved_root)
            except ValueError as exc:
                raise ValueError(f"Draft output escapes site root: {resolved_target}") from exc
            if resolved_target.is_dir():
                shutil.rmtree(resolved_target)
            elif resolved_target.is_file():
                resolved_target.unlink()


def _generate_bundle_wordclouds(
    parsed: list[tuple[Path, Review]],
    out_root: Path,
) -> tuple[Path, ...]:
    """Generate deterministic wordclouds for every included review bundle."""
    bundles = [(path, review) for path, review in parsed if is_review_bundle(path)]
    if not bundles:
        return ()

    from scripts.wordclouds import run as generate_wordcloud

    out_dir = out_root / "static" / "images" / "wordclouds"
    generated: list[Path] = []
    for path, _ in bundles:
        generated.append(generate_wordcloud(path, out_dir))
    return tuple(generated)


def _render_aggregations(
    reviews: tuple[Review, ...],
    env,
    site: SiteConfig,
    out_root: Path,
    issue_configs: Optional[dict] = None,
    home_widgets: Optional[list] = None,
    wordcloud_dir: Optional[Path] = None,
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
            render_issue(
                issue_no,
                reviews,
                site=site,
                env=env,
                config=configs.get(issue_no),
                wordcloud_dir=wordcloud_dir or STATIC_DIR / "images" / "wordclouds",
            ),
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

    # Corpus-wide bibliography export (Zotero mass-import channel).
    write_bibliography_exports(reviews, data_dir)

    return pages


def _iter_corpus(corpus_dir: Path, limit: Optional[int]) -> Iterable[Path]:
    files = list(iter_tei_files(corpus_dir))
    return files[:limit] if limit else files


def _run_parse_pass(
    corpus_dir: Path,
    limit: Optional[int],
    out_root: Path,
    include_drafts: bool,
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
            review, report = _parse_one(
                path,
                out_root,
                ride_root=RIDE_ROOT,
                include_drafts=include_drafts,
            )
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
    - **Duplicate review DOIs.** Two reviews claiming one DOI would overwrite
      the same output path and publish contradictory identifiers, so the build
      stops before rendering.
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
            "review xml:id does not match its registered DOI:\n  - " + "\n  - ".join(id_errors)
        )

    duplicate_dois = find_duplicate_review_dois(parsed)
    if duplicate_dois:
        raise IssueConfigError(
            "reviews share a DOI and would overwrite one output path:\n  - "
            + "\n  - ".join(duplicate_dois),
        )

    issue_configs = discover_issue_configs()
    issue_errors = validate_issue_configs(issue_configs, rendered)
    if issue_errors:
        raise IssueConfigError(
            "issue YAML and TEI corpus disagree:\n  - " + "\n  - ".join(issue_errors)
        )
    return issue_configs


def _run_render_pass(
    parsed: list[tuple[Path, Review]],
    env,
    site: SiteConfig,
    out_root: Path,
    failed: list[tuple[Path, Exception]],
    pdf_available: bool,
) -> None:
    """Render every parsed Review to its per-review page. Per-file render
    failures are appended to ``failed`` (mutated in place) so the build
    finishes and reports them rather than aborting on one bad TEI.
    """
    for path, review in parsed:
        try:
            _render_review(
                path,
                review,
                env,
                site,
                out_root,
                pdf_available=pdf_available,
            )
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
            validation_report = validate_corpus(corpus_dir, REPO_ROOT / "schema" / "ride.rng")
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
    wordclouds: int,
    drafts: int,
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
    if wordclouds:
        print(f"Wordclouds: {wordclouds} generated from review bundles")
    if drafts:
        print(f"Draft previews: {drafts} rendered")
    print("Wrote api/build-info.json")

    _print_asset_summary(asset_reports)


def _raise_for_hard_failures(
    *,
    failed: list[tuple[Path, Exception]],
    validation_report: Optional[ValidationReport],
    asset_reports: list[AssetReport],
    pdf_failed: list[tuple[str, str]],
) -> None:
    """Fail CI after all actionable diagnostics have been collected."""
    messages: list[str] = []
    for path, exc in failed:
        messages.append(f"{path.as_posix()}: {exc}")
    if validation_report:
        for finding in validation_report.findings:
            if finding.severity == "error":
                messages.append(f"{finding.file}:{finding.line}: {finding.message}")
    for report in asset_reports:
        if not report.bundle:
            continue
        for url in report.missing:
            messages.append(f"{report.review_id}: missing bundle asset {url}")
        for url in report.unparseable:
            messages.append(f"{report.review_id}: bundle figure must use pictures/...: {url}")
    for review_id, error in pdf_failed:
        messages.append(f"{review_id}: {error}")
    if messages:
        raise BuildFailure("Build completed with hard failures:\n  - " + "\n  - ".join(messages))


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
    pdf_drafts_only: bool = False,
    tei_editorials: bool = True,
    include_drafts: bool = False,
) -> int:
    """Run the build and return the number of review pages written.

    The flow is parse → consistency-check → render → aux-pages →
    machine-artefacts → optional-PDF → validation-layer → summary. Each
    step is a named helper. Drafts are parsed and validated in every run,
    but are rendered only when ``include_drafts`` is true. Public
    aggregations and machine-readable outputs always receive published
    reviews exclusively.
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
    parsed, asset_reports, failed = _run_parse_pass(
        corpus_dir,
        limit,
        out_root,
        include_drafts,
    )
    published_parsed = [(path, review) for path, review in parsed if not review.is_draft]
    published = tuple(review for _, review in published_parsed)
    preview_parsed = parsed if include_drafts else published_parsed
    preview_reviews = tuple(review for _, review in preview_parsed)
    draft_count = sum(review.is_draft for _, review in parsed)

    # Consistency: folder ↔ biblScope @n; issue YAML ↔ corpus. Hard errors.
    issue_configs = _check_corpus_consistency(parsed, published)

    # Navigation YAML resolved against the parsed corpus, then re-bound
    # onto site so every subsequent render call sees the populated Issues
    # dropdown.
    site = _site_with_navigation(site, published)

    # Per-review HTML — render failures append to `failed`.
    if not include_drafts:
        _remove_excluded_draft_outputs(parsed, out_root)
    _run_render_pass(
        preview_parsed,
        env,
        site,
        out_root,
        failed,
        pdf_available=pdf,
    )

    # Editorial pages, aggregation pages, static asset tree.
    editorials = _render_editorials(
        env,
        site,
        out_root,
        parsed=published_parsed,
        tei_editorials=tei_editorials,
    )
    home_widgets = discover_home_widgets()
    _copy_static(out_root)
    wordclouds = _generate_bundle_wordclouds(preview_parsed, out_root)
    aggregations = _render_aggregations(
        published,
        env,
        site,
        out_root,
        issue_configs=issue_configs,
        home_widgets=home_widgets,
        wordcloud_dir=out_root / "static" / "images" / "wordclouds",
    )
    if include_drafts:
        drafts_dir = out_root / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        (drafts_dir / "index.html").write_text(
            render_drafts(
                preview_reviews,
                site=site,
                env=env,
                wordcloud_dir=out_root / "static" / "images" / "wordclouds",
                pdf_available=pdf,
            ),
            encoding="utf-8",
        )
        aggregations += 1

    # Machine-readable artefacts and legacy-URL redirects.
    sitemap_written = _write_sitemap(published, site, out_root)
    feed_written = _write_atom_feed(published, site, out_root)
    rss_written = _write_rss_feed(published, site, out_root)
    rdf_written = _write_rdf_feed(published, site, out_root)
    feed_aliases = _write_legacy_feed_aliases(out_root)
    _write_corpus_dump(published, site, out_root)
    oai_files = _write_oai_pmh_snapshot(published, site, out_root)
    redirect_count = write_redirects(published, out_root, base_url=site.base_url)

    # Optional PDF pass (Phase 14). Requested PDF failures are collected,
    # written to build-info.json, and fail the build after the summary.
    pdf_parsed = (
        [(path, review) for path, review in preview_parsed if review.is_draft]
        if pdf_drafts_only
        else preview_parsed
    )
    pdf_count, pdf_failed = _render_pdfs(pdf_parsed, out_root) if pdf else (0, [])

    # Validation + linkcheck + aggregated build-info.json (Phase 13).
    validation_report, link_report = _run_validation_layer(
        corpus_dir, published, validate, linkcheck
    )
    _write_build_info(
        out_root=out_root,
        site=site,
        reviews=published,
        asset_reports=asset_reports,
        failed=failed,
        drafts_discovered=draft_count,
        drafts_rendered=draft_count if include_drafts else 0,
        validation_report=validation_report,
        link_report=link_report,
        pdf_requested=pdf,
        pdf_rendered=pdf_count,
        pdf_failed=pdf_failed,
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
        wordclouds=len(wordclouds),
        drafts=draft_count if include_drafts else 0,
    )

    _raise_for_hard_failures(
        failed=failed,
        validation_report=validation_report,
        asset_reports=asset_reports,
        pdf_failed=pdf_failed,
    )

    return len(preview_reviews)


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
    drafts_discovered: int = 0,
    drafts_rendered: int = 0,
    validation_report=None,
    link_report=None,
    pdf_requested: bool = False,
    pdf_rendered: int = 0,
    pdf_failed: tuple[tuple[str, str], ...] | list[tuple[str, str]] = (),
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
            "rendered": len(reviews) + drafts_rendered,
            "published": len(reviews),
            "drafts_discovered": drafts_discovered,
            "drafts_rendered": drafts_rendered,
            "failed": [{"file": str(p.name), "error": str(exc)} for p, exc in failed],
        },
        "assets": {
            "copied": sum(len(r.copied) for r in asset_reports),
            "missing": sum(len(r.missing) for r in asset_reports),
            "unparseable": sum(len(r.unparseable) for r in asset_reports),
            "bundle_errors": [
                {
                    "review_id": report.review_id,
                    "missing": list(report.missing),
                    "unparseable": list(report.unparseable),
                }
                for report in asset_reports
                if report.bundle and (report.missing or report.unparseable)
            ],
        },
        "pdf": {
            "requested": pdf_requested,
            "rendered": pdf_rendered,
            "failed": [{"review_id": review_id, "error": error} for review_id, error in pdf_failed],
        },
        "validation": validation_report.to_dict() if validation_report else None,
        "linkcheck": link_report.to_dict() if link_report else None,
    }
    api_dir = out_root / "api"
    api_dir.mkdir(parents=True, exist_ok=True)
    (api_dir / "build-info.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _write_oai_pmh_snapshot(reviews: tuple[Review, ...], site: SiteConfig, out_root: Path) -> int:
    """Write the OAI-PMH snapshot under ``site/oai/`` if ``base_url`` is set.

    Like the sitemap, OAI-PMH identifiers and ``baseURL`` need an
    absolute origin, so dev builds without a deploy prefix skip silently.
    Returns the number of XML files written (0 when skipped).
    """
    if not site.base_url:
        return 0
    build_date = _build_date(site)
    return write_oai_pmh(reviews, base_url=site.base_url, out_root=out_root, build_date=build_date)


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
        write_atom_feed(reviews, base_url=site.base_url, out_root=out_root, build_date=build_date)
    )


def _write_rss_feed(reviews: tuple[Review, ...], site: SiteConfig, out_root: Path) -> bool:
    """Write the RSS 2.0 feed (``site/feed/rss.xml``) when a base_url is
    set — same deploy-only rule as the Atom feed."""
    from src.render.rss import write_rss_feed

    build_date = _build_date(site)
    return bool(
        write_rss_feed(reviews, base_url=site.base_url, out_root=out_root, build_date=build_date)
    )


def _write_rdf_feed(reviews: tuple[Review, ...], site: SiteConfig, out_root: Path) -> bool:
    """Write the RSS 1.0 feed (``site/feed/rdf.xml``) when a base_url is
    set — same deploy-only rule as its siblings."""
    from src.render.rdf import write_rdf_feed

    build_date = _build_date(site)
    return bool(
        write_rdf_feed(reviews, base_url=site.base_url, out_root=out_root, build_date=build_date)
    )


def _write_legacy_feed_aliases(out_root: Path) -> int:
    """Copy the feed XML to the legacy WP feed paths (no-op when the
    deploy-only feeds were skipped)."""
    from src.render.feed import write_legacy_feed_aliases

    return write_legacy_feed_aliases(out_root)


def _print_asset_summary(reports: list[AssetReport]) -> None:
    """Aggregate per-review AssetReports into one build-summary line.

    Per-review missing/unparseable lists go to stderr so CI surfaces them
    without polluting the success output. New-bundle findings are also
    recorded as hard failures; historical asset findings remain warnings.
    """
    total_copied = sum(len(r.copied) for r in reports)
    total_missing = sum(len(r.missing) for r in reports)
    total_unparseable = sum(len(r.unparseable) for r in reports)
    print(
        f"Assets: copied {total_copied}, missing {total_missing}, unparseable {total_unparseable}"
    )
    for report in reports:
        if report.missing or report.unparseable:
            for url in report.missing:
                print(f"  asset missing: {report.review_id}: {url}", file=sys.stderr)
            for url in report.unparseable:
                print(f"  asset url-unparseable: {report.review_id}: {url}", file=sys.stderr)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build the ride.i-d-e.de static site.")
    parser.add_argument(
        "--reviews", type=int, default=None, help="Limit to first N reviews (for iteration)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=SITE_DIR,
        help="Output directory; defaults to site/.",
    )
    parser.add_argument(
        "--base-url", default="", help="Deploy URL prefix; empty for relative paths"
    )
    parser.add_argument(
        "--pdf", action="store_true", help="Render a PDF next to every review's HTML via WeasyPrint"
    )
    parser.add_argument(
        "--pdf-drafts-only",
        action="store_true",
        help="With --include-drafts --pdf, render PDFs only for draft reviews.",
    )
    parser.add_argument(
        "--include-drafts",
        action="store_true",
        help="Render marked draft preview pages; formal publication outputs still exclude drafts",
    )
    parser.add_argument(
        "--no-validate", action="store_true", help="Skip the RelaxNG validation pre-check"
    )
    parser.add_argument(
        "--linkcheck",
        action="store_true",
        help="Probe external bibliography URLs (slow ~5min, off by default)",
    )
    parser.add_argument(
        "--matomo-url",
        default="",
        help="Matomo tracker URL (e.g. https://matomo.example.org/); empty disables tracking",
    )
    parser.add_argument(
        "--matomo-site-id", default="", help="Matomo site id; required when --matomo-url is set"
    )
    parser.add_argument(
        "--no-tei-editorials",
        action="store_false",
        dest="tei_editorials",
        help="Fall back to the legacy content/*.md Markdown editorials. By default the build renders the pages/*.xml TEI editorials with precedence (Markdown remains the fallback for slugs no TEI page covers).",
    )
    args = parser.parse_args(argv)

    if bool(args.matomo_url) != bool(args.matomo_site_id):
        parser.error("--matomo-url and --matomo-site-id must be set together")
    if args.pdf_drafts_only and not (args.pdf and args.include_drafts):
        parser.error("--pdf-drafts-only requires --pdf and --include-drafts")

    try:
        written = build(
            out_root=args.output,
            limit=args.reviews,
            base_url=args.base_url,
            validate=not args.no_validate,
            linkcheck=args.linkcheck,
            matomo_url=args.matomo_url,
            matomo_site_id=args.matomo_site_id,
            pdf=args.pdf,
            pdf_drafts_only=args.pdf_drafts_only,
            tei_editorials=args.tei_editorials,
            include_drafts=args.include_drafts,
        )
    except BuildFailure as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Wrote {written} review pages to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
