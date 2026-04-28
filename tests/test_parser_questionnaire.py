"""Tests for the per-review questionnaire parser.

Synthetic fixtures cover the standard pattern (taxonomy with @xml:base,
nested categories with num markers in catDesc), the multi-taxonomy
case, the missing-taxonomy case, and the ``value="3"`` anomaly.
A real-corpus smoke verifies the magnitude of answer aggregates against
``inventory/taxonomy.json`` (≈20053 num occurrences corpus-wide).
"""
from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree

from src.model.questionnaire import Questionnaire, QuestionnaireAnswer
from src.parser.questionnaire import parse_questionnaires


TEI = "http://www.tei-c.org/ns/1.0"


def _root(xml: str) -> etree._Element:
    return etree.fromstring(xml.strip().encode("utf-8"))


# -- Standard cases -------------------------------------------------------


def test_parse_questionnaire_collects_num_answers():
    root = _root("""
        <TEI xmlns="http://www.tei-c.org/ns/1.0"
             xmlns:xml="http://www.w3.org/XML/1998/namespace">
          <teiHeader>
            <encodingDesc>
              <classDecl>
                <taxonomy xml:base="http://example.org/criteria-v1">
                  <category xml:id="se001">
                    <catDesc>Bibliographic description</catDesc>
                    <category xml:id="se002">
                      <catDesc>Yes <num type="boolean" value="1"/></catDesc>
                    </category>
                    <category xml:id="se003">
                      <catDesc>No <num type="boolean" value="0"/></catDesc>
                    </category>
                  </category>
                </taxonomy>
              </classDecl>
            </encodingDesc>
          </teiHeader>
          <text><body><p>x</p></body></text>
        </TEI>
    """)
    qs = parse_questionnaires(root)
    assert len(qs) == 1
    q = qs[0]
    assert q.criteria_url == "http://example.org/criteria-v1"
    assert len(q.answers) == 2
    assert q.answers[0] == QuestionnaireAnswer(category_xml_id="se002", value="1")
    assert q.answers[1] == QuestionnaireAnswer(category_xml_id="se003", value="0")


def test_parse_questionnaire_skips_categories_without_num():
    """Top-level (section) and intermediate (criterion) categories
    typically have no <num>; only leaves carry the answer."""
    root = _root("""
        <TEI xmlns="http://www.tei-c.org/ns/1.0"
             xmlns:xml="http://www.w3.org/XML/1998/namespace">
          <teiHeader>
            <encodingDesc>
              <classDecl>
                <taxonomy xml:base="http://example.org/c">
                  <category>
                    <catDesc>Section without xml:id</catDesc>
                    <category xml:id="q001">
                      <catDesc>Question (no num)</catDesc>
                      <category xml:id="a001">
                        <catDesc>Yes <num type="boolean" value="1"/></catDesc>
                      </category>
                    </category>
                  </category>
                </taxonomy>
              </classDecl>
            </encodingDesc>
          </teiHeader>
          <text><body><p>x</p></body></text>
        </TEI>
    """)
    q = parse_questionnaires(root)[0]
    # Only the leaf with num is collected; section without xml:id is skipped,
    # the q001 question has no num itself.
    assert q.answers == (QuestionnaireAnswer(category_xml_id="a001", value="1"),)


def test_parse_questionnaire_anomaly_value_3_preserved_as_string():
    """One corpus review uses value="3" — kept verbatim per anomaly policy."""
    root = _root("""
        <TEI xmlns="http://www.tei-c.org/ns/1.0"
             xmlns:xml="http://www.w3.org/XML/1998/namespace">
          <teiHeader>
            <encodingDesc>
              <classDecl>
                <taxonomy xml:base="http://example.org/c">
                  <category xml:id="weird">
                    <catDesc>Weird <num value="3"/></catDesc>
                  </category>
                </taxonomy>
              </classDecl>
            </encodingDesc>
          </teiHeader>
          <text><body><p>x</p></body></text>
        </TEI>
    """)
    q = parse_questionnaires(root)[0]
    assert q.answers[0].value == "3"


