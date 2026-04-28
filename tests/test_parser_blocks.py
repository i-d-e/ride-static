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
    parse_block,
    parse_block_sequence,
    parse_cit,
    parse_figure,
    parse_list,
    parse_paragraph,
    parse_paragraph_or_split,
    parse_table,
)
from src.parser.common import UnknownTeiElement


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
    # Phase 5 wired the inline walker; @n captures the visible margin number.
    from src.model.inline import Text
    assert out.inlines == (Text(text="Body text."),)


def test_parse_paragraph_without_n():
    p = _el('<p xmlns="http://www.tei-c.org/ns/1.0">No number.</p>')
    assert parse_paragraph(p).n is None


def test_parse_paragraph_xml_id_carried_for_copy_link():
    """`@xml:id` is the citation-anchor target referenced by the §11
    copy-link affordance. Capture it on the Paragraph dataclass."""
    p = _el(
        '<p xmlns="http://www.tei-c.org/ns/1.0" '
        'xmlns:xml="http://www.w3.org/XML/1998/namespace" '
        'xml:id="div2.p3">Anchored.</p>'
    )
    assert parse_paragraph(p).xml_id == "div2.p3"


def test_parse_paragraph_without_xml_id_yields_none():
    """219 of 3809 paragraphs in the corpus have no xml:id; field stays None."""
    p = _el('<p xmlns="http://www.tei-c.org/ns/1.0">Plain.</p>')
    assert parse_paragraph(p).xml_id is None


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


def test_parse_figure_xml_id_for_apparate_backlink():
    """Figures need a stable id for the parallel apparate sub-block (§6)."""
    fig = _el(
        '<figure xmlns="http://www.tei-c.org/ns/1.0" '
        'xmlns:xml="http://www.w3.org/XML/1998/namespace" '
        'xml:id="fig.intro"><head>I</head><graphic url="x.png"/></figure>'
    )
    assert parse_figure(fig).xml_id == "fig.intro"


def test_parse_figure_alt_from_figdesc():
    """`<figDesc>` is empty in the current corpus, but the parser captures it
    when present so Phase 13's build report can act on missing values."""
    fig = _el(
        '<figure xmlns="http://www.tei-c.org/ns/1.0">'
        "<head>F</head>"
        '<graphic url="x.png"/>'
        "<figDesc>A diagram of the workflow.</figDesc>"
        "</figure>"
    )
    assert parse_figure(fig).alt == "A diagram of the workflow."


def test_parse_figure_alt_none_when_figdesc_absent():
    """The corpus today: 874 figures, 0 figDesc — the dominant case."""
    fig = _el(
        '<figure xmlns="http://www.tei-c.org/ns/1.0">'
        '<head>F</head><graphic url="x.png"/></figure>'
    )
    assert parse_figure(fig).alt is None


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
    # Phase 6 unified the bibl shape: Citation.bibl is now a BibEntry that
    # mirrors the back-bibliography form. bibl_target stays as a top-level
    # convenience for renderers (it equals bibl.ref_target).
    from src.model.bibliography import BibEntry
    from src.model.inline import Reference, Text
    assert out.quote_inlines == (Text(text="Famous line."),)
    assert isinstance(out.bibl, BibEntry)
    assert out.bibl.inlines[0] == Text(text="Smith ")
    assert isinstance(out.bibl.inlines[1], Reference)
    assert out.bibl.inlines[1].target == "#s2010"
    assert out.bibl.ref_target == "#s2010"
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


# -- Real-corpus anomaly: <list> inside <item> ----------------------------


_RIDE = Path(__file__).resolve().parent.parent.parent / "ride" / "tei_all"
_ANEMOSKALA = _RIDE / "anemoskala-tei.xml"


@pytest.mark.skipif(not _ANEMOSKALA.exists(), reason="anemoskala-tei.xml not present")
def test_real_corpus_list_inside_item() -> None:
    """The corpus has 3 occurrences of ``<list>`` nested inside ``<item>``;
    anemoskala-tei.xml is one of them. The parser must surface them as
    ``ListItem.blocks`` rather than dropping or raising.

    This is a documented anomaly per ``knowledge/data.md``; the test pins
    the named branch end-to-end against the real corpus (no synthetic
    fixture — the structure is delicate enough that we want the empirical
    shape exercised).
    """
    from src.parser.review import parse_review
    from src.model.block import List as ListBlock, ListItem

    review = parse_review(_ANEMOSKALA)

    found_nested = False

    def walk_block(b):
        nonlocal found_nested
        if isinstance(b, ListBlock):
            for item in b.items:
                for nested in item.blocks:
                    if isinstance(nested, ListBlock):
                        found_nested = True
                    walk_block(nested)

    def walk_section(s):
        for b in s.blocks:
            walk_block(b)
        for sub in s.subsections:
            walk_section(sub)

    for s in review.front + review.body + review.back:
        walk_section(s)
    assert found_nested, (
        "anemoskala-tei.xml is supposed to carry a <list> inside <item> — "
        "if this fails, either the corpus has drifted or the parser "
        "regressed on the ListItem.blocks branch."
    )


# -- Paragraph splitting --------------------------------------------------


def test_split_paragraph_no_block_children_fast_path():
    """Without block children, parse_paragraph_or_split returns one element."""
    p = _el(
        '<p xmlns="http://www.tei-c.org/ns/1.0">'
        "Just plain text with <emph>emphasis</emph>.</p>"
    )
    out = parse_paragraph_or_split(p)
    assert len(out) == 1
    assert isinstance(out[0], Paragraph)


