"""Tests for the back-bibliography parser.

Synthetic TEI fixtures cover the standard cases (single ``<listBibl>``,
multiple ``<bibl>``s, missing ``<back>``, missing ``<listBibl>``,
nested ``<bibl>`` inside ``<cit>`` not collected). A real-corpus smoke
verifies the magnitude of the aggregate against the inventory's
1389 bibls in listBibl.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree

from src.model.bibliography import BibEntry
from src.model.inline import Reference, Text
from src.parser.bibliography import parse_bibl, parse_bibliography


TEI = "http://www.tei-c.org/ns/1.0"


def _text_el(xml: str) -> etree._Element:
    """Parse an XML fragment and return the ``<text>`` root."""
    return etree.fromstring(xml.strip().encode("utf-8"))


# -- parse_bibl -----------------------------------------------------------


def test_parse_bibl_captures_xml_id_and_inlines():
    bibl = etree.fromstring(
        '<bibl xmlns="http://www.tei-c.org/ns/1.0" '
        'xmlns:xml="http://www.w3.org/XML/1998/namespace" '
        'xml:id="bib.smith2010">Smith, John. <emph>A study</emph>. 2010.</bibl>'
    )
    out = parse_bibl(bibl)
    assert isinstance(out, BibEntry)
    assert out.xml_id == "bib.smith2010"
    assert out.inlines[0] == Text(text="Smith, John. ")
    assert out.ref_target is None


def test_parse_bibl_extracts_first_ref_target():
    bibl = etree.fromstring(
        '<bibl xmlns="http://www.tei-c.org/ns/1.0">'
        '<emph>Foo</emph> by Smith, '
        '<ref target="https://doi.org/10.1234/example">DOI</ref> '
        '<ref target="https://other.example/secondary">Secondary</ref>.</bibl>'
    )
    out = parse_bibl(bibl)
    assert out.ref_target == "https://doi.org/10.1234/example"


def test_parse_bibl_with_structured_children_passes_text_through():
    """``<respStmt>``, ``<date>``, ``<title>``, ``<editor>``, ``<idno>``
    are passthrough-text in the inline walker — their content survives
    as Text in the inlines tuple, just without sub-structure."""
    bibl = etree.fromstring(
        '<bibl xmlns="http://www.tei-c.org/ns/1.0">'
        '<respStmt>edited by</respStmt> <editor>Eve Editor</editor>, '
        '<date when="2010">2010</date>.</bibl>'
    )
    out = parse_bibl(bibl)
    text_blob = "".join(i.text for i in out.inlines if isinstance(i, Text))
    assert "edited by" in text_blob
    assert "Eve Editor" in text_blob
    assert "2010" in text_blob


# -- parse_bibliography ---------------------------------------------------


def test_parse_bibliography_with_single_listbibl():
    text_el = _text_el("""
        <text xmlns="http://www.tei-c.org/ns/1.0">
          <body><div><head>Body</head></div></body>
          <back>
            <div type="bibliography">
              <head>Bibliography</head>
              <listBibl>
                <bibl>Smith 2010.</bibl>
                <bibl>Jones 2015.</bibl>
              </listBibl>
            </div>
          </back>
        </text>
    """)
    out = parse_bibliography(text_el)
    assert len(out) == 2
    assert all(isinstance(b, BibEntry) for b in out)


def test_parse_bibliography_returns_empty_when_no_back():
    """Seven corpus reviews have no <back>; parse must return ()."""
    text_el = _text_el("""
        <text xmlns="http://www.tei-c.org/ns/1.0">
          <body><div><head>Body</head></div></body>
        </text>
    """)
    assert parse_bibliography(text_el) == ()


def test_parse_bibliography_returns_empty_when_no_listbibl():
    """A back-div without listBibl yields no entries."""
    text_el = _text_el("""
        <text xmlns="http://www.tei-c.org/ns/1.0">
          <body><div><head>Body</head></div></body>
          <back><div type="appendix"><head>Appendix</head><p>Text.</p></div></back>
        </text>
    """)
    assert parse_bibliography(text_el) == ()


def test_parse_bibliography_skips_bibl_inside_cit():
    """Inline citations have <bibl> inside <cit>; those must NOT be
    collected as bibliography entries."""
    text_el = _text_el("""
        <text xmlns="http://www.tei-c.org/ns/1.0">
          <body>
            <div>
              <head>Body</head>
              <p>quoted: <cit><quote>q</quote><bibl>Inline bibl</bibl></cit></p>
            </div>
          </body>
          <back>
            <div type="bibliography">
              <listBibl><bibl>Real bibl</bibl></listBibl>
            </div>
          </back>
        </text>
    """)
    out = parse_bibliography(text_el)
    assert len(out) == 1
    assert "Real" in out[0].inlines[0].text


def test_parse_bibliography_handles_multiple_listbibls_in_same_back_div():
    """Some reviews split bibliography across several listBibls."""
    text_el = _text_el("""
        <text xmlns="http://www.tei-c.org/ns/1.0">
          <body><div><head>Body</head></div></body>
          <back>
            <div type="bibliography">
              <head>Bibliography</head>
              <listBibl><bibl>Primary 1</bibl><bibl>Primary 2</bibl></listBibl>
              <listBibl><bibl>Secondary</bibl></listBibl>
            </div>
          </back>
        </text>
    """)
    out = parse_bibliography(text_el)
    assert len(out) == 3


def test_parse_bibliography_text_el_none_yields_empty():
    assert parse_bibliography(None) == ()


# -- Real-corpus smoke ----------------------------------------------------


_RIDE = Path(__file__).resolve().parent.parent.parent / "ride" / "tei_all"


@pytest.mark.skipif(not _RIDE.exists(), reason="../ride/ corpus not present")
def test_smoke_real_corpus_aggregate_bibl_count() -> None:
    """The corpus inventory reports 1389 ``<bibl>``s inside ``<listBibl>``.
    The bibliography parser should reach approximately that magnitude
    when run across all 107 reviews."""
    files = sorted(_RIDE.glob("*-tei.xml"))
    total = 0
    no_back_count = 0
    for f in files:
        tree = etree.parse(str(f))
        text_el = tree.getroot().find(f"{{{TEI}}}text")
        entries = parse_bibliography(text_el)
        if entries == ():
            if text_el is not None and text_el.find(f"{{{TEI}}}back") is None:
                no_back_count += 1
        total += len(entries)
    # Inventory says ~1389; allow a small drift for parsing edge cases.
    assert total >= 1300, f"only {total} bibl entries collected (expected ~1389)"
    # The seven no-back reviews from knowledge/data.md must contribute zero.
    assert no_back_count == 7, f"expected 7 no-back reviews, got {no_back_count}"
