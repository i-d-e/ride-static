"""Tests for src.parser.page — do the page data arrive correctly?

Two layers:

1. Synthetic TEI (a temp file) for deterministic structure: header
   metadata, block nesting, inline order, Lb/PersName/Email/Ref/Hi.
2. Real-corpus checks on pages/*.xml for the actual content shape.

Tests assert the parsed domain model, not rendered HTML — the point is
that the data is extracted faithfully before anything is rendered.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.model.page import (
    BulletList,
    Code,
    CodeBlock,
    Email,
    Hi,
    Lb,
    Para,
    PersName,
    Ref,
    Section,
    Table,
    inline_text,
    page_text,
)
from src.parser.page import PAGES_DIR, discover_pages, parse_page

needs_corpus = pytest.mark.skipif(
    not PAGES_DIR.is_dir() or not any(PAGES_DIR.glob("*.xml")),
    reason="page corpus not present",
)


SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader><fileDesc>
    <titleStmt><title>Sample Page</title></titleStmt>
    <publicationStmt>
      <publisher>Institut für Dokumentologie und Editorik e.V.</publisher>
      <idno type="URI">https://ride.i-d-e.de/sample/</idno>
      <availability><licence target="http://creativecommons.org/licenses/by/4.0/"/></availability>
    </publicationStmt>
    <seriesStmt>
      <title level="j">RIDE - A review journal for digital editions and resources</title>
      <editor role="managing" ref="https://orcid.org/0000-0003-2852-065X">Ulrike Henny-Krahmer</editor>
      <editor role="managing" ref="https://orcid.org/0000-0003-1438-3236">Martina Scholger</editor>
    </seriesStmt>
    <sourceDesc><p>born digital</p></sourceDesc>
  </fileDesc></teiHeader>
  <text><body>
    <p>Intro with a <ref target="https://example.org">link</ref> and <hi rend="italic">emphasis</hi>.</p>
    <div>
      <head>First Section</head>
      <p>Body sentence with a break<lb/>second line and <persName ref="https://www.i-d-e.de/mitglieder/x">A Person</persName>.</p>
      <div>
        <head>Nested</head>
        <p>Reach us at <email>info (at) i-d-e (dot) de</email>.</p>
        <list><item>one</item><item>two</item><item>three</item></list>
      </div>
    </div>
  </body></text>
</TEI>
"""


def _write(tmp_path: Path, xml: str) -> Path:
    p = tmp_path / "sample.xml"
    p.write_text(xml, encoding="utf-8")
    return p


def _walk_inlines(page) -> list:
    out: list = []

    def inl(nodes):
        for n in nodes:
            out.append(n)
            if isinstance(n, (Ref, Hi)):
                inl(n.children)

    def blk(b):
        if isinstance(b, Section):
            inl(b.head)
            for c in b.blocks:
                blk(c)
        elif isinstance(b, Para):
            inl(b.inlines)
        elif isinstance(b, BulletList):
            for it in b.items:
                inl(it.inlines)
        elif isinstance(b, Table):
            for r in b.rows:
                for c in r.cells:
                    inl(c.inlines)

    for b in page.blocks:
        blk(b)
    return out


# ── Synthetic structure ───────────────────────────────────────────────


def test_header_metadata(tmp_path):
    page = parse_page(_write(tmp_path, SAMPLE))
    assert page.title == "Sample Page"
    assert page.source_url == "https://ride.i-d-e.de/sample/"
    assert page.licence == "http://creativecommons.org/licenses/by/4.0/"
    assert page.journal_title.startswith("RIDE")
    assert len(page.editors) == 2
    assert page.editors[0].name == "Ulrike Henny-Krahmer"
    assert page.editors[0].role == "managing"
    assert page.editors[0].ref.endswith("0000-0003-2852-065X")


def test_body_structure(tmp_path):
    page = parse_page(_write(tmp_path, SAMPLE))
    # Top level: a lead Para, then one Section.
    assert isinstance(page.blocks[0], Para)
    assert isinstance(page.blocks[1], Section)

    lead = page.blocks[0]
    assert isinstance(lead.inlines[1], Ref)
    assert lead.inlines[1].target == "https://example.org"
    assert inline_text((lead.inlines[1],)) == "link"
    assert any(isinstance(n, Hi) and n.rend == "italic" for n in lead.inlines)

    sec = page.blocks[1]
    assert inline_text(sec.head) == "First Section"
    assert isinstance(sec.blocks[0], Para)
    assert isinstance(sec.blocks[1], Section)

    para = sec.blocks[0]
    assert any(isinstance(n, Lb) for n in para.inlines)
    pers = [n for n in para.inlines if isinstance(n, PersName)][0]
    assert pers.name == "A Person"
    assert pers.ref.endswith("/mitglieder/x")

    nested = sec.blocks[1]
    assert inline_text(nested.head) == "Nested"
    assert any(
        isinstance(n, Email)
        for b in nested.blocks
        if isinstance(b, Para)
        for n in b.inlines
    )
    blist = [b for b in nested.blocks if isinstance(b, BulletList)][0]
    assert len(blist.items) == 3
    assert inline_text(blist.items[0].inlines) == "one"


