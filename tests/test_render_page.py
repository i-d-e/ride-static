"""Tests for src.render.page — does the page model render to the right HTML?

Synthetic fixtures pin the HTML contract (heading levels, links, lists,
person links, line breaks, escaping); a real-corpus smoke renders
ethical-code end to end through editorial.html.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.parser.page import PAGES_DIR, parse_page
from src.render.page import render_page, render_page_body

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
      <editor role="managing">Ulrike Henny-Krahmer</editor>
      <editor role="managing">Martina Scholger</editor>
    </seriesStmt>
    <sourceDesc><p>born digital</p></sourceDesc>
  </fileDesc></teiHeader>
  <text><body>
    <p>Intro with a <ref target="https://example.org">link</ref> and <hi rend="italic">emphasis</hi>.</p>
    <div>
      <head>First Section</head>
      <p>Line one<lb/>line two and <persName ref="https://www.i-d-e.de/mitglieder/x">A Person</persName>.</p>
      <div>
        <head>Nested</head>
        <p>Mail <email>info (at) i-d-e (dot) de</email>.</p>
        <list><item>one</item><item>two</item></list>
      </div>
    </div>
  </body></text>
</TEI>
"""

ESCAPE_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader><fileDesc>
    <titleStmt><title>Esc</title></titleStmt>
    <publicationStmt><publisher>X</publisher></publicationStmt>
    <sourceDesc><p>born digital</p></sourceDesc>
  </fileDesc></teiHeader>
  <text><body><p>a &lt; b &amp; c</p></body></text>
</TEI>
"""


def _write(tmp_path: Path, xml: str, name: str = "s.xml") -> Path:
    p = tmp_path / name
    p.write_text(xml, encoding="utf-8")
    return p


def test_body_html_contract(tmp_path):
    html = render_page_body(parse_page(_write(tmp_path, SAMPLE)))
    assert "<h1>Sample Page</h1>" in html
    assert "<h2>First Section</h2>" in html
    assert "<h3>Nested</h3>" in html  # nesting deepens the heading level
    assert '<a href="https://example.org">link</a>' in html
    assert "<em>emphasis</em>" in html
    assert "<br/>" in html
    assert (
        '<a class="ride-persname" href="https://www.i-d-e.de/mitglieder/x">A Person</a>'
        in html
    )
    assert '<span class="ride-email">info (at) i-d-e (dot) de</span>' in html
    assert "<ul>" in html and "<li>one</li>" in html


def test_text_is_escaped(tmp_path):
    html = render_page_body(parse_page(_write(tmp_path, ESCAPE_SAMPLE)))
    assert "a &lt; b &amp; c" in html
    assert "a < b & c" not in html


CODE_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader><fileDesc>
    <titleStmt><title>Code</title></titleStmt>
    <publicationStmt><publisher>X</publisher></publicationStmt>
    <sourceDesc><p>born digital</p></sourceDesc>
  </fileDesc></teiHeader>
  <text><body>
    <p>Use <code>&lt;rs&gt;</code> and <code>@type</code>.</p>
    <eg><![CDATA[
<teiHeader>
    <fileDesc/>
</teiHeader>
]]></eg>
  </body></text>
</TEI>
"""


def test_code_renders_inline_and_block(tmp_path):
    html = render_page_body(parse_page(_write(tmp_path, CODE_SAMPLE)))
    assert "<code>&lt;rs&gt;</code>" in html
    assert "<code>@type</code>" in html
    # Block code escapes its angle brackets inside <pre><code>.
    assert "<pre><code>&lt;teiHeader&gt;\n    &lt;fileDesc/&gt;\n&lt;/teiHeader&gt;</code></pre>" in html


@needs_corpus
def test_render_ethical_code_full_page():
    page = parse_page(PAGES_DIR / "ethical-code.xml")
    html = render_page(page)
    assert "<html" in html  # full document via base.html
    assert "<h1>Ethical Code</h1>" in html
    assert "<h2>Editors’ responsibilities</h2>" in html
    assert '<a href="https://publicationethics.org/core-practices">' in html
    assert '<a href="mailto:ride-editors@i-d-e.de">ride-editors@i-d-e.de</a>' in html
    # the four complaint bullet points
    assert html.count("<li>") >= 4
