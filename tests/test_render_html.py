"""Tests for src.render.html — Phase 8 HTML rendering.

Two layers:

1. Synthetic fixtures — small Review instances built in code, rendered
   to HTML, asserted against expected markers. Independent of the corpus.
2. Real-corpus smoke test — parse and render up to N reviews from
   ``../ride/tei_all/`` end-to-end. Skips when the corpus is absent.

Tests assert the *contract* (right elements, classes, anchors), not the
exact HTML; templates can evolve without forcing test rewrites.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.model.bibliography import BibEntry
from src.model.block import Citation, Figure, List, ListItem, Paragraph
from src.model.inline import Emphasis, Note, Reference, Text
from src.model.questionnaire import Questionnaire, QuestionnaireAnswer
from src.model.review import Author, Person, Review
from src.model.section import Section
from src.render.html import (
    SiteConfig,
    _inlines_to_text,
    _obfuscate_mail,
    _slugify,
    make_env,
    render_review,
    split_abstract,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO_ROOT.parent / "ride" / "tei_all"


# ── Fixture builders ─────────────────────────────────────────────────


def _para(text: str, xml_id: str = "", n: str = "") -> Paragraph:
    return Paragraph(
        inlines=(Text(text=text),),
        xml_id=xml_id or None,
        n=n or None,
    )


def _section(xml_id: str, heading: str, blocks=(), type=None, level=1) -> Section:
    return Section(
        xml_id=xml_id,
        type=type,
        heading=(Text(text=heading),) if heading else None,
        level=level,
        blocks=tuple(blocks),
        subsections=(),
    )


def _minimal_review(**overrides) -> Review:
    body = (
        _section(
            "abstract", "Abstract", blocks=(_para("This is the abstract."),), type="abstract"
        ),
        _section(
            "intro",
            "Introduction",
            blocks=(_para("First body paragraph.", xml_id="p1", n="1"),),
        ),
    )
    base = dict(
        id="ride.13.7",
        issue="13",
        title="A Sample Review",
        publication_date="2026-04-29",
        language="en",
        licence="https://creativecommons.org/licenses/by/4.0/",
        keywords=("digital editions", "test"),
        authors=(
            Author(
                person=Person(full_name="Jane Reviewer", forename="Jane", surname="Reviewer"),
                email="jane@example.org",
            ),
        ),
        body=body,
        figures=(),
        notes=(),
    )
    base.update(overrides)
    return Review(**base)


# ── Filter unit tests ────────────────────────────────────────────────


def test_slugify_basic():
    assert _slugify("Digital Editions") == "digital-editions"
    assert _slugify("  Foo / Bar! ") == "foo-bar"
    assert _slugify("") == ""


def test_obfuscate_mail():
    out = _obfuscate_mail("a@b.c")
    assert "@" not in out
    assert "." not in out


def test_inlines_to_text_recurses_into_emphasis():
    seq = (Text(text="hello "), Emphasis(children=(Text(text="bold"),)), Text(text=" world"))
    assert _inlines_to_text(seq) == "hello bold world"


# ── split_abstract ────────────────────────────────────────────────────


def test_split_abstract_pulls_first_abstract_section():
    review = _minimal_review()
    abstract, rest = split_abstract(review)
    assert abstract is not None
    assert abstract.type == "abstract"
    assert all(s.type != "abstract" for s in rest)
    assert len(rest) == 1


# ── render_review — synthetic fixture ────────────────────────────────


def test_render_review_emits_skeleton():
    html = render_review(_minimal_review())
    # Page chrome
    assert "<!doctype html>" in html
    assert 'lang="en"' in html
    assert "ride-skip" in html
    assert "ride-search-slot" in html
    # Review-specific structure
    assert "A Sample Review" in html
    assert "ride-review__title" in html
    assert "ride-review__abstract" in html
    # Numbered paragraph anchor
    assert 'id="p1"' in html
    assert 'class="ride-paragraph__anchor"' in html
    # Sidebar
    assert "ride-toc" in html
    assert "ride-cite__btn" in html
    # Author email is obfuscated
    assert "jane@example.org" not in html
    assert "[at]" in html


def test_render_review_lists_keywords_with_links():
    html = render_review(_minimal_review())
    assert "/tags/digital-editions/" in html
    assert "/tags/test/" in html


def test_render_review_blocks_macro_handles_all_kinds():
    """Smoke: list, table, figure, citation all render without raising."""
    body = (
        _section(
            "s1",
            "Mixed content",
            blocks=(
                _para("Plain.", xml_id="p1"),
                List(
                    items=(
                        ListItem(inlines=(Text(text="alpha"),)),
                        ListItem(inlines=(Text(text="beta"),)),
                    ),
                    kind="bulleted",
                ),
                Figure(
                    kind="graphic",
                    head=(Text(text="Caption"),),
                    graphic_url="figures/x.png",
                    xml_id="fig1",
                ),
                Citation(
                    quote_inlines=(Text(text="Ipsum dolor"),),
                    bibl=(Text(text="Cicero"),),
                ),
            ),
        ),
    )
    html = render_review(_minimal_review(body=body, figures=()))
    assert "ride-list" in html
    assert "ride-figure" in html
    assert "ride-citation" in html


def test_render_review_apparate_omits_panels_when_empty():
    html = render_review(_minimal_review())
    # Both figures and notes are empty in the minimal fixture; the apparate aside
    # should collapse rather than render empty panels.
    assert "ride-apparate" not in html


def test_render_review_apparate_renders_when_notes_present():
    notes = (
        Note(
            children=(Text(text="A footnote body."),),
            xml_id="ftn1",
            n="1",
        ),
    )
    html = render_review(_minimal_review(notes=notes))
    assert "ride-apparate" in html
    assert "ride-apparate__panel--notes" in html
    assert 'id="ftn1"' in html


def test_render_review_apparate_renders_bibliography():
    bib = (
        BibEntry(
            inlines=(Text(text="Smith, "), Emphasis(children=(Text(text="Title"),)), Text(text=" 2024.")),
            xml_id="bib1",
            ref_target="https://doi.org/10.1234/x",
        ),
        BibEntry(
            inlines=(Text(text="Doe, Other Title 2025."),),
            xml_id="bib2",
            ref_target=None,
        ),
    )
    html = render_review(_minimal_review(bibliography=bib))
    assert "ride-apparate__panel--refs" in html
    assert 'id="bib1"' in html
    assert 'href="https://doi.org/10.1234/x"' in html
    # Entry without ref_target renders without surrounding anchor
    assert 'id="bib2"' in html


def test_render_review_factsheet_summary():
    q = Questionnaire(
        criteria_url="https://www.i-d-e.de/publikationen/weitereschriften/criteria-text-collections/",
        answers=(
            QuestionnaireAnswer("se002", "1"),
            QuestionnaireAnswer("se003", "0"),
            QuestionnaireAnswer("se004", "1"),
            QuestionnaireAnswer("se005", "1"),
        ),
    )
    html = render_review(_minimal_review(questionnaires=(q,)))
    assert "ride-sidebar__box--factsheet" in html
    assert "3 / 4" in html  # three "1"s out of four valid answers
    assert "https://www.i-d-e.de/publikationen/weitereschriften/criteria-text-collections/" in html


def test_render_review_factsheet_excludes_anomaly_value_3():
    q = Questionnaire(
        criteria_url="https://example.org/crit",
        answers=(
            QuestionnaireAnswer("a", "1"),
            QuestionnaireAnswer("b", "0"),
            QuestionnaireAnswer("c", "3"),  # anomaly — excluded
        ),
    )
    html = render_review(_minimal_review(questionnaires=(q,)))
    assert "1 / 2" in html  # value=3 excluded from both numerator and denominator
    assert "⚠ 1" in html  # anomaly counter visible


def test_render_review_with_ref_renders_anchor():
    body = (
        _section(
            "s",
            "S",
            blocks=(
                Paragraph(
                    inlines=(
                        Text(text="See "),
                        Reference(
                            children=(Text(text="Section 2"),),
                            target="#sec2",
                            type="crossref",
                        ),
                        Text(text="."),
                    )
                ),
            ),
        ),
    )
    html = render_review(_minimal_review(body=body))
    assert 'href="#sec2"' in html
    assert 'data-ref-type="crossref"' in html


# ── env.get_template never raises for templates we know about ────────


@pytest.mark.parametrize(
    "name",
    [
        "base.html",
        "review.html",
        "partials/render.html",
        "partials/section.html",
        "partials/apparate.html",
    ],
)
def test_known_templates_load(name):
    env = make_env()
    env.get_template(name)


# ── Real-corpus smoke ────────────────────────────────────────────────


@pytest.mark.skipif(not CORPUS_DIR.exists(), reason="../ride/tei_all not present")
def test_smoke_render_first_corpus_review_without_raising():
    from src.parser.review import parse_review

    sample = sorted(CORPUS_DIR.glob("*.xml"))[0]
    review = parse_review(sample)
    html = render_review(review)
    assert "<!doctype html>" in html
    assert review.title in html