def test_lb_contributes_no_text(tmp_path):
    page = parse_page(_write(tmp_path, SAMPLE))
    # The line break joins the two lines without inserting a space.
    assert "breaksecond line" in page_text(page)


SAMPLE_CODE = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader><fileDesc>
    <titleStmt><title>Code Page</title></titleStmt>
    <publicationStmt><publisher>X</publisher></publicationStmt>
    <sourceDesc><p>born digital</p></sourceDesc>
  </fileDesc></teiHeader>
  <text><body>
    <p>Encode with <code>&lt;rs&gt;</code> and <code>@type</code>.</p>
    <eg><![CDATA[
<teiHeader>
    <fileDesc/>
</teiHeader>
]]></eg>
    <p>Code 1: TEI Header.</p>
  </body></text>
</TEI>
"""


def test_code_inline_and_block(tmp_path):
    page = parse_page(_write(tmp_path, SAMPLE_CODE))
    # Inline <code> mentions in the lead paragraph, verbatim.
    lead = page.blocks[0]
    codes = [n for n in lead.inlines if isinstance(n, Code)]
    assert [c.value for c in codes] == ["<rs>", "@type"]
    # Block <eg>: dedented, surrounding newlines trimmed, inner layout kept.
    cb = page.blocks[1]
    assert isinstance(cb, CodeBlock)
    assert cb.text == "<teiHeader>\n    <fileDesc/>\n</teiHeader>"
    # The caption is the following paragraph, not part of the code block.
    assert isinstance(page.blocks[2], Para)
    assert inline_text(page.blocks[2].inlines) == "Code 1: TEI Header."
    # Code text reaches the text projection (fidelity checks see it).
    assert "<teiHeader>" in page_text(page)


# ── Real corpus ───────────────────────────────────────────────────────


@needs_corpus
def test_corpus_loads():
    pages = discover_pages()
    slugs = {p.slug for p in pages}
    assert {"about/ethical-code", "about/team", "about/editorial", "imprint", "data"} <= slugs
    assert len(pages) >= 13
    for p in pages:
        assert p.title
        assert p.source_url and p.source_url.startswith("https://ride.i-d-e.de/")
        assert p.licence == "http://creativecommons.org/licenses/by/4.0/"
        assert p.journal_title and p.journal_title.startswith("RIDE")
        assert len(p.editors) == 2


@needs_corpus
def test_ethical_code_metadata():
    page = parse_page(PAGES_DIR / "about" / "ethical-code.xml")
    assert page.title == "Ethical Code"
    assert page.source_url == "https://ride.i-d-e.de/ethical-code/"
    assert [e.name for e in page.editors] == [
        "Ulrike Henny-Krahmer",
        "Martina Scholger",
    ]


@needs_corpus
def test_ethical_code_structure():
    page = parse_page(PAGES_DIR / "about" / "ethical-code.xml")
    assert isinstance(page.blocks[0], Para)  # lead paragraph
    sections = [b for b in page.blocks if isinstance(b, Section)]
    heads = [inline_text(s.head) for s in sections]
    assert "Editors’ responsibilities" in heads
    assert "Peer Reviewers’ responsibilities" in heads

    lead = page.blocks[0]
    targets = [n.target for n in lead.inlines if isinstance(n, Ref)]
    assert "https://publicationethics.org/core-practices" in targets

    editors_sec = [
        s for s in sections if inline_text(s.head) == "Editors’ responsibilities"
    ][0]
    nested = [b for b in editors_sec.blocks if isinstance(b, Section)]
    alleg = [
        s for s in nested if inline_text(s.head) == "Allegations of misconduct"
    ][0]
    blist = [b for b in alleg.blocks if isinstance(b, BulletList)][0]
    assert len(blist.items) == 4
    mailtos = [
        n.target
        for b in alleg.blocks
        if isinstance(b, Para)
        for n in b.inlines
        if isinstance(n, Ref)
    ]
    assert "mailto:ride-editors@i-d-e.de" in mailtos


@needs_corpus
def test_team_has_linked_persons_and_email():
    page = parse_page(PAGES_DIR / "about" / "team.xml")
    inlines = _walk_inlines(page)
    persnames = [n for n in inlines if isinstance(n, PersName)]
    assert persnames
    assert any(p.ref and "i-d-e.de/mitglieder" in p.ref for p in persnames)
    assert any(isinstance(n, Email) for n in inlines)
