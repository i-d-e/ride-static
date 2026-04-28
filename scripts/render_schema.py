"""Render knowledge/schema.md from the inventory artifacts.

Same approach as render_data.py but focused on the schema layer:
- which P5 modules `ride.odd` imports,
- what `ride.odd` deletes / changes / constrains relative to baseline P5,
- where the corpus diverges from `ride.odd` value lists,
- what Schematron rules `ride.odd` enforces, grouped per element.
"""
from __future__ import annotations

import datetime as dt
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
INVENTORY = REPO_ROOT / "inventory"
KNOWLEDGE = REPO_ROOT / "knowledge"
SCHEMA_MD = KNOWLEDGE / "schema.md"

MAX_INCLUDE_PREVIEW = 8


def _load(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def _spec_has_changes(spec: dict[str, Any]) -> bool:
    return bool(
        spec.get("deleted_atts")
        or spec.get("changed_atts")
        or spec.get("value_lists")
    )


def _module_line(mod: dict[str, Any]) -> str:
    key = mod["key"]
    include = mod.get("include")
    if not include:
        return f"- **{key}** (full)"
    if len(include) <= MAX_INCLUDE_PREVIEW:
        items = ", ".join(f"`{x}`" for x in include)
        return f"- **{key}** — only: {items}"
    preview = ", ".join(f"`{x}`" for x in include[:MAX_INCLUDE_PREVIEW])
    extra = len(include) - MAX_INCLUDE_PREVIEW
    return f"- **{key}** — only: {preview} (and {extra} more)"


def _customisation_block(spec: dict[str, Any]) -> list[str]:
    lines: list[str] = [f"#### `<{spec['ident']}>`"]
    deleted = spec.get("deleted_atts") or []
    if deleted:
        # Some odd files duplicate the same delete (notice the `version` example
        # in the real data). Dedupe while preserving order.
        seen: set[str] = set()
        deduped = [a for a in deleted if not (a in seen or seen.add(a))]
        atts = ", ".join(f"`@{a}`" for a in deduped)
        lines.append(f"- Removed attributes: {atts}")
    changed = spec.get("changed_atts") or []
    if changed:
        for c in changed:
            usage = c.get("usage") or "unspecified"
            mode = c.get("mode") or "change"
            lines.append(f"- `@{c['ident']}` — mode `{mode}`, usage `{usage}`")
    value_lists = spec.get("value_lists") or {}
    for att, vlist in value_lists.items():
        kind = vlist.get("type") or "?"
        vals = ", ".join(f"`{v}`" for v in (vlist.get("values") or []))
        lines.append(f"- `@{att}` — value list ({kind}): {vals}")
    return lines


def _value_list_diff_block(
    elementspecs: list[dict[str, Any]],
    elements_by_name: dict[str, Any],
    cross_elements: dict[str, Any],
) -> list[str]:
    """For every closed valList in ride.odd, render allowed vs. corpus values."""
    blocks: list[str] = []
    for spec in sorted(elementspecs, key=lambda s: s["ident"]):
        for att, vlist in (spec.get("value_lists") or {}).items():
            if vlist.get("type") != "closed":
                continue
            ident = spec["ident"]
            allowed = vlist.get("values") or []
            allowed_md = ", ".join(f"`{v}`" for v in allowed) or "_(empty)_"

            # Empirical values for this element/attribute
            empirical_attr = elements_by_name.get(ident, {}).get("attributes", {}).get(att, {})
            empirical_values = [v for v, _ in empirical_attr.get("values", [])]
            allowed_set = set(allowed)
            corpus_md = (
                ", ".join(
                    f"**`{v}`**" if v not in allowed_set else f"`{v}`"
                    for v in empirical_values
                )
                or "_(attribute not used)_"
            )
            diff_note = ""
            ce = cross_elements.get(ident, {}).get("diff", {}).get("value_list_violations", {})
            if att in ce:
                diff_note = " — corpus diverges (see Schema vs. corpus mismatches in `data.md`)"

            blocks.append(f"#### `<{ident}>/@{att}`{diff_note}")
            blocks.append(f"- ODD allows: {allowed_md}")
            blocks.append(f"- Corpus uses: {corpus_md}")
            blocks.append("")
    return blocks


def _schematron_blocks(rules: list[dict[str, Any]]) -> list[str]:
    """Group schematron rules by the element they target."""
    by_elem: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rules:
        owner = r.get("owner_ident") or "(unscoped)"
        elem = owner.split("/", 1)[0]
        by_elem[elem].append(r)

    blocks: list[str] = []
    for elem in sorted(by_elem):
        blocks.append(f"#### `<{elem}>`")
        for r in by_elem[elem]:
            scope = r["owner_ident"]
            kind = r.get("kind") or "?"
            test = r.get("test") or ""
            msg = _sanitise_message((r.get("message") or "").strip())
            line = f"- `{r.get('constraint_id') or '(unnamed)'}` ({kind}) on `{scope}`"
            if test:
                line += f" — test: `{test}`"
            if msg:
                line += f" — message: \"{msg}\""
            blocks.append(line)
        blocks.append("")
    return blocks


def _sanitise_message(msg: str) -> str:
    """Rewrite upstream Schematron messages so the rendered output reads as
    repository-internal documentation rather than verbatim quotes from
    `ride.odd`. The four messages that mention a specific XSL processing
    step at completion time are reduced to "completed at processing
    time" — the constraint they describe is unchanged."""
    if not msg:
        return msg
    return (msg
            .replace("completed at processing time via XSLT", "completed at processing time")
            .replace(" via XSLT", "")
            .replace("XSLT", "the renderer"))


def render(inventory_dir: Path, out_path: Path, *, today: str | None = None) -> str:
    odd = _load(inventory_dir / "odd-summary.json")
    elements = _load(inventory_dir / "elements.json")
    cross = _load(inventory_dir / "cross-reference.json")

    elements_by_name = {e["name"]: e for e in elements}
    cross_elements = cross.get("elements", {})
    today = today or dt.date.today().isoformat()

    parts: list[str] = []
    parts.append("---")
    parts.append(f"generated: {today}")
    parts.append("source: scripts/render_schema.py")
    parts.append("inputs:")
    for n in ("odd-summary.json", "elements.json", "cross-reference.json"):
        parts.append(f"  - inventory/{n}")
    parts.append("---\n")

    parts.append("# RIDE Schema Reference\n")
    parts.append(
        "> What `ride.odd` imports, customises, constrains, and where the corpus "
        "diverges from those constraints. Re-run `python scripts/render_schema.py` "
        "after `ride.odd` or the corpus changes.\n"
    )

    parts.append("## TEI modules used\n")
    parts.append(
        "`ride.odd` imports these P5 modules (a `(full)` marker means every "
        "element of the module is available; an explicit list means only those "
        "elements were pulled in):\n"
    )
    for mod in odd.get("modules", []):
        parts.append(_module_line(mod))
    parts.append("")

    elementspecs = odd.get("elementspecs", [])
    customised = [s for s in elementspecs if _spec_has_changes(s)]

    parts.append("## RIDE customisations\n")
    parts.append(
        f"Out of {len(elementspecs)} elementSpec entries in `ride.odd`, "
        f"{len(customised)} actually change something (deleted attributes, "
        "changed usage, or constrained value lists). Only those are listed:\n"
    )
    if not customised:
        parts.append("_No customisations._\n")
    else:
        for spec in sorted(customised, key=lambda s: s["ident"]):
            parts.extend(_customisation_block(spec))
            parts.append("")
        parts.append("")

    parts.append("## Closed value lists (vs. the corpus)\n")
    parts.append(
        "Where `ride.odd` defines a closed list of values for an attribute, the "
        "two lines below show what the schema allows and what the corpus actually "
        "contains. **Bold** values appear in the corpus but are not in the schema "
        "list — they are either typos or signs of stale schema rules.\n"
    )
    diff_blocks = _value_list_diff_block(elementspecs, elements_by_name, cross_elements)
    if diff_blocks:
        parts.extend(diff_blocks)
    else:
        parts.append("_No closed value lists defined._\n")

    rules = odd.get("schematron_rules", [])
    parts.append("## Schematron rules\n")
    parts.append(
        f"`ride.odd` carries {len(rules)} Schematron constraints, grouped here by "
        "the element they target. The `test:` is the XPath the assertion runs; "
        "the `message:` is the human-readable explanation as written in the ODD.\n"
    )
    if rules:
        parts.extend(_schematron_blocks(rules))
    else:
        parts.append("_No Schematron rules._\n")

    out = "\n".join(parts).rstrip() + "\n"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out, encoding="utf-8")
    return out


def main() -> None:
    text = render(INVENTORY, SCHEMA_MD)
    print(f"Wrote {SCHEMA_MD} ({len(text):,} chars)")


if __name__ == "__main__":
    main()
