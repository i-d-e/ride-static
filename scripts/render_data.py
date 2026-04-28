"""Render knowledge/data.md from the inventory/*.json artifacts.

Produces the human-readable corpus overview that lives in the Obsidian
vault. Re-run after any change to the corpus or extractor scripts.
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

LANGUAGE_NAMES = {"en": "English", "de": "German", "fr": "French", "it": "Italian"}


def _load(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def _md_table(rows: list[list[str]], header: list[str]) -> str:
    sep = ["---"] * len(header)
    return "\n".join(["| " + " | ".join(line) + " |" for line in [header, sep, *rows]])


def _percent(n: int, total: int) -> str:
    return f"{(n / total * 100):.0f}%" if total else "n/a"


def render(inventory_dir: Path, out_path: Path, *, today: str | None = None) -> str:
    elements = _load(inventory_dir / "elements.json")
    attributes = _load(inventory_dir / "attributes.json")
    stats = _load(inventory_dir / "corpus-stats.json")
    sections = _load(inventory_dir / "sections.json")
    cross = _load(inventory_dir / "cross-reference.json")
    structure = _load(inventory_dir / "structure.json")["by_element"]

    today = today or dt.date.today().isoformat()
    files_total = stats["files_total"]
    parts: list[str] = []

    # Frontmatter -----------------------------------------------------------
    parts.append("---")
    parts.append(f"generated: {today}")
    parts.append("source: scripts/render_data.py")
    parts.append("inputs:")
    for name in ("elements.json", "attributes.json", "corpus-stats.json",
                 "sections.json", "structure.json", "cross-reference.json"):
        parts.append(f"  - inventory/{name}")
    parts.append("---\n")

    parts.append("# RIDE Corpus Data\n")
    parts.append(
        "> Generated from `inventory/*.json`. Re-run `python scripts/render_data.py` "
        "whenever the corpus or extractor scripts change.\n"
    )

    # Overview --------------------------------------------------------------
    langs = ", ".join(f"{LANGUAGE_NAMES.get(code, code)} ({n})" for code, n in stats["review_languages"])
    issues_min, issues_max = (stats["issues"][0][0], stats["issues"][-1][0]) if stats["issues"] else (None, None)
    parts.append("## Overview\n")
    parts.append(f"- **Reviews:** {files_total}")
    parts.append(f"- **Total elements:** {stats['elements_total']:,}")
    parts.append(f"- **Distinct elements:** {stats['distinct_elements']}")
    parts.append(f"- **Distinct attributes:** {stats['distinct_attributes']}")
    parts.append(f"- **Publication dates:** {stats['publication_dates_min']} – {stats['publication_dates_max']}")
    parts.append(f"- **Issues:** {len(stats['issues'])} (no. {issues_min} – {issues_max})")
    parts.append(f"- **Languages:** {langs}")
    parts.append(f"- **Distinct editors (ORCID):** {stats['distinct_editors']}")
    licences = stats.get("licences") or []
    if licences:
        lic_target, lic_count = licences[0]
        parts.append(f"- **Licence:** {lic_target} ({lic_count}/{files_total})")
    parts.append("")

    # Sections --------------------------------------------------------------
    parts.append("## Section types (`<div type>`)\n")
    type_rows = [
        [t, str(n), _percent(n, files_total)]
        for t, n in sections["type_distribution"]
    ]
    parts.append(_md_table(type_rows, ["Type", "Count", "Coverage"]))
    parts.append("")
    parts.append(f"- **Sections without `<head>`:** {sections['missing_head_count']}")
    no_bib = sorted({
        f["file"] for f in sections["files"]
        if not any(s.get("type") == "bibliography"
                   for s in (f.get("back") or []) + (f.get("body") or []))
    })
    parts.append(f"- **Reviews without a bibliography section ({len(no_bib)}):** "
                 + (", ".join(f"`{n}`" for n in no_bib) if no_bib else "none"))
    parts.append("")

    # Top elements ----------------------------------------------------------
    parts.append("## Most-used elements (top 20)\n")
    rows = [
        [f"`{e['name']}`", f"{e['count']:,}", str(e['file_count'])]
        for e in elements[:20]
    ]
    parts.append(_md_table(rows, ["Element", "Occurrences", "Files"]))
    parts.append("")

    # Top attributes --------------------------------------------------------
    parts.append("## Most-used attributes (top 15)\n")
    rows = [
        [f"`@{a['name']}`", f"{a['count']:,}", str(a['distinct_values'])]
        for a in attributes[:15]
    ]
    parts.append(_md_table(rows, ["Attribute", "Occurrences", "Distinct values"]))
    parts.append("")

    # Findings --------------------------------------------------------------
    parts.append("## Findings\n")
    summary = cross["summary"]

    parts.append("### Attributes outside the P5 spec\n")
    outside = summary["elements_with_attrs_outside_p5"]
    if not outside:
        parts.append("_None._\n")
    else:
        for ident in outside:
            entry = cross["elements"][ident]
            attrs = entry["diff"]["attrs_outside_p5"]
            parts.append(f"- `<{ident}>`: {', '.join(f'`@{a}`' for a in attrs)}")
        parts.append("")

    parts.append("### Closed value-list violations (vs. `ride.odd`)\n")
    violators = summary["elements_with_value_violations"]
    if not violators:
        parts.append("_None._\n")
    else:
        for ident in violators:
            entry = cross["elements"][ident]
            for att, info in entry["diff"]["value_list_violations"].items():
                allowed = ", ".join(f"`{v}`" for v in info["allowed"])
                bad = ", ".join(f"`{v}`×{n}" for v, n in info["empirical_unknown_values"])
                parts.append(f"- `<{ident}>/@{att}`: corpus uses {bad}; ODD allows [{allowed}]")
        parts.append("")

    parts.append("### Sections without a `<head>`\n")
    parts.append(f"{sections['missing_head_count']} of all `<div>` sections have no immediate `<head>`. "
                 f"Templates must provide a fallback (e.g. derived from `xml:id` or position).\n")

    # Element index ---------------------------------------------------------
    parts.append("## Element index\n")
    parts.append("Compact reference for every element used in the corpus.\n")
    for e in sorted(elements, key=lambda x: x["name"]):
        name = e["name"]
        struct = structure.get(name, {})
        parts.append(f"### `<{name}>`")
        parts.append(f"- Occurrences: **{e['count']:,}** in {e['file_count']} review(s)")
        if e.get("attributes"):
            attr_summary = ", ".join(
                f"`@{a}` ({info['count']}, {info['presence_ratio']:.0%})"
                for a, info in sorted(e["attributes"].items(), key=lambda kv: -kv[1]["count"])
            )
            parts.append(f"- Attributes: {attr_summary}")
        top_kids = struct.get("children", [])[:5]
        if top_kids:
            kid_summary = ", ".join(f"`{k}`×{n}" for k, n in top_kids)
            parts.append(f"- Top children: {kid_summary}")
        top_seqs = struct.get("child_sequences", [])[:2]
        if top_seqs:
            seq_summary = "; ".join(
                f"`[{', '.join(s['sequence'])}]` ({s['count']})" for s in top_seqs
            )
            parts.append(f"- Frequent child sequences: {seq_summary}")
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
