"""Tests for the recursive section parser.

Synthetic TEI fixtures cover the standard cases plus the four documented
anomalies. The body-wrap anomaly (Commit 2.2) is exercised in its own
test once the wrap branch lands.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from lxml import etree

from src.model.section import Section
from src.parser.sections import parse_sections


TEI = "http://www.tei-c.org/ns/1.0"


def _parse_host(xml: str, host_tag: str = "body") -> etree._Element:
    """Parse a fragment, return the named host element (front/body/back)."""
    root = etree.fromstring(xml.strip().encode("utf-8"))
    host = root.find(f"{{{TEI}}}text/{{{TEI}}}{host_tag}")
    assert host is not None, f"<{host_tag}> not found in fixture"
    return host


# -- Standard cases -------------------------------------------------------


def test_single_div_with_head_and_type():
    host = _parse_host(
        textwrap.dedent("""
            <TEI xmlns="http://www.tei-c.org/ns/1.0">
              <text><body>
                <div xml:id="abstract" type="abstract">
                  <head>Abstract</head>
                </div>
              </body></text>
            </TEI>
        """)
    )
    sections = parse_sections(host)
    assert len(sections) == 1
    s = sections[0]
    assert s.xml_id == "abstract"
    assert s.type == "abstract"
    assert s.heading is not None and s.heading[0].text == "Abstract"
    assert s.level == 1
    assert s.blocks == ()
    assert s.subsections == ()


def test_two_levels_of_nesting():
    host = _parse_host(
        textwrap.dedent("""
            <TEI xmlns="http://www.tei-c.org/ns/1.0">
              <text><body>
                <div xml:id="div1">
                  <head>Outer</head>
                  <div xml:id="div1.1">
                    <head>Inner</head>
                  </div>
                </div>
              </body></text>
            </TEI>
        """)
    )
    sections = parse_sections(host)
    assert len(sections) == 1
    outer = sections[0]
    assert outer.xml_id == "div1"
    assert outer.level == 1
    assert len(outer.subsections) == 1
    inner = outer.subsections[0]
    assert inner.xml_id == "div1.1"
    assert inner.level == 2
    assert inner.heading[0].text == "Inner"


def test_three_levels_of_nesting_is_allowed():
    host = _parse_host(
        textwrap.dedent("""
            <TEI xmlns="http://www.tei-c.org/ns/1.0">
              <text><body>
                <div xml:id="a"><div xml:id="a.b"><div xml:id="a.b.c"/></div></div>
              </body></text>
            </TEI>
        """)
    )
    sections = parse_sections(host)
    assert sections[0].subsections[0].subsections[0].level == 3


# -- Anomalies ------------------------------------------------------------


def test_div_without_xml_id_gets_positional_fallback():
    host = _parse_host(
        textwrap.dedent("""
            <TEI xmlns="http://www.tei-c.org/ns/1.0">
              <text><body>
                <div>
                  <head>First</head>
                  <div><head>Nested</head></div>
                </div>
                <div><head>Second</head></div>
              </body></text>
            </TEI>
        """)
    )
    sections = parse_sections(host)
    assert sections[0].xml_id == "sec-1"
    assert sections[0].subsections[0].xml_id == "sec-1.1"
    assert sections[1].xml_id == "sec-2"


def test_div_without_head_yields_heading_none():
    host = _parse_host(
        textwrap.dedent("""
            <TEI xmlns="http://www.tei-c.org/ns/1.0">
              <text><body>
                <div xml:id="x"/>
              </body></text>
            </TEI>
        """)
    )
    s = parse_sections(host)[0]
    assert s.heading is None


def test_unknown_div_type_resets_to_none():
    host = _parse_host(
        textwrap.dedent("""
            <TEI xmlns="http://www.tei-c.org/ns/1.0">
              <text><body>
                <div xml:id="x" type="some-other-type"><head>X</head></div>
              </body></text>
            </TEI>
        """)
    )
    assert parse_sections(host)[0].type is None


def test_known_div_types_pass_through():
    host = _parse_host(
        textwrap.dedent("""
            <TEI xmlns="http://www.tei-c.org/ns/1.0">
              <text><body>
                <div type="abstract"/>
                <div type="bibliography"/>
                <div type="appendix"/>
              </body></text>
            </TEI>
        """)
    )
    sections = parse_sections(host)
    assert [s.type for s in sections] == ["abstract", "bibliography", "appendix"]


def test_nesting_beyond_three_raises():
    host = _parse_host(
        textwrap.dedent("""
            <TEI xmlns="http://www.tei-c.org/ns/1.0">
              <text><body>
                <div><div><div><div xml:id="too-deep"/></div></div></div>
              </body></text>
            </TEI>
        """)
    )
    with pytest.raises(ValueError, match="nesting exceeds 3"):
        parse_sections(host)


# -- Edge cases -----------------------------------------------------------


def test_no_back_returns_empty_tuple():
    """One of the seven no-back reviews: parse_sections(None) yields ()."""
    assert parse_sections(None) == ()


def test_empty_body_yields_empty_tuple():
    host = _parse_host(
        textwrap.dedent("""
            <TEI xmlns="http://www.tei-c.org/ns/1.0">
              <text><body/></text>
            </TEI>
        """)
    )
    assert parse_sections(host) == ()


# -- Real-corpus smoke test ----------------------------------------------


_RIDE = Path(__file__).resolve().parent.parent.parent / "ride" / "tei_all"


@pytest.mark.skipif(not _RIDE.exists(), reason="../ride/ corpus not present")
def test_smoke_real_corpus_one_sample_review() -> None:
    """Parse one real review's <body> through parse_sections — must not raise."""
    sample = next(iter(sorted(_RIDE.glob("*-tei.xml"))))
    tree = etree.parse(str(sample))
    body = tree.getroot().find(f"{{{TEI}}}text/{{{TEI}}}body")
    sections = parse_sections(body)
    # Most reviews have at least one top-level div in body
    assert isinstance(sections, tuple)
    for s in sections:
        assert isinstance(s, Section)
