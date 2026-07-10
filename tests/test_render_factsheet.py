"""Tests for src.render.factsheet — the Factsheet full page (R18).

Two layers, per the CLAUDE.md hard rule:

1. Contract fixture — ``_review_with_factsheet`` is a documented
   render-contract builder: a small Review with controlled personnel and
   a single question, so the block-heading / selected-answer / K-ref
   assertions stay crisp. The helper unit tests (``group_personnel``,
   ``humanize_label``, ``criteria_link``) are pure functions over their
   argument shape.
2. Real-corpus drive — the ``corpus_review`` fixture (conftest.py) is
   makingandknowing (ride.21.4), the documented reference factsheet;
   the smoke test renders it end to end.

Tests assert the contract, not exact HTML, so the template can evolve.
"""
from __future__ import annotations

from src.model.questionnaire import (
    Questionnaire,
    QuestionnaireAnswer,
    QuestionnaireQuestion,
)
from src.model.review import Author, Person, RelatedItem, Review
from src.render.factsheet import (
    criteria_link,
    group_personnel,
    humanize_label,
    render_factsheet,
    reviewed_resource,
)


# ── Fixture builder ───────────────────────────────────────────────────


def _review_with_factsheet(**overrides) -> Review:
    question = QuestionnaireQuestion(
        section_label="Documentation",
        question_label="Bibliographic description",
        question_text="Is it possible to describe the project bibliographically?",
        criteria_ref="#K1.2",
        selected=("Yes",),
        anomaly=False,
    )
    questionnaire = Questionnaire(
        criteria_url="http://example.org/criteria-v1",
        answers=(QuestionnaireAnswer(category_xml_id="se002", value="1"),),
        questions=(question,),
    )
    reviewed = RelatedItem(
        type="reviewed_resource",
        bibl_text="The reviewed project",
        bibl_targets=("https://example.org/project",),
        last_accessed="2023-11-15",
        publication_date="2020",
        title="The Reviewed Project",
        personnel=(("Editor", "Smith, Pamela"), ("Programmer", "Catapano, Terry")),
    )
    base = dict(
        id="ride.21.4",
        issue="21",
        title="A Sample Review",
        publication_date="2026-04-29",
        language="en",
        licence="https://creativecommons.org/licenses/by/4.0/",
        authors=(
            Author(
                person=Person(full_name="Jane Reviewer", forename="Jane", surname="Reviewer"),
                email="jane@example.org",
            ),
        ),
        related_items=(reviewed,),
        questionnaires=(questionnaire,),
    )
    base.update(overrides)
    return Review(**base)


# ── Helper unit tests ─────────────────────────────────────────────────


def test_group_personnel_groups_by_role_preserving_order():
    item = RelatedItem(
        type="reviewed_resource",
        bibl_text="",
        personnel=(
            ("Editor", "Smith, Pamela"),
            ("Programmer", "Catapano, Terry"),
            ("Editor", "Rosenkranz, Naomi"),
        ),
    )
    groups = group_personnel(item)
    assert groups == [
        ("Editor", ["Smith, Pamela", "Rosenkranz, Naomi"]),
        ("Programmer", ["Catapano, Terry"]),
    ]


def test_group_personnel_handles_none_and_empty():
    assert group_personnel(None) == []
    assert group_personnel(RelatedItem(type="reviewed_resource", bibl_text="")) == []


def test_reviewed_resource_returns_first_or_none():
    review = _review_with_factsheet()
    assert reviewed_resource(review) is not None
    bare = Review(
        id="x", issue="1", title="t", publication_date="", language="en", licence=""
    )
    assert reviewed_resource(bare) is None


def test_criteria_link_resolves_and_guards():
    assert criteria_link("http://e.org/c", "#K1.2") == "http://e.org/c#K1.2"
    assert criteria_link("", "#K1.2") is None
    assert criteria_link("http://e.org/c", None) is None


def test_humanize_label():
    # xml:id-style headings (text-collections) get humanised …
    assert humanize_label("general_information") == "General information"
    assert humanize_label("data-modelling") == "Data modelling"
    assert humanize_label("aims") == "Aims"
    # … prose headings (digital-editions) keep their wording.
    assert humanize_label("Documentation") == "Documentation"
    assert humanize_label("Aims and methods") == "Aims and methods"
    assert humanize_label("") == ""


# ── Render contract ───────────────────────────────────────────────────


def test_render_factsheet_contains_block_headings():
    html = render_factsheet(_review_with_factsheet())
    assert "Reviewed resource" in html
    assert "People" in html
    assert "Questionnaire" in html


def test_render_factsheet_shows_question_and_selection():
    html = render_factsheet(_review_with_factsheet())
    assert "Bibliographic description" in html
    assert "Documentation" in html  # section heading
    assert "Yes" in html  # selected answer
    # K-ref link resolved against the taxonomy URL.
    assert "http://example.org/criteria-v1#K1.2" in html


def test_render_factsheet_shows_reviewed_resource_publication_date():
    html = render_factsheet(_review_with_factsheet())
    # The reviewed work's own publication date (R18 parity with the live
    # factsheet), distinct from the review's publication_date in the header.
    assert "2020" in html


def test_render_factsheet_shows_personnel_name():
    html = render_factsheet(_review_with_factsheet())
    assert "Smith, Pamela" in html
    assert "Programmer" in html


def test_render_factsheet_marks_anomaly_and_unanswered():
    anomaly_q = QuestionnaireQuestion(
        section_label="Quality",
        question_label="Quality check",
        question_text="Was quality checked?",
        criteria_ref=None,
        selected=(),
        anomaly=True,
    )
    none_q = QuestionnaireQuestion(
        section_label="Quality",
        question_label="Other",
        question_text="Anything?",
        criteria_ref=None,
        selected=(),
        anomaly=False,
    )
    q = Questionnaire(criteria_url="", answers=(), questions=(anomaly_q, none_q))
    html = render_factsheet(_review_with_factsheet(questionnaires=(q,)))
    assert "Not evaluated" in html
    assert "—" in html  # unanswered marker


def test_render_factsheet_without_reviewed_resource_does_not_crash():
    review = _review_with_factsheet(related_items=())
    html = render_factsheet(review)
    # Reviewed-resource and People blocks are omitted, questionnaire stays.
    assert "Questionnaire" in html
    assert "Smith, Pamela" not in html


def test_render_factsheet_obfuscates_reviewer_email():
    html = render_factsheet(_review_with_factsheet())
    assert "jane@example.org" not in html
    assert "[at]" in html


# ── Real-corpus smoke ─────────────────────────────────────────────────


def test_render_factsheet_real_corpus_makingandknowing(corpus_review):
    """corpus_review is makingandknowing (ride.21.4) — the documented
    reference factsheet with reviewed resource, personnel and a K-ref."""
    html = render_factsheet(corpus_review)
    for heading in ("Reviewed resource", "People", "Questionnaire"):
        assert heading in html, f"missing block: {heading}"
    # Documented first question and a known contributor.
    assert "Bibliographic description" in html
    assert "Smith, Pamela" in html
    # A resolved K-ref link against the criteria document.
    assert "criteria-version-1-1#K1.2" in html
