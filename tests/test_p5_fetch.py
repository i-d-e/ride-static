"""Tests for scripts/p5_fetch.py — uses a synthetic p5subset stub so no network is touched."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import p5_fetch

# Synthetic p5subset.xml: two elementSpecs, two classSpecs, one closed-valList.
P5_STUB = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <elementSpec ident="div" module="textstructure">
    <gloss>division</gloss>
    <desc>Marks a logical subdivision of the body, front, or back. Further details follow.</desc>
    <classes>
      <memberOf key="att.global"/>
      <memberOf key="att.divLike"/>
    </classes>
    <attList>
      <attDef ident="type" usage="rec"/>
      <attDef ident="subtype" usage="opt"/>
    </attList>
  </elementSpec>
  <elementSpec ident="head" module="core">
    <gloss>heading</gloss>
    <desc>Contains any kind of heading.</desc>
    <classes>
      <memberOf key="att.global"/>
    </classes>
    <attList/>
  </elementSpec>
  <classSpec ident="att.global" type="atts" module="tei">
    <attList>
      <attDef ident="xml:id" usage="opt"/>
      <attDef ident="xml:lang" usage="opt"/>
    </attList>
  </classSpec>
  <classSpec ident="att.divLike" type="atts" module="textstructure">
    <attList>
      <attDef ident="org" usage="opt">
        <valList type="closed">
          <valItem ident="composite"/>
          <valItem ident="uniform"/>
        </valList>
      </attDef>
    </attList>
  </classSpec>
  <classSpec ident="att.unrelated" type="atts" module="other">
    <attList><attDef ident="x" usage="opt"/></attList>
  </classSpec>
</TEI>
"""


@pytest.fixture
def fixture_paths(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    p5 = tmp_path / "p5stub.xml"
    p5.write_text(P5_STUB, encoding="utf-8")

    elements = tmp_path / "elements.json"
    # The corpus uses div, head, and a fake unknown_in_p5 element.
    elements.write_text(
        json.dumps([
            {"name": "div", "count": 1},
            {"name": "head", "count": 1},
            {"name": "unknown_in_p5", "count": 1},
        ]),
        encoding="utf-8",
    )
    attributes = tmp_path / "attributes.json"
    attributes.write_text(
        json.dumps([{"name": "type", "count": 1}, {"name": "xml:id", "count": 1}]),
        encoding="utf-8",
    )
    out = tmp_path / "tei-spec.json"
    return p5, elements, attributes, out


def test_run_writes_tei_spec(fixture_paths: tuple[Path, Path, Path, Path]) -> None:
    p5, elements, attributes, out = fixture_paths
    p5_fetch.run(p5, elements, attributes, out)
    assert out.is_file()


def test_only_used_elements_extracted(fixture_paths: tuple[Path, Path, Path, Path]) -> None:
    p5, elements, attributes, out = fixture_paths
    payload = p5_fetch.run(p5, elements, attributes, out)
    assert set(payload["elements"].keys()) == {"div", "head"}
    assert payload["elements_missing_from_p5"] == ["unknown_in_p5"]


def test_referenced_attribute_classes_only(fixture_paths: tuple[Path, Path, Path, Path]) -> None:
    p5, elements, attributes, out = fixture_paths
    payload = p5_fetch.run(p5, elements, attributes, out)
    # att.global and att.divLike are referenced; att.unrelated must NOT appear.
    assert set(payload["attribute_classes"].keys()) == {"att.global", "att.divLike"}


def test_closed_value_list_captured(fixture_paths: tuple[Path, Path, Path, Path]) -> None:
    p5, elements, attributes, out = fixture_paths
    payload = p5_fetch.run(p5, elements, attributes, out)
    div_like = payload["attribute_classes"]["att.divLike"]
    org_def = next(a for a in div_like["attributes"] if a["ident"] == "org")
    assert org_def["closed_values"] == ["composite", "uniform"]


def test_div_spec_fields(fixture_paths: tuple[Path, Path, Path, Path]) -> None:
    p5, elements, attributes, out = fixture_paths
    payload = p5_fetch.run(p5, elements, attributes, out)
    div = payload["elements"]["div"]
    assert div["module"] == "textstructure"
    assert div["gloss"] == "division"
    assert div["desc"].startswith("Marks a logical subdivision")
    assert div["desc"].endswith(".")
    assert "att.global" in div["classes"]
    assert {a["ident"] for a in div["attributes_direct"]} == {"type", "subtype"}


def test_fetch_p5_uses_cache(tmp_path: Path) -> None:
    cache = tmp_path / "p5cache.xml"
    cache.write_bytes(b"<TEI xmlns='http://www.tei-c.org/ns/1.0'/>")
    # If the cache is honored, the URL is irrelevant — passing nonsense must not raise.
    result = p5_fetch.fetch_p5(url="http://invalid.invalid/never-fetched", dest=cache)
    assert result == cache
