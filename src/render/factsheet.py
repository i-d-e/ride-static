"""HTML rendering for the Factsheet full page (R18).

Parallel to :func:`src.render.html.render_review`: same SiteConfig, same
Jinja environment, same path factories. The page sits at
``/issues/{N}/{id}/factsheet/`` and renders the per-review header, the
reviewed resource, its contributors, and the questionnaire one question
at a time — the full view the sidebar box only summarises.
"""
from __future__ import annotations

from typing import Optional

from jinja2 import Environment

from src.model.review import RelatedItem, Review
from src.render.html import (
    SiteConfig,
    make_env,
    media_path_factory,
    static_path_factory,
)


def reviewed_resource(review: Review) -> Optional[RelatedItem]:
    """The first ``reviewed_resource`` relatedItem, or None.

    Single source for the "Reviewed resource" and "People" blocks so the
    two stay in sync; returns None for reviews that carry no reviewed
    resource (block then renders empty).
    """
    for item in review.related_items:
        if item.type == "reviewed_resource":
            return item
    return None


def group_personnel(item: Optional[RelatedItem]) -> list[tuple[str, list[str]]]:
    """Group an item's ``(resp, persName)`` pairs by role, order preserved.

    Returns ``[(role, [name, …]), …]`` with roles in first-seen order and
    names in document order; duplicates kept verbatim (the corpus repeats
    persons across roles). Empty list when the item is None or carries no
    respStmt.
    """
    if item is None or not item.personnel:
        return []
    order: list[str] = []
    by_role: dict[str, list[str]] = {}
    for resp, name in item.personnel:
        role = resp or "Contributor"
        if role not in by_role:
            by_role[role] = []
            order.append(role)
        by_role[role].append(name)
    return [(role, by_role[role]) for role in order]


def criteria_link(criteria_url: str, criteria_ref: Optional[str]) -> Optional[str]:
    """Resolve a ``#K1.2`` K-ref against the taxonomy's criteria URL.

    The criteria IDs are fragment anchors on the external criteria
    document (see ``refs_resolver`` ``criteria`` bucket). Returns the
    concatenated URL, or None when either part is missing.
    """
    if not criteria_url or not criteria_ref:
        return None
    return f"{criteria_url}{criteria_ref}"


def render_factsheet(
    review: Review,
    site: Optional[SiteConfig] = None,
    env: Optional[Environment] = None,
) -> str:
    """Render one Review's Factsheet full page to a complete HTML string."""
    site = site or SiteConfig()
    env = env or make_env()

    item = reviewed_resource(review)

    template = env.get_template("factsheet.html")
    return template.render(
        site=site,
        review=review,
        reviewed=item,
        personnel_groups=group_personnel(item),
        criteria_link=criteria_link,
        page_lang=review.language or site.default_language,
        page_title=f"{review.title} — Factsheet" if review.title else "Factsheet",
        page_url=(
            f"{site.base_url}/issues/{review.issue}/{review.id}/factsheet/"
            if site.base_url
            else None
        ),
        page_description=None,
        og=None,
        json_ld=None,
        static_path=static_path_factory(site.base_url),
        media_path=media_path_factory(site.base_url),
    )
