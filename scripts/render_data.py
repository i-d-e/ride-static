"""Render knowledge/data.md as a structure-and-knowledge reference.

Goal: someone (or a Python script) reading data.md should know how to walk
every part of the corpus correctly — what nests under what, what attributes
carry which values, where the anomalies are.

Quantities are intentionally avoided. They appear only where they encode a
categorical rule ("always", "in 7 specific files"). What matters is the
structural shape and the value space; counts of occurrences would just
distract from the rules a script needs.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
INVENTORY = REPO_ROOT / "inventory"
KNOWLEDGE = REPO_ROOT / "knowledge"
DATA_MD = KNOWLEDGE / "data.md"

# Each of the 77 elements appears in exactly one group, ordered top-down
# along the document structure (skeleton → header → body → editorial).
FUNCTIONAL_GROUPS: list[tuple[str, list[str]]] = [
    ("Document skeleton", ["TEI", "teiHeader", "text"]),
    ("Header — file description", [
        "fileDesc", "titleStmt", "publicationStmt", "seriesStmt",
        "notesStmt", "sourceDesc",
    ]),
    ("Header — encoding & classification", [
        "encodingDesc", "classDecl", "taxonomy", "category", "catDesc", "num",
    ]),
    ("Header — profile", [
        "profileDesc", "langUsage", "language", "textClass", "keywords",
        "term", "gloss",
    ]),
    ("Header — revision", ["revisionDesc", "listChange", "change"]),
    ("Sections", ["front", "body", "back", "div", "head"]),
    ("Block content", [
        "p", "list", "item", "table", "row", "cell", "figure", "graphic",
        "cit", "quote", "code", "lb", "space", "eg",
    ]),
    ("Inline content", ["emph", "ref", "hi", "note", "label"]),
    ("Bibliography apparatus", [
        "listBibl", "bibl", "title", "biblScope", "idno", "date",
        "publisher", "availability", "licence", "editor", "author",
        "respStmt", "resp", "relatedItem",
    ]),
    ("People & affiliation", [
        "persName", "forename", "surname", "name", "orgName", "placeName",
        "affiliation", "email",
    ]),
    ("Editorial markup", ["mod", "subst", "add", "del", "seg", "desc"]),
]


def _load(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


# Qualitative descriptors ---------------------------------------------------

def _presence(ratio: float) -> str:
    if ratio >= 0.95:
        return "always"
    if ratio >= 0.7:
        return "usually"
    if ratio >= 0.3:
        return "often"
    if ratio >= 0.05:
        return "occasionally"
    return "rare"


def _attr_values_label(attr_info: dict[str, Any]) -> str:
    distinct = attr_info.get("distinct", 0)
    values = attr_info.get("values", [])
    if not values:
        return ""
    if distinct == 1:
        return f"always `{values[0][0]}`"
    if attr_info.get("values_complete"):
        vals = [v for v, _ in values]
        return "values seen: " + " | ".join(f"`{v}`" for v in vals)
    if distinct > 50:
        return "open (free identifier or URL)"
    vals = [v for v, _ in values[:5]]
    suffix = " (and others)" if distinct > 5 else ""
    return "values: " + ", ".join(f"`{v}`" for v in vals) + suffix


def _attribute_lines(elem: dict[str, Any]) -> list[str]:
    attrs = elem.get("attributes", {})
    if not attrs:
        return []
    lines: list[str] = []
    for name, info in sorted(attrs.items(), key=lambda kv: (-kv[1].get("presence_ratio", 0), kv[0])):
        presence = _presence(info.get("presence_ratio", 0))
        values_label = _attr_values_label(info)
        line = f"  - `@{name}` — {presence}"
        if values_label:
            line += f"; {values_label}"
        lines.append(line)
    return lines


def _children_summary(struct: dict[str, Any]) -> str | None:
    count = struct.get("count", 0)
    if count == 0:
        return None
    if struct.get("leaf_count", 0) == count:
        return "Leaf — text content only."
    seqs = struct.get("child_sequences", [])
    children = struct.get("children", [])
    if not children:
        return None
    if seqs:
        top = seqs[0]
        ratio = top["count"] / count
        if ratio >= 0.95:
            return f"Children: `[{', '.join(top['sequence'])}]` (always)."
        if ratio >= 0.7 and len(seqs) >= 2:
            second = seqs[1]
            return (
                f"Children: typically `[{', '.join(top['sequence'])}]`; "
                f"sometimes `[{', '.join(second['sequence'])}]`."
            )
    names = [c for c, _ in children[:6]]
    return "Common children: " + ", ".join(f"`{c}`" for c in names) + "."


def _appears_under(struct: dict[str, Any]) -> str | None:
    paths = struct.get("ancestor_paths", [])
    if not paths:
        return None
    visible = [p for p, _ in paths[:3] if p]
    if not visible:
        return "Appears at document root."
    if len(visible) == 1:
        return f"Appears under `{visible[0]}`."
    return "Appears under " + ", ".join(f"`{p}`" for p in visible) + "."


# Pattern rules -------------------------------------------------------------

def _seq(struct: dict[str, Any], idx: int = 0) -> list[str] | None:
    seqs = struct.get("child_sequences", [])
    if idx < len(seqs):
        return seqs[idx]["sequence"]
    return None


def _build_pattern_rules(
    elements_by_name: dict[str, Any],
    structure: dict[str, Any],
    sections: dict[str, Any],
) -> list[str]:
    rules: list[str] = []

    tei = structure.get("TEI", {})
    seq = _seq(tei)
    if seq:
        rules.append(f"Document root is `<TEI>` with children `[{', '.join(seq)}]` (always).")

    text = structure.get("text", {})
    seqs = [_seq(text, i) for i in range(2)]
    seqs = [s for s in seqs if s]
    if seqs:
        rules.append(
            "`<text>` children appear in two shapes: `["
            + "]`, `[".join(", ".join(s) for s in seqs)
            + "]`. The shorter shape is reviews without back-matter. Code must accept both."
        )

    no_back = sorted({f["file"] for f in sections.get("files", []) if not (f.get("back") or [])})
    if no_back:
        files_md = ", ".join(f"`{n}`" for n in no_back)
        rules.append(
            f"{len(no_back)} reviews omit `<back>` entirely (no bibliography, no appendix): "
            f"{files_md}."
        )

    fd = structure.get("fileDesc", {})
    fd_seq = _seq(fd)
    if fd_seq:
        anomalies = [
            s for s in fd.get("child_sequences", [])[1:]
            if list(s["sequence"]) != list(fd_seq)
        ]
        rule = f"`<fileDesc>` children are `[{', '.join(fd_seq)}]` in fixed order."
        if anomalies:
            anom_seq = anomalies[0]["sequence"]
            extras = [c for c in anom_seq if anom_seq.count(c) > fd_seq.count(c)]
            if extras:
                rule += f" Anomaly: one review duplicates `<{extras[0]}>`."
        rules.append(rule)

    pubstmt = _seq(structure.get("publicationStmt", {}))
    if pubstmt:
        rules.append(f"`<publicationStmt>` children are `[{', '.join(pubstmt)}]` in every review.")

    num = elements_by_name.get("num")
    if num and num.get("attributes"):
        type_vals = [v for v, _ in num["attributes"].get("type", {}).get("values", [])]
        value_vals = [v for v, _ in num["attributes"].get("value", {}).get("values", [])]
        if type_vals and value_vals:
            rules.append(
                "`<num>` carries the RIDE questionnaire payload (the dominant element by occurrence). "
                "It always sits inside `<catDesc>` and always has `@type` ∈ {"
                + ", ".join(f"`{v}`" for v in type_vals)
                + "} with `@value` ∈ {"
                + ", ".join(f"`{v}`" for v in value_vals)
                + "}. `@value` outside `0` / `1` should be treated as a data anomaly."
            )

    cell = elements_by_name.get("cell")
    if cell:
        rows = cell.get("attributes", {}).get("rows", {})
        cols = cell.get("attributes", {}).get("cols", {})
        if rows.get("distinct") == 1 and cols.get("distinct") == 1:
            rules.append(
                "`<row>` and `<cell>` always carry `@rows=\"1\"` and `@cols=\"1\"`. "
                "No merged cells exist in this corpus; the attributes are redundant noise."
            )

    if sections.get("missing_head_count"):
        rules.append(
            "A non-trivial fraction of `<div>` elements lacks a `<head>` child. "
            "Code must derive a section title from `@xml:id` or position."
        )

    body_first = structure.get("body", {}).get("first_child", [])
    if body_first:
        names = [n for n, _ in body_first]
        if len(names) > 1:
            rules.append(
                f"`<body>` usually starts with `<{names[0]}>`, but in some reviews it starts with "
                + " or ".join(f"`<{n}>`" for n in names[1:3])
                + " — these are flat-content reviews (no top-level `<div>` wrapping)."
            )

    rules.append(
        "Classification chain: "
        "`<encodingDesc>` → `<classDecl>` → `<taxonomy>` → `<category>` (recursive) → "
        "`<catDesc>` → `<num>` | `<ref>` | `<gloss>`. "
        "This chain encodes the structured part of every RIDE review."
    )

    return rules


# Findings ------------------------------------------------------------------

def _build_findings(cross: dict[str, Any]) -> list[str]:
    out: list[str] = []
    summary = cross["summary"]

    for ident in summary.get("elements_with_attrs_outside_p5") or []:
        for a in cross["elements"][ident]["diff"]["attrs_outside_p5"]:
            out.append(
                f"`<{ident}>/@{a}` is not documented in TEI P5 — likely a custom or stale "
                f"attribute. Code should not rely on it."
            )

    for ident in summary.get("elements_with_value_violations") or []:
        diff = cross["elements"][ident]["diff"]["value_list_violations"]
        for att, info in diff.items():
            allowed = ", ".join(f"`{v}`" for v in info["allowed"])
            bad = ", ".join(f"`{v}`" for v, _ in info["empirical_unknown_values"])
            out.append(
                f"`<{ident}>/@{att}`: corpus uses {bad} which are not in the `ride.odd` "
                f"closed list [{allowed}]. Either the schema is stale or the data has typos."
            )

    return out


def render(inventory_dir: Path, out_path: Path, *, today: str | None = None) -> str:
    elements = _load(inventory_dir / "elements.json")
    structure = _load(inventory_dir / "structure.json")["by_element"]
    sections = _load(inventory_dir / "sections.json")
    cross = _load(inventory_dir / "cross-reference.json")

    elements_by_name = {e["name"]: e for e in elements}
    today = today or dt.date.today().isoformat()

    parts: list[str] = []
    parts.append("---")
    parts.append(f"generated: {today}")
    parts.append("source: scripts/render_data.py")
    parts.append("inputs:")
    for n in ("elements.json", "structure.json", "sections.json",
              "cross-reference.json", "odd-summary.json", "tei-spec.json"):
        parts.append(f"  - inventory/{n}")
    parts.append("---\n")

    parts.append("# RIDE TEI Structure Reference\n")
    parts.append(
        "> Structural knowledge for code that walks the RIDE corpus. "
        "Lists what each element contains, what attributes it carries, and the rules "
        "a script can rely on. Re-run `python scripts/render_data.py` after the inventory changes.\n"
    )

    parts.append("## Document patterns\n")
    parts.append("Rules that hold for every RIDE TEI document, derived from the inventory:\n")
    for r in _build_pattern_rules(elements_by_name, structure, sections):
        parts.append(f"- {r}")
    parts.append("")

    findings = _build_findings(cross)
    if findings:
        parts.append("## Schema vs. corpus mismatches\n")
        parts.append(
            "Cases where the empirical corpus does not match `ride.odd`. "
            "Each item is either a stale schema rule or a real data anomaly:\n"
        )
        for f in findings:
            parts.append(f"- {f}")
        parts.append("")

    parts.append("## Functional element reference\n")
    seen: set[str] = set()
    for group_name, members in FUNCTIONAL_GROUPS:
        present = [m for m in members if m in elements_by_name]
        if not present:
            continue
        parts.append(f"### {group_name}\n")
        for name in present:
            seen.add(name)
            elem = elements_by_name[name]
            struct = structure.get(name, {})
            parts.append(f"#### `<{name}>`")
            ctx = _appears_under(struct)
            if ctx:
                parts.append(f"- {ctx}")
            kids = _children_summary(struct)
            if kids:
                parts.append(f"- {kids}")
            attr_lines = _attribute_lines(elem)
            if attr_lines:
                parts.append("- Attributes:")
                parts.extend(attr_lines)
            parts.append("")
        parts.append("")

    unassigned = sorted(set(elements_by_name) - seen)
    if unassigned:
        parts.append("### Unassigned elements\n")
        parts.append("These elements appear in the corpus but are not yet placed in a functional group:\n")
        for name in unassigned:
            parts.append(f"- `<{name}>`")
        parts.append("")

    out = "\n".join(parts).rstrip() + "\n"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out, encoding="utf-8")
    return out


def main() -> None:
    text = render(INVENTORY, DATA_MD)
    print(f"Wrote {DATA_MD} ({len(text):,} chars)")


if __name__ == "__main__":
    main()
