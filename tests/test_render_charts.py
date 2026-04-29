"""Tests for src.render.charts — questionnaire aggregate + SVG (R9).

Test-data philosophy per CLAUDE.md hard rule:

* :func:`aggregate_questionnaires` and :func:`render_chart_svg` are
  pure functions over typed inputs; their unit tests build a small
  synthetic corpus directly so per-branch behaviour (yes/no/anomaly
  bookkeeping, slug merging, empty-section handling, escape) is
  exercised crisply — pure-function-unit per the CLAUDE.md exception.
* :func:`render_charts_block` and the editorial-hook integration test
  use the real corpus: that's where the four criteria URLs and the
  ``value="3"`` anomaly review live, and that's the only place that
  proves the pipeline (parse → aggregate → SVG → marker substitution)
  end-to-end.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree

from src.model.questionnaire import (
    Questionnaire,
    QuestionnaireAnswer,
    TaxonomySection,
)
from src.model.review import Review
from src.parser.questionnaire import parse_taxonomy_sections
from src.parser.review import parse_review
from src.render.charts import (
    CRITERIA_LABELS,
    aggregate_questionnaires,
    collect_sections_from_corpus,
    criteria_label,
    criteria_slug,
    render_chart_svg,
    render_charts_block,
    render_charts_html,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
RIDE_TEI_DIR = REPO_ROOT.parent / "ride" / "tei_all"

needs_corpus = pytest.mark.skipif(
    not RIDE_TEI_DIR.is_dir(), reason="../ride/ corpus not available"
)


# ── Slug + label registry ─────────────────────────────────────────────


def test_criteria_slug_maps_known_urls_to_their_canonical_form():
    """The four corpus URLs collapse to three logical slugs."""
    slugs = {criteria_slug(u) for u in CRITERIA_LABELS}
    assert slugs == {"digital-editions-1.1", "tools-1.0", "text-collections-1.0"}


def test_criteria_slug_falls_back_to_url_tail_for_unknown():
    """Unregistered URLs use a stable tail-of-path slug, never empty."""
    assert criteria_slug("http://example.org/criteria/foo-1") == "foo-1"
    assert criteria_slug("http://example.org/criteria/") == "criteria"


def test_criteria_label_returns_url_when_unknown():
    """Unknown URLs fall through to themselves so the chart still renders."""
    assert criteria_label("http://example.org/x") == "http://example.org/x"


# ── Aggregation (synthetic) ──────────────────────────────────────────


def _make_review(
    review_id: str,
    criteria_url: str,
    answers: list[tuple[str, str]],
) -> Review:
    """Build a minimally-populated Review carrying one Questionnaire.

    Synthetic by design — pure-function unit per CLAUDE.md exception:
    aggregate_questionnaires only looks at ``review.id`` and the
    ``Questionnaire`` tuple, so the rest of the dataclass is empty."""
    return Review(
        id=review_id,
        issue="0",
        title="t",
        publication_date="",
        language="en",
        licence="",
        keywords=(),
        authors=(),
        editors=(),
        related_items=(),
        front=(),
        body=(),
        back=(),
        figures=(),
        notes=(),
        bibliography=(),
        questionnaires=(
            Questionnaire(
                criteria_url=criteria_url,
                answers=tuple(
                    QuestionnaireAnswer(category_xml_id=cid, value=v)
                    for cid, v in answers
                ),
            ),
        ),
    )


def _sections(label_leaves: list[tuple[str, list[str]]]) -> tuple[TaxonomySection, ...]:
    return tuple(
        TaxonomySection(label=lbl, leaf_xml_ids=tuple(leaves))
        for lbl, leaves in label_leaves
    )


def test_aggregate_counts_yes_no_anomaly_per_section():
    sections = _sections([("aims", ["a1", "a2"]), ("content", ["c1"])])
    reviews = (
        _make_review("r1", "http://crit/x", [("a1", "1"), ("a2", "0"), ("c1", "1")]),
        _make_review("r2", "http://crit/x", [("a1", "1"), ("a2", "1"), ("c1", "3")]),
    )
    charts = aggregate_questionnaires(reviews, {"http://crit/x": sections})
    assert len(charts) == 1
    chart = charts[0]
    assert chart.review_count == 2
    aims, content = chart.sections
    assert (aims.yes, aims.total, aims.anomaly) == (3, 4, 0)
    assert (content.yes, content.total, content.anomaly) == (1, 1, 1)
    assert chart.anomaly_count == 1


def test_aggregate_merges_url_variants_under_same_slug():
    """The two text-collections URLs share a slug; they must aggregate together."""
    url_a, url_b = (
        "http://www.i-d-e.de/criteria-text-collections-version-1-0",
        "https://www.i-d-e.de/publikationen/weitereschriften/criteria-text-collections-version-1-0/",
    )
    secs = _sections([("aims", ["a1"])])
    reviews = (
        _make_review("r1", url_a, [("a1", "1")]),
        _make_review("r2", url_b, [("a1", "0")]),
    )
    charts = aggregate_questionnaires(reviews, {url_a: secs, url_b: secs})
    text_coll = [c for c in charts if c.slug == "text-collections-1.0"]
    assert len(text_coll) == 1
    assert text_coll[0].review_count == 2
    assert text_coll[0].sections[0].total == 2
    assert text_coll[0].sections[0].yes == 1


def test_aggregate_routes_unknown_leaf_to_other_bucket():
    sections = _sections([("aims", ["a1"])])
    reviews = (_make_review("r1", "http://crit/x", [("a1", "1"), ("ZZ", "1")]),)
    chart = aggregate_questionnaires(reviews, {"http://crit/x": sections})[0]
    other = [s for s in chart.sections if s.label == "(other)"]
    assert other and other[0].yes == 1


def test_aggregate_returns_empty_when_no_reviews():
    assert aggregate_questionnaires((), {}) == ()


def test_aggregate_orders_charts_by_canonical_label_priority():
    """Digital-editions slug must come before tools and text-collections."""
    de_url = "http://www.i-d-e.de/publikationen/weitereschriften/criteria-version-1-1"
    tools_url = "https://www.i-d-e.de/publikationen/weitereschriften/criteria-tools-version-1/"
    secs = _sections([("aims", ["a"])])
    reviews = (
        _make_review("r-tools", tools_url, [("a", "1")]),
        _make_review("r-de", de_url, [("a", "1")]),
    )
    charts = aggregate_questionnaires(reviews, {de_url: secs, tools_url: secs})
    assert charts[0].slug == "digital-editions-1.1"
    assert charts[1].slug == "tools-1.0"


# ── SVG rendering ────────────────────────────────────────────────────


def test_render_chart_svg_emits_one_bar_per_section_and_axis_ticks():
    sections = _sections([("aims", ["a1"]), ("content", ["c1"])])
    reviews = (_make_review("r1", "http://crit/x", [("a1", "1"), ("c1", "0")]),)
    chart = aggregate_questionnaires(reviews, {"http://crit/x": sections})[0]
    svg = render_chart_svg(chart)

    assert svg.startswith("<svg")
    # Axis ticks at 0/25/50/75/100.
    for tick in (0, 25, 50, 75, 100):
        assert f">{tick}%</text>" in svg
    # One row label per section.
    assert ">aims</text>" in svg
    assert ">content</text>" in svg
    # 100% bar for aims (1/1) and 0% bar for content (0/1).
    assert "1 / 1 (100%)" in svg
    assert "0 / 1 (0%)" in svg


def test_render_chart_svg_escapes_html_in_section_labels():
    sections = _sections([("<script>", ["a1"])])
    chart = aggregate_questionnaires(
        (_make_review("r1", "http://crit/x", [("a1", "1")]),),
        {"http://crit/x": sections},
    )[0]
    svg = render_chart_svg(chart)
    assert "<script>" not in svg
    assert "&lt;script&gt;" in svg


def test_render_charts_html_includes_anomaly_note_when_present():
    sections = _sections([("aims", ["a1"])])
    reviews = (_make_review("r1", "http://crit/x", [("a1", "3")]),)
    out = render_charts_html(reviews, {"http://crit/x": sections})
    assert "ride-charts__anomaly" in out
    assert 'value="3"' in out


def test_render_charts_html_omits_anomaly_note_when_clean():
    sections = _sections([("aims", ["a1"])])
    reviews = (_make_review("r1", "http://crit/x", [("a1", "1")]),)
    out = render_charts_html(reviews, {"http://crit/x": sections})
    assert "ride-charts__anomaly" not in out


def test_render_charts_html_returns_empty_string_when_no_data():
    assert render_charts_html((), {}) == ""


def test_render_charts_block_with_empty_inputs_is_empty():
    """The build calls render_charts_block before the corpus may be loaded
    (e.g. test mode) — empty inputs return '' so the editorial marker
    stays untouched in the output."""
    assert render_charts_block((), parsed_paths=None) == ""
    assert render_charts_block((), parsed_paths=[]) == ""


# ── Real-corpus drive ────────────────────────────────────────────────


@needs_corpus
def test_collect_sections_finds_every_criteria_url_in_corpus():
    """The four corpus criteria URLs each yield a non-empty section list."""
    files = sorted(RIDE_TEI_DIR.glob("*-tei.xml"))
    parsed = []
    for f in files:
        try:
            r = parse_review(f)
        except Exception:
            continue
        if r.questionnaires:
            parsed.append((f, r))
    sections_by_url = collect_sections_from_corpus(parsed)
    # Each URL has at least 5 top-level sections.
    for url in CRITERIA_LABELS:
        assert url in sections_by_url, f"missing taxonomy for {url}"
        assert len(sections_by_url[url]) >= 5, (
            f"{url} yielded only {len(sections_by_url[url])} sections"
        )


@needs_corpus
def test_real_corpus_charts_block_carries_three_sets_and_anomaly():
    """Render the block from the real corpus and pin its corpus-level
    invariants: three logical criteria sets, the value=3 anomaly is
    reported, and review_count totals match the questionnaire count."""
    files = sorted(RIDE_TEI_DIR.glob("*-tei.xml"))
    reviews = []
    parsed = []
    for f in files:
        try:
            r = parse_review(f)
        except Exception:
            continue
        reviews.append(r)
        parsed.append((f, r))
    block = render_charts_block(tuple(reviews), parsed_paths=parsed)

    assert "Criteria for Reviewing Digital Editions (1.1)" in block
    assert "Criteria for Reviewing Tools and Environments (1.0)" in block
    assert "Criteria for Reviewing Text Collections (1.0)" in block
    # Three figures (one per slug), three SVGs.
    assert block.count('class="ride-charts__figure"') == 3
    assert block.count("<svg") == 3
    # value=3 anomaly is present in the corpus (varitext-tei.xml).
    assert "ride-charts__anomaly" in block

    # review_count is *distinct reviews* answering each criteria set —
    # collationtools-tei.xml carries three taxonomies all pointing at the
    # digital-editions URL, so the questionnaire count (73) is two higher
    # than the deduped review count (71).
    sections_by_url = collect_sections_from_corpus(parsed)
    charts = aggregate_questionnaires(tuple(reviews), sections_by_url)
    by_slug = {c.slug: c for c in charts}
    assert by_slug["digital-editions-1.1"].review_count >= 70
    assert by_slug["tools-1.0"].review_count >= 15
    # text-collections appears under both http and https URL variants —
    # 10 reviews each per the corpus probe, merged by slug.
    assert by_slug["text-collections-1.0"].review_count >= 18


@needs_corpus
def test_real_corpus_aggregation_has_no_other_bucket():
    """Every answered leaf must land under a known top-level section.

    The (other) bucket only appears when a review answers a leaf whose
    xml:id is missing from the union of taxonomy walks. A single
    review's <taxonomy> only declares the leaves *that review* answered,
    so the section walker must (a) merge multiple taxonomies under the
    same URL within one review (carlyle-addams-tei.xml carries two,
    rev1-* and rev2-*) and (b) union across files. Both invariants
    are exercised here against the full corpus."""
    files = sorted(RIDE_TEI_DIR.glob("*-tei.xml"))
    parsed = []
    reviews = []
    for f in files:
        try:
            r = parse_review(f)
        except Exception:
            continue
        reviews.append(r)
        parsed.append((f, r))
    sections_by_url = collect_sections_from_corpus(parsed)
    charts = aggregate_questionnaires(tuple(reviews), sections_by_url)
    for chart in charts:
        labels = [s.label for s in chart.sections]
        assert "(other)" not in labels, (
            f"{chart.slug} produced an (other) bucket — "
            f"a leaf was answered without a known section. "
            f"Sections: {labels}"
        )


@needs_corpus
def test_real_corpus_data_charts_page_substitutes_marker(tmp_path):
    """Integration: rendering content/data-charts.md with a corpus-derived
    chart block substitutes the marker and emits inline SVG. Skips the
    full build() to avoid coupling the chart contract to the issue-config
    validator — that path is exercised by tests/test_render_editorial.py."""
    from src.render.editorial import parse_editorial, render_editorial

    files = sorted(RIDE_TEI_DIR.glob("*-tei.xml"))
    parsed = []
    reviews = []
    for f in files[:30]:
        try:
            r = parse_review(f)
        except Exception:
            continue
        reviews.append(r)
        parsed.append((f, r))

    chart_html = render_charts_block(tuple(reviews), parsed_paths=parsed)
    page = parse_editorial(REPO_ROOT / "content" / "data-charts.md")
    html = render_editorial(page, chart_html=chart_html)

    assert "<!-- ride:charts -->" not in html
    assert "<svg" in html
    assert "ride-charts" in html
    assert "Criteria for Reviewing" in html
