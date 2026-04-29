"""Aggregation- und Übersichtsseiten — Phase 10.

Sechs Seitentypen aus ``knowledge/interface.md`` §4, alle gegen die
Domänenobjekte aus ``src.model`` und die Cross-Korpus-Aggregate aus
``src.parser.datasets``:

- :func:`render_index`             — Startseite (aktuelles Issue + Browse)
- :func:`render_issues_overview`   — Issue-Übersicht (alle Issues)
- :func:`render_issue`             — Issue-Ansicht (ein Issue mit Beiträgen)
- :func:`render_tags_overview`     — Tag-Übersicht (alphabetisch)
- :func:`render_tag`               — eine Tag-Seite
- :func:`render_reviewers_overview` — Reviewer-Liste
- :func:`render_reviewer`          — eine Reviewer-Seite
- :func:`render_resources`         — Reviewed-Resources-Tabelle

Jede Funktion nimmt die geparste Korpus-Sequenz und gibt einen HTML-String
zurück. Schreiben in das Build-Verzeichnis macht ``src.build``.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Optional

from jinja2 import Environment

from src.model.review import Review
from src.parser.datasets import (
    ReviewedResourceAggregate,
    ReviewerAggregate,
    TagAggregate,
    aggregate_reviewed_resources,
    aggregate_reviewers,
    aggregate_tags,
)
from src.render.editorial import HomeWidget, discover_home_widgets
from src.render.html import (
    SiteConfig,
    make_env,
    media_path_factory,
    slugify,
    static_path_factory,
)
from src.render.issues_config import IssueConfig, order_reviews


# ── helpers ────────────────────────────────────────────────────────────


def _common_ctx(site: SiteConfig) -> dict:
    """Variables every aggregation template needs in addition to its own."""
    return {
        "site": site,
        "static_path": static_path_factory(site.base_url),
        "media_path": media_path_factory(site.base_url),
        "page_lang": site.default_language,
        "og": None,
        "json_ld": None,
        "page_description": None,
    }


def _abs_url(site: SiteConfig, path: str) -> Optional[str]:
    """Absolute canonical URL, or None when no base_url is set (preview mode)."""
    if not site.base_url:
        return None
    return f"{site.base_url.rstrip('/')}/{path.lstrip('/')}"


def group_reviews_by_issue(reviews: Iterable[Review]) -> dict[str, list[Review]]:
    """Bucket reviews by their issue number; preserves per-issue id order."""
    grouped: dict[str, list[Review]] = defaultdict(list)
    for r in reviews:
        grouped[r.issue or ""].append(r)
    return {k: sorted(v, key=lambda r: r.id) for k, v in grouped.items()}


def _issue_sort_key(item: tuple[str, list[Review]]) -> tuple:
    """Latest publication date first; integer issue order as tiebreaker."""
    issue_no, reviews = item
    latest = max((r.publication_date or "" for r in reviews), default="")
    try:
        issue_int = int(issue_no)
    except ValueError:
        issue_int = 0
    return (latest, issue_int)


def reviewer_slug(reviewer: ReviewerAggregate) -> str:
    """Stable URL slug for a reviewer page."""
    if reviewer.person.surname:
        if reviewer.person.forename:
            return slugify(f"{reviewer.person.surname} {reviewer.person.forename}")
        return slugify(reviewer.person.surname)
    return slugify(reviewer.person.full_name)


# ── home + issues ──────────────────────────────────────────────────────


def render_index(
    reviews: tuple[Review, ...],
    site: SiteConfig,
    env: Environment,
    home_widgets: Optional[list[HomeWidget]] = None,
) -> str:
    """Site root — current issue prominent plus editorial widgets.

    ``home_widgets`` is loaded by the build (``discover_home_widgets``)
    so the redaktionelle Heimseite is bearbeitbar via Markdown unter
    ``content/home/``. None falls back to the empty list — useful for
    isolated unit tests that don't care about widget content.
    """
    by_issue = group_reviews_by_issue(reviews)
    current_issue = ""
    current_reviews: list[Review] = []
    if by_issue:
        current_issue, current_reviews = max(by_issue.items(), key=_issue_sort_key)
    return env.get_template("index.html").render(
        **_common_ctx(site),
        page_title=site.title,
        page_url=_abs_url(site, "/"),
        current_issue=current_issue,
        current_reviews=current_reviews,
        total_reviews=len(reviews),
        total_issues=len(by_issue),
        home_widgets=home_widgets or [],
    )


def render_issues_overview(
    reviews: tuple[Review, ...],
    site: SiteConfig,
    env: Environment,
    issue_configs: Optional[dict[str, IssueConfig]] = None,
) -> str:
    by_issue = group_reviews_by_issue(reviews)
    issues = sorted(by_issue.items(), key=_issue_sort_key, reverse=True)
    configs = issue_configs or {}
    issues_with_cfg = [(no, revs, configs.get(no)) for no, revs in issues]
    return env.get_template("issues.html").render(
        **_common_ctx(site),
        page_title="Issues",
        page_url=_abs_url(site, "/issues/"),
        issues=issues_with_cfg,
    )


def render_issue(
    issue_no: str,
    reviews: tuple[Review, ...],
    site: SiteConfig,
    env: Environment,
    config: Optional[IssueConfig] = None,
) -> str:
    issue_reviews = [r for r in reviews if r.issue == issue_no]
    issue_reviews = order_reviews(issue_no, issue_reviews, config)
    latest = max((r.publication_date or "" for r in issue_reviews), default="")
    title = (config.title if config and config.title else f"Issue {issue_no}")
    return env.get_template("issue.html").render(
        **_common_ctx(site),
        page_title=title,
        page_url=_abs_url(site, f"/issues/{issue_no}/"),
        issue_no=issue_no,
        reviews=issue_reviews,
        latest_date=latest,
        config=config,
    )


# ── tags ───────────────────────────────────────────────────────────────


def render_tags_overview(reviews: tuple[Review, ...], site: SiteConfig, env: Environment) -> str:
    tags = aggregate_tags(reviews)
    return env.get_template("tags.html").render(
        **_common_ctx(site),
        page_title="Tags",
        page_url=_abs_url(site, "/tags/"),
        tags=tags,
    )


def render_tag(tag: TagAggregate, reviews: tuple[Review, ...], site: SiteConfig, env: Environment) -> str:
    by_id = {r.id: r for r in reviews}
    matched = [by_id[rid] for rid in tag.review_ids if rid in by_id]
    return env.get_template("tag.html").render(
        **_common_ctx(site),
        page_title=f"Tag: {tag.display_name}",
        page_url=_abs_url(site, f"/tags/{slugify(tag.name)}/"),
        tag=tag,
        reviews=matched,
    )


# ── reviewers ──────────────────────────────────────────────────────────


def render_reviewers_overview(reviews: tuple[Review, ...], site: SiteConfig, env: Environment) -> str:
    reviewers = aggregate_reviewers(reviews)
    return env.get_template("reviewers.html").render(
        **_common_ctx(site),
        page_title="Reviewers",
        page_url=_abs_url(site, "/reviewers/"),
        reviewers=[(reviewer_slug(r), r) for r in reviewers],
    )


def render_reviewer(reviewer: ReviewerAggregate, reviews: tuple[Review, ...], site: SiteConfig, env: Environment) -> str:
    by_id = {r.id: r for r in reviews}
    matched = [by_id[rid] for rid in reviewer.review_ids if rid in by_id]
    return env.get_template("reviewer.html").render(
        **_common_ctx(site),
        page_title=reviewer.person.full_name,
        page_url=_abs_url(site, f"/reviewers/{reviewer_slug(reviewer)}/"),
        reviewer=reviewer,
        reviews=matched,
    )


# ── reviewed resources ────────────────────────────────────────────────


def render_resources(reviews: tuple[Review, ...], site: SiteConfig, env: Environment) -> str:
    resources = aggregate_reviewed_resources(reviews)
    review_index = {r.id: r for r in reviews}
    return env.get_template("resources.html").render(
        **_common_ctx(site),
        page_title="Reviewed Resources",
        page_url=_abs_url(site, "/resources/"),
        resources=resources,
        review_index=review_index,
    )
