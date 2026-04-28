"""Tests for scripts/render_data.py.

The renderer produces a structure-and-knowledge reference rather than a
quantitative dump, so tests focus on the rules and qualitative labels
that appear, not on counts.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import render_data


def _seed(inventory: Path, *, no_back_files: int = 1) -> None:
    inventory.mkdir()

    # elements.json — exercises closed value list, single-value attr,
    # open identifier, and the <num>/<cell> patterns.
    (inventory / "elements.json").write_text(json.dumps([
        {"name": "TEI", "count": 2, "file_count": 2, "attributes": {}},
        {"name": "text", "count": 2, "file_count": 2, "attributes": {}},
        {"name": "body", "count": 2, "file_count": 2, "attributes": {}},
        {"name": "div", "count": 4, "file_count": 2, "attributes": {
            "type": {"count": 2, "presence_ratio": 0.5, "distinct": 2,
                     "values_complete": True,
                     "values": [["abstract", 1], ["bibliography", 1]]},
            "xml:id": {"count": 4, "presence_ratio": 1.0, "distinct": 4,
                       "values_complete": False,
                       "values": [["d1", 1], ["d2", 1], ["d3", 1], ["d4", 1]]},
        }},
        {"name": "head", "count": 4, "file_count": 2, "attributes": {}},
        {"name": "p", "count": 4, "file_count": 2, "attributes": {}},
        {"name": "num", "count": 10, "file_count": 2, "attributes": {
            "type": {"count": 10, "presence_ratio": 1.0, "distinct": 1,
                     "values_complete": True, "values": [["boolean", 10]]},
            "value": {"count": 10, "presence_ratio": 1.0, "distinct": 2,
                      "values_complete": False, "values": [["0", 7], ["1", 3]]},
        }},
        {"name": "cell", "count": 6, "file_count": 1, "attributes": {
            "rows": {"count": 6, "presence_ratio": 1.0, "distinct": 1,
                     "values_complete": False, "values": [["1", 6]]},
            "cols": {"count": 6, "presence_ratio": 1.0, "distinct": 1,
                     "values_complete": False, "values": [["1", 6]]},
            "role": {"count": 6, "presence_ratio": 1.0, "distinct": 1,
                     "values_complete": True, "values": [["data", 6]]},
        }},
        {"name": "ref", "count": 100, "file_count": 2, "attributes": {
            "target": {"count": 100, "presence_ratio": 1.0, "distinct": 60,
                       "values_complete": False,
                       "values": [["http://x", 5], ["http://y", 4]]},
        }},
        {"name": "row", "count": 2, "file_count": 1, "attributes": {}},
    ]), encoding="utf-8")

    # structure.json — provides the always-pattern data for TEI/text/fileDesc
    (inventory / "structure.json").write_text(json.dumps({
        "by_element": {
            "TEI": {
                "count": 2, "leaf_count": 0,
                "children": [["teiHeader", 2], ["text", 2]],
                "child_sequences": [{"sequence": ["teiHeader", "text"], "count": 2}],
                "first_child": [["teiHeader", 2]], "last_child": [["text", 2]],
                "ancestor_paths": [["", 2]], "depth": [[0, 2]],
            },
            "text": {
                "count": 2, "leaf_count": 0,
                "children": [["body", 2], ["front", 2 - no_back_files], ["back", 2 - no_back_files]],
                "child_sequences": [
                    {"sequence": ["front", "body", "back"], "count": 2 - no_back_files},
                    {"sequence": ["front", "body"], "count": no_back_files},
                ],
                "first_child": [["front", 2]], "last_child": [["back", 2 - no_back_files]],
                "ancestor_paths": [["TEI", 2]], "depth": [[1, 2]],
            },
            "body": {
                "count": 2, "leaf_count": 0,
                "children": [["div", 4], ["p", 1], ["cit", 1]],
                "child_sequences": [
                    {"sequence": ["div", "div"], "count": 1},
                    {"sequence": ["p"], "count": 1},
                ],
                "first_child": [["div", 1], ["p", 1]],
                "last_child": [["div", 1], ["p", 1]],
                "ancestor_paths": [["TEI/text", 2]], "depth": [[2, 2]],
            },
            "fileDesc": {
                "count": 2, "leaf_count": 0,
                "children": [["titleStmt", 2], ["sourceDesc", 3]],
                "child_sequences": [
                    {"sequence": ["titleStmt", "sourceDesc"], "count": 1},
                    {"sequence": ["titleStmt", "sourceDesc", "sourceDesc"], "count": 1},
                ],
                "first_child": [["titleStmt", 2]], "last_child": [["sourceDesc", 2]],
                "ancestor_paths": [["TEI/teiHeader", 2]], "depth": [[2, 2]],
            },
            "div": {
                "count": 4, "leaf_count": 0,
                "children": [["head", 3], ["p", 4]],
                "child_sequences": [
                    {"sequence": ["head", "p"], "count": 3},
                    {"sequence": ["p"], "count": 1},
                ],
                "first_child": [["head", 3], ["p", 1]],
                "last_child": [["p", 4]],
                "ancestor_paths": [["TEI/text/body", 4]], "depth": [[3, 4]],
            },
            "num": {
                "count": 10, "leaf_count": 10,
                "children": [], "child_sequences": [],
                "first_child": [], "last_child": [],
                "ancestor_paths": [["TEI/text/body/div/catDesc", 10]],
                "depth": [[5, 10]],
            },
            "head": {"count": 4, "leaf_count": 4, "children": [], "child_sequences": [],
                     "first_child": [], "last_child": [], "ancestor_paths": [["TEI/text/body/div", 4]],
                     "depth": [[4, 4]]},
            "p": {"count": 4, "leaf_count": 4, "children": [], "child_sequences": [],
                  "first_child": [], "last_child": [], "ancestor_paths": [["TEI/text/body/div", 4]],
                  "depth": [[4, 4]]},
            "cell": {"count": 6, "leaf_count": 6, "children": [], "child_sequences": [],
                     "first_child": [], "last_child": [], "ancestor_paths": [["TEI/text/body/table/row", 6]],
                     "depth": [[5, 6]]},
            "ref": {"count": 100, "leaf_count": 100, "children": [], "child_sequences": [],
                    "first_child": [], "last_child": [], "ancestor_paths": [["TEI/text/body/p", 100]],
                    "depth": [[4, 100]]},
            "row": {"count": 2, "leaf_count": 0,
                    "children": [["cell", 6]],
                    "child_sequences": [{"sequence": ["cell", "cell", "cell"], "count": 2}],
                    "first_child": [["cell", 2]], "last_child": [["cell", 2]],
                    "ancestor_paths": [["TEI/text/body/table", 2]], "depth": [[4, 2]]},
        },
    }), encoding="utf-8")

    # sections.json — one file with <back>, one without
    files = []
    files.append({"file": "with_back.xml", "front": [], "body": [], "back": [{"type": "bibliography"}]})
    if no_back_files:
        files.append({"file": "no_back.xml", "front": [], "body": [], "back": []})
    (inventory / "sections.json").write_text(json.dumps({
        "file_count": len(files),
        "type_distribution": [["bibliography", 1]],
        "missing_head_count": 1,
        "files": files,
    }), encoding="utf-8")

    # cross-reference.json — one mismatch to surface in findings
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


def test_writes_file_with_frontmatter(seeded: tuple[Path, Path]) -> None:
    inventory, out = seeded
    render_data.render(inventory, out, today="2026-04-28")
    text = out.read_text(encoding="utf-8")
    assert text.startswith("---\ngenerated: 2026-04-28\n")
    assert "# RIDE TEI Structure Reference" in text


def test_no_quantitative_overview_section(seeded: tuple[Path, Path]) -> None:
    """The redesigned output should NOT contain the old quantity-heavy sections."""
    inventory, out = seeded
    text = render_data.render(inventory, out, today="2026-04-28")
    assert "Most-used elements" not in text
    assert "Most-used attributes" not in text
    assert "**Reviews:**" not in text
    assert "**Total elements:**" not in text


def test_tei_root_rule_present(seeded: tuple[Path, Path]) -> None:
    inventory, out = seeded
    text = render_data.render(inventory, out, today="2026-04-28")
    assert "Document root is `<TEI>` with children `[teiHeader, text]`" in text


def test_text_two_shapes_rule(seeded: tuple[Path, Path]) -> None:
    inventory, out = seeded
    text = render_data.render(inventory, out, today="2026-04-28")
    assert "two shapes" in text
    assert "front, body, back" in text
    assert "front, body]`" in text


def test_no_back_finding_lists_files(seeded: tuple[Path, Path]) -> None:
    inventory, out = seeded
    text = render_data.render(inventory, out, today="2026-04-28")
    assert "1 reviews omit `<back>` entirely" in text
    assert "`no_back.xml`" in text


def test_filedesc_anomaly_surfaced(seeded: tuple[Path, Path]) -> None:
    inventory, out = seeded
    text = render_data.render(inventory, out, today="2026-04-28")
    assert "`<fileDesc>` children are `[titleStmt, sourceDesc]`" in text
    assert "duplicates `<sourceDesc>`" in text


def test_num_rule_describes_questionnaire(seeded: tuple[Path, Path]) -> None:
    inventory, out = seeded
    text = render_data.render(inventory, out, today="2026-04-28")
    assert "RIDE questionnaire payload" in text
    assert "always sits inside `<catDesc>`" in text
    assert "`@type` ∈ {`boolean`}" in text
    assert "`@value` ∈ {`0`, `1`}" in text


def test_cell_redundant_attrs_rule(seeded: tuple[Path, Path]) -> None:
    inventory, out = seeded
    text = render_data.render(inventory, out, today="2026-04-28")
    assert "No merged cells exist" in text
    assert "`@rows=\"1\"`" in text


def test_classification_chain_rule(seeded: tuple[Path, Path]) -> None:
    inventory, out = seeded
    text = render_data.render(inventory, out, today="2026-04-28")
    assert "Classification chain:" in text
    assert "`<taxonomy>`" in text and "`<catDesc>`" in text


def test_qualitative_attribute_labels(seeded: tuple[Path, Path]) -> None:
    inventory, out = seeded
    text = render_data.render(inventory, out, today="2026-04-28")
    # exhaustive (empirical) list with multiple values
    assert "values seen: `abstract` | `bibliography`" in text
    # always (presence == 1) with closed single value
    assert "always `boolean`" in text
    # high-distinct identifier suppressed
    assert "open (free identifier or URL)" in text


def test_functional_groups_appear(seeded: tuple[Path, Path]) -> None:
    inventory, out = seeded
    text = render_data.render(inventory, out, today="2026-04-28")
    assert "### Document skeleton" in text
    assert "### Sections" in text
    assert "### Block content" in text
    # element placement: <div> goes to Sections, not Block content
    sections_idx = text.find("### Sections")
    block_idx = text.find("### Block content")
    div_idx = text.find("#### `<div>`")
    assert sections_idx < div_idx < block_idx


def test_findings_reframe_violations(seeded: tuple[Path, Path]) -> None:
    inventory, out = seeded
    text = render_data.render(inventory, out, today="2026-04-28")
    assert "Schema vs. corpus mismatches" in text
    assert "stale or the data has typos" in text


def test_unassigned_section_only_when_needed(seeded: tuple[Path, Path]) -> None:
    inventory, out = seeded
    text = render_data.render(inventory, out, today="2026-04-28")
    # The seed fixture's elements are all in groups; no unassigned section expected.
    assert "Unassigned elements" not in text


def test_unassigned_section_appears_for_unknown_element(tmp_path: Path) -> None:
    """An element that is in elements.json but not in any FUNCTIONAL_GROUP
    must surface in the catch-all 'Unassigned elements' section so it cannot
    silently drop off the document."""
    inventory = tmp_path / "inventory"
    out = tmp_path / "knowledge" / "data.md"
    _seed(inventory)
    # Append a fake element that no group claims.
    elems = json.loads((inventory / "elements.json").read_text(encoding="utf-8"))
    elems.append({"name": "phantom", "count": 1, "file_count": 1, "attributes": {}})
    (inventory / "elements.json").write_text(json.dumps(elems), encoding="utf-8")

    text = render_data.render(inventory, out, today="2026-04-28")
    assert "### Unassigned elements" in text
    assert "- `<phantom>`" in text


def test_findings_section_omitted_when_no_mismatches(tmp_path: Path) -> None:
    """If cross-reference reports no violations and no attrs-outside-P5,
    the entire 'Schema vs. corpus mismatches' section is dropped (we don't
    want a section that says '_None._')."""
    inventory = tmp_path / "inventory"
    out = tmp_path / "knowledge" / "data.md"
    _seed(inventory)
    # Override cross-reference.json to report a clean corpus.
    (inventory / "cross-reference.json").write_text(json.dumps({
        "summary": {
            "elements_total": 0,
            "elements_absent_from_p5": [],
            "elements_with_attrs_outside_p5": [],
            "elements_with_value_violations": [],
        },
        "elements": {},
    }), encoding="utf-8")

    text = render_data.render(inventory, out, today="2026-04-28")
    assert "Schema vs. corpus mismatches" not in text
