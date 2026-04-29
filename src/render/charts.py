"""Aggregated questionnaire charts — Phase 10 R9.

The Data-Charts editorial page (``content/data-charts.md``) shows one
inline-SVG bar chart per criteria set, summarising how the corpus
answered each top-level section of that set. The chart block is
emitted at build time and substituted into the editorial body where
the marker ``<!-- ride:charts -->`` appears, so the markdown stays
human-curatable but the data view is always derived from the parsed
corpus.

Per ``requirements.md`` R9 the charts:

* are produced at build time, no runtime backend
* preserve at least the visualisations the legacy site had — one bar
  chart per criteria set, broken down by top-level section
* count ``value="3"`` answers separately from yes/no, surfaced as a
  small "anomaly" line under each chart so readers know how many
  responses were excluded from the percentage

The four criteria URLs in the corpus collapse into three logical sets
(text-collections appears under both http and https form). Charts
groups by ``CRITERIA_LABELS``; entries that share a slug are merged
into one chart, summing review counts and answers across the URL
variants.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from html import escape
from typing import Optional

from src.model.questionnaire import TaxonomySection
from src.model.review import Review

# canonical slug + display label for every criteria URL seen in the corpus.
# Order matters — charts are rendered in the order keys appear here, so the
# busiest set (digital editions) comes first.
CRITERIA_LABELS: dict[str, tuple[str, str]] = {
    "http://www.i-d-e.de/publikationen/weitereschriften/criteria-version-1-1": (
        "digital-editions-1.1",
        "Criteria for Reviewing Digital Editions (1.1)",
    ),
    "https://www.i-d-e.de/publikationen/weitereschriften/criteria-tools-version-1/": (
        "tools-1.0",
        "Criteria for Reviewing Tools and Environments (1.0)",
    ),
    "https://www.i-d-e.de/publikationen/weitereschriften/criteria-text-collections-version-1-0/": (
        "text-collections-1.0",
        "Criteria for Reviewing Text Collections (1.0)",
    ),
    "http://www.i-d-e.de/criteria-text-collections-version-1-0": (
        "text-collections-1.0",
        "Criteria for Reviewing Text Collections (1.0)",
    ),
}


def criteria_slug(url: str) -> str:
    """Canonical slug for a criteria URL, falling back to a normalised host."""
    if url in CRITERIA_LABELS:
        return CRITERIA_LABELS[url][0]
    return url.rstrip("/").rsplit("/", 1)[-1] or "unknown"


def criteria_label(url: str) -> str:
    """Display label for a criteria URL."""
    if url in CRITERIA_LABELS:
        return CRITERIA_LABELS[url][1]
    return url


# ── Aggregation ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class SectionAggregate:
    """One bar in one chart: a top-level section's yes/no counts."""

    label: str
    yes: int
    total: int  # excludes value="3" anomalies
    anomaly: int

    @property
    def yes_pct(self) -> float:
        return (100.0 * self.yes / self.total) if self.total else 0.0


@dataclass(frozen=True)
class CriteriaSetChart:
    """One chart: criteria set label + per-section aggregates."""

    slug: str
    label: str
    review_count: int
    sections: tuple[SectionAggregate, ...]
    anomaly_count: int  # total value="3" answers across all sections


