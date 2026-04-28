"""Tests for scripts/render_schema.py."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import render_schema


ODD = {
    "modules": [
        {"key": "tei", "include": None},
        {"key": "core", "include": ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k"]},
        {"key": "tiny", "include": ["a"]},
    ],
    "element_count": 4,
    "elementspecs": [
        {
            "ident": "TEI",
            "mode": "change",
            "module": None,
            "deleted_atts": ["n", "n", "rend"],  # duplicates must be deduped
            "changed_atts": [{"ident": "xml:id", "mode": "change", "usage": "req"}],
            "value_lists": {},
        },
        {
            "ident": "num",
            "mode": "change",
            "module": "core",
            "deleted_atts": [],
            "changed_atts": [],
            "value_lists": {
                "type": {
                    "type": "closed",
                    "mode": "replace",
                    "values": ["cardinal", "ordinal"],
                }
            },
        },
        {
            "ident": "boring",
            "mode": "change",
            "module": "core",
            "deleted_atts": [],
            "changed_atts": [],
            "value_lists": {},
        },
        {
            "ident": "open",
            "mode": "change",
            "module": "core",
            "deleted_atts": [],
            "changed_atts": [],
            "value_lists": {
                "type": {"type": "open", "mode": "add", "values": ["x"]},
            },
        },
    ],
    "schematron_rule_count": 2,
    "schematron_rules": [
        {
            "constraint_id": "id-format",
            "owner_kind": "attDef",
            "owner_ident": "TEI/@xml:id",
            "kind": "assert",
            "context": "tei:TEI/@xml:id",
            "test": "matches(., 'X')",
            "message": "ID must match X",
        },
        {
            "constraint_id": "first-editor",
            "owner_kind": "elementSpec",
            "owner_ident": "seriesStmt",
            "kind": "assert",
            "context": "tei:seriesStmt/tei:editor[1]",
            "test": "not(@role)",
            "message": "first editor has no role",
        },
    ],
}

ELEMENTS = [
    {"name": "num", "count": 10, "file_count": 1, "attributes": {
        "type": {"count": 10, "presence_ratio": 1.0, "distinct": 1,
                 "values_complete": True, "values": [["boolean", 10]]},
    }},
    {"name": "open", "count": 0, "file_count": 0, "attributes": {}},
]

CROSS = {
    "summary": {"elements_with_value_violations": ["num"]},
    "elements": {
        "num": {
            "diff": {
                "attrs_outside_p5": [],
                "value_list_violations": {
                    "type": {
                        "allowed": ["cardinal", "ordinal"],
                        "empirical_unknown_values": [["boolean", 10]],
                    }
                },
            }
        }
    },
}


@pytest.fixture
def seeded(tmp_path: Path) -> tuple[Path, Path]:
    inv = tmp_path / "inventory"
    inv.mkdir()
    (inv / "odd-summary.json").write_text(json.dumps(ODD), encoding="utf-8")
    (inv / "elements.json").write_text(json.dumps(ELEMENTS), encoding="utf-8")
    (inv / "cross-reference.json").write_text(json.dumps(CROSS), encoding="utf-8")
    return inv, tmp_path / "knowledge" / "schema.md"


def test_writes_file(seeded: tuple[Path, Path]) -> None:
    inv, out = seeded
    render_schema.render(inv, out, today="2026-04-28")
    assert out.is_file()
    text = out.read_text(encoding="utf-8")
    assert text.startswith("---\ngenerated: 2026-04-28\n")


def test_module_lines_full_and_subset_and_truncated(seeded: tuple[Path, Path]) -> None:
    inv, out = seeded
    text = render_schema.render(inv, out, today="2026-04-28")
    assert "**tei** (full)" in text
    # Truncated: 11 elements, MAX_INCLUDE_PREVIEW=8
    assert "**core**" in text and "and 3 more" in text
    # Small list: shown in full
    assert "**tiny** — only: `a`" in text


def test_customisations_skip_boring_specs(seeded: tuple[Path, Path]) -> None:
    inv, out = seeded
    text = render_schema.render(inv, out, today="2026-04-28")
    # 4 specs total, 3 with changes (TEI, num, open)
    assert "Out of 4 elementSpec entries" in text
    assert "3 actually change something" in text
    # boring has no changes - must NOT appear as a customisation block
    assert "#### `<boring>`" not in text


def test_deleted_atts_deduplicated(seeded: tuple[Path, Path]) -> None:
    inv, out = seeded
    text = render_schema.render(inv, out, today="2026-04-28")
    # `n` appears twice in input; we dedupe -> appears once in output
    tei_block_start = text.index("#### `<TEI>`")
    tei_block_end = text.index("#### `<", tei_block_start + 1)
    tei_block = text[tei_block_start:tei_block_end]
    assert tei_block.count("`@n`") == 1
    assert "`@rend`" in tei_block


def test_changed_attrs_show_usage(seeded: tuple[Path, Path]) -> None:
    inv, out = seeded
    text = render_schema.render(inv, out, today="2026-04-28")
    assert "`@xml:id` — mode `change`, usage `req`" in text


def test_closed_value_list_shows_violation_in_bold(seeded: tuple[Path, Path]) -> None:
    inv, out = seeded
    text = render_schema.render(inv, out, today="2026-04-28")
    # The corpus uses `boolean` which is NOT in [cardinal, ordinal] -> bold
    assert "ODD allows: `cardinal`, `ordinal`" in text
    assert "Corpus uses: **`boolean`**" in text


def test_open_value_list_excluded(seeded: tuple[Path, Path]) -> None:
    """Only closed valLists belong in the diff section; open ones are noise here."""
    inv, out = seeded
    text = render_schema.render(inv, out, today="2026-04-28")
    # `open/@type` is an open valList; should not appear as a diff block
    assert "#### `<open>/@type`" not in text


def test_schematron_grouped_by_element(seeded: tuple[Path, Path]) -> None:
    inv, out = seeded
    text = render_schema.render(inv, out, today="2026-04-28")
    # 2 rules grouped under TEI and seriesStmt
    assert "`ride.odd` carries 2 Schematron constraints" in text
    # Rule attached to TEI/@xml:id is grouped under <TEI>
    sch = text.index("## Schematron rules")
    tei_idx = text.index("#### `<TEI>`", sch)
    series_idx = text.index("#### `<seriesStmt>`", sch)
    # Both groups present
    assert tei_idx > 0 and series_idx > 0
    # Rule body appears with test and message
    assert "test: `matches(., 'X')`" in text
    assert "ID must match X" in text
