"""Tests for the top-level ``parse_review`` entry point.

Synthetic-TEI cases pin the wiring (front/body/back populated, figures
and notes aggregates produced); a corpus-wide smoke test confirms
end-to-end parsing of all 107 reviews without raising.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from lxml import etree

from src.model.block import Figure, Paragraph
from src.model.inline import Note
from src.model.review import Review
from src.parser.aggregate import collect_figures, collect_notes
from src.parser.review import parse_review


_RIDE = Path(__file__).resolve().parent.parent.parent / "ride" / "tei_all"


def _write_synth_tei(tmp_path: Path, body_xml: str) -> Path:
    """Wrap ``body_xml`` in a minimal valid RIDE-shaped TEI file and return its path."""
    full = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<TEI xmlns="http://www.tei-c.org/ns/1.0" '
        'xmlns:xml="http://www.w3.org/XML/1998/namespace" '
        'xml:id="ride.test.1">\n'
        '  <teiHeader>\n'
        '    <fileDesc>\n'
        '      <titleStmt><title>Test review</title></titleStmt>\n'
        '      <publicationStmt>\n'
        '        <date when="2026-01-01">2026</date>\n'
        '        <availability>'
        '<licence target="https://creativecommons.org/licenses/by/4.0/"/>'
        '</availability>\n'
        '      </publicationStmt>\n'
        '      <seriesStmt><biblScope unit="issue" n="99"/></seriesStmt>\n'
        '      <sourceDesc><p>Source.</p></sourceDesc>\n'
        '    </fileDesc>\n'
        '    <profileDesc>\n'
        '      <langUsage><language ident="en"/></langUsage>\n'
        '    </profileDesc>\n'
        '  </teiHeader>\n'
        '  <text>\n'
        f'    <body>{body_xml}</body>\n'
        '  </text>\n'
        '</TEI>\n'
    )
    p = tmp_path / "synth-tei.xml"
    p.write_text(full, encoding="utf-8")
    return p


# -- Wiring ---------------------------------------------------------------


def test_parse_review_populates_body_sections(tmp_path):
    path = _write_synth_tei(tmp_path, """
        <div xml:id="d1" type="abstract"><head>Abstract</head><p>Short.</p></div>
        <div xml:id="d2"><head>Main</head><p>Body paragraph.</p></div>
    """)
    review = parse_review(path)
    assert isinstance(review, Review)
    assert review.id == "ride.test.1"
    assert review.issue == "99"
    assert len(review.body) == 2
    assert review.body[0].xml_id == "d1"
    assert review.body[0].type == "abstract"
    assert isinstance(review.body[0].blocks[0], Paragraph)


def test_parse_review_aggregates_figures_in_document_order(tmp_path):
    path = _write_synth_tei(tmp_path, """
        <div xml:id="d1"><head>One</head>
          <figure xml:id="fig.a"><head>A</head><graphic url="a.png"/></figure>
          <p>Text.</p>
          <figure xml:id="fig.b"><head>B</head><graphic url="b.png"/></figure>
        </div>
        <div xml:id="d2"><head>Two</head>
          <figure xml:id="fig.c"><head>C</head><graphic url="c.png"/></figure>
        </div>
    """)
    review = parse_review(path)
    assert len(review.figures) == 3
    assert [f.xml_id for f in review.figures] == ["fig.a", "fig.b", "fig.c"]


def test_parse_review_aggregates_figures_inside_table_cells(tmp_path):
    """The cell-figure pattern (22 corpus occurrences) must reach the aggregate."""
    path = _write_synth_tei(tmp_path, """
        <div xml:id="d1"><head>X</head>
          <table>
            <row><cell><figure xml:id="cell.fig"><graphic url="x.png"/></figure></cell></row>
          </table>
        </div>
    """)
    review = parse_review(path)
    assert len(review.figures) == 1
    assert review.figures[0].xml_id == "cell.fig"


def test_parse_review_aggregates_notes_in_document_order(tmp_path):
    path = _write_synth_tei(tmp_path, """
        <div xml:id="d1"><head>One</head>
          <p>Text<note xml:id="ftn1">First note.</note> more.</p>
          <p>Other<note xml:id="ftn2">Second.</note> text.</p>
        </div>
    """)
    review = parse_review(path)
    assert len(review.notes) == 2
    assert [n.xml_id for n in review.notes] == ["ftn1", "ftn2"]


def test_parse_review_no_back_yields_empty_back(tmp_path):
    """Seven corpus reviews have no <back>; the field stays an empty tuple."""
    path = _write_synth_tei(tmp_path, """
        <div xml:id="d1"><head>X</head><p>x</p></div>
    """)
    review = parse_review(path)
    assert review.back == ()


# -- Real-corpus smoke ----------------------------------------------------


@pytest.mark.skipif(not _RIDE.exists(), reason="../ride/ corpus not present")
def test_smoke_real_corpus_all_reviews_parse_through_parse_review() -> None:
    """End-to-end Stage 2.B closure: every review file parses through
    ``parse_review`` without raising, and every review has at least one
    body section. The aggregates may be empty (some reviews carry no
    figures or no notes) but the structure must be valid."""
    files = sorted(_RIDE.glob("*-tei.xml"))
    assert len(files) >= 100
    figure_count_total = 0
    note_count_total = 0
    for f in files:
        review = parse_review(f)
        assert isinstance(review, Review)
        assert review.id  # every review has an xml:id
        assert review.body, f"empty body in {f.name}"
        figure_count_total += len(review.figures)
        note_count_total += len(review.notes)
    # Inventory says 874 figures, 1926 notes corpus-wide.
    # The aggregates must reach roughly that magnitude.
    assert figure_count_total >= 800
    assert note_count_total >= 1800
