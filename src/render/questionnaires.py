"""Aggregated questionnaire tables — the Data-Questionnaires view.

The Data-Charts page (``src/render/charts.py``) summarises the corpus at
the top-level-section granularity as one bar chart per criteria set. The
Data-Questionnaires page goes one level finer, one row per individual
question. It is the static materialisation of the interactive per-answer
table the page long carried only as a placeholder.

Like the charts, the block is emitted at build time and substituted into
the editorial body where the marker ``<!-- ride:questionnaires -->``
appears in ``content/data-questionnaires.md``, so the framing prose stays
hand-editable while the table is always derived from the parsed corpus.

The aggregation walks each review's per-question view
(:class:`src.model.questionnaire.QuestionnaireQuestion`, already parsed
for the factsheet) rather than the flat answers, so it reuses the section
and question labels the taxonomy carries. Questions are keyed by their
``category_xml_id`` with any compound-review ``revN-`` prefix stripped, so
the same question aggregates across a compound review's several resources
and across the whole corpus.

Answer bookkeeping mirrors the charts (``knowledge/data.md`` anomaly rule):

* A question counts as *answered* by a review when the review selected at
  least one option or gave a binary No. The ``value="3"`` anomaly never
  counts as answered and is tallied separately.
* *yes* counts reviews whose answer is affirmative: a binary ``Yes``, or,
  for a categorical (multi-select) question, any non-empty selection. The
  distinction between binary and categorical is surfaced in the table so
  the yes-rate is read correctly.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from html import escape
from typing import Optional

from src.model.questionnaire import QuestionnaireQuestion
from src.model.review import Review
from src.render.charts import CRITERIA_LABELS, criteria_label, criteria_slug


def _question_key(category_xml_id: str) -> str:
    """Question id with any compound-review ``revN-`` prefix removed.

    ``rev1-te042`` and ``rev2-te042`` are the same question asked of two
    reviewed resources; both fold onto ``te042`` so the corpus count is
    per question, not per resource. Bare ids (``se016``) pass through.
    """
    prefix, sep, rest = category_xml_id.partition("-")
    if sep and prefix.startswith("rev"):
        return rest
    return category_xml_id


def _is_yes(question: QuestionnaireQuestion) -> bool:
    """Whether a review's answer to this question is affirmative.

    Binary questions carry a single ``Yes``/``No`` selection; categorical
    questions carry the labels of the options ticked. Either way a
    non-empty, non-``No`` selection is an affirmative answer. The
    ``value="3"`` anomaly leaves ``selected`` empty and ``anomaly`` set, so
    it is neither yes nor answered.
    """
    if not question.selected:
        return False
    if len(question.selected) == 1 and question.selected[0] == "No":
        return False
    return True


def _is_answered(question: QuestionnaireQuestion) -> bool:
    """Whether the review answered the question at all (anomaly excluded)."""
    return bool(question.selected)


# ── Aggregation ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class QuestionAggregate:
    """One row of one table: a single question's corpus-wide tally."""

    key: str
    label: str
    section: str
    yes: int
    answered: int
    anomaly: int
    categorical: bool

    @property
    def yes_pct(self) -> float:
        return (100.0 * self.yes / self.answered) if self.answered else 0.0


@dataclass(frozen=True)
class QuestionnaireSetTable:
    """One table: criteria set label plus its per-question rows in
    document order, carrying their section grouping."""

    slug: str
    label: str
    review_count: int
    rows: tuple[QuestionAggregate, ...]
    anomaly_count: int


def aggregate_questions(
    reviews: tuple[Review, ...],
) -> tuple[QuestionnaireSetTable, ...]:
    """Aggregate every review's per-question answers per criteria slug.

    URLs that share a slug per :data:`src.render.charts.CRITERIA_LABELS`
    (the two text-collections spellings) merge into one table. Question
    order and section labels follow the first review encountered for each
    slug, matching the taxonomy's document order; every review pointing at
    the same criteria set presents the same question sequence.
    """
    # Per slug: ordered question keys, and per key its display label,
    # section, and whether it is categorical (seen with a multi-option or
    # non-Yes/No selection anywhere in the corpus).
    order: dict[str, list[str]] = defaultdict(list)
    seen_key: dict[str, set[str]] = defaultdict(set)
    label_of: dict[tuple[str, str], str] = {}
    section_of: dict[tuple[str, str], str] = {}
    categorical: dict[tuple[str, str], bool] = defaultdict(bool)

    tally: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: {"yes": 0, "answered": 0, "anomaly": 0})
    )
    review_counts: dict[str, int] = defaultdict(int)
    seen_review_per_slug: dict[str, set[str]] = defaultdict(set)

    for review in reviews:
        for q in review.questionnaires:
            slug = criteria_slug(q.criteria_url)
            if review.id and review.id not in seen_review_per_slug[slug]:
                seen_review_per_slug[slug].add(review.id)
                review_counts[slug] += 1
            for question in q.questions:
                if not question.category_xml_id:
                    continue
                key = _question_key(question.category_xml_id)
                if key not in seen_key[slug]:
                    seen_key[slug].add(key)
                    order[slug].append(key)
                    label_of[(slug, key)] = question.question_label or key
                    section_of[(slug, key)] = question.section_label or "(other)"
                # A question is categorical if it ever presents more than one
                # selected option, or an option label other than Yes/No.
                if len(question.selected) > 1 or any(
                    lbl not in ("Yes", "No") for lbl in question.selected
                ):
                    categorical[(slug, key)] = True
                cell = tally[slug][key]
                if question.anomaly and not question.selected:
                    cell["anomaly"] += 1
                    continue
                if _is_answered(question):
                    cell["answered"] += 1
                    if _is_yes(question):
                        cell["yes"] += 1

    tables: list[QuestionnaireSetTable] = []
    canonical_order = list(dict.fromkeys(criteria_slug(u) for u in CRITERIA_LABELS))
    ordered_slugs = canonical_order + sorted(s for s in tally if s not in canonical_order)
    seen_slugs: set[str] = set()
    for slug in ordered_slugs:
        if slug in seen_slugs or slug not in tally:
            continue
        seen_slugs.add(slug)
        rows: list[QuestionAggregate] = []
        anomaly_total = 0
        for key in order[slug]:
            cell = tally[slug][key]
            anomaly_total += cell["anomaly"]
            rows.append(
                QuestionAggregate(
                    key=key,
                    label=label_of[(slug, key)],
                    section=section_of[(slug, key)],
                    yes=cell["yes"],
                    answered=cell["answered"],
                    anomaly=cell["anomaly"],
                    categorical=categorical[(slug, key)],
                )
            )
        urls = _urls_for_slug(slug)
        display = criteria_label(urls[0]) if urls else slug
        tables.append(
            QuestionnaireSetTable(
                slug=slug,
                label=display,
                review_count=review_counts[slug],
                rows=tuple(rows),
                anomaly_count=anomaly_total,
            )
        )
    return tuple(tables)