def aggregate_questionnaires(
    reviews: tuple[Review, ...],
    sections_by_url: dict[str, tuple[TaxonomySection, ...]],
) -> tuple[CriteriaSetChart, ...]:
    """Aggregate every review's answers per criteria slug + top-level section.

    ``sections_by_url`` maps each criteria URL observed in the corpus
    to its top-level taxonomy structure (one example walked per URL —
    see :func:`src.parser.questionnaire.parse_taxonomy_sections`).
    URLs that share a slug per :data:`CRITERIA_LABELS` are merged so
    text-collections appears once even though the corpus carries two
    URL spellings of it.

    Sections are emitted in :data:`CRITERIA_LABELS` slug order so the
    chart block is reproducible build-to-build.
    """

    # 1. Build per-slug section template: {slug: {section_label: set(leaf_ids)}}.
    slug_sections: dict[str, "dict[str, set[str]]"] = defaultdict(
        lambda: defaultdict(set)
    )
    for url, sections in sections_by_url.items():
        slug = criteria_slug(url)
        for sec in sections:
            slug_sections[slug][sec.label].update(sec.leaf_xml_ids)

    # 2. Build leaf->section lookup per slug.
    leaf_to_section: dict[str, dict[str, str]] = {}
    for slug, sections in slug_sections.items():
        m: dict[str, str] = {}
        for label, leaves in sections.items():
            for leaf in leaves:
                m[leaf] = label
        leaf_to_section[slug] = m

    # 3. Walk reviews and tally yes / total / anomaly per (slug, section).
    tallies: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: {"yes": 0, "total": 0, "anomaly": 0})
    )
    review_counts: dict[str, int] = defaultdict(int)
    seen_review_per_slug: dict[str, set[str]] = defaultdict(set)
    for review in reviews:
        for q in review.questionnaires:
            slug = criteria_slug(q.criteria_url)
            if review.id and review.id not in seen_review_per_slug[slug]:
                seen_review_per_slug[slug].add(review.id)
                review_counts[slug] += 1
            section_lookup = leaf_to_section.get(slug, {})
            for ans in q.answers:
                section = section_lookup.get(ans.category_xml_id, "(other)")
                cell = tallies[slug][section]
                if ans.value == "1":
                    cell["yes"] += 1
                    cell["total"] += 1
                elif ans.value == "0":
                    cell["total"] += 1
                else:
                    cell["anomaly"] += 1

    # 4. Materialise charts in the canonical slug order.
    charts: list[CriteriaSetChart] = []
    seen_slugs: set[str] = set()
    canonical_order = [s for s, _ in CRITERIA_LABELS.values()]
    ordered_slugs = list(dict.fromkeys(canonical_order)) + sorted(
        s for s in tallies if s not in canonical_order
    )
    for slug in ordered_slugs:
        if slug in seen_slugs or slug not in tallies:
            continue
        seen_slugs.add(slug)
        # Section order: follow the order they appear in the (first) taxonomy walk.
        section_order = list(slug_sections[slug].keys())
        section_aggs: list[SectionAggregate] = []
        anomaly_total = 0
        for label in section_order:
            cell = tallies[slug].get(label, {"yes": 0, "total": 0, "anomaly": 0})
            section_aggs.append(
                SectionAggregate(
                    label=label,
                    yes=cell["yes"],
                    total=cell["total"],
                    anomaly=cell["anomaly"],
                )
            )
            anomaly_total += cell["anomaly"]
        # "(other)" bucket if any answers landed outside the known sections.
        if "(other)" in tallies[slug]:
            cell = tallies[slug]["(other)"]
            section_aggs.append(
                SectionAggregate(
                    label="(other)",
                    yes=cell["yes"],
                    total=cell["total"],
                    anomaly=cell["anomaly"],
                )
            )
            anomaly_total += cell["anomaly"]

        # Find the display label by reverse-lookup on the slug.
        display = next(
            (lbl for u, (s, lbl) in CRITERIA_LABELS.items() if s == slug),
            slug,
        )
        charts.append(
            CriteriaSetChart(
                slug=slug,
                label=display,
                review_count=review_counts[slug],
                sections=tuple(section_aggs),
                anomaly_count=anomaly_total,
            )
        )
    return tuple(charts)


# ── SVG rendering ─────────────────────────────────────────────────────


_BAR_HEIGHT = 22
_ROW_GAP = 8
_LEFT = 220
_BAR_WIDTH = 360
_AXIS_TOP = 20
_AXIS_BOTTOM_PAD = 36


def render_chart_svg(chart: CriteriaSetChart) -> str:
    """One inline SVG for a single :class:`CriteriaSetChart`.

    Layout: horizontal bar chart, one row per top-level section.
    Y-labels live at the left, the bar fills 0–100 % yes-rate, the
    in-bar annotation reads ``yes / total (pct%)``. Width is fixed at
    600 px so it scales responsively under the editorial column.
    """
    rows = len(chart.sections)
    height = _AXIS_TOP + rows * (_BAR_HEIGHT + _ROW_GAP) + _AXIS_BOTTOM_PAD
    width = _LEFT + _BAR_WIDTH + 60  # right padding for tail labels

    parts: list[str] = []
    parts.append(
        f'<svg class="ride-chart__svg" viewBox="0 0 {width} {height}" '
        f'role="img" aria-labelledby="chart-{chart.slug}-title" '
        f'preserveAspectRatio="xMinYMin meet" xmlns="http://www.w3.org/2000/svg">'
    )
    parts.append(
        f'<title id="chart-{chart.slug}-title">'
        f'{escape(chart.label)} — yes-rate per top-level section across '
        f'{chart.review_count} reviews</title>'
    )

    # Vertical grid lines + axis ticks at 0/25/50/75/100.
    for tick in (0, 25, 50, 75, 100):
        x = _LEFT + (tick / 100.0) * _BAR_WIDTH
        parts.append(
            f'<line x1="{x:.1f}" y1="{_AXIS_TOP}" x2="{x:.1f}" '
            f'y2="{_AXIS_TOP + rows * (_BAR_HEIGHT + _ROW_GAP)}" '
            f'class="ride-chart__grid"/>'
        )
        parts.append(
            f'<text x="{x:.1f}" y="{_AXIS_TOP + rows * (_BAR_HEIGHT + _ROW_GAP) + 16}" '
            f'class="ride-chart__tick" text-anchor="middle">{tick}%</text>'
        )

    # Bars.
    for i, sec in enumerate(chart.sections):
        y = _AXIS_TOP + i * (_BAR_HEIGHT + _ROW_GAP)
        bar_w = (sec.yes_pct / 100.0) * _BAR_WIDTH
        parts.append(
            f'<text x="{_LEFT - 10}" y="{y + _BAR_HEIGHT * 0.7:.1f}" '
            f'class="ride-chart__row-label" text-anchor="end">{escape(sec.label)}</text>'
        )
        parts.append(
            f'<rect x="{_LEFT}" y="{y}" width="{_BAR_WIDTH}" height="{_BAR_HEIGHT}" '
            f'class="ride-chart__bar-bg"/>'
        )
        if bar_w > 0:
            parts.append(
                f'<rect x="{_LEFT}" y="{y}" width="{bar_w:.1f}" height="{_BAR_HEIGHT}" '
                f'class="ride-chart__bar-fg"/>'
            )
        annotation = f"{sec.yes} / {sec.total} ({sec.yes_pct:.0f}%)"
        # Place annotation outside the bar when bar is too short to fit it.
        anno_x = _LEFT + max(bar_w + 6, 6)
        parts.append(
            f'<text x="{anno_x:.1f}" y="{y + _BAR_HEIGHT * 0.7:.1f}" '
            f'class="ride-chart__bar-annotation">{annotation}</text>'
        )

    parts.append("</svg>")
    return "".join(parts)


