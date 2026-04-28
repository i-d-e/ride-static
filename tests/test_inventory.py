"""Tests for scripts/inventory.py.

Uses a synthetic minimal TEI fixture so the test is fast, deterministic,
and independent of the real corpus.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import inventory

TEI_NS = "http://www.tei-c.org/ns/1.0"

FIXTURE_TEI = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:lang="en">
  <teiHeader>
    <fileDesc>
      <titleStmt><title>Sample review</title></titleStmt>
      <publicationStmt>
        <date when="2024-06-15">June 2024</date>
        <availability><licence target="https://creativecommons.org/licenses/by/4.0/">CC-BY-4.0</licence></availability>
      </publicationStmt>
      <seriesStmt>
        <biblScope n="42"/>
        <editor ref="https://orcid.org/0000-0000-0000-0001"/>
      </seriesStmt>
      <sourceDesc><p>Born digital.</p></sourceDesc>
    </fileDesc>
    <profileDesc>
      <langUsage><language ident="en">English</language></langUsage>
    </profileDesc>
  </teiHeader>
  <text>
    <front>
      <div type="abstract"><head>Abstract</head><p>Short abstract.</p></div>
    </front>
    <body>
      <div xml:id="div1"><head>Intro</head><p>First paragraph with <ref type="external">a link</ref>.</p></div>
      <div xml:id="div2"><head>Findings</head><p>Second paragraph.</p></div>
    </body>
    <back>
      <div type="bibliography"><head>References</head><listBibl><bibl>Item.</bibl></listBibl></div>
    </back>
  </text>
</TEI>
"""


@pytest.fixture
def fixture_corpus(tmp_path: Path) -> tuple[Path, Path]:
    tei_dir = tmp_path / "tei"
    out_dir = tmp_path / "out"
    tei_dir.mkdir()
    (tei_dir / "sample-tei.xml").write_text(FIXTURE_TEI, encoding="utf-8")
    return tei_dir, out_dir


def test_run_writes_three_outputs(fixture_corpus: tuple[Path, Path]) -> None:
    tei_dir, out_dir = fixture_corpus
    inventory.run(tei_dir, out_dir)
    for name in ("elements.json", "attributes.json", "corpus-stats.json"):
        assert (out_dir / name).is_file(), f"missing {name}"


def test_corpus_stats_basics(fixture_corpus: tuple[Path, Path]) -> None:
    tei_dir, out_dir = fixture_corpus
    stats = inventory.run(tei_dir, out_dir)
    assert stats["files_total"] == 1
    assert stats["distinct_elements"] >= 10
    assert stats["review_languages"] == [("en", 1)]
    assert stats["publication_dates_min"] == "2024-06-15"
    assert stats["distinct_editors"] == 1
    assert stats["licences"][0][0] == "https://creativecommons.org/licenses/by/4.0/"


def test_div_has_presence_ratio_and_full_type_values(fixture_corpus: tuple[Path, Path]) -> None:
    tei_dir, out_dir = fixture_corpus
    inventory.run(tei_dir, out_dir)
    elements = json.loads((out_dir / "elements.json").read_text(encoding="utf-8"))
    div = next(e for e in elements if e["name"] == "div")
    # 4 <div> total, 2 carry @type ("abstract", "bibliography")
    assert div["count"] == 4
    type_attr = div["attributes"]["type"]
    assert type_attr["count"] == 2
    assert type_attr["presence_ratio"] == 0.5
    assert type_attr["values_complete"] is True
    type_values = {v for v, _ in type_attr["values"]}
    assert type_values == {"abstract", "bibliography"}


def test_non_structuring_attribute_is_capped(fixture_corpus: tuple[Path, Path]) -> None:
    tei_dir, out_dir = fixture_corpus
    inventory.run(tei_dir, out_dir)
    elements = json.loads((out_dir / "elements.json").read_text(encoding="utf-8"))
    div = next(e for e in elements if e["name"] == "div")
    xml_id = div["attributes"]["xml:id"]
    assert xml_id["values_complete"] is False
    # Cap is 10; we only have 2 values so not actually truncated, but the flag matters.
    assert len(xml_id["values"]) <= 10


# Second small file to exercise cross-file aggregation. Uses the same elements
# but a different language and different attribute values, so we can prove the
# inventory really sums across files instead of overwriting.
FIXTURE_TEI_DE = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:lang="de">
  <teiHeader>
    <fileDesc>
      <titleStmt><title>Zweite Rezension</title></titleStmt>
      <publicationStmt>
        <date when="2025-03-01">März 2025</date>
        <availability><licence target="https://creativecommons.org/licenses/by/4.0/">CC-BY-4.0</licence></availability>
      </publicationStmt>
      <seriesStmt>
        <biblScope n="43"/>
        <editor ref="https://orcid.org/0000-0000-0000-0002"/>
      </seriesStmt>
      <sourceDesc><p>Born digital.</p></sourceDesc>
    </fileDesc>
    <profileDesc>
      <langUsage><language ident="de">German</language></langUsage>
    </profileDesc>
  </teiHeader>
  <text>
    <body>
      <div xml:id="div1"><head>Einleitung</head><p>Text.</p></div>
    </body>
  </text>
</TEI>
"""


def test_aggregates_across_multiple_files(tmp_path: Path) -> None:
    """Counters must sum across files; languages and editors must accumulate."""
    tei_dir = tmp_path / "tei"
    out_dir = tmp_path / "out"
    tei_dir.mkdir()
    (tei_dir / "a-tei.xml").write_text(FIXTURE_TEI, encoding="utf-8")
    (tei_dir / "b-tei.xml").write_text(FIXTURE_TEI_DE, encoding="utf-8")

    stats = inventory.run(tei_dir, out_dir)
    assert stats["files_total"] == 2
    # Languages from <language @ident> on both files
    assert dict(stats["review_languages"]) == {"en": 1, "de": 1}
    # Two distinct editor ORCIDs across files
    assert stats["distinct_editors"] == 2
    # Date range spans both files
    assert stats["publication_dates_min"] == "2024-06-15"
    assert stats["publication_dates_max"] == "2025-03-01"

    elements = json.loads((out_dir / "elements.json").read_text(encoding="utf-8"))
    div = next(e for e in elements if e["name"] == "div")
    # Fixture A has 4 <div>; fixture B has 1 <div>; aggregated count must be 5.
    assert div["count"] == 5
    assert div["file_count"] == 2
