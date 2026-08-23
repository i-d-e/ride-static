"""HTML rendering for the Factsheet full page (R18).

Parallel to :func:`src.render.html.render_review`: same SiteConfig, same
Jinja environment, same path factories. The page sits at
``/issues/{N}/{id}/factsheet/`` and renders the per-review header, the
reviewed resource, its contributors, and the questionnaire one question
at a time — the full view the sidebar box only summarises.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import markdown
from jinja2 import Environment

from src.model.questionnaire import Questionnaire, QuestionnaireQuestion
from src.model.review import RelatedItem, Review
from src.render.html import (
    REPO_ROOT,
    SiteConfig,
    base_ctx,
    make_env,
    review_url,
)

HELP_DIR = REPO_ROOT / "content" / "factsheet-help"

_HELP_HEADING_RE = re.compile(r"^##\s+(\S+)\s*$", re.MULTILINE)


def load_help_texts(help_dir: Path = HELP_DIR) -> dict[str, str]:
    """Load ``content/factsheet-help/*.md`` into ``category-id -> HTML``.

    Each file carries per-criterion sections keyed by an ``## {id}`` heading;
    the body under a heading (until the next heading) is rendered to HTML with
    the same Markdown pipeline as the editorial pages. A missing directory or
    unreadable file degrades to an empty dict so the factsheet still renders."""
    texts: dict[str, str] = {}
    if not help_dir.exists():
        return texts
    for path in sorted(help_dir.glob("*.md")):
        try:
            body = path.read_text(encoding="utf-8")
        except OSError:
            continue
        matches = list(_HELP_HEADING_RE.finditer(body))
        for i, m in enumerate(matches):
            key = m.group(1)
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
            section = body[start:end].strip()
            if not section:
                continue
            texts[key] = markdown.markdown(
                section,
                extensions=["extra", "sane_lists", "smarty"],
                output_format="html5",
            )
    return texts


def help_lookup_key(category_xml_id: str) -> str:
    """Strip a compound review's ``revN-`` resource prefix from a category id
    so ``rev1-te042`` resolves against the ``te042`` help entry."""
    prefix, sep, rest = category_xml_id.partition("-")
    if sep and prefix.startswith("rev"):
        return rest
    return category_xml_id


def make_question_help(help_texts: dict[str, str]):
    """Return ``fn(question) -> HTML | ""`` resolving a question's help text."""

    def question_help(question: QuestionnaireQuestion) -> str:
        if not question.category_xml_id:
            return ""
        return help_texts.get(help_lookup_key(question.category_xml_id), "")

    return question_help


def make_questionnaire_heading(review: Review):
    """Return ``fn(questionnaire) -> title | None`` naming a block's resource.

    Compound reviews carry one taxonomy per reviewed resource; the block's
    ``resource_key`` (``rev1``) matches a ``relatedItem @xml:id``, whose title
    labels the block. Single-resource reviews have no key, so the heading is
    omitted and their rendering is unchanged.

    Deliberate simplification: sequential labelled blocks stand in for the
    legacy multi-column answer table. Upgrade path — when a side-by-side
    comparison is wanted, join the blocks on shared question ids into one
    table with an answer column per resource."""
    by_id: dict[str, RelatedItem] = {
        item.xml_id: item
        for item in review.related_items
        if item.xml_id and item.type == "reviewed_resource"
    }

    def questionnaire_heading(q: Questionnaire) -> Optional[str]:
        if not q.resource_key:
            return None
        item = by_id.get(q.resource_key)
        if item is None:
            return None
        return (item.title or q.resource_key).strip() or None

    return questionnaire_heading


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


def humanize_label(label: str) -> str:
    """Humanise an xml:id-style section label (``general_information`` →
    "General information"). Labels already in prose (containing a space)
    keep their wording; only the first letter is capitalised. The
    text-collections criteria sets carry section headings as xml:ids,
    while the digital-editions sets carry prose ``catDesc`` headings.
    """
    if not label:
        return label
    if " " not in label:
        label = label.replace("_", " ").replace("-", " ")
    return label[:1].upper() + label[1:]


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
    help_texts: Optional[dict[str, str]] = None,
    pdf_available: bool = True,
) -> str:
    """Render one Review's Factsheet full page to a complete HTML string.

    ``help_texts`` is the ``category-id -> HTML`` map from
    :func:`load_help_texts`; loaded lazily when omitted so a bare
    ``render_factsheet(review)`` call keeps working."""
    site = site or SiteConfig()
    env = env or make_env()
    if help_texts is None:
        help_texts = load_help_texts()

    item = reviewed_resource(review)

    template = env.get_template("factsheet.html")
    return template.render(
        **base_ctx(site, page_lang=review.language),
        review=review,
        reviewed=item,
        personnel_groups=group_personnel(item),
        criteria_link=criteria_link,
        humanize_label=humanize_label,
        question_help=make_question_help(help_texts),
        questionnaire_heading=make_questionnaire_heading(review),
        pdf_available=pdf_available,
        page_title=f"{review.title} — Factsheet" if review.title else "Factsheet",
        page_url=(
            review_url(review, site.base_url) + "factsheet/"
            if site.base_url and not review.is_draft
            else None
        ),
    )
