"""Tests for the mixed-content inline parser.

Synthetic TEI fragments cover the walker (text + child + tail), the
whitespace strategy (collapse internal, strip edges), each of the six
inline kinds, nesting (Emphasis containing Reference, Reference
containing Emphasis), the soft-skip set (``<lb/>``), the ``crosssref``
normalisation, and the unknown-element raise.

A real-corpus smoke test parses ``<head>`` elements from a few reviews
without raising, and another verifies that the single ``crosssref`` typo
is normalised to ``crossref``.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree

from src.model.inline import (
    Emphasis,
    Highlight,
    InlineCode,
    Note,
    Reference,
    Text,
)
from src.parser.blocks import UnknownTeiElement
from src.parser.inlines import parse_inlines


TEI = "http://www.tei-c.org/ns/1.0"


def _el(xml: str) -> etree._Element:
    """Parse an XML fragment with the TEI default namespace and return its root."""
    return etree.fromstring(xml.strip().encode("utf-8"))


# -- Walker basics --------------------------------------------------------


def test_pure_text():
    p = _el('<p xmlns="http://www.tei-c.org/ns/1.0">hello</p>')
    out = parse_inlines(p)
    assert out == (Text(text="hello"),)


def test_empty_element_yields_empty_tuple():
    p = _el('<p xmlns="http://www.tei-c.org/ns/1.0"/>')
    assert parse_inlines(p) == ()


def test_text_child_tail():
    p = _el(
        '<p xmlns="http://www.tei-c.org/ns/1.0">before<emph>x</emph>after</p>'
    )
    out = parse_inlines(p)
    assert out == (
        Text(text="before"),
        Emphasis(children=(Text(text="x"),)),
        Text(text="after"),
    )


def test_only_child_no_text_around():
    p = _el(
        '<p xmlns="http://www.tei-c.org/ns/1.0"><emph>x</emph></p>'
    )
    out = parse_inlines(p)
    assert out == (Emphasis(children=(Text(text="x"),)),)


def test_multiple_children_with_interleaved_text():
    p = _el(
        '<p xmlns="http://www.tei-c.org/ns/1.0">'
        "a<emph>b</emph>c<hi>d</hi>e</p>"
    )
    out = parse_inlines(p)
    assert len(out) == 5
    assert out[0] == Text(text="a")
    assert isinstance(out[1], Emphasis)
    assert out[2] == Text(text="c")
    assert isinstance(out[3], Highlight)
    assert out[4] == Text(text="e")


# -- Whitespace -----------------------------------------------------------


def test_internal_whitespace_collapsed():
    p = _el('<p xmlns="http://www.tei-c.org/ns/1.0">foo   bar</p>')
    assert parse_inlines(p) == (Text(text="foo bar"),)


def test_leading_and_trailing_stripped_at_sequence_edges():
    p = _el('<p xmlns="http://www.tei-c.org/ns/1.0">   foo   </p>')
    assert parse_inlines(p) == (Text(text="foo"),)


def test_whitespace_between_word_and_element_preserved():
    p = _el(
        '<p xmlns="http://www.tei-c.org/ns/1.0">a <emph>b</emph> c</p>'
    )
    out = parse_inlines(p)
    assert out[0] == Text(text="a ")
    assert isinstance(out[1], Emphasis)
    assert out[2] == Text(text=" c")


def test_pure_whitespace_around_single_child_dropped():
    p = _el(
        '<p xmlns="http://www.tei-c.org/ns/1.0"> <emph>x</emph> </p>'
    )
    out = parse_inlines(p)
    assert out == (Emphasis(children=(Text(text="x"),)),)


def test_pure_whitespace_only_yields_empty_tuple():
    p = _el('<p xmlns="http://www.tei-c.org/ns/1.0">   </p>')
    assert parse_inlines(p) == ()


# -- Per-kind -------------------------------------------------------------


def test_emph_with_rend():
    p = _el(
        '<p xmlns="http://www.tei-c.org/ns/1.0">'
        '<emph rend="italic">x</emph></p>'
    )
    out = parse_inlines(p)
    assert out == (Emphasis(children=(Text(text="x"),), rend="italic"),)


def test_hi_with_rend_sup():
    p = _el(
        '<p xmlns="http://www.tei-c.org/ns/1.0">'
        '<hi rend="sup">2</hi></p>'
    )
    out = parse_inlines(p)
    assert out == (Highlight(children=(Text(text="2"),), rend="sup"),)


def test_ref_with_target_and_type():
    p = _el(
        '<p xmlns="http://www.tei-c.org/ns/1.0">'
        '<ref target="#K4.4" type="crossref">criterion</ref></p>'
    )
    out = parse_inlines(p)
    assert out == (
        Reference(
            children=(Text(text="criterion"),),
            target="#K4.4",
            type="crossref",
        ),
    )


def test_ref_without_type_is_none():
    p = _el(
        '<p xmlns="http://www.tei-c.org/ns/1.0">'
        '<ref target="https://example.org">link</ref></p>'
    )
    ref = parse_inlines(p)[0]
    assert isinstance(ref, Reference)
    assert ref.type is None
    assert ref.target == "https://example.org"


def test_ref_crosssref_typo_normalised_to_crossref():
    """One review in the corpus has @type='crosssref' (1 of 1705 refs).
    The parser normalises it silently to 'crossref'."""
    p = _el(
        '<p xmlns="http://www.tei-c.org/ns/1.0">'
        '<ref target="#K1" type="crosssref">x</ref></p>'
    )
    ref = parse_inlines(p)[0]
    assert isinstance(ref, Reference)
    assert ref.type == "crossref"


def test_note_with_xml_id_and_attributes():
    p = _el(
        '<p xmlns="http://www.tei-c.org/ns/1.0" '
        'xmlns:xml="http://www.w3.org/XML/1998/namespace">'
        '<note xml:id="ftn1" n="1" place="foot">See discussion below.</note>'
        "</p>"
    )
    out = parse_inlines(p)
    note = out[0]
    assert isinstance(note, Note)
    assert note.xml_id == "ftn1"
    assert note.n == "1"
    assert note.place == "foot"
    assert note.children == (Text(text="See discussion below."),)


def test_inline_code_with_lang():
    p = _el(
        '<p xmlns="http://www.tei-c.org/ns/1.0">'
        '<code lang="xml">&lt;p/&gt;</code></p>'
    )
    code = parse_inlines(p)[0]
    assert isinstance(code, InlineCode)
    assert code.text == "<p/>"
    assert code.lang == "xml"


def test_inline_code_preserves_internal_whitespace():
    """Code content is significant: do not collapse runs."""
    p = _el(
        '<p xmlns="http://www.tei-c.org/ns/1.0">'
        '<code>a   b</code></p>'
    )
    code = parse_inlines(p)[0]
    assert isinstance(code, InlineCode)
    assert code.text == "a   b"


# -- Nested ---------------------------------------------------------------


def test_emph_contains_ref():
    """11 of 9916 refs have an emph parent."""
    p = _el(
        '<p xmlns="http://www.tei-c.org/ns/1.0">'
        '<emph>foo <ref target="#x">bar</ref></emph></p>'
    )
    out = parse_inlines(p)
    emph = out[0]
    assert isinstance(emph, Emphasis)
    assert emph.children[0] == Text(text="foo ")
    assert isinstance(emph.children[1], Reference)
    assert emph.children[1].target == "#x"


def test_ref_contains_emph():
    """16 of 5055 emph elements have a ref parent."""
    p = _el(
        '<p xmlns="http://www.tei-c.org/ns/1.0">'
        '<ref target="#x">see <emph>also</emph> here</ref></p>'
    )
    out = parse_inlines(p)
    ref = out[0]
    assert isinstance(ref, Reference)
    assert ref.children[0] == Text(text="see ")
    assert isinstance(ref.children[1], Emphasis)
    assert ref.children[2] == Text(text=" here")


# -- Soft-skip ------------------------------------------------------------


def test_lb_becomes_single_space():
    """<lb/> appears 25× in <quote>; treated as soft whitespace, not modelled."""
    p = _el(
        '<p xmlns="http://www.tei-c.org/ns/1.0">line one<lb/>line two</p>'
    )
    out = parse_inlines(p)
    # The <lb/> is rendered as a single space, then coalesces with adjacent text
    assert out == (Text(text="line one line two"),)


# -- Comments and PIs -----------------------------------------------------


def test_comment_is_skipped_but_tail_preserved():
    p = _el(
        '<p xmlns="http://www.tei-c.org/ns/1.0">'
        "before<!-- editorial -->after</p>"
    )
    out = parse_inlines(p)
    assert out == (Text(text="beforeafter"),)


# -- Unknown element ------------------------------------------------------


def test_unknown_inline_raises_with_localname():
    p = _el(
        '<p xmlns="http://www.tei-c.org/ns/1.0">'
        '<weirdInline>x</weirdInline></p>'
    )
    with pytest.raises(UnknownTeiElement) as exc_info:
        parse_inlines(p)
    assert exc_info.value.localname == "weirdInline"


def test_block_inside_p_raises():
    """<figure>/<list>/<cit>/<table> inside <p> is a known data shape but
    not handled at the inline level. Phase 5 will route around it; for
    now, parse_inlines raises so callers cannot silently lose blocks."""
    p = _el(
        '<p xmlns="http://www.tei-c.org/ns/1.0">'
        'before<figure><graphic url="x.png"/></figure>after</p>'
    )
    with pytest.raises(UnknownTeiElement) as exc_info:
        parse_inlines(p)
    assert exc_info.value.localname == "figure"


# -- Real-corpus smoke ----------------------------------------------------


_RIDE = Path(__file__).resolve().parent.parent.parent / "ride" / "tei_all"


@pytest.mark.skipif(not _RIDE.exists(), reason="../ride/ corpus not present")
def test_smoke_real_corpus_first_ten_heads_parse() -> None:
    """``<head>`` elements have only inline children in the corpus
    (1917 occurrences with emph/ref/note/code/hi inside). Pick the first
    ten across alphabetically-first reviews and confirm they parse without
    raising."""
    seen = 0
    for f in sorted(_RIDE.glob("*-tei.xml")):
        tree = etree.parse(str(f))
        for head in tree.iter("{%s}head" % TEI):
            inlines = parse_inlines(head)
            assert isinstance(inlines, tuple)
            seen += 1
            if seen >= 10:
                return
    assert seen > 0


@pytest.mark.skipif(not _RIDE.exists(), reason="../ride/ corpus not present")
def test_smoke_real_corpus_crosssref_normalised() -> None:
    """Find the single ``<ref type="crosssref">`` in the corpus (one
    occurrence per inventory) and verify the parser normalises it to
    ``crossref``."""
    import copy
    found = False
    for f in sorted(_RIDE.glob("*-tei.xml")):
        tree = etree.parse(str(f))
        for ref in tree.iter("{%s}ref" % TEI):
            if ref.get("type") == "crosssref":
                # Wrap a detached copy of the ref in a synthetic <p> host so
                # parse_inlines sees just the one child (without the original
                # parent's surrounding text).
                host = etree.Element("{%s}p" % TEI)
                clone = copy.deepcopy(ref)
                clone.tail = None
                host.append(clone)
                out = parse_inlines(host)
                assert len(out) == 1
                assert isinstance(out[0], Reference)
                assert out[0].type == "crossref"
                found = True
                break
        if found:
            break
    assert found, "expected exactly one <ref type='crosssref'> in the corpus"
