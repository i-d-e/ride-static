"""Tests for src/parser — header metadata extraction.

Synthetic fixture exercises every metadata field the Stage 2.A parser
covers: id, issue, title, date, language, licence, keywords, authors
(with affiliation, ORCID, email), editors (with role + ORCID), and
related items.

A separate smoke test parses a real RIDE review when the sibling
``../ride/`` directory is present.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.model.review import Affiliation, Author, Editor, Person, RelatedItem, Review
from src.parser.review import parse_review

REPO_ROOT = Path(__file__).resolve().parent.parent
RIDE_TEI_DIR = REPO_ROOT.parent / "ride" / "tei_all"


FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="ride.99.42">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title>A review of a digital edition of something interesting</title>
        <author ref="https://orcid.org/0000-0000-0000-0001">
          <name><forename>Alice</forename><surname>Smith</surname></name>
          <affiliation>
            <orgName>Test University</orgName>
            <placeName>Berlin</placeName>
          </affiliation>
          <email>alice@example.org</email>
        </author>
        <author ref="https://orcid.org/0000-0000-0000-0002">
          <name><forename>Bob</forename><surname>Jones</surname></name>
          <affiliation>
            <orgName>Other Institute</orgName>
            <placeName>Vienna</placeName>
          </affiliation>
          <email>bob@example.org</email>
        </author>
      </titleStmt>
      <publicationStmt>
        <publisher>IDE</publisher>
        <date when="2024-06-15">June 2024</date>
        <idno type="DOI">10.example/x</idno>
        <idno type="URI">https://ride.example/99/42</idno>
        <idno type="archive">whatever</idno>
        <availability>
          <licence target="https://creativecommons.org/licenses/by/4.0/">CC-BY-4.0</licence>
        </availability>
      </publicationStmt>
      <seriesStmt>
        <title>RIDE</title>
        <editor ref="https://orcid.org/0000-0000-0000-0099">Eve Editor</editor>
        <editor ref="https://orcid.org/0000-0000-0000-0098" role="chief">Chief Editor</editor>
        <biblScope n="99"/>
        <idno type="ISSN">2364-3196</idno>
      </seriesStmt>
      <notesStmt>
        <relatedItem type="reviewed_resource" xml:id="rev1">
          <bibl>The thing being reviewed. <ref target="https://example.org/thing">link</ref></bibl>
        </relatedItem>
        <relatedItem type="reviewing_criteria">
          <bibl>The criteria.</bibl>
        </relatedItem>
      </notesStmt>
      <sourceDesc><p>Born digital.</p></sourceDesc>
    </fileDesc>
    <profileDesc>
      <langUsage><language ident="en">English</language></langUsage>
      <textClass>
        <keywords xml:lang="en">
          <term>digital edition</term>
          <term>review</term>
          <term>methodology</term>
        </keywords>
      </textClass>
    </profileDesc>
  </teiHeader>
  <text><body><div xml:id="div1"><p>placeholder</p></div></body></text>
</TEI>
"""


@pytest.fixture
def fixture_path(tmp_path: Path) -> Path:
    p = tmp_path / "sample-tei.xml"
    p.write_text(FIXTURE, encoding="utf-8")
    return p


def test_top_level_fields(fixture_path: Path) -> None:
    r = parse_review(fixture_path)
    assert isinstance(r, Review)
    assert r.source_file == "sample-tei.xml"
    assert r.id == "ride.99.42"
    assert r.issue == "99"
    assert r.title.startswith("A review of a digital edition")
    assert r.publication_date == "2024-06-15"
    assert r.language == "en"
    assert r.licence == "https://creativecommons.org/licenses/by/4.0/"


def test_body_fields_populated_via_section_parser(fixture_path: Path) -> None:
    """Phase 5 wires parse_sections into parse_review; the synthetic fixture
    exercises the full path. The fixture has at least one body section but
    no <front> or <back>, so those stay empty."""
    r = parse_review(fixture_path)
    assert r.front == ()
    assert len(r.body) >= 1
    assert r.back == ()


def test_keywords(fixture_path: Path) -> None:
    r = parse_review(fixture_path)
    assert r.keywords == ("digital edition", "review", "methodology")


