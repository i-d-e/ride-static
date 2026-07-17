"""Tests for src.render.questionnaires — per-question aggregate tables.

Test-data philosophy per CLAUDE.md hard rule, mirroring
``tests/test_render_charts.py``:

* :func:`aggregate_questions` and :func:`render_questionnaire_table` are
  pure functions over typed inputs; their unit tests build a small
  synthetic corpus directly so per-branch behaviour (yes/answered/anomaly
  bookkeeping, categorical detection, slug merging, compound-review key
  folding, escape) is exercised crisply — pure-function-unit per the
  CLAUDE.md exception.
* The real-corpus integration proves the parse → aggregate → HTML →
  marker-substitution pipeline against the four criteria URLs and the
  ``value="3"`` anomaly review that only live in the corpus.
"""
from __future__ import annotations

from src.model.questionnaire import Questionnaire, QuestionnaireQuestion
from src.model.review import Review
from src.render.questionnaires import (
    _is_answered,
    _is_yes,
    _question_key,
    aggregate_questions,
    render_questionnaire_table,
    render_questionnaires_html,
)

from tests._shared import REPO_ROOT


# ── Key + answer helpers ──────────────────────────────────────────────


def test_question_key_strips_compound_resource_prefix():
    """``rev1-te042`` and ``rev2-te042`` fold onto the same question key."""
    assert _question_key("rev1-te042") == "te042"
    assert _question_key("rev2-te042") == "te042"
    assert _question_key("se016") == "se016"


def test_is_yes_and_answered_classify_selection_shapes():
    def q(selected, anomaly=False):
        return QuestionnaireQuestion(
            section_label="s",
            question_label="q",
            question_text="",
            criteria_ref=None,
            selected=selected,
            anomaly=anomaly,
        )

    assert _is_yes(q(("Yes",))) is True
    assert _is_yes(q(("No",))) is False
    assert _is_yes(q(())) is False
    assert _is_yes(q(("doc", "rtf"))) is True  # categorical, any selection
    assert _is_answered(q(("No",))) is True
    assert _is_answered(q(())) is False


# ── Aggregation (synthetic) ──────────────────────────────────────────


def _review(
    review_id: str,
    criteria_url: str,
    questions: list[QuestionnaireQuestion],
) -> Review:
    """Minimally-populated Review carrying one Questionnaire with a
    per-question view. Synthetic by design — aggregate_questions only
    reads ``review.id`` and each questionnaire's ``questions`` tuple."""
    return Review(
        id=review_id,
        issue="0",
        title="t",
        publication_date="",
        language="en",
        licence="",
        questionnaires=(
            Questionnaire(
                criteria_url=criteria_url,
                answers=(),
                questions=tuple(questions),
            ),
        ),
    )


def _q(qid, section, label, selected, anomaly=False):
    return QuestionnaireQuestion(
        section_label=section,
        question_label=label,
        question_text="",
        criteria_ref=None,
        selected=tuple(selected),
        anomaly=anomaly,
        category_xml_id=qid,
    )


def test_aggregate_counts_yes_answered_per_question():
    url = "http://www.i-d-e.de/publikationen/weitereschriften/criteria-version-1-1"
    reviews = (
        _review("r1", url, [_q("q1", "aims", "Has aims?", ["Yes"])]),
        _review("r2", url, [_q("q1", "aims", "Has aims?", ["No"])]),
        _review("r3", url, [_q("q1", "aims", "Has aims?", ["Yes"])]),
    )
    [table] = aggregate_questions(reviews)
    assert table.review_count == 3
    [row] = table.rows
    assert (row.yes, row.answered, row.anomaly) == (2, 3, 0)
    assert abs(row.yes_pct - (100.0 * 2 / 3)) < 1e-9
    assert row.categorical is False


def test_aggregate_tracks_anomaly_separately():
    url = "http://www.i-d-e.de/publikationen/weitereschriften/criteria-version-1-1"
    reviews = (
        _review("r1", url, [_q("q1", "aims", "Q", ["Yes"])]),
        _review("r2", url, [_q("q1", "aims", "Q", [], anomaly=True)]),
    )
    [table] = aggregate_questions(reviews)
    [row] = table.rows
    assert (row.yes, row.answered, row.anomaly) == (1, 1, 1)
    assert table.anomaly_count == 1


def test_aggregate_flags_categorical_question():
    url = "http://www.i-d-e.de/publikationen/weitereschriften/criteria-version-1-1"
    reviews = (
        _review("r1", url, [_q("q1", "content", "Formats", ["doc", "rtf"])]),
        _review("r2", url, [_q("q1", "content", "Formats", ["epub"])]),
    )
    [table] = aggregate_questions(reviews)
    [row] = table.rows
    assert row.categorical is True
    # Any non-empty selection is affirmative for a categorical question.
    assert (row.yes, row.answered) == (2, 2)


def test_aggregate_folds_compound_resource_prefix():
    """One compound review answering the same question for two resources
    counts the question twice (once per resource), under one key."""
    url = "http://www.i-d-e.de/publikationen/weitereschriften/criteria-version-1-1"
    review = Review(
        id="r1",
        issue="0",
        title="t",
        publication_date="",
        language="en",
        licence="",
        questionnaires=(
            Questionnaire(
                criteria_url=url,
                answers=(),
                questions=(_q("rev1-te042", "aims", "Q", ["Yes"]),),
            ),
            Questionnaire(
                criteria_url=url,
                answers=(),
                questions=(_q("rev2-te042", "aims", "Q", ["No"]),),
            ),
        ),
    )
    [table] = aggregate_questions((review,))
    assert len(table.rows) == 1
    [row] = table.rows
    assert row.key == "te042"
    assert (row.yes, row.answered) == (1, 2)


