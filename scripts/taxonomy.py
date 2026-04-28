"""Extract the ``<taxonomy>`` trees that drive the RIDE questionnaire.

Each review embeds a ``<classDecl>/<taxonomy>`` in its header, defining the
criteria categories with ``@xml:id`` and ``<catDesc>`` children. Each
``<catDesc>`` carries a ``<num type="boolean" value="0"|"1">`` — the
review's answer for that category.

Taxonomies are grouped by ``@xml:base`` because RIDE has multiple criteria
sets (``criteria-version-1-1``, ``criteria-tools-version-1``,
``criteria-text-collections-version-1-0``) and a review uses whichever set
fits its reviewed resource.

Output (in inventory/ at repo root):
  taxonomy.json
    criteria_sets        per @xml:base: canonical category tree, depth, count
    review_to_criteria   per file: which criteria URLs and per-category answer
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from lxml import etree

from _tei import (
    TEI_NS,
    XML_BASE_ATTR,
    XML_ID_ATTR,
    is_tei_element,
    localname,
    normalize,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
TEI_DIR = REPO_ROOT.parent / "ride" / "tei_all"
OUT_DIR = REPO_ROOT / "inventory"


def _extract_category(category_el: etree._Element) -> dict[str, Any]:
    """Recursive build of the category tree (without @value answers)."""
    xml_id = category_el.get(XML_ID_ATTR)
    cat_desc_el = None
    children: list[dict[str, Any]] = []
    for child in category_el:
        if not is_tei_element(child):
            continue
        name = localname(child.tag)
        if name == "catDesc":
            cat_desc_el = child
        elif name == "category":
            children.append(_extract_category(child))

    gloss = None
    desc_text = None
    if cat_desc_el is not None:
        gloss_el = next(
            (c for c in cat_desc_el if is_tei_element(c) and localname(c.tag) == "gloss"),
            None,
        )
        if gloss_el is not None:
            gloss = normalize("".join(gloss_el.itertext())) or None
        desc_text = normalize("".join(cat_desc_el.itertext())) or None
        if len(desc_text or "") > 240:
            desc_text = desc_text[:240].rstrip() + "…"

    return {
        "xml_id": xml_id,
        "gloss": gloss,
        "desc": desc_text,
        "children": children,
    }


def _extract_answers(tax_el: etree._Element) -> dict[str, Any]:
    """Walk all <num> inside this taxonomy, return {category_xml_id: value}."""
    answers: dict[str, Any] = {}
    for cat in tax_el.iter(f"{{{TEI_NS}}}category"):
        cat_id = cat.get(XML_ID_ATTR)
        if not cat_id:
            continue
        # The <num> sits inside <catDesc>; iter() finds it whether one or many.
        num_el = next(iter(cat.iter(f"{{{TEI_NS}}}num")), None)
        if num_el is None:
            continue
        val = num_el.get("value")
        try:
            answers[cat_id] = int(val) if val is not None else None
        except ValueError:
            # Keep non-integer as string for diagnostics (e.g. "3" anomaly).
            answers[cat_id] = val
    return answers


def _shape(tree: list[dict[str, Any]]) -> Any:
    """Structural fingerprint: sequence of (xml_id, child_shape)."""
    return [(n["xml_id"], _shape(n["children"])) for n in tree]


def _max_depth(tree: list[dict[str, Any]], current: int = 1) -> int:
    if not tree:
        return current - 1
    return max(_max_depth(node["children"], current + 1) for node in tree)


def _count_categories(tree: list[dict[str, Any]]) -> int:
    return sum(1 + _count_categories(node["children"]) for node in tree)


def run(tei_dir: Path, out_dir: Path) -> dict[str, Any]:
    if not tei_dir.is_dir():
        raise SystemExit(f"TEI dir not found: {tei_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(tei_dir.glob("*.xml"))
    if not files:
        raise SystemExit(f"No .xml files in {tei_dir}")

    nsmap = {"t": TEI_NS}
    by_base: dict[str, list[dict[str, Any]]] = defaultdict(list)
    review_to_criteria: list[dict[str, Any]] = []

    for path in files:
        try:
            tree = etree.parse(str(path))
        except etree.XMLSyntaxError as e:
            print(f"PARSE ERROR {path.name}: {e}")
            continue
        root = tree.getroot()

        per_review_entries: list[dict[str, Any]] = []
        for tax_el in root.findall(".//t:taxonomy", nsmap):
            base = tax_el.get(XML_BASE_ATTR) or tax_el.get("base") or "(no base)"
            top_categories = [
                _extract_category(c)
                for c in tax_el
                if is_tei_element(c) and localname(c.tag) == "category"
            ]
            answers = _extract_answers(tax_el)
            by_base[base].append({
                "file": path.name,
                "categories": top_categories,
                "answers": answers,
            })
            per_review_entries.append({
                "criteria": base,
                "answers": answers,
            })
        if per_review_entries:
            review_to_criteria.append({
                "file": path.name,
                "taxonomies": per_review_entries,
            })

    criteria_sets: dict[str, Any] = {}
    for base, instances in sorted(by_base.items()):
        canonical = instances[0]["categories"]
        canonical_shape = _shape(canonical)
        deviating = [
            inst["file"] for inst in instances[1:]
            if _shape(inst["categories"]) != canonical_shape
        ]
        criteria_sets[base] = {
            "category_count": _count_categories(canonical),
            "max_depth": _max_depth(canonical),
            "review_count": len(instances),
            "structurally_deviating_reviews": deviating,
            "tree": canonical,
        }

    payload = {
        "criteria_sets": criteria_sets,
        "review_to_criteria": review_to_criteria,
    }
    (out_dir / "taxonomy.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return payload


def main() -> None:
    payload = run(TEI_DIR, OUT_DIR)
    print(f"Criteria sets: {len(payload['criteria_sets'])}")
    for base, info in payload["criteria_sets"].items():
        short = base if len(base) <= 70 else base[:67] + "…"
        print(f"  {short}")
        print(f"    {info['category_count']} categories, depth {info['max_depth']}, "
              f"used by {info['review_count']} taxonomy embeddings")
        if info["structurally_deviating_reviews"]:
            print(f"    structurally deviating: {info['structurally_deviating_reviews']}")
    print(f"Reviews with at least one taxonomy: {len(payload['review_to_criteria'])}")
    print(f"Output: {OUT_DIR / 'taxonomy.json'}")


if __name__ == "__main__":
    main()
