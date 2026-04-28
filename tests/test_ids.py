"""Tests for scripts/ids.py.

Note: lxml validates xml:id uniqueness at parse time, so the duplicate
case is exercised via the parse_errors output (the file never reaches
our scanner).
"""
from __future__ import annotations

from pathlib import Path

import pytest

import ids

CLEAN_FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="ride.5.7">
  <teiHeader><fileDesc>
    <titleStmt><title>Clean</title></titleStmt>
    <publicationStmt><p>x</p></publicationStmt>
    <sourceDesc><p>x</p></sourceDesc>
  </fileDesc></teiHeader>
  <text><body>
    <div xml:id="div1"><head>One</head><p xml:id="p1">a</p></div>
    <div xml:id="div2"><head>Two</head><p xml:id="p2">b</p></div>
    <div xml:id="div2.1"><head>Sub</head><p>c</p></div>
  </body></text>
</TEI>
"""

# Valid XML (unique IDs) but the values violate Schematron format patterns.
BAD_FORMAT_FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="not-the-right-format">
  <teiHeader><fileDesc>
    <titleStmt><title>Bad format</title></titleStmt>
    <publicationStmt><p>x</p></publicationStmt>
    <sourceDesc><p>x</p></sourceDesc>
  </fileDesc></teiHeader>
  <text><body>
    <div xml:id="invalid_div_name"><head>Bad</head></div>
    <div xml:id="div9"><head>Ok</head></div>
  </body></text>
</TEI>
"""

# Invalid XML — duplicate xml:id. lxml refuses to parse this; our scanner
# must surface it as a parse error rather than silently ignore it.
DUPLICATE_ID_FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="ride.1.1">
  <teiHeader><fileDesc>
    <titleStmt><title>Dup</title></titleStmt>
    <publicationStmt><p>x</p></publicationStmt>
    <sourceDesc><p>x</p></sourceDesc>
  </fileDesc></teiHeader>
  <text><body>
    <div xml:id="dup"><head>One</head></div>
    <div xml:id="dup"><head>Two</head></div>
  </body></text>
</TEI>
"""


@pytest.fixture
def fixture_corpus(tmp_path: Path) -> tuple[Path, Path]:
    tei = tmp_path / "tei"
    out = tmp_path / "out"
    tei.mkdir()
    (tei / "clean-tei.xml").write_text(CLEAN_FIXTURE, encoding="utf-8")
    (tei / "bad-format-tei.xml").write_text(BAD_FORMAT_FIXTURE, encoding="utf-8")
    (tei / "dup-tei.xml").write_text(DUPLICATE_ID_FIXTURE, encoding="utf-8")
    return tei, out


def test_writes_ids_json(fixture_corpus: tuple[Path, Path]) -> None:
    tei, out = fixture_corpus
    ids.run(tei, out)
    assert (out / "ids.json").is_file()


def test_clean_file_has_no_violations(fixture_corpus: tuple[Path, Path]) -> None:
    tei, out = fixture_corpus
    payload = ids.run(tei, out)
    clean = next(f for f in payload["per_file"] if f["file"] == "clean-tei.xml")
    assert clean["format_violations"] == []
    # 1 TEI + 3 div + 2 p = 6 ids
    assert clean["ids_total"] == 6


def test_format_violations_detected(fixture_corpus: tuple[Path, Path]) -> None:
    tei, out = fixture_corpus
    payload = ids.run(tei, out)
    bad = next(f for f in payload["per_file"] if f["file"] == "bad-format-tei.xml")
    violations = {(v["element"], v["id"]) for v in bad["format_violations"]}
    # TEI/@xml:id="not-the-right-format" violates `^ride\.\d{1,2}\.\d{1,2}$`
    # div/@xml:id="invalid_div_name" violates `^div\d{1,2}(\.\d{1,2}){0,2}$`
    # div/@xml:id="div9" is valid
    assert ("TEI", "not-the-right-format") in violations
    assert ("div", "invalid_div_name") in violations
    assert ("div", "div9") not in violations


def test_duplicate_id_surfaces_as_parse_error(fixture_corpus: tuple[Path, Path]) -> None:
    """Duplicate xml:id is rejected by libxml2 at parse time; we must record
    that fact so the user knows the file was never scanned."""
    tei, out = fixture_corpus
    payload = ids.run(tei, out)
    parse_errors = {e["file"] for e in payload["parse_errors"]}
    assert parse_errors == {"dup-tei.xml"}
    # The unparseable file does not contribute to per_file
    files_in_per_file = {f["file"] for f in payload["per_file"]}
    assert "dup-tei.xml" not in files_in_per_file


def test_summary_aggregates(fixture_corpus: tuple[Path, Path]) -> None:
    tei, out = fixture_corpus
    payload = ids.run(tei, out)
    s = payload["summary"]
    # 2 parseable files (clean + bad-format), 1 unparseable (dup).
    assert s["files_total"] == 2
    assert s["files_unparseable"] == 1
    assert s["files_with_format_violations"] == 1  # only bad-format
    assert s["violations_by_element"]["div"] == 1
    assert s["violations_by_element"]["TEI"] == 1
    # Pattern set must be reported so consumers know what was checked.
    assert "TEI" in s["patterns_checked"]
    assert "div" in s["patterns_checked"]
