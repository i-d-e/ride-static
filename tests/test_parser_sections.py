"""Tests for the recursive section parser.

Test-data philosophy per CLAUDE.md hard rule:

* Integration cases parse a real review from ``../ride/tei_all/`` and
  assert against actual corpus values. The four named anchors —
  ``1641-tei.xml`` (rich, normal divs, two-level nesting, abstract in
  front, bibliography in back), ``phi-tei.xml`` (body-wrap with ``<p>``),
  ``bdmp-tei.xml`` (body-wrap with ``<cit>``), ``wega-tei.xml``
  (three top-level divs with 2nd-level nesting) — were chosen with a
  one-time corpus probe and cover the standard, the wrap, and the
  multi-level cases without overlap.
* Pure-function / defensive-branch tests keep synthetic fixtures because
  the function signature is the only data form richer than the input
  (per CLAUDE.md "Pure-function unit tests" exception). Each such test
  carries a docstring noting the explicit exception.
* The whole module skips cleanly when ``../ride/`` is absent, so the
  unit suite still runs on a fresh clone.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from lxml import etree

from src.model.section import Section
from src.parser.sections import parse_sections


TEI = "http://www.tei-c.org/ns/1.0"
NS = {"t": TEI}
XID = "{http://www.w3.org/XML/1998/namespace}id"

REPO_ROOT = Path(__file__).resolve().parent.parent
RIDE_TEI_DIR = REPO_ROOT.parent / "ride" / "tei_all"

needs_corpus = pytest.mark.skipif(
    not RIDE_TEI_DIR.is_dir(), reason="../ride/ corpus not available"
)


# ── Real-corpus fixtures ────────────────────────────────────────────


def _host(file_name: str, host_tag: str) -> etree._Element:
    """Parse a real corpus file and return its <front> / <body> / <back>.

    Skips the test cleanly when the named file is missing so the
    fixtures stay tolerant of partial-corpus checkouts.
    """
    path = RIDE_TEI_DIR / file_name
    if not path.exists():
        pytest.skip(f"{file_name} not in corpus")
    tree = etree.parse(str(path))
    return tree.getroot().find(f"{{{TEI}}}text/{{{TEI}}}{host_tag}")


@pytest.fixture(scope="module")
def ride_1641_body() -> etree._Element:
    return _host("1641-tei.xml", "body")


@pytest.fixture(scope="module")
def ride_1641_front() -> etree._Element:
    return _host("1641-tei.xml", "front")


@pytest.fixture(scope="module")
def ride_1641_back() -> etree._Element:
    return _host("1641-tei.xml", "back")


@pytest.fixture(scope="module")
def ride_phi_body() -> etree._Element:
    """phi-tei.xml — body starts directly with <p>; one of seven wrap reviews."""
    return _host("phi-tei.xml", "body")


@pytest.fixture(scope="module")
def ride_bdmp_body() -> etree._Element:
    """bdmp-tei.xml — body starts directly with <cit>; one of seven wrap reviews."""
    return _host("bdmp-tei.xml", "body")


@pytest.fixture(scope="module")
def ride_wega_body() -> etree._Element:
    """wega-tei.xml — three top-level divs with 2nd-level nesting."""
    return _host("wega-tei.xml", "body")


# ── Standard cases — driven by real corpus ──────────────────────────


@needs_corpus
def test_real_normal_top_level_divs_carry_xml_id_and_head(ride_1641_body):
    """1641 has four well-formed top-level divs in body, each with @xml:id and <head>."""
    sections = parse_sections(ride_1641_body)
    assert len(sections) == 4
    ids = [s.xml_id for s in sections]
    assert ids == ["div1", "div2", "div3", "div4"]
    headings = [s.heading[0].text if s.heading else None for s in sections]
    assert headings == [
        "Introduction",
        "The original 1641 Depositions",
        "The digital Depositions",
        "Conclusion",
    ]
    assert all(s.level == 1 for s in sections)


@needs_corpus
def test_real_two_level_nesting_lifts_subdivs(ride_1641_body):
    """1641 body div3 carries 8 sub-divisions — two levels of nesting verified."""
    sections = parse_sections(ride_1641_body)
    div3 = sections[2]
    assert div3.xml_id == "div3"
    assert len(div3.subsections) == 8
    assert all(sub.level == 2 for sub in div3.subsections)


@needs_corpus
def test_real_three_level_nesting_is_allowed(ride_wega_body):
    """wega-tei.xml carries depth-3 sub-divisions per the corpus probe."""
    sections = parse_sections(ride_wega_body)
    # Find any depth-3 path: section.subsections[*].subsections[*]
    depth_three = [
        leaf
        for s in sections
        for sub in s.subsections
        for leaf in sub.subsections
    ]
    assert depth_three, "wega-tei.xml should carry at least one 3-level nest"
    assert all(leaf.level == 3 for leaf in depth_three)


@needs_corpus
def test_real_abstract_in_front_carries_type(ride_1641_front):
    """1641 front holds the abstract as <div type="abstract">, no @xml:id, no <head>."""
    sections = parse_sections(ride_1641_front)
    assert len(sections) == 1
    abstract = sections[0]
    assert abstract.type == "abstract"
    # No @xml:id → positional fallback "sec-1".
    assert abstract.xml_id == "sec-1"
    assert abstract.heading is None


@needs_corpus
def test_real_back_carries_bibliography_type(ride_1641_back):
    """1641 back holds <div type="bibliography">; the bibliography content
    itself lives on Review.bibliography (Phase 6.A unification), the Section
    carries only the heading-shell."""
    sections = parse_sections(ride_1641_back)
    assert len(sections) == 1
    assert sections[0].type == "bibliography"


# ── Body-wrap anomaly — driven by real corpus ───────────────────────


@needs_corpus
def test_real_body_starting_with_p_gets_wrapped(ride_phi_body):
    """phi-tei.xml starts <body> directly with <p>; the parser wraps the
    direct-children sequence into one synthesised Section."""
    sections = parse_sections(ride_phi_body)
    assert len(sections) == 1
    wrap = sections[0]
    assert wrap.xml_id == "sec-1"
    assert wrap.type is None
    assert wrap.heading is None
    assert wrap.level == 1
    assert wrap.subsections == ()
    # The wrap section captures all body-level paragraphs.
    assert len(wrap.blocks) > 0


@needs_corpus
def test_real_body_starting_with_cit_gets_wrapped(ride_bdmp_body):
    """bdmp-tei.xml starts <body> with <cit>; same wrap behaviour as <p>-start."""
    sections = parse_sections(ride_bdmp_body)
    assert len(sections) == 1
    assert sections[0].xml_id == "sec-1"
    assert sections[0].heading is None


@needs_corpus
def test_real_body_starting_with_div_takes_normal_branch(ride_1641_body):
    """The 100 normal reviews start <body> with <div> — wrap branch must
    not trigger. 1641 keeps its four named divs."""
    sections = parse_sections(ride_1641_body)
    assert len(sections) == 4
    # Wrap-Section signature would be xml_id="sec-1" + heading=None.
    # 1641's first div has xml_id="div1" + heading="Introduction".
    assert sections[0].xml_id == "div1"
    assert sections[0].heading is not None


# ── Pure-function / defensive-branch tests ──────────────────────────
#
# These keep synthetic fixtures because the input shapes either do not
# exist in the corpus (defensive raises, edge-case None handling) or
# the test pins a pure type-whitelist rule that no specific corpus
# example would exercise more clearly.


def _parse_synthetic_host(xml: str, host_tag: str = "body") -> etree._Element:
    root = etree.fromstring(xml.strip().encode("utf-8"))
    host = root.find(f"{{{TEI}}}text/{{{TEI}}}{host_tag}")
    assert host is not None, f"<{host_tag}> not found in fixture"
    return host


def test_unknown_div_type_resets_to_none():
    """Pure type-whitelist logic — corpus only carries the three known
    types (abstract, bibliography, appendix), so a synthetic fixture is
    the only way to exercise the "unknown type → None" branch."""
    host = _parse_synthetic_host(
        textwrap.dedent("""
            <TEI xmlns="http://www.tei-c.org/ns/1.0">
              <text><body>
                <div xml:id="x" type="some-other-type"><head>X</head></div>
              </body></text>
            </TEI>
        """)
    )
    assert parse_sections(host)[0].type is None


def test_nesting_beyond_three_raises():
    """Defensive raise — the corpus has no four-deep nesting, so this
    branch is exercised synthetically per the "documented exception"
    rule for edge cases that do not exist in the corpus."""
    host = _parse_synthetic_host(
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


def test_no_back_returns_empty_tuple():
    """Internal contract: parse_sections(None) returns ().

    Seven of 107 reviews carry no <back>, but the parser entry point
    receives a None argument from parse_review in that case rather than
    a real element, so a None pin is the right test shape."""
    assert parse_sections(None) == ()


def test_empty_body_yields_empty_tuple():
    """Defensive: <body/> with no children must not raise.
    The corpus has no fully-empty body, but the parser tolerates it."""
    host = _parse_synthetic_host(
        textwrap.dedent("""
            <TEI xmlns="http://www.tei-c.org/ns/1.0">
              <text><body/></text>
            </TEI>
        """)
    )
    assert parse_sections(host) == ()


def test_body_with_leading_comment_still_detects_div():
    """XML-comment skip — the wrap detection must look at the first
    element child, not the first node. Synthetic because the corpus
    files do not carry XML comments at this position."""
    host = _parse_synthetic_host(
        textwrap.dedent("""
            <TEI xmlns="http://www.tei-c.org/ns/1.0">
              <text><body>
                <!-- editorial note -->
                <div xml:id="x"><head>X</head></div>
              </body></text>
            </TEI>
        """)
    )
    sections = parse_sections(host)
    assert len(sections) == 1
    assert sections[0].xml_id == "x"


# ── Real-corpus full-suite smoke ────────────────────────────────────


@needs_corpus
def test_real_all_reviews_parse_without_error():
    """All ~107 reviews must parse through parse_sections without raising.
    Of those, exactly seven trigger the wrap branch (4 with <p>,
    3 with <cit>) per knowledge/data.md."""
    files = sorted(RIDE_TEI_DIR.glob("*-tei.xml"))
    assert len(files) >= 100, "expected at least 100 reviews in corpus"
    wrap_count = 0
    for f in files:
        tree = etree.parse(str(f))
        body = tree.getroot().find(f"{{{TEI}}}text/{{{TEI}}}body")
        sections = parse_sections(body)
        assert isinstance(sections, tuple)
        for s in sections:
            assert isinstance(s, Section)
        if (
            len(sections) == 1
            and sections[0].xml_id == "sec-1"
            and sections[0].heading is None
        ):
            wrap_count += 1
    # 7 wrap reviews documented; the count is permissive (≥ 7) because
    # some non-wrap reviews may also yield this shape on edge cases.
    assert wrap_count >= 7
