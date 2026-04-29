"""Tests for ``src.render.jsonld`` — Phase 12 R15 / A5.

Two layers, mirroring the Phase 8 render-test pattern:

1. Synthetic Review fixtures — ``to_jsonld`` is a pure formatter
   (Review → dict). Under the test-data hard rule from CLAUDE.md, formatter
   tests may use synthetic inputs because the function signature is the
   only data form richer than that. Each test pins one schema.org property.
2. Real-corpus integration — parse one TEI file end-to-end and assert that
   the produced JSON-LD survives the embedding round-trip (valid JSON,
   load-able by stdlib) with the load-bearing fields populated. Skips
   cleanly when ``../ride/`` is absent.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.model.block import Paragraph
from src.model.inline import Emphasis, Reference, Text
from src.model.review import (
    Affiliation,
    Author,
    Editor,
    Person,
    RelatedItem,
    Review,
)
from src.model.section import Section
from src.render.jsonld import to_jsonld, to_jsonld_string

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO_ROOT.parent / "ride" / "tei_all"


# ── Fixture helpers ──────────────────────────────────────────────────


def _minimal_review(**overrides) -> Review:
    base = dict(
        id="ride.13.7",
        issue="13",
        title="A Test Review",
        publication_date="2024-06-01",
        language="en",
        licence="http://creativecommons.org/licenses/by/4.0/",
    )
    base.update(overrides)
    return Review(**base)


def _abstract_section(text: str) -> Section:
    return Section(
        xml_id="abs",
        type="abstract",
        heading=None,
        level=1,
        blocks=(Paragraph(inlines=(Text(text=text),)),),
        subsections=(),
    )


# ── Pure-formatter tests ─────────────────────────────────────────────


def test_minimal_review_has_required_schema_keys():
    """Every emitted ScholarlyArticle carries @context, @type, headline, name."""
    data = to_jsonld(_minimal_review())
    assert data["@context"] == "https://schema.org"
    assert data["@type"] == "ScholarlyArticle"
    assert data["headline"] == "A Test Review"
    assert data["name"] == "A Test Review"


def test_url_and_id_present_when_base_url_set():
    """Without a DOI, the page URL serves as both @id and url."""
    data = to_jsonld(_minimal_review(), base_url="https://ride.i-d-e.de")
    assert data["url"] == "https://ride.i-d-e.de/issues/13/ride.13.7/"
    assert data["@id"] == data["url"]


def test_url_omitted_when_base_url_empty():
    data = to_jsonld(_minimal_review(), base_url="")
    assert "url" not in data
    assert "@id" not in data


def test_doi_becomes_canonical_id_and_identifier_property_value():
    """When a DOI is set, @id points at the DOI URL (persistent identifier)
    while url stays on the deployed page (mutable address). The DOI also
    surfaces as a schema.org PropertyValue so DOI-aware harvesters lift it."""
    data = to_jsonld(
        _minimal_review(doi="10.18716/ride.a.5.4"),
        base_url="https://ride.i-d-e.de",
    )
    assert data["@id"] == "https://doi.org/10.18716/ride.a.5.4"
    assert data["url"] == "https://ride.i-d-e.de/issues/13/ride.13.7/"
    assert data["identifier"] == {
        "@type": "PropertyValue",
        "propertyID": "DOI",
        "value": "10.18716/ride.a.5.4",
        "url": "https://doi.org/10.18716/ride.a.5.4",
    }


def test_doi_id_works_even_without_base_url():
    """DOIs are absolute identifiers — they should populate @id even when
    no deploy URL is configured (e.g. local builds for inspection)."""
    data = to_jsonld(_minimal_review(doi="10.18716/ride.a.5.4"), base_url="")
    assert data["@id"] == "https://doi.org/10.18716/ride.a.5.4"
    assert "url" not in data
    assert data["identifier"]["value"] == "10.18716/ride.a.5.4"


def test_no_identifier_field_when_doi_missing():
    data = to_jsonld(_minimal_review(), base_url="https://ride.i-d-e.de")
    assert "identifier" not in data


def test_publication_date_language_licence_pass_through():
    data = to_jsonld(_minimal_review())
    assert data["datePublished"] == "2024-06-01"
    assert data["inLanguage"] == "en"
    assert data["license"] == "http://creativecommons.org/licenses/by/4.0/"


def test_authors_emit_person_with_orcid_sameAs():
    """Email is intentionally suppressed — see _author_to_jsonld docstring."""
    review = _minimal_review(
        authors=(
            Author(
                person=Person(
                    full_name="Jane Doe",
                    forename="Jane",
                    surname="Doe",
                    orcid="https://orcid.org/0000-0001-2345-6789",
                ),
                affiliation=Affiliation(org_name="University X"),
                email="jane@example.org",
            ),
        ),
    )
    data = to_jsonld(review)
    [author] = data["author"]
    assert author["@type"] == "Person"
    assert author["name"] == "Jane Doe"
    assert author["givenName"] == "Jane"
    assert author["familyName"] == "Doe"
    assert author["@id"] == "https://orcid.org/0000-0001-2345-6789"
    assert author["sameAs"] == "https://orcid.org/0000-0001-2345-6789"
    assert author["affiliation"] == {"@type": "Organization", "name": "University X"}
    assert "email" not in author


def test_editors_with_role_emit_jobTitle():
    review = _minimal_review(
        editors=(
            Editor(person=Person(full_name="E. Editor"), role="managing"),
        ),
    )
    [editor] = to_jsonld(review)["editor"]
    assert editor["name"] == "E. Editor"
    assert editor["jobTitle"] == "managing"


def test_keywords_become_string_array():
    review = _minimal_review(keywords=("digital editions", "TEI", "review"))
    data = to_jsonld(review)
    assert data["keywords"] == ["digital editions", "TEI", "review"]


def test_issue_emits_publication_issue_isPartOf():
    data = to_jsonld(_minimal_review(issue="13"))
    assert data["isPartOf"] == {
        "@type": "PublicationIssue",
        "issueNumber": "13",
        "name": "RIDE Issue 13",
    }


def test_abstract_pulled_from_front_first_then_body():
    """split_abstract checks front then body — JSON-LD must mirror that order."""
    review_front = _minimal_review(front=(_abstract_section("Front abstract."),))
    review_body = _minimal_review(body=(_abstract_section("Body abstract."),))
    review_both = _minimal_review(
        front=(_abstract_section("Front abstract."),),
        body=(_abstract_section("Body abstract."),),
    )
    assert to_jsonld(review_front)["abstract"] == "Front abstract."
    assert to_jsonld(review_body)["abstract"] == "Body abstract."
    assert to_jsonld(review_both)["abstract"] == "Front abstract."


def test_inline_emphasis_in_abstract_collapses_to_plain_text():
    """JSON-LD literals must not carry HTML — inline wrappers flatten."""
    section = Section(
        xml_id="abs",
        type="abstract",
        heading=None,
        level=1,
        blocks=(
            Paragraph(
                inlines=(
                    Text(text="A study of "),
                    Emphasis(children=(Text(text="Beowulf"),)),
                    Text(text="."),
                ),
            ),
        ),
        subsections=(),
    )
    review = _minimal_review(front=(section,))
    assert to_jsonld(review)["abstract"] == "A study of Beowulf."


def test_reviewed_resource_lands_in_about_with_url():
    review = _minimal_review(
        related_items=(
            RelatedItem(
                type="reviewed_resource",
                bibl_text="Some Digital Edition",
                bibl_targets=("https://example.org/edition",),
            ),
            RelatedItem(
                type="reviewing_criteria",
                bibl_text="RIDE Criteria",
                bibl_targets=("https://example.org/criteria",),
            ),
        ),
    )
    data = to_jsonld(review)
    assert data["about"] == [
        {
            "@type": "CreativeWork",
            "name": "Some Digital Edition",
            "url": "https://example.org/edition",
        }
    ]


def test_optional_fields_omitted_when_empty():
    review = _minimal_review()
    data = to_jsonld(review)
    for absent in ("author", "editor", "keywords", "abstract", "about"):
        assert absent not in data


def test_to_jsonld_string_returns_loadable_json():
    s = to_jsonld_string(_minimal_review())
    assert json.loads(s)["@type"] == "ScholarlyArticle"


# ── Real-corpus integration ──────────────────────────────────────────


@pytest.mark.skipif(not CORPUS_DIR.exists(), reason="../ride/ corpus not checked out")
def test_real_corpus_review_round_trips_through_jsonld():
    """Parse 1641-tei.xml end-to-end and verify the load-bearing keys appear.

    1641 was chosen as the JSON-LD smoke fixture because it is the
    rich-metadata reference review (author with ORCID + affiliation,
    editors with roles, keywords, reviewed_resource RelatedItem) — a
    weaker fixture would let regressions hide.
    """
    from src.parser.review import parse_review

    review = parse_review(CORPUS_DIR / "1641-tei.xml")
    data = to_jsonld(review, base_url="https://ride.i-d-e.de")

    assert data["@type"] == "ScholarlyArticle"
    assert data["headline"] == review.title
    # Welle 1.B: DOI is the canonical @id, page URL stays in url.
    assert data["@id"] == "https://doi.org/10.18716/ride.a.5.4"
    assert data["url"] == f"https://ride.i-d-e.de/issues/{review.issue}/{review.id}/"
    assert data["identifier"]["value"] == "10.18716/ride.a.5.4"
    assert data["datePublished"] == "2017-02"
    assert data["inLanguage"] == "en"
    assert data["isPartOf"]["issueNumber"] == "5"
    assert data["author"], "1641 has at least one author"
    assert data["editor"], "1641 has multiple editors"
    assert any("@id" in a for a in data["author"]), "first author has ORCID"
    assert data["keywords"], "1641 carries keywords"
    assert data["about"], "reviewed_resource RelatedItem must surface in about"

    # Round-trip the serialised string — embedded JSON-LD must always be
    # valid JSON or browsers/crawlers reject the whole script tag.
    parsed = json.loads(to_jsonld_string(review, base_url="https://ride.i-d-e.de"))
    assert parsed["@id"] == data["@id"]
