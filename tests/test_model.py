"""Tests for the Section / Block / Inline domain types.

These exercise the dataclass shapes only — no parser, no renderer. The point is
to lock down the field signatures, immutability, and hashability so that later
phases consume a stable contract.
"""
import dataclasses

import pytest

from src.model import (
    Citation,
    Emphasis,
    Figure,
    Highlight,
    InlineCode,
    List,
    ListItem,
    Note,
    Paragraph,
    Reference,
    Section,
    Table,
    TableCell,
    TableRow,
    Text,
)


# -- Inline ---------------------------------------------------------------


def test_text_holds_string():
    t = Text("hello")
    assert t.text == "hello"


def test_emphasis_with_children_and_rend():
    e = Emphasis(children=(Text("italic"),), rend="italic")
    assert e.rend == "italic"
    assert e.children[0].text == "italic"


def test_highlight_defaults_rend_to_none():
    h = Highlight(children=(Text("x"),))
    assert h.rend is None


def test_reference_with_target_and_type():
    r = Reference(children=(Text("Fig. 1"),), target="#fig1", type="crossref")
    assert r.target == "#fig1"
    assert r.type == "crossref"


def test_note_carries_n_and_place():
    n = Note(children=(Text("see ibid."),), n="3", place="foot")
    assert n.n == "3"
    assert n.place == "foot"


def test_inline_code_with_lang():
    c = InlineCode(text="<persName/>", lang="xml")
    assert c.lang == "xml"


# -- Block ----------------------------------------------------------------


def test_paragraph_with_n_for_citation_anchor():
    p = Paragraph(inlines=(Text("Body."),), n="12")
    assert p.n == "12"


def test_list_kinds_and_labeled_items():
    bullet = List(items=(ListItem(inlines=(Text("a"),)),), kind="bulleted")
    assert bullet.kind == "bulleted"

    glossary = List(
        items=(
            ListItem(inlines=(Text("Application Programming Interface"),), label=(Text("API"),)),
            ListItem(inlines=(Text("Text Encoding Initiative"),), label=(Text("TEI"),)),
        ),
        kind="labeled",
    )
    assert glossary.kind == "labeled"
    assert glossary.items[0].label[0].text == "API"


def test_table_flat_with_optional_head():
    table = Table(
        rows=(
            TableRow(cells=(TableCell(inlines=(Text("h"),), is_header=True),)),
            TableRow(cells=(TableCell(inlines=(Text("v"),)),)),
        ),
        head=(Text("Sample table"),),
    )
    assert table.head[0].text == "Sample table"
    assert table.rows[0].cells[0].is_header is True
    assert table.rows[1].cells[0].is_header is False


def test_figure_two_kinds():
    img = Figure(
        kind="graphic",
        head=(Text("Fig. 1: screenshot"),),
        graphic_url="figures/screenshot.png",
    )
    assert img.kind == "graphic"
    assert img.code is None

    sample = Figure(
        kind="code_example",
        head=(Text("Sample TEI"),),
        code="<persName>Anna</persName>",
        code_lang="xml",
    )
    assert sample.kind == "code_example"
    assert sample.graphic_url is None


def test_citation_keeps_bibl_inlines():
    cit = Citation(
        quote_inlines=(Text("To be or not to be."),),
        bibl=(Text("Shakespeare, "), Emphasis(children=(Text("Hamlet"),))),
        bibl_target="#hamlet",
    )
    assert cit.bibl[1].children[0].text == "Hamlet"


# -- Section --------------------------------------------------------------


def test_section_flat():
    s = Section(
        xml_id="div1",
        type=None,
        heading=(Text("Introduction"),),
        level=1,
        blocks=(Paragraph(inlines=(Text("Body."),)),),
        subsections=(),
    )
    assert s.xml_id == "div1"
    assert s.heading[0].text == "Introduction"


def test_section_recursive():
    inner = Section(
        xml_id="div1.1",
        type=None,
        heading=(Text("Method"),),
        level=2,
        blocks=(),
        subsections=(),
    )
    outer = Section(
        xml_id="div1",
        type=None,
        heading=(Text("Body"),),
        level=1,
        blocks=(),
        subsections=(inner,),
    )
    assert outer.subsections[0].xml_id == "div1.1"
    assert outer.subsections[0].level == 2


def test_section_with_typed_block():
    abstract = Section(
        xml_id="abstract",
        type="abstract",
        heading=None,
        level=1,
        blocks=(Paragraph(inlines=(Text("Short abstract."),)),),
        subsections=(),
    )
    assert abstract.type == "abstract"
    assert abstract.heading is None


# -- Immutability and hashability ----------------------------------------


def test_paragraph_is_frozen():
    p = Paragraph(inlines=(Text("x"),))
    with pytest.raises(dataclasses.FrozenInstanceError):
        p.inlines = (Text("y"),)


def test_section_is_frozen():
    s = Section(xml_id="d", type=None, heading=None, level=1, blocks=(), subsections=())
    with pytest.raises(dataclasses.FrozenInstanceError):
        s.level = 2


def test_inlines_and_blocks_are_hashable():
    # tuple-typed sequences must keep instances hashable so they can sit in
    # sets, dict keys, or be deduplicated.
    items = {
        Text("x"),
        Paragraph(inlines=(Text("y"),)),
        List(items=(ListItem(inlines=(Text("a"),)),), kind="bulleted"),
    }
    assert len(items) == 3


def test_section_hashable_recursive():
    inner = Section(xml_id="c", type=None, heading=None, level=2, blocks=(), subsections=())
    outer = Section(xml_id="p", type=None, heading=None, level=1, blocks=(), subsections=(inner,))
    assert hash(outer) != hash(inner)