def test_aggregate_merges_text_collections_url_variants():
    url_a = "http://www.i-d-e.de/criteria-text-collections-version-1-0"
    url_b = "https://www.i-d-e.de/publikationen/weitereschriften/criteria-text-collections-version-1-0/"
    reviews = (
        _review("r1", url_a, [_q("q1", "aims", "Q", ["Yes"])]),
        _review("r2", url_b, [_q("q1", "aims", "Q", ["No"])]),
    )
    tables = aggregate_questions(reviews)
    tc = [t for t in tables if t.slug == "text-collections-1.0"]
    assert len(tc) == 1
    assert tc[0].review_count == 2
    assert tc[0].rows[0].answered == 2


def test_aggregate_orders_sets_by_canonical_priority():
    de_url = "http://www.i-d-e.de/publikationen/weitereschriften/criteria-version-1-1"
    tools_url = "https://www.i-d-e.de/publikationen/weitereschriften/criteria-tools-version-1/"
    reviews = (
        _review("r-tools", tools_url, [_q("q1", "s", "Q", ["Yes"])]),
        _review("r-de", de_url, [_q("q1", "s", "Q", ["Yes"])]),
    )
    tables = aggregate_questions(reviews)
    assert tables[0].slug == "digital-editions-1.1"
    assert tables[1].slug == "tools-1.0"


def test_aggregate_returns_empty_when_no_reviews():
    assert aggregate_questions(()) == ()


# ── HTML rendering ────────────────────────────────────────────────────


def test_render_table_groups_rows_under_section_heading():
    url = "http://www.i-d-e.de/publikationen/weitereschriften/criteria-version-1-1"
    reviews = (
        _review(
            "r1",
            url,
            [
                _q("q1", "Documentation", "Bibliographic description", ["Yes"]),
                _q("q2", "Contents", "Scope", ["No"]),
            ],
        ),
    )
    [table] = aggregate_questions(reviews)
    html = render_questionnaire_table(table)
    assert "ride-questionnaires__section" in html
    assert ">Documentation<" in html
    assert ">Contents<" in html
    assert "Bibliographic description" in html


def test_render_table_escapes_html_in_labels():
    url = "http://www.i-d-e.de/publikationen/weitereschriften/criteria-version-1-1"
    reviews = (_review("r1", url, [_q("q1", "<sec>", "<script>", ["Yes"])]),)
    [table] = aggregate_questions(reviews)
    html = render_questionnaire_table(table)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "&lt;sec&gt;" in html


def test_render_html_includes_anomaly_note_when_present():
    url = "http://www.i-d-e.de/publikationen/weitereschriften/criteria-version-1-1"
    reviews = (_review("r1", url, [_q("q1", "s", "Q", [], anomaly=True)]),)
    html = render_questionnaires_html(reviews)
    # A review whose only question is an anomaly has no answered rows, so
    # the table is dropped and the block is empty; anomaly note appears only
    # alongside real rows. Add a real answer to surface both.
    reviews2 = (
        _review("r1", url, [_q("q1", "s", "Q", ["Yes"]), _q("q2", "s", "Q2", [], anomaly=True)]),
    )
    html2 = render_questionnaires_html(reviews2)
    assert "ride-questionnaires__anomaly" in html2
    assert 'value="3"' in html2


def test_render_html_returns_empty_when_no_data():
    assert render_questionnaires_html(()) == ""


# ── Real-corpus drive ────────────────────────────────────────────────


def test_real_corpus_questionnaires_block_carries_sets_and_anomaly(corpus_parsed):
    """Render the block from the real corpus and pin its corpus-level
    invariants: the three logical criteria sets each yield a table, the
    per-question tables carry section groupings, and the value=3 anomaly
    is reported."""
    reviews = tuple(r for _, r in corpus_parsed)
    block = render_questionnaires_html(reviews)

    assert "Criteria for Reviewing Digital Editions (1.1)" in block
    assert "Criteria for Reviewing Tools and Environments (1.0)" in block
    assert "Criteria for Reviewing Text Collections (1.0)" in block
    # One table per logical set.
    assert block.count("ride-questionnaires__table") == 3
    # Section grouping rows are present.
    assert "ride-questionnaires__section" in block
    # value=3 anomaly is present in the corpus (varitext-tei.xml).
    assert "ride-questionnaires__anomaly" in block


def test_real_corpus_aggregation_review_counts_are_deduped(corpus_parsed):
    """review_count is distinct reviews per set, matching the charts view."""
    reviews = tuple(r for _, r in corpus_parsed)
    tables = {t.slug: t for t in aggregate_questions(reviews)}
    assert tables["digital-editions-1.1"].review_count >= 70
    assert tables["tools-1.0"].review_count >= 15
    assert tables["text-collections-1.0"].review_count >= 18
    # Every table has at least one question row.
    for table in tables.values():
        assert table.rows


def test_real_corpus_data_questionnaires_page_substitutes_marker(corpus_parsed):
    """Integration: rendering content/data-questionnaires.md with a
    corpus-derived block substitutes the marker and emits the tables."""
    from src.render.editorial import parse_editorial, render_editorial

    reviews = tuple(r for _, r in corpus_parsed[:40])
    block = render_questionnaires_html(reviews)
    page = parse_editorial(REPO_ROOT / "content" / "data-questionnaires.md")
    html = render_editorial(page, questionnaires_html=block)

    assert "<!-- ride:questionnaires -->" not in html
    assert "ride-questionnaires__table" in html
    assert "Criteria for Reviewing" in html