def render_charts_html(
    reviews: tuple[Review, ...],
    sections_by_url: dict[str, tuple[TaxonomySection, ...]],
) -> str:
    """Full chart block to substitute into the editorial body.

    Wrapped in ``<div class="ride-charts">`` so the editorial CSS can
    style the block as a unit. Each chart is its own ``<figure>`` with
    a heading, the SVG, and an anomaly note when applicable.
    """
    charts = aggregate_questionnaires(reviews, sections_by_url)
    if not charts:
        return ""
    parts: list[str] = ['<div class="ride-charts">']
    for chart in charts:
        parts.append(
            f'<figure class="ride-charts__figure" id="chart-{chart.slug}">'
        )
        parts.append(
            f'<figcaption class="ride-charts__caption">'
            f'<strong>{escape(chart.label)}</strong> '
            f'<span class="ride-charts__count">— {chart.review_count} review'
            f'{"s" if chart.review_count != 1 else ""}</span>'
            f'</figcaption>'
        )
        parts.append(render_chart_svg(chart))
        if chart.anomaly_count > 0:
            parts.append(
                f'<p class="ride-charts__anomaly">'
                f'{chart.anomaly_count} answer'
                f'{"s" if chart.anomaly_count != 1 else ""} carried '
                f'<code>value="3"</code> and were excluded from the '
                f'percentage (anomaly per <a href="data.html">data.md</a>).'
                f'</p>'
            )
        parts.append("</figure>")
    parts.append("</div>")
    return "".join(parts)


def collect_sections_from_corpus(
    parsed_paths: "list[tuple[object, Review]]",
) -> dict[str, tuple[TaxonomySection, ...]]:
    """Extract a merged section structure per criteria URL from the corpus.

    Each TEI file's ``<taxonomy>`` only declares leaves the review
    actually answered, so a single review's tree is incomplete. The
    function walks every parsed file, runs
    :func:`src.parser.questionnaire.parse_taxonomy_sections`, and
    unions the leaf xml:ids per (criteria_url, top-level-section). The
    resulting map covers every leaf that appears anywhere in the
    corpus — without it, leaves that are absent from the first walked
    review fall into the ``(other)`` aggregation bucket.

    Top-level section *order* follows the first review encountered for
    each URL, since every review using the same criteria document
    presents the same top-level section sequence.
    """
    from lxml import etree

    from src.parser.questionnaire import parse_taxonomy_sections

    section_order: dict[str, list[str]] = {}
    leaves: dict[str, dict[str, set[str]]] = {}
    needed: set[str] = set()
    for _, review in parsed_paths:
        for q in review.questionnaires:
            needed.add(q.criteria_url)
    for path, review in parsed_paths:
        urls_in_review = {q.criteria_url for q in review.questionnaires}
        if not (urls_in_review & needed):
            continue
        tree = etree.parse(str(path))
        per_url = parse_taxonomy_sections(tree.getroot())
        for url, sections in per_url.items():
            if url not in needed:
                continue
            url_leaves = leaves.setdefault(url, {})
            url_order = section_order.setdefault(url, [])
            for sec in sections:
                if sec.label not in url_leaves:
                    url_leaves[sec.label] = set()
                    url_order.append(sec.label)
                url_leaves[sec.label].update(sec.leaf_xml_ids)

    return {
        url: tuple(
            TaxonomySection(label=label, leaf_xml_ids=tuple(sorted(leaves[url][label])))
            for label in section_order[url]
        )
        for url in leaves
    }


def render_charts_block(
    reviews: tuple[Review, ...],
    parsed_paths: "Optional[list[tuple[object, Review]]]" = None,
) -> str:
    """Convenience wrapper used by the build: collect sections then render.

    ``parsed_paths`` is the build's ``parsed`` list (path, review). When
    the data-charts page is rendered outside the build (tests, dev), pass
    the same shape — the function tolerates an empty list and returns
    the empty string, which the editorial template substitutes in place
    of the marker without breaking the page.
    """
    if not reviews or not parsed_paths:
        return ""
    sections_by_url = collect_sections_from_corpus(parsed_paths)
    return render_charts_html(reviews, sections_by_url)
