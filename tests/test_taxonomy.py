"""Tests for scripts/taxonomy.py."""
from __future__ import annotations

from pathlib import Path

import pytest

import taxonomy

# Two files using the same criteria base -> structurally identical taxonomies,
# different per-review answers.
FIXTURE_A = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="ride.1.1">
  <teiHeader>
    <fileDesc>
      <titleStmt><title>A</title></titleStmt>
      <publicationStmt><p>x</p></publicationStmt>
      <sourceDesc><p>x</p></sourceDesc>
    </fileDesc>
    <encodingDesc>
      <classDecl>
        <taxonomy xml:base="https://example.org/criteria-v1">
          <category xml:id="general">
            <catDesc><gloss>General</gloss><num value="1"/></catDesc>
            <category xml:id="general.scope">
              <catDesc><gloss>Scope</gloss><num value="1"/></catDesc>
            </category>
            <category xml:id="general.audience">
              <catDesc><gloss>Audience</gloss><num value="0"/></catDesc>
            </category>
          </category>
          <category xml:id="content">
            <catDesc><gloss>Content</gloss><num value="0"/></catDesc>
          </category>
        </taxonomy>
      </classDecl>
    </encodingDesc>
  </teiHeader>
  <text><body><div><p>x</p></div></body></text>
</TEI>
"""

FIXTURE_B = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="ride.1.2">
  <teiHeader>
    <fileDesc>
      <titleStmt><title>B</title></titleStmt>
      <publicationStmt><p>x</p></publicationStmt>
      <sourceDesc><p>x</p></sourceDesc>
    </fileDesc>
    <encodingDesc>
      <classDecl>
        <taxonomy xml:base="https://example.org/criteria-v1">
          <category xml:id="general">
            <catDesc><gloss>General</gloss><num value="0"/></catDesc>
            <category xml:id="general.scope">
              <catDesc><gloss>Scope</gloss><num value="1"/></catDesc>
            </category>
            <category xml:id="general.audience">
              <catDesc><gloss>Audience</gloss><num value="1"/></catDesc>
            </category>
          </category>
          <category xml:id="content">
            <catDesc><gloss>Content</gloss><num value="1"/></catDesc>
          </category>
        </taxonomy>
      </classDecl>
    </encodingDesc>
  </teiHeader>
  <text><body><div><p>x</p></div></body></text>
</TEI>
"""

# Third file uses a different criteria base AND has a structurally deviating
# tree compared to its own siblings (only one of them, but the criteria_set
# only has one instance so no deviation is reported).
FIXTURE_C = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="ride.2.1">
  <teiHeader>
    <fileDesc>
      <titleStmt><title>C</title></titleStmt>
      <publicationStmt><p>x</p></publicationStmt>
      <sourceDesc><p>x</p></sourceDesc>
    </fileDesc>
    <encodingDesc>
      <classDecl>
        <taxonomy xml:base="https://example.org/criteria-tools">
          <category xml:id="usability">
            <catDesc><gloss>Usability</gloss><num value="1"/></catDesc>
          </category>
        </taxonomy>
      </classDecl>
    </encodingDesc>
  </teiHeader>
  <text><body><div><p>x</p></div></body></text>
</TEI>
"""


@pytest.fixture
def fixture_corpus(tmp_path: Path) -> tuple[Path, Path]:
    tei = tmp_path / "tei"
    out = tmp_path / "out"
    tei.mkdir()
    (tei / "a-tei.xml").write_text(FIXTURE_A, encoding="utf-8")
    (tei / "b-tei.xml").write_text(FIXTURE_B, encoding="utf-8")
    (tei / "c-tei.xml").write_text(FIXTURE_C, encoding="utf-8")
    return tei, out


def test_writes_taxonomy_json(fixture_corpus: tuple[Path, Path]) -> None:
    tei, out = fixture_corpus
    taxonomy.run(tei, out)
    assert (out / "taxonomy.json").is_file()


def test_two_distinct_criteria_sets(fixture_corpus: tuple[Path, Path]) -> None:
    tei, out = fixture_corpus
    payload = taxonomy.run(tei, out)
    bases = set(payload["criteria_sets"].keys())
    assert bases == {"https://example.org/criteria-v1", "https://example.org/criteria-tools"}


def test_canonical_tree_structure(fixture_corpus: tuple[Path, Path]) -> None:
    tei, out = fixture_corpus
    payload = taxonomy.run(tei, out)
    v1 = payload["criteria_sets"]["https://example.org/criteria-v1"]
    assert v1["category_count"] == 4    # general, general.scope, general.audience, content
    assert v1["max_depth"] == 2         # general -> general.scope
    assert v1["review_count"] == 2      # used by A and B
    # First-level category xml_ids
    top_ids = [c["xml_id"] for c in v1["tree"]]
    assert top_ids == ["general", "content"]
    # general's two children
    general_kids = v1["tree"][0]["children"]
    assert [c["xml_id"] for c in general_kids] == ["general.scope", "general.audience"]
    # gloss preserved
    assert v1["tree"][0]["gloss"] == "General"


def test_no_structural_deviation_when_trees_match(fixture_corpus: tuple[Path, Path]) -> None:
    tei, out = fixture_corpus
    payload = taxonomy.run(tei, out)
    v1 = payload["criteria_sets"]["https://example.org/criteria-v1"]
    # A and B have identical structure (same xml_ids in same shape)
    assert v1["structurally_deviating_reviews"] == []


def test_per_review_answers_captured(fixture_corpus: tuple[Path, Path]) -> None:
    tei, out = fixture_corpus
    payload = taxonomy.run(tei, out)
    by_file = {r["file"]: r for r in payload["review_to_criteria"]}
    a = by_file["a-tei.xml"]["taxonomies"][0]["answers"]
    b = by_file["b-tei.xml"]["taxonomies"][0]["answers"]
    # Same categories, different yes/no values
    assert a == {"general": 1, "general.scope": 1, "general.audience": 0, "content": 0}
    assert b == {"general": 0, "general.scope": 1, "general.audience": 1, "content": 1}


def test_review_with_only_other_criteria_set(fixture_corpus: tuple[Path, Path]) -> None:
    tei, out = fixture_corpus
    payload = taxonomy.run(tei, out)
    by_file = {r["file"]: r for r in payload["review_to_criteria"]}
    c_entry = by_file["c-tei.xml"]
    assert c_entry["taxonomies"][0]["criteria"] == "https://example.org/criteria-tools"
    assert c_entry["taxonomies"][0]["answers"] == {"usability": 1}
