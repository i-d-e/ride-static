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
    help_lookup_key,
    humanize_label,
    load_help_texts,
    render_factsheet,
    reviewed_resource,
)
from src.render.html import SiteConfig


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


def test_render_factsheet_canonical_url_is_review_url_plus_factsheet():
    """The canonical/og:url is the single-source review URL with a
    ``factsheet/`` suffix, so it stays in lockstep with ``review_url`` and
    the page's own address ``/issues/{issue}/{id}/factsheet/``."""
    site = SiteConfig(title="RIDE", base_url="https://ride.i-d-e.de", default_language="en")
    html = render_factsheet(_review_with_factsheet(), site)
    assert (
        '<link rel="canonical" href="https://ride.i-d-e.de/issues/21/ride.21.4/factsheet/">'
        in html
    )


def test_render_factsheet_obfuscates_reviewer_email():
    html = render_factsheet(_review_with_factsheet())
    assert "jane@example.org" not in html
    assert "[at]" in html
    # Obfuscated text only — a mailto: built from the obfuscated form
    # would be an invalid URL and a dead link (W3C Nu finding 2026-07-10).
    assert "mailto:" not in html


# ── Feature 1: criteria help texts ────────────────────────────────────


def test_help_lookup_key_strips_compound_prefix():
    # Pure function: revN- prefix stripped, bare ids untouched.
    assert help_lookup_key("rev1-te042") == "te042"
    assert help_lookup_key("se016") == "se016"
    assert help_lookup_key("") == ""


def test_load_help_texts_parses_sections(tmp_path):
    """Synthetic fixture (pure loader over a tiny vault): ``## id`` sections
    become an id→HTML map; the intro comment before the first heading is
    ignored."""
    d = tmp_path / "factsheet-help"
    d.mkdir()
    (d / "se.md").write_text(
        "<!-- provenance comment -->\n\n"
        "## se016\n\n*Archiving of data*\n\nChoose yes if the data is cared for.\n\n"
        "## se075\n\n- **Letters** — letters of one or several authors.\n",
        encoding="utf-8",
    )
    texts = load_help_texts(d)
    assert set(texts) == {"se016", "se075"}
    assert "Archiving of data" in texts["se016"]
    assert "<p>" in texts["se016"]
    assert "provenance comment" not in texts["se016"]
    assert "Letters" in texts["se075"]


def test_load_help_texts_missing_dir_degrades(tmp_path):
    assert load_help_texts(tmp_path / "nope") == {}


def test_render_factsheet_attaches_help_details():
    """A question whose category id has a help entry renders a native
    ``<details>`` toggle with the help HTML; ``<details>`` sits as a sibling
    of the label/answer paragraphs (flow content, not inside a ``<p>``)."""
    q = QuestionnaireQuestion(
        section_label="Documentation",
        question_label="Archiving of data",
        question_text="Is archiving documented?",
        criteria_ref=None,
        selected=("Yes",),
        category_xml_id="se016",
    )
    questionnaire = Questionnaire(criteria_url="", answers=(), questions=(q,))
    review = _review_with_factsheet(questionnaires=(questionnaire,))
    help_texts = {"se016": "<p>archiving help body</p>"}
    html = render_factsheet(review, help_texts=help_texts)
    assert 'class="ride-question__help"' in html
    assert "archiving help body" in html
    assert 'aria-label="Explanation"' in html
    # details must not be nested inside the label paragraph.
    assert "<p class=\"ride-question__label\">" in html


def test_render_factsheet_no_help_when_absent():
    """A question without a matching help entry renders no details toggle."""
    html = render_factsheet(_review_with_factsheet(), help_texts={})
    assert "ride-question__help" not in html


# ── Feature 3: compound-review resource headings ───────────────────────


def test_render_factsheet_labels_compound_blocks():
    """Two taxonomies with revN resource keys each get a heading naming the
    matching reviewed resource; single-resource reviews get none."""
    res1 = RelatedItem(type="reviewed_resource", bibl_text="", xml_id="rev1", title="Juxta")
    res2 = RelatedItem(type="reviewed_resource", bibl_text="", xml_id="rev2", title="LERA")
    q1 = Questionnaire(criteria_url="", answers=(), questions=(), resource_key="rev1")
    q2 = Questionnaire(criteria_url="", answers=(), questions=(), resource_key="rev2")
    review = _review_with_factsheet(
        related_items=(res1, res2), questionnaires=(q1, q2)
    )
    html = render_factsheet(review)
    assert 'class="ride-questionnaire__resource"' in html
    assert "Juxta" in html
    assert "LERA" in html


def test_render_factsheet_single_resource_has_no_block_heading():
    html = render_factsheet(_review_with_factsheet())
    assert "ride-questionnaire__resource" not in html


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


def test_render_factsheet_real_corpus_makingandknowing_help(corpus_review):
    """Feature 1 end to end: the se016 criterion ("Archiving of data") carries
    a help entry, so its rendered row gains a native help toggle with the
    definition body from content/factsheet-help/se.md."""
    html = render_factsheet(corpus_review)
    assert 'class="ride-question__help"' in html
    assert "long term sustainability" in html


def _find_tei_or_skip(stem):
    from src._corpus import find_tei

    path = find_tei(stem)
    if not path.exists():
        import pytest

        pytest.skip(f"{stem} not in corpus")
    return path


def test_render_factsheet_real_corpus_collationtools_labels_three_blocks():
    """Feature 3 end to end: collationtools reviews three resources across
    three taxonomies; each block renders a heading naming its resource."""
    from src.parser.review import parse_review

    review = parse_review(_find_tei_or_skip("collationtools"))
    html = render_factsheet(review)
    assert html.count('class="ride-questionnaire__resource"') == 3
    for title in ("Juxta Web Service", "LERA", "Variance Viewer"):
        assert title in html, f"missing resource heading: {title}"


def test_render_factsheet_real_corpus_collationtools_gloss():
    """Feature 2 end to end: the "Other" free-text gloss surfaces in the
    rendered selection."""
    from src.parser.review import parse_review

    review = parse_review(_find_tei_or_skip("collationtools"))
    html = render_factsheet(review)
    assert "doc, rtf, epub" in html