def test_split_paragraph_around_figure_yields_three_blocks():
    """`<p>before<figure/>after</p>` becomes Paragraph, Figure, Paragraph."""
    p = _el(
        '<p xmlns="http://www.tei-c.org/ns/1.0">'
        'before <figure><graphic url="x.png"/></figure> after</p>'
    )
    out = parse_paragraph_or_split(p)
    assert len(out) == 3
    assert isinstance(out[0], Paragraph)
    assert isinstance(out[1], Figure)
    assert isinstance(out[2], Paragraph)


def test_split_paragraph_xml_id_only_on_first_chunk():
    """The first chunk inherits @xml:id; continuation chunks are synthetic."""
    p = _el(
        '<p xmlns="http://www.tei-c.org/ns/1.0" '
        'xmlns:xml="http://www.w3.org/XML/1998/namespace" '
        'xml:id="p1" n="42">'
        'before <figure><graphic url="x.png"/></figure> after</p>'
    )
    out = parse_paragraph_or_split(p)
    assert isinstance(out[0], Paragraph) and out[0].xml_id == "p1" and out[0].n == "42"
    assert isinstance(out[2], Paragraph) and out[2].xml_id is None and out[2].n is None


def test_split_paragraph_starting_with_block_drops_empty_leading_paragraph():
    """`<p><figure/>after</p>` → just (Figure, Paragraph) — no empty leading chunk."""
    p = _el(
        '<p xmlns="http://www.tei-c.org/ns/1.0">'
        '<figure><graphic url="x.png"/></figure>after text</p>'
    )
    out = parse_paragraph_or_split(p)
    assert len(out) == 2
    assert isinstance(out[0], Figure)
    assert isinstance(out[1], Paragraph)


def test_split_paragraph_ending_with_block_drops_empty_trailing_paragraph():
    """`<p>before<figure/></p>` → (Paragraph, Figure)."""
    p = _el(
        '<p xmlns="http://www.tei-c.org/ns/1.0">'
        'before text<figure><graphic url="x.png"/></figure></p>'
    )
    out = parse_paragraph_or_split(p)
    assert len(out) == 2
    assert isinstance(out[0], Paragraph)
    assert isinstance(out[1], Figure)


def test_split_paragraph_with_only_block_yields_block_alone():
    """`<p><figure/></p>` → (Figure,)."""
    p = _el(
        '<p xmlns="http://www.tei-c.org/ns/1.0">'
        '<figure><graphic url="x.png"/></figure></p>'
    )
    out = parse_paragraph_or_split(p)
    assert len(out) == 1
    assert isinstance(out[0], Figure)


def test_split_paragraph_with_inline_emph_around_block():
    """Inlines around a block survive into the chunks they belong to."""
    p = _el(
        '<p xmlns="http://www.tei-c.org/ns/1.0">'
        'see <emph>fig</emph> here<figure><graphic url="x.png"/></figure>'
        'and <emph>more</emph></p>'
    )
    out = parse_paragraph_or_split(p)
    assert len(out) == 3
    para_a, fig, para_b = out
    assert isinstance(para_a, Paragraph)
    # First chunk: Text("see "), Emphasis("fig"), Text(" here")
    assert len(para_a.inlines) == 3
    assert isinstance(fig, Figure)
    # Trailing chunk: Text("and "), Emphasis("more")
    assert len(para_b.inlines) == 2


# -- Block sequence -------------------------------------------------------


def test_parse_block_sequence_skips_div_and_head():
    """`parse_block_sequence` consumes only direct block-level children;
    nested <div> stays the section parser's responsibility, <head> is the
    section heading and is consumed there."""
    div = _el(
        '<div xmlns="http://www.tei-c.org/ns/1.0">'
        "<head>Title</head>"
        "<p>One.</p>"
        "<p>Two.</p>"
        '<div><head>Sub</head><p>Inner.</p></div>'
        "</div>"
    )
    blocks = parse_block_sequence(div)
    assert len(blocks) == 2
    assert all(isinstance(b, Paragraph) for b in blocks)


def test_parse_block_sequence_explodes_paragraph_with_block_child():
    """A <p> with embedded <list> inside a <div> contributes 3 blocks."""
    div = _el(
        '<div xmlns="http://www.tei-c.org/ns/1.0">'
        "<head>X</head>"
        "<p>before<list><item>a</item></list>after</p>"
        "</div>"
    )
    blocks = parse_block_sequence(div)
    assert len(blocks) == 3
    assert isinstance(blocks[0], Paragraph)
    assert isinstance(blocks[1], List)
    assert isinstance(blocks[2], Paragraph)


# -- Real-corpus smoke ----------------------------------------------------


_RIDE = Path(__file__).resolve().parent.parent.parent / "ride" / "tei_all"


@pytest.mark.skipif(not _RIDE.exists(), reason="../ride/ corpus not present")
def test_smoke_real_corpus_all_reviews_section_blocks_parse() -> None:
    """Every <body>'s sections through `parse_sections` (which now calls
    `parse_block_sequence` recursively) must parse without raising. This is
    the corpus-wide validation that wires Phases 1–5 together."""
    from src.parser.sections import parse_sections
    files = sorted(_RIDE.glob("*-tei.xml"))
    assert len(files) >= 100
    block_in_p_seen = 0
    for f in files:
        tree = etree.parse(str(f))
        body = tree.getroot().find(f"{{{TEI}}}text/{{{TEI}}}body")
        sections = parse_sections(body)
        # Walk every section's blocks recursively to count Paragraph splits.
        stack = list(sections)
        while stack:
            s = stack.pop()
            for b in s.blocks:
                pass  # touching .blocks proves it parsed
            stack.extend(s.subsections)
        # Also count paragraphs that are clearly continuation-chunks
        # (xml_id=None even though the source has many xml:id'd <p>).
    # Enough signal that the smoke went through 107 files


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