def test_authors_with_affiliation_and_orcid(fixture_path: Path) -> None:
    r = parse_review(fixture_path)
    assert len(r.authors) == 2
    a1 = r.authors[0]
    assert isinstance(a1, Author)
    assert a1.person.full_name == "Alice Smith"
    assert a1.person.forename == "Alice"
    assert a1.person.surname == "Smith"
    assert a1.person.orcid == "https://orcid.org/0000-0000-0000-0001"
    assert a1.affiliation == Affiliation(org_name="Test University", place_name="Berlin")
    assert a1.email == "alice@example.org"
    # second author
    assert r.authors[1].person.surname == "Jones"
    assert r.authors[1].affiliation.place_name == "Vienna"


def test_editors_with_role(fixture_path: Path) -> None:
    r = parse_review(fixture_path)
    assert len(r.editors) == 2
    assert r.editors[0].person.full_name == "Eve Editor"
    assert r.editors[0].role is None  # no @role on first editor
    assert r.editors[0].person.orcid == "https://orcid.org/0000-0000-0000-0099"
    assert r.editors[1].role == "chief"


def test_related_items(fixture_path: Path) -> None:
    r = parse_review(fixture_path)
    assert len(r.related_items) == 2
    rev = r.related_items[0]
    assert isinstance(rev, RelatedItem)
    assert rev.type == "reviewed_resource"
    assert rev.xml_id == "rev1"
    assert "thing being reviewed" in rev.bibl_text
    assert rev.bibl_targets == ("https://example.org/thing",)
    assert r.related_items[1].type == "reviewing_criteria"
    assert r.related_items[1].xml_id is None


def test_review_is_immutable(fixture_path: Path) -> None:
    r = parse_review(fixture_path)
    with pytest.raises(Exception):
        r.id = "different"  # type: ignore[misc]


@pytest.mark.skipif(not RIDE_TEI_DIR.is_dir(), reason="sibling ride/ corpus not available")
def test_smoke_real_corpus_smallest_file() -> None:
    """Parse the smallest review in the real corpus end-to-end without errors."""
    smallest = sorted(RIDE_TEI_DIR.glob("*.xml"), key=lambda p: p.stat().st_size)[0]
    r = parse_review(smallest)
    assert r.id.startswith("ride.")
    assert r.issue.isdigit()
    assert r.title
    assert r.language in {"en", "de", "fr", "it"}
    assert r.licence.startswith("http")
    assert r.authors  # every review has at least one author per Schematron
    assert r.editors  # every review has editors
    assert any(ri.type == "reviewed_resource" for ri in r.related_items)


# Minimal review with optional fields stripped — covers what the parser must
# tolerate when reality differs from the maximal fixture used above.
MINIMAL_FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="ride.0.0">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title>Bare-bones review</title>
        <author>
          <name>Solo Author</name>
        </author>
      </titleStmt>
      <publicationStmt>
        <date when="2020-01-01">January 2020</date>
        <availability><licence target="https://creativecommons.org/licenses/by/4.0/">CC-BY-4.0</licence></availability>
      </publicationStmt>
      <seriesStmt>
        <editor>Lone Editor</editor>
        <biblScope n="1"/>
      </seriesStmt>
      <sourceDesc><p>x</p></sourceDesc>
    </fileDesc>
    <profileDesc>
      <langUsage><language ident="en">English</language></langUsage>
    </profileDesc>
  </teiHeader>
  <text><body><div><p>x</p></div></body></text>
</TEI>
"""


@pytest.fixture
def minimal_path(tmp_path: Path) -> Path:
    p = tmp_path / "minimal-tei.xml"
    p.write_text(MINIMAL_FIXTURE, encoding="utf-8")
    return p


def test_author_without_affiliation_or_email(minimal_path: Path) -> None:
    """Authors with only a <name>, no <affiliation>/<email>/@ref, must produce
    a valid Author with optional fields set to None."""
    r = parse_review(minimal_path)
    assert len(r.authors) == 1
    a = r.authors[0]
    assert a.person.full_name == "Solo Author"
    assert a.person.orcid is None
    assert a.affiliation is None
    assert a.email is None


def test_editor_with_plain_text_no_name_child(minimal_path: Path) -> None:
    """Editors written as <editor>Plain text</editor> (no <name> child, no
    @ref, no @role) must still produce a usable Editor."""
    r = parse_review(minimal_path)
    assert len(r.editors) == 1
    e = r.editors[0]
    assert e.person.full_name == "Lone Editor"
    assert e.person.forename is None and e.person.surname is None
    assert e.person.orcid is None
    assert e.role is None


def test_review_without_keywords(minimal_path: Path) -> None:
    """A review whose <profileDesc> has no <keywords> must yield an empty tuple."""
    r = parse_review(minimal_path)
    assert r.keywords == ()
