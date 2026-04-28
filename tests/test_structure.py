"""Tests for scripts/structure.py."""
from __future__ import annotations

from pathlib import Path

import pytest

import structure

# Two minimal TEI files exercising sibling order, leaves, and nesting.
FIXTURE_A = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader><fileDesc><titleStmt><title>A</title></titleStmt>
    <publicationStmt><p>x</p></publicationStmt>
    <sourceDesc><p>x</p></sourceDesc></fileDesc></teiHeader>
  <text><body>
    <div xml:id="d1"><head>One</head><p>a</p><p>b</p></div>
    <div xml:id="d2"><head>Two</head><p>c</p></div>
  </body></text>
</TEI>
"""

FIXTURE_B = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader><fileDesc><titleStmt><title>B</title></titleStmt>
    <publicationStmt><p>x</p></publicationStmt>
    <sourceDesc><p>x</p></sourceDesc></fileDesc></teiHeader>
  <text><body>
    <div xml:id="d1"><head>X</head><p>a</p><p>b</p></div>
  </body></text>
</TEI>
"""


@pytest.fixture
def fixture_corpus(tmp_path: Path) -> tuple[Path, Path]:
    tei_dir = tmp_path / "tei"
    out_dir = tmp_path / "out"
    tei_dir.mkdir()
    (tei_dir / "a-tei.xml").write_text(FIXTURE_A, encoding="utf-8")
    (tei_dir / "b-tei.xml").write_text(FIXTURE_B, encoding="utf-8")
    return tei_dir, out_dir


def test_run_writes_structure_json(fixture_corpus: tuple[Path, Path]) -> None:
    tei_dir, out_dir = fixture_corpus
    structure.run(tei_dir, out_dir)
    assert (out_dir / "structure.json").is_file()


def test_div_children_sequences(fixture_corpus: tuple[Path, Path]) -> None:
    tei_dir, out_dir = fixture_corpus
    payload = structure.run(tei_dir, out_dir)
    div = payload["by_element"]["div"]
    # 3 div total: 2 with [head,p,p], 1 with [head,p]
    assert div["count"] == 3
    seqs = {tuple(s["sequence"]): s["count"] for s in div["child_sequences"]}
    assert seqs[("head", "p", "p")] == 2
    assert seqs[("head", "p")] == 1
    # first child is always <head>
    assert dict(div["first_child"]) == {"head": 3}


def test_leaf_count_and_ancestors(fixture_corpus: tuple[Path, Path]) -> None:
    tei_dir, out_dir = fixture_corpus
    payload = structure.run(tei_dir, out_dir)
    p = payload["by_element"]["p"]
    # 5 <p> in body across both files (all leaves), plus 2 <p> in publicationStmt
    # and 2 in sourceDesc -> 9 total. All leaves.
    assert p["count"] == 9
    assert p["leaf_count"] == 9
    # body/div is the dominant ancestor path for body <p>s
    paths = dict(p["ancestor_paths"])
    assert "TEI/text/body/div" in paths


# Fixture with nested <div>s so first_child/last_child and recursive ancestor
# paths are exercised separately from the flat fixtures above.
NESTED_FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader><fileDesc><titleStmt><title>N</title></titleStmt>
    <publicationStmt><p>x</p></publicationStmt>
    <sourceDesc><p>x</p></sourceDesc></fileDesc></teiHeader>
  <text><body>
    <div xml:id="outer">
      <head>Outer</head>
      <div xml:id="inner1"><head>Inner 1</head><p>a</p></div>
      <div xml:id="inner2"><head>Inner 2</head><p>b</p></div>
    </div>
  </body></text>
</TEI>
"""


def test_first_last_child_and_nested_div_paths(tmp_path: Path) -> None:
    """Nested <div>s contribute distinct ancestor paths; first/last child reflect order."""
    tei_dir = tmp_path / "tei"
    out_dir = tmp_path / "out"
    tei_dir.mkdir()
    (tei_dir / "n-tei.xml").write_text(NESTED_FIXTURE, encoding="utf-8")
    payload = structure.run(tei_dir, out_dir)

    div = payload["by_element"]["div"]
    # 3 divs total: 1 outer + 2 inner.
    assert div["count"] == 3

    # The outer div's first child is <head>, last is the second nested <div>.
    # Aggregated across all three divs, first_child Counter has both <head>
    # (for inner1, inner2) and <head> again for outer = 3 total.
    assert dict(div["first_child"]) == {"head": 3}
    # last_child: outer ends with <div>, inner1/inner2 each end with <p>.
    assert dict(div["last_child"]) == {"p": 2, "div": 1}

    # Ancestor paths now include both the body level (outer) and a nested div level.
    paths = dict(div["ancestor_paths"])
    assert "TEI/text/body" in paths       # for outer div
    assert "TEI/text/body/div" in paths   # for inner1 + inner2
