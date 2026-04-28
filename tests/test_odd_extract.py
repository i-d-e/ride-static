"""Tests for scripts/odd_extract.py.

The previous version of odd_extract.py wrote to a stale ``.inventory/``
path (a leftover from before the directory rename). Tests now lock the
output path down so a regression cannot ship unnoticed.
"""
from __future__ import annotations

from pathlib import Path

import pytest

import odd_extract

ODD_FIXTURE = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0"
     xmlns:sch="http://purl.oclc.org/dsdl/schematron"
     xmlns:rng="http://relaxng.org/ns/structure/1.0">
  <teiHeader><fileDesc>
    <titleStmt><title>Stub ODD</title></titleStmt>
    <publicationStmt><p>x</p></publicationStmt>
    <sourceDesc><p>x</p></sourceDesc>
  </fileDesc></teiHeader>
  <text><body>
    <schemaSpec ident="ride">
      <moduleRef key="tei"/>
      <moduleRef key="core" include="p list item"/>

      <elementSpec ident="div" module="textstructure" mode="change">
        <attList>
          <attDef ident="rend" mode="delete"/>
          <attDef ident="type" mode="change" usage="rec">
            <valList type="closed" mode="replace">
              <valItem ident="abstract"/>
              <valItem ident="bibliography"/>
            </valList>
          </attDef>
        </attList>
        <constraintSpec ident="div-must-have-head" scheme="schematron">
          <constraint>
            <sch:rule context="tei:div">
              <sch:assert test="tei:head">div needs head</sch:assert>
            </sch:rule>
          </constraint>
        </constraintSpec>
      </elementSpec>

      <elementSpec ident="num" module="core" mode="change">
        <attList>
          <attDef ident="type" mode="change" usage="req">
            <constraintSpec ident="type-not-zero" scheme="schematron">
              <constraint>
                <sch:rule context="tei:num/@type">
                  <sch:report test=". = '0'">no zero</sch:report>
                </sch:rule>
              </constraint>
            </constraintSpec>
          </attDef>
        </attList>
      </elementSpec>

      <elementSpec ident="ignored" module="core" mode="change"/>

      <constraintSpec ident="not-schematron" scheme="something-else">
        <constraint><sch:rule context="."><sch:assert test="true()">x</sch:assert></sch:rule></constraint>
      </constraintSpec>
    </schemaSpec>
  </body></text>
</TEI>
"""


@pytest.fixture
def fixture_paths(tmp_path: Path) -> tuple[Path, Path]:
    odd = tmp_path / "ride.odd"
    odd.write_text(ODD_FIXTURE, encoding="utf-8")
    out = tmp_path / "inventory" / "odd-summary.json"
    return odd, out


def test_run_writes_to_expected_path(fixture_paths: tuple[Path, Path]) -> None:
    """Locks the output path so the historical .inventory/ regression cannot
    return — and the parent directory is auto-created."""
    odd, out = fixture_paths
    assert not out.parent.exists()
    odd_extract.run(odd, out)
    assert out.is_file()
    assert out.parent.is_dir()


def test_modules_extracted_with_includes(fixture_paths: tuple[Path, Path]) -> None:
    odd, out = fixture_paths
    payload = odd_extract.run(odd, out)
    keys = {m["key"]: m["include"] for m in payload["modules"]}
    assert keys["tei"] is None                       # full module
    assert keys["core"] == ["p", "list", "item"]     # explicit subset


def test_elementspec_separates_deleted_changed_and_value_lists(
    fixture_paths: tuple[Path, Path],
) -> None:
    odd, out = fixture_paths
    payload = odd_extract.run(odd, out)
    div = next(s for s in payload["elementspecs"] if s["ident"] == "div")
    assert div["deleted_atts"] == ["rend"]
    assert {a["ident"] for a in div["changed_atts"]} == {"type"}
    assert div["value_lists"]["type"]["type"] == "closed"
    assert div["value_lists"]["type"]["values"] == ["abstract", "bibliography"]


def test_empty_elementspec_records_nothing(fixture_paths: tuple[Path, Path]) -> None:
    odd, out = fixture_paths
    payload = odd_extract.run(odd, out)
    ignored = next(s for s in payload["elementspecs"] if s["ident"] == "ignored")
    assert ignored["deleted_atts"] == []
    assert ignored["changed_atts"] == []
    assert ignored["value_lists"] == {}


def test_schematron_rules_owner_routing(fixture_paths: tuple[Path, Path]) -> None:
    """Element-scoped rules attach to the elementSpec; attDef-scoped rules
    are reported as element/@attr."""
    odd, out = fixture_paths
    payload = odd_extract.run(odd, out)
    by_id = {r["constraint_id"]: r for r in payload["schematron_rules"]}
    # div-must-have-head is on the elementSpec
    div_rule = by_id["div-must-have-head"]
    assert div_rule["owner_kind"] == "elementSpec"
    assert div_rule["owner_ident"] == "div"
    assert div_rule["kind"] == "assert"
    assert div_rule["test"] == "tei:head"
    # type-not-zero is on the attDef inside <num>
    type_rule = by_id["type-not-zero"]
    assert type_rule["owner_kind"] == "attDef"
    assert type_rule["owner_ident"] == "num/@type"
    assert type_rule["kind"] == "report"


def test_non_schematron_constraints_skipped(fixture_paths: tuple[Path, Path]) -> None:
    """A constraintSpec with scheme!=schematron must not appear in the rules list."""
    odd, out = fixture_paths
    payload = odd_extract.run(odd, out)
    rule_ids = {r["constraint_id"] for r in payload["schematron_rules"]}
    assert "not-schematron" not in rule_ids


def test_summary_counts_match(fixture_paths: tuple[Path, Path]) -> None:
    odd, out = fixture_paths
    payload = odd_extract.run(odd, out)
    assert payload["element_count"] == len(payload["elementspecs"])
    assert payload["schematron_rule_count"] == len(payload["schematron_rules"])
