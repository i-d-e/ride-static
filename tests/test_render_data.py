"""Tests for scripts/render_data.py."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import render_data


def _seed(inventory: Path) -> None:
    inventory.mkdir()
    (inventory / "elements.json").write_text(json.dumps([
        {"name": "p", "count": 100, "file_count": 2, "attributes": {}},
        {"name": "div", "count": 4, "file_count": 2, "attributes": {
            "type": {"count": 2, "presence_ratio": 0.5, "distinct": 2,
                     "values_complete": True,
                     "values": [["abstract", 1], ["bibliography", 1]]}
        }},
    ]), encoding="utf-8")
    (inventory / "attributes.json").write_text(json.dumps([
        {"name": "type", "count": 2, "on_elements": [["div", 2]],
         "distinct_values": 2, "top_values": [["abstract", 1], ["bibliography", 1]]},
    ]), encoding="utf-8")
    (inventory / "corpus-stats.json").write_text(json.dumps({
        "files_total": 2, "elements_total": 104,
        "distinct_elements": 2, "distinct_attributes": 1,
        "review_languages": [["en", 1], ["de", 1]],
        "issues": [["1", 2]],
        "publication_dates_min": "2024-01", "publication_dates_max": "2024-12",
        "licences": [["https://creativecommons.org/licenses/by/4.0/", 2]],
        "distinct_editors": 1,
        "files_size": [],
    }), encoding="utf-8")
    (inventory / "sections.json").write_text(json.dumps({
        "file_count": 2,
        "type_distribution": [["abstract", 1], ["bibliography", 1]],
        "missing_head_count": 3,
        "files": [
            {"file": "a.xml", "front": [], "body": [], "back": [{"type": "bibliography"}]},
            {"file": "b.xml", "front": [], "body": [], "back": []},  # no biblio
        ],
    }), encoding="utf-8")
    (inventory / "structure.json").write_text(json.dumps({
        "element_count": 2,
        "by_element": {
            "div": {
                "count": 4, "leaf_count": 0,
                "children": [["p", 10], ["head", 4]],
                "child_sequences": [{"sequence": ["head", "p", "p"], "count": 2}],
                "first_child": [["head", 4]], "last_child": [["p", 4]],
                "ancestor_paths": [["TEI/text/body", 2]],
                "depth": [[2, 4]],
            },
            "p": {"count": 100, "leaf_count": 100, "children": [], "child_sequences": [],
                  "first_child": [], "last_child": [],
                  "ancestor_paths": [["TEI/text/body/div", 100]], "depth": [[3, 100]]},
        },
    }), encoding="utf-8")
    (inventory / "cross-reference.json").write_text(json.dumps({
        "summary": {
            "elements_total": 2,
            "elements_absent_from_p5": [],
            "elements_with_attrs_outside_p5": [],
            "elements_with_value_violations": ["div"],
        },
        "elements": {
            "div": {
                "diff": {
                    "attrs_outside_p5": [],
                    "value_list_violations": {
                        "type": {
                            "allowed": ["abstract"],
                            "empirical_unknown_values": [["bibliography", 1]],
                        }
                    },
                }
            },
        },
    }), encoding="utf-8")


@pytest.fixture
def seeded(tmp_path: Path) -> tuple[Path, Path]:
    inventory = tmp_path / "inventory"
    out = tmp_path / "knowledge" / "data.md"
    _seed(inventory)
    return inventory, out


def test_writes_file(seeded: tuple[Path, Path]) -> None:
    inventory, out = seeded
    render_data.render(inventory, out, today="2026-04-28")
    assert out.is_file()
    text = out.read_text(encoding="utf-8")
    assert text.startswith("---\ngenerated: 2026-04-28\n")
    assert "# RIDE Corpus Data" in text


def test_overview_table_values(seeded: tuple[Path, Path]) -> None:
    inventory, out = seeded
    text = render_data.render(inventory, out, today="2026-04-28")
    assert "**Reviews:** 2" in text
    assert "**Distinct elements:** 2" in text
    assert "English (1), German (1)" in text


def test_section_types_and_no_biblio(seeded: tuple[Path, Path]) -> None:
    inventory, out = seeded
    text = render_data.render(inventory, out, today="2026-04-28")
    assert "abstract" in text and "bibliography" in text
    # Only b.xml lacks a bibliography
    assert "Reviews without a bibliography section (1)" in text
    assert "`b.xml`" in text


def test_value_violation_rendered(seeded: tuple[Path, Path]) -> None:
    inventory, out = seeded
    text = render_data.render(inventory, out, today="2026-04-28")
    assert "`<div>/@type`" in text
    assert "`bibliography`×1" in text


def test_element_index_alphabetical(seeded: tuple[Path, Path]) -> None:
    inventory, out = seeded
    text = render_data.render(inventory, out, today="2026-04-28")
    assert text.find("### `<div>`") < text.find("### `<p>`")
