"""Tests for scripts/cross_reference.py."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import cross_reference

ELEMENTS = [
    {
        "name": "div",
        "count": 4,
        "file_count": 2,
        "attributes": {
            "type": {"count": 3, "values": [["abstract", 2], ["bibliography", 1]]},
            "rogueAttr": {"count": 1, "values": [["x", 1]]},
        },
    },
    {
        "name": "head",
        "count": 4,
        "file_count": 2,
        "attributes": {
            "xml:id": {"count": 1, "values": [["h1", 1]]},
        },
    },
    {
        "name": "phantom",
        "count": 1,
        "file_count": 1,
        "attributes": {},
    },
]

TEI_SPEC = {
    "elements": {
        "div": {
            "module": "textstructure",
            "gloss": "division",
            "desc": "subdivision",
            "classes": ["att.global", "att.divLike"],
            "attributes_direct": [{"ident": "type", "usage": "rec", "closed_values": None}],
        },
        "head": {
            "module": "core",
            "gloss": "heading",
            "desc": "heading",
            "classes": ["att.global"],
            "attributes_direct": [],
        },
    },
    "attribute_classes": {
        "att.global": {
            "classes": ["att.global.linking"],
            "attributes": [{"ident": "xml:id", "usage": "opt", "closed_values": None}],
        },
        "att.global.linking": {
            "classes": [],
            "attributes": [{"ident": "corresp", "usage": "opt", "closed_values": None}],
        },
        "att.divLike": {
            "classes": [],
            "attributes": [{"ident": "org", "usage": "opt", "closed_values": None}],
        },
    },
}

ODD = {
    "elementspecs": [
        {
            "ident": "div",
            "mode": "change",
            "deleted_atts": ["xml:base"],
            "changed_atts": [],
            "value_lists": {
                "type": {
                    "type": "closed",
                    "mode": "replace",
                    "values": ["abstract", "bibliography"],
                },
            },
        }
    ],
    "schematron_rules": [
        {
            "constraint_id": "div-must-have-head",
            "owner_kind": "elementSpec",
            "owner_ident": "div",
            "kind": "assert",
            "context": "tei:div",
            "test": "tei:head",
            "message": "div needs head",
        },
        {
            "constraint_id": "type-not-zero",
            "owner_kind": "attDef",
            "owner_ident": "div/@type",
            "kind": "assert",
            "context": "tei:div/@type",
            "test": ". != '0'",
            "message": "no zeros",
        },
    ],
}


@pytest.fixture
def fixture_paths(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    e = tmp_path / "elements.json"
    e.write_text(json.dumps(ELEMENTS), encoding="utf-8")
    t = tmp_path / "tei-spec.json"
    t.write_text(json.dumps(TEI_SPEC), encoding="utf-8")
    o = tmp_path / "odd-summary.json"
    o.write_text(json.dumps(ODD), encoding="utf-8")
    out = tmp_path / "cross-reference.json"
    return e, t, o, out


def test_writes_output(fixture_paths: tuple[Path, Path, Path, Path]) -> None:
    e, t, o, out = fixture_paths
    cross_reference.run(e, t, o, out)
    assert out.is_file()


def test_phantom_element_marked_absent(fixture_paths: tuple[Path, Path, Path, Path]) -> None:
    e, t, o, out = fixture_paths
    payload = cross_reference.run(e, t, o, out)
    assert payload["summary"]["elements_absent_from_p5"] == ["phantom"]
    assert payload["elements"]["phantom"]["p5"] is None


def test_attrs_outside_p5_detected(fixture_paths: tuple[Path, Path, Path, Path]) -> None:
    e, t, o, out = fixture_paths
    payload = cross_reference.run(e, t, o, out)
    div = payload["elements"]["div"]
    assert div["diff"]["attrs_outside_p5"] == ["rogueAttr"]
    assert "div" in payload["summary"]["elements_with_attrs_outside_p5"]
    # head/xml:id IS in P5 via att.global, so head must be clean
    assert "head" not in payload["summary"]["elements_with_attrs_outside_p5"]


def test_value_list_violations(fixture_paths: tuple[Path, Path, Path, Path]) -> None:
    e, t, o, out = fixture_paths
    # ODD allows ["abstract","bibliography"]; empirical has those (no violation).
    payload = cross_reference.run(e, t, o, out)
    div = payload["elements"]["div"]
    assert div["diff"]["value_list_violations"] == {}
    # Now inject an empirical value not in ODD list.
    elements_with_bad = json.loads(e.read_text(encoding="utf-8"))
    elements_with_bad[0]["attributes"]["type"]["values"].append(["appendix", 1])
    e.write_text(json.dumps(elements_with_bad), encoding="utf-8")
    payload = cross_reference.run(e, t, o, out)
    div = payload["elements"]["div"]
    assert "type" in div["diff"]["value_list_violations"]
    assert div["diff"]["value_list_violations"]["type"]["empirical_unknown_values"] == [["appendix", 1]]
    assert "div" in payload["summary"]["elements_with_value_violations"]


def test_p5_attrs_resolved_via_classes(fixture_paths: tuple[Path, Path, Path, Path]) -> None:
    e, t, o, out = fixture_paths
    payload = cross_reference.run(e, t, o, out)
    div_attrs = payload["elements"]["div"]["p5"]["attrs_available"]
    assert div_attrs["type"]["source"] == "direct"
    assert div_attrs["xml:id"]["source"] == "class:att.global"
    assert div_attrs["org"]["source"] == "class:att.divLike"
    # corresp is only reachable via att.global -> att.global.linking (recursion)
    assert div_attrs["corresp"]["source"] == "class:att.global.linking"


def test_schematron_rules_routed_to_element(fixture_paths: tuple[Path, Path, Path, Path]) -> None:
    e, t, o, out = fixture_paths
    payload = cross_reference.run(e, t, o, out)
    rule_ids = {r["constraint_id"] for r in payload["elements"]["div"]["schematron"]}
    # both the elementSpec rule and the attDef rule (div/@type) should attach to div
    assert rule_ids == {"div-must-have-head", "type-not-zero"}
    # head has no rules
    assert payload["elements"]["head"]["schematron"] == []
