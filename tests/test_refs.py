"""Tests for scripts/refs.py."""
from __future__ import annotations

from pathlib import Path

import pytest

import refs

FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="ride.1.1">
  <teiHeader><fileDesc>
    <titleStmt><title>Refs</title></titleStmt>
    <publicationStmt><p>x</p></publicationStmt>
    <sourceDesc><p>x</p></sourceDesc>
  </fileDesc></teiHeader>
  <text><body>
    <div xml:id="div1"><head>One</head>
      <p>
        See <ref target="#div2" type="crossref">section 2</ref>.
        Visit <ref target="https://github.com/foo">our repo</ref>.
        Also <ref target="https://example.org/page">example</ref>.
        And <ref target="http://old.tld">old</ref>.
        Broken: <ref target="#nonexistent" type="crossref">dead</ref>.
        Mailto: <ref target="mailto:user@example.org">contact</ref>.
        Relative: <ref target="../assets/img.png">img</ref>.
      </p>
    </div>
    <div xml:id="div2"><head>Two</head><p>here.</p></div>
  </body></text>
</TEI>
"""


@pytest.fixture
def fixture_corpus(tmp_path: Path) -> tuple[Path, Path]:
    tei = tmp_path / "tei"
    out = tmp_path / "out"
    tei.mkdir()
    (tei / "r-tei.xml").write_text(FIXTURE, encoding="utf-8")
    return tei, out


def test_writes_refs_json(fixture_corpus: tuple[Path, Path]) -> None:
    tei, out = fixture_corpus
    refs.run(tei, out)
    assert (out / "refs.json").is_file()


def test_categories_classified(fixture_corpus: tuple[Path, Path]) -> None:
    tei, out = fixture_corpus
    payload = refs.run(tei, out)
    s = payload["summary"]
    assert s["ref_total"] == 7
    assert s["internal_total"] == 2          # #div2, #nonexistent
    assert s["external_url_total"] == 3      # github, example.org, old.tld
    assert s["other_total"] == 2             # mailto:, relative path


def test_dangling_internal_anchor_detected(fixture_corpus: tuple[Path, Path]) -> None:
    tei, out = fixture_corpus
    payload = refs.run(tei, out)
    assert payload["summary"]["dangling_internal_total"] == 1
    targets = {s["target"] for s in payload["dangling_samples"]}
    assert "#nonexistent" in targets
    # The valid #div2 anchor must not be flagged
    assert "#div2" not in targets


def test_external_domain_aggregation(fixture_corpus: tuple[Path, Path]) -> None:
    tei, out = fixture_corpus
    payload = refs.run(tei, out)
    domains = dict(payload["external_top_domains"])
    assert "github.com" in domains
    assert "example.org" in domains
    assert "old.tld" in domains
    # 3 distinct external targets
    assert payload["summary"]["external_distinct_targets"] == 3


def test_other_samples_capture_non_url_non_anchor(fixture_corpus: tuple[Path, Path]) -> None:
    tei, out = fixture_corpus
    payload = refs.run(tei, out)
    other_targets = {s["target"] for s in payload["other_samples"]}
    assert "mailto:user@example.org" in other_targets
    assert "../assets/img.png" in other_targets


def test_per_file_counts_match_summary(fixture_corpus: tuple[Path, Path]) -> None:
    tei, out = fixture_corpus
    payload = refs.run(tei, out)
    f = next(p for p in payload["per_file"] if p["file"] == "r-tei.xml")
    assert f["internal"] + f["external_url"] + f["other"] == payload["summary"]["ref_total"]
    assert f["dangling"] == 1


# Second fixture: many dangling refs with a recognisable prefix scheme. Mirrors
# the real-corpus pattern where #K1.2 / #K2.1 dangling refs cluster together
# (they all point at external RIDE criteria categories, not local anchors).
PREFIX_FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="ride.1.2">
  <teiHeader><fileDesc>
    <titleStmt><title>Prefix</title></titleStmt>
    <publicationStmt><p>x</p></publicationStmt>
    <sourceDesc><p>x</p></sourceDesc>
  </fileDesc></teiHeader>
  <text><body><div xml:id="div1"><p>
    <ref target="#K1.2"/><ref target="#K2.1"/><ref target="#K1.4"/>
    <ref target="#fig-foo"/><ref target="#fn1"/>
  </p></div></body></text>
</TEI>
"""


def test_dangling_prefix_buckets(tmp_path: Path) -> None:
    """Dangling targets are bucketed by leading alphabetic prefix so consumers
    can spot families of broken refs (e.g. all #K... refs to external criteria)."""
    tei = tmp_path / "tei"
    out = tmp_path / "out"
    tei.mkdir()
    (tei / "p-tei.xml").write_text(PREFIX_FIXTURE, encoding="utf-8")
    payload = refs.run(tei, out)
    buckets = dict(payload["dangling_prefix_buckets"])
    assert buckets["K"] == 3      # #K1.2, #K2.1, #K1.4
    assert buckets["fig"] == 1
    assert buckets["fn"] == 1