def _urls_for_slug(slug: str) -> list[str]:
    """Criteria URLs whose canonical slug is ``slug`` (for the display label)."""
    from src.render.charts import CRITERIA_LABELS

    return [u for u, (s, _) in CRITERIA_LABELS.items() if s == slug]


# ── HTML rendering ────────────────────────────────────────────────────


def render_questionnaire_table(table: QuestionnaireSetTable) -> str:
    """One HTML table for a single :class:`QuestionnaireSetTable`.

    Rows are grouped under their section with a spanning section heading
    row, mirroring the taxonomy structure; each question row carries its
    yes / answered count and a percentage bar cell. A trailing note counts
    the ``value="3"`` anomalies excluded from the denominators.
    """
    parts: list[str] = []
    parts.append(f'<table class="ride-questionnaires__table" id="quest-{escape(table.slug)}">')
    parts.append(
        "<thead><tr>"
        '<th scope="col" class="ride-questionnaires__q">Question</th>'
        '<th scope="col" class="ride-questionnaires__num">Yes</th>'
        '<th scope="col" class="ride-questionnaires__num">Answered</th>'
        '<th scope="col" class="ride-questionnaires__rate">Yes-rate</th>'
        "</tr></thead>"
    )
    parts.append("<tbody>")
    current_section: Optional[str] = None
    for row in table.rows:
        if row.section != current_section:
            current_section = row.section
            parts.append(
                '<tr class="ride-questionnaires__section">'
                f'<th scope="colgroup" colspan="4">{escape(current_section)}</th>'
                "</tr>"
            )
        kind = " (multi)" if row.categorical else ""
        pct = f"{row.yes_pct:.0f}%" if row.answered else "—"
        bar_w = row.yes_pct if row.answered else 0.0
        parts.append(
            "<tr>"
            f'<td class="ride-questionnaires__q">{escape(row.label)}'
            f'<span class="ride-questionnaires__kind">{kind}</span></td>'
            f'<td class="ride-questionnaires__num">{row.yes}</td>'
            f'<td class="ride-questionnaires__num">{row.answered}</td>'
            f'<td class="ride-questionnaires__rate">'
            f'<span class="ride-questionnaires__bar" style="width:{bar_w:.0f}%"></span>'
            f'<span class="ride-questionnaires__pct">{pct}</span>'
            "</td>"
            "</tr>"
        )
    parts.append("</tbody></table>")
    return "".join(parts)


def render_questionnaires_html(reviews: tuple[Review, ...]) -> str:
    """Full questionnaires block to substitute into the editorial body.

    Wrapped in ``<div class="ride-questionnaires">`` so the editorial CSS
    can style the block as a unit. Each criteria set is a ``<section>``
    with a heading, the table, and an anomaly note when applicable.
    Returns the empty string when the corpus carries no questionnaires, so
    the marker stays untouched.
    """
    tables = aggregate_questions(reviews)
    tables = tuple(t for t in tables if t.rows)
    if not tables:
        return ""
    parts: list[str] = ['<div class="ride-questionnaires">']
    for table in tables:
        parts.append('<section class="ride-questionnaires__set">')
        parts.append(
            f'<h2 class="ride-questionnaires__heading">{escape(table.label)} '
            f'<span class="ride-questionnaires__count">'
            f"({table.review_count} review{'s' if table.review_count != 1 else ''})"
            f"</span></h2>"
        )
        parts.append(render_questionnaire_table(table))
        if table.anomaly_count > 0:
            parts.append(
                f'<p class="ride-questionnaires__anomaly">'
                f"{table.anomaly_count} answer"
                f"{'s' if table.anomaly_count != 1 else ''} carried "
                f'<code>value="3"</code> and were excluded from the '
                f"denominators.</p>"
            )
        parts.append("</section>")
    parts.append("</div>")
    return "".join(parts)