def test_parse_questionnaire_multiple_taxonomies():
    """Three corpus reviews carry two <taxonomy> elements — one per
    criteria set they answer."""
    root = _root("""
        <TEI xmlns="http://www.tei-c.org/ns/1.0"
             xmlns:xml="http://www.w3.org/XML/1998/namespace">
          <teiHeader>
            <encodingDesc>
              <classDecl>
                <taxonomy xml:base="http://example.org/a">
                  <category xml:id="a1"><catDesc>X<num value="1"/></catDesc></category>
                </taxonomy>
                <taxonomy xml:base="http://example.org/b">
                  <category xml:id="b1"><catDesc>Y<num value="0"/></catDesc></category>
                </taxonomy>
              </classDecl>
            </encodingDesc>
          </teiHeader>
          <text><body><p>x</p></body></text>
        </TEI>
    """)
    qs = parse_questionnaires(root)
    assert len(qs) == 2
    assert qs[0].criteria_url == "http://example.org/a"
    assert qs[1].criteria_url == "http://example.org/b"


def test_parse_questionnaire_no_taxonomy_yields_empty():
    root = _root("""
        <TEI xmlns="http://www.tei-c.org/ns/1.0">
          <teiHeader>
            <encodingDesc><classDecl/></encodingDesc>
          </teiHeader>
          <text><body><p>x</p></body></text>
        </TEI>
    """)
    assert parse_questionnaires(root) == ()


def test_parse_questionnaire_root_none_yields_empty():
    assert parse_questionnaires(None) == ()


def test_parse_questionnaire_taxonomy_without_xml_base():
    """Defensive: a taxonomy without @xml:base still parses; criteria_url
    becomes the empty string, signalling the missing reference."""
    root = _root("""
        <TEI xmlns="http://www.tei-c.org/ns/1.0"
             xmlns:xml="http://www.w3.org/XML/1998/namespace">
          <teiHeader>
            <encodingDesc>
              <classDecl>
                <taxonomy>
                  <category xml:id="x"><catDesc>Y<num value="1"/></catDesc></category>
                </taxonomy>
              </classDecl>
            </encodingDesc>
          </teiHeader>
          <text><body><p>x</p></body></text>
        </TEI>
    """)
    q = parse_questionnaires(root)[0]
    assert q.criteria_url == ""
    assert len(q.answers) == 1


# -- Real-corpus smoke ----------------------------------------------------


_RIDE = Path(__file__).resolve().parent.parent.parent / "ride" / "tei_all"


@pytest.mark.skipif(not _RIDE.exists(), reason="../ride/ corpus not present")
def test_smoke_real_corpus_questionnaire_count() -> None:
    """The corpus inventory reports ~20053 ``<num>`` elements across 110
    ``<taxonomy>`` blocks. The parser should reach the same magnitude."""
    files = sorted(_RIDE.glob("*-tei.xml"))
    total_taxonomies = 0
    total_answers = 0
    anomaly_value_3_seen = False
    criteria_urls: set[str] = set()
    for f in files:
        tree = etree.parse(str(f))
        qs = parse_questionnaires(tree.getroot())
        total_taxonomies += len(qs)
        for q in qs:
            criteria_urls.add(q.criteria_url)
            total_answers += len(q.answers)
            for a in q.answers:
                if a.value == "3":
                    anomaly_value_3_seen = True
    # 110 taxonomies, ~20000 answers per inventory.
    assert total_taxonomies >= 100
    assert total_answers >= 19000, f"only {total_answers} answers (expected ~20000)"
    # Four distinct criteria-set URLs per inventory/taxonomy.json.
    assert len(criteria_urls) >= 4
    # The known value="3" anomaly must be reachable through the parser.
    assert anomaly_value_3_seen, "the <num value='3'> anomaly was not encountered"
