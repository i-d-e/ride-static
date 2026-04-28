"""Tests for the per-kind block parser and the dispatcher.

Synthetic TEI fragments cover one happy-path case per block kind, the
list-rend normalisation rules, the figure-kind detection, and the
dispatcher's raise on unknown element names.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree

from src.model.block import (
    Citation,
    Figure,
    List,
    Paragraph,
    Table,
)
from src.parser.blocks import (
    UnknownTeiElement,
    parse_block,
    parse_cit,
    parse_figure,
    parse_list,
    parse_paragraph,
    parse_table,
)


TEI = "http://www.tei-c.org/ns/1.0"


def _el(xml: str) -> etree._Element:
    """Parse an XML fragment with the TEI default namespace and return its root."""
    return etree.fromstring(xml.strip().encode("utf-8"))


# -- Paragraph ------------------------------------------------------------


def test_parse_paragraph_carries_n_for_citation_anchor():
    p = _el('<p xmlns="http://www.tei-c.org/ns/1.0" n="12">Body text.</p>')
    out = parse_paragraph(p)
    assert isinstance(out, Paragraph)
    assert out.n == "12"
    assert out.inlines == ()  # Phase 4 fills this


def test_parse_paragraph_without_n():
    p = _el('<p xmlns="http://www.tei-c.org/ns/1.0">No number.</p>')
    assert parse_paragraph(p).n is None


# -- List -----------------------------------------------------------------


def test_parse_list_default_kind_is_bulleted():
    lst = _el(
        '<list xmlns="http://www.tei-c.org/ns/1.0">'
        "<item>a</item><item>b</item></list>"
    )
    out = parse_list(lst)
    assert out.kind == "bulleted"
    assert len(out.items) == 2


def test_parse_list_normalises_numbered_to_ordered():
    lst = _el(
        '<list xmlns="http://www.tei-c.org/ns/1.0" rend="numbered">'
        "<item>x</item></list>"
    )
    assert parse_list(lst).kind == "ordered"


def test_parse_list_normalises_unordered_to_bulleted():
    lst = _el(
        '<list xmlns="http://www.tei-c.org/ns/1.0" rend="unordered">'
        "<item>x</item></list>"
    )
    assert parse_list(lst).kind == "bulleted"


def test_parse_list_labeled_extracts_label_per_item():
    lst = _el(
        '<list xmlns="http://www.tei-c.org/ns/1.0" rend="labeled">'
        "<item><label>API</label> Application Programming Interface</item>"
        "<item><label>TEI</label> Text Encoding Initiative</item>"
        "</list>"
    )
    out = parse_list(lst)
    assert out.kind == "labeled"
    assert out.items[0].label is not None
    assert out.items[0].label[0].text == "API"
    assert out.items[1].label[0].text == "TEI"


def test_parse_list_labeled_item_without_label_yields_none():
    """Mixed labeled lists are rare but possible; missing label is not an error."""
    lst = _el(
        '<list xmlns="http://www.tei-c.org/ns/1.0" rend="labeled">'
        "<item>no label here</item></list>"
    )
    assert parse_list(lst).items[0].label is None


# -- Table ----------------------------------------------------------------


def test_parse_table_with_head_and_header_cell():
    tbl = _el(
        '<table xmlns="http://www.tei-c.org/ns/1.0">'
        "<head>Sample</head>"
        '<row><cell role="label">H</cell></row>'
        "<row><cell>v</cell></row>"
        "</table>"
    )
    out = parse_table(tbl)
    assert isinstance(out, Table)
    assert out.head is not None and out.head[0].text == "Sample"
    assert len(out.rows) == 2
    assert out.rows[0].cells[0].is_header is True
    assert out.rows[1].cells[0].is_header is False


def test_parse_table_without_head():
    tbl = _el(
        '<table xmlns="http://www.tei-c.org/ns/1.0">'
        "<row><cell>v</cell></row></table>"
    )
    assert parse_table(tbl).head is None


# -- Figure ---------------------------------------------------------------


def test_parse_figure_graphic():
    fig = _el(
        '<figure xmlns="http://www.tei-c.org/ns/1.0">'
        "<head>Fig. 1</head>"
        '<graphic url="figures/screenshot.png"/>'
        "</figure>"
    )
    out = parse_figure(fig)
    assert out.kind == "graphic"
    assert out.graphic_url == "figures/screenshot.png"
    assert out.code is None
    assert out.head[0].text == "Fig. 1"


def test_parse_figure_code_example_via_eg():
    fig = _el(
        '<figure xmlns="http://www.tei-c.org/ns/1.0">'
        "<head>TEI markup sample</head>"
        '<eg lang="xml"><persName>Anna</persName></eg>'
        "</figure>"
    )
    out = parse_figure(fig)
    assert out.kind == "code_example"
    assert out.code is not None and "Anna" in out.code
    assert out.code_lang == "xml"
    assert out.graphic_url is None


def test_parse_figure_without_graphic_or_eg_falls_back_to_graphic_kind():
    fig = _el(
        '<figure xmlns="http://www.tei-c.org/ns/1.0"><head>Empty</head></figure>'
    )
    out = parse_figure(fig)
    assert out.kind == "graphic"
    assert out.graphic_url is None


# -- Citation -------------------------------------------------------------


def test_parse_cit_with_bibl_and_target():
    cit = _el(
        '<cit xmlns="http://www.tei-c.org/ns/1.0">'
        "<quote>Famous line.</quote>"
        '<bibl>Smith <ref target="#s2010">2010</ref></bibl>'
        "</cit>"
    )
    out = parse_cit(cit)
    assert isinstance(out, Citation)
    assert out.bibl == ()  # Phase 4 fills with mixed-content inlines
    assert out.bibl_target == "#s2010"


def test_parse_cit_without_bibl():
    cit = _el(
        '<cit xmlns="http://www.tei-c.org/ns/1.0">'
        "<quote>Line.</quote></cit>"
    )
    out = parse_cit(cit)
    assert out.bibl is None
    assert out.bibl_target is None


# -- Dispatcher -----------------------------------------------------------


def test_dispatch_paragraph():
    p = _el('<p xmlns="http://www.tei-c.org/ns/1.0">x</p>')
    assert isinstance(parse_block(p), Paragraph)


def test_dispatch_list():
    lst = _el(
        '<list xmlns="http://www.tei-c.org/ns/1.0"><item>a</item></list>'
    )
    assert isinstance(parse_block(lst), List)


def test_dispatch_table_figure_cit():
    tbl = _el(
        '<table xmlns="http://www.tei-c.org/ns/1.0">'
        "<row><cell>v</cell></row></table>"
    )
    fig = _el(
        '<figure xmlns="http://www.tei-c.org/ns/1.0">'
        '<head>F</head><graphic url="x.png"/></figure>'
    )
    cit = _el(
        '<cit xmlns="http://www.tei-c.org/ns/1.0">'
        "<quote>q</quote></cit>"
    )
    assert isinstance(parse_block(tbl), Table)
    assert isinstance(parse_block(fig), Figure)
    assert isinstance(parse_block(cit), Citation)


def test_dispatch_unknown_raises_with_localname():
    el = _el(
        '<unknownThing xmlns="http://www.tei-c.org/ns/1.0">x</unknownThing>'
    )
    with pytest.raises(UnknownTeiElement) as exc_info:
        parse_block(el)
    assert exc_info.value.localname == "unknownThing"
    assert "<unknownThing>" in str(exc_info.value)


def test_dispatch_unknown_includes_div_hint():
    """When the unknown element sits inside a <div xml:id=...>, the hint
    points to that ancestor so the offending block is locatable in the source."""
    container = _el(
        '<div xmlns="http://www.tei-c.org/ns/1.0" xml:id="div3">'
        "<weirdBlock>x</weirdBlock></div>"
    )
    weird = container.find("{%s}weirdBlock" % TEI)
    with pytest.raises(UnknownTeiElement) as exc_info:
        parse_block(weird)
    assert "div3" in str(exc_info.value)


# -- Real-corpus smoke ----------------------------------------------------


_RIDE = Path(__file__).resolve().parent.parent.parent / "ride" / "tei_all"


@pytest.mark.skipif(not _RIDE.exists(), reason="../ride/ corpus not present")
def test_smoke_real_corpus_figure_with_eg():
    """At least one review in the corpus has a <figure> with <eg> (41 total).
    Pick the first such figure and confirm parse_figure yields kind=code_example.
    """
    found = False
    for f in sorted(_RIDE.glob("*-tei.xml")):
        tree = etree.parse(str(f))
        for fig in tree.iter("{%s}figure" % TEI):
            eg = fig.find("{%s}eg" % TEI)
            if eg is not None:
                out = parse_figure(fig)
                assert out.kind == "code_example"
                assert out.code is not None
                found = True
                break
        if found:
            break
    assert found, "expected at least one <figure>/<eg> in the corpus"
