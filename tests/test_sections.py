"""Tests for scripts/sections.py."""
from __future__ import annotations

from pathlib import Path

import pytest

import sections

FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader><fileDesc><titleStmt><title>S</title></titleStmt>
    <publicationStmt><p>x</p></publicationStmt>
    <sourceDesc><p>x</p></sourceDesc></fileDesc></teiHeader>
  <text>
    <front>
      <div type="abstract"><head>Abstract</head><p>a</p></div>
    </front>
    <body>
      <div xml:id="div1"><head>Intro</head>
        <div xml:id="div1.1"><head>Background</head><p>b</p></div>
        <div xml:id="div1.2"><head>Goal</head><p>c</p></div>
      </div>
      <div xml:id="div2"><p>no head here</p></div>
    </body>
    <back>
      <div type="bibliography"><head>References</head><listBibl><bibl>x</bibl></listBibl></div>
    </back>
  </text>
</TEI>
"""


@pytest.fixture
def fixture_corpus(tmp_path: Path) -> tuple[Path, Path]:
    tei_dir = tmp_path / "tei"
    out_dir = tmp_path / "out"
    tei_dir.mkdir()
    (tei_dir / "s-tei.xml").write_text(FIXTURE, encoding="utf-8")
    return tei_dir, out_dir


def test_run_writes_sections_json(fixture_corpus: tuple[Path, Path]) -> None:
    tei_dir, out_dir = fixture_corpus
    sections.run(tei_dir, out_dir)
    assert (out_dir / "sections.json").is_file()


def test_section_tree_shape(fixture_corpus: tuple[Path, Path]) -> None:
    tei_dir, out_dir = fixture_corpus
    payload = sections.run(tei_dir, out_dir)
    assert payload["file_count"] == 1
    f = payload["files"][0]
    assert len(f["front"]) == 1 and f["front"][0]["type"] == "abstract"
    assert len(f["body"]) == 2
    intro = f["body"][0]
    assert intro["xml_id"] == "div1"
    assert intro["head"] == "Intro"
    assert intro["depth"] == 1
    assert [c["xml_id"] for c in intro["children"]] == ["div1.1", "div1.2"]
    assert intro["children"][0]["depth"] == 2
    # div2 has no <head>, gets counted
    assert f["body"][1]["head"] is None
    assert payload["missing_head_count"] == 1
    # type distribution counts only divs with @type
    assert dict(payload["type_distribution"]) == {"abstract": 1, "bibliography": 1}
