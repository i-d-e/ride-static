"""Cross-reference empirical inventory × TEI P5 spec × RIDE ODD.

Produces a per-element report that joins what the corpus actually uses
(`elements.json`), what P5 normatively documents (`tei-spec.json`), and
what `ride.odd` customizes (`odd-summary.json`). The diff highlights
empirical attributes that aren't in P5, empirical values that violate
RIDE's closed value lists, and Schematron rules attached to each element.

Output (in inventory/ at repo root):
  cross-reference.json   {summary: ..., elements: {ident -> report}}
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "inventory"

ELEMENTS_JSON = OUT_DIR / "elements.json"
TEI_SPEC_JSON = OUT_DIR / "tei-spec.json"
ODD_SUMMARY_JSON = OUT_DIR / "odd-summary.json"
CROSS_REF_OUT = OUT_DIR / "cross-reference.json"


def _resolve_class_closure(start: list[str], attribute_classes: dict[str, Any]) -> list[str]:
    """Transitive closure over classSpecs' own ``classes`` lists."""
    seen: set[str] = set()
    order: list[str] = []
    stack = list(start)
    while stack:
        c = stack.pop(0)
        if c in seen or c not in attribute_classes:
            continue
        seen.add(c)
        order.append(c)
        stack.extend(attribute_classes[c].get("classes", []))
    return order


def _p5_attrs_for_element(p5_spec: dict[str, Any], attribute_classes: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Union of direct attDefs and the recursively-resolved class chain."""
    attrs: dict[str, dict[str, Any]] = {}
    for a in p5_spec.get("attributes_direct", []):
        attrs[a["ident"]] = {"source": "direct", "usage": a.get("usage"), "closed_values": a.get("closed_values")}
    for cls_ident in _resolve_class_closure(p5_spec.get("classes", []), attribute_classes):
        cls = attribute_classes[cls_ident]
        for a in cls.get("attributes", []):
            ident = a["ident"]
            if ident in attrs:
                continue
            attrs[ident] = {
                "source": f"class:{cls_ident}",
                "usage": a.get("usage"),
                "closed_values": a.get("closed_values"),
            }
    return attrs


def _odd_for_element(odd: dict[str, Any], ident: str) -> dict[str, Any] | None:
    for spec in odd.get("elementspecs", []):
        if spec.get("ident") == ident:
            return spec
    return None


def _schematron_rules_for_element(odd: dict[str, Any], ident: str) -> list[dict[str, Any]]:
    rules = []
    for r in odd.get("schematron_rules", []):
        owner = r.get("owner_ident") or ""
        # owner_ident is either "<element>" or "<element>/@<attr>"
        if owner == ident or owner.startswith(f"{ident}/"):
            rules.append(r)
    return rules


def _value_list_violations(empirical_values: list[list[Any]], allowed: list[str] | None) -> list[Any]:
    if not allowed:
        return []
    allowed_set = set(allowed)
    return [[v, n] for v, n in empirical_values if v not in allowed_set]


def run(
    elements_json: Path,
    tei_spec_json: Path,
    odd_summary_json: Path,
    out_path: Path,
) -> dict[str, Any]:
    elements = json.loads(elements_json.read_text(encoding="utf-8"))
    p5 = json.loads(tei_spec_json.read_text(encoding="utf-8"))
    odd = json.loads(odd_summary_json.read_text(encoding="utf-8"))

    p5_elements = p5["elements"]
    attribute_classes = p5["attribute_classes"]

    by_element: dict[str, Any] = {}
    elements_with_violations: list[str] = []
    elements_with_attrs_outside_p5: list[str] = []

    for emp in elements:
        ident = emp["name"]
        p5_spec = p5_elements.get(ident)

        if p5_spec is None:
            by_element[ident] = {
                "empirical": {"count": emp["count"], "file_count": emp["file_count"]},
                "p5": None,
                "ride_odd": None,
                "schematron": [],
                "diff": {"reason": "element absent from P5 subset"},
            }
            continue

        p5_attrs = _p5_attrs_for_element(p5_spec, attribute_classes)
        empirical_attrs = emp.get("attributes", {})

        attrs_outside_p5 = sorted(set(empirical_attrs.keys()) - set(p5_attrs.keys()))

        # RIDE ODD-defined closed value lists vs. empirical usage.
        odd_spec = _odd_for_element(odd, ident)
        value_violations: dict[str, Any] = {}
        if odd_spec:
            for att_ident, vlist in (odd_spec.get("value_lists") or {}).items():
                if vlist.get("type") != "closed":
                    continue
                allowed = vlist.get("values") or []
                empirical = empirical_attrs.get(att_ident, {}).get("values", [])
                violations = _value_list_violations(empirical, allowed)
                if violations:
                    value_violations[att_ident] = {
                        "allowed": allowed,
                        "empirical_unknown_values": violations,
                    }

        if value_violations:
            elements_with_violations.append(ident)
        if attrs_outside_p5:
            elements_with_attrs_outside_p5.append(ident)

        by_element[ident] = {
            "empirical": {
                "count": emp["count"],
                "file_count": emp["file_count"],
                "attrs_used": sorted(empirical_attrs.keys()),
            },
            "p5": {
                "module": p5_spec.get("module"),
                "gloss": p5_spec.get("gloss"),
                "desc": p5_spec.get("desc"),
                "classes": p5_spec.get("classes"),
                "attrs_available": p5_attrs,
            },
            "ride_odd": {
                "mode": odd_spec.get("mode") if odd_spec else None,
                "deleted_atts": odd_spec.get("deleted_atts") if odd_spec else [],
                "changed_atts": odd_spec.get("changed_atts") if odd_spec else [],
                "value_lists": odd_spec.get("value_lists") if odd_spec else {},
            } if odd_spec else None,
            "schematron": _schematron_rules_for_element(odd, ident),
            "diff": {
                "attrs_outside_p5": attrs_outside_p5,
                "value_list_violations": value_violations,
            },
        }

    payload = {
        "summary": {
            "elements_total": len(by_element),
            "elements_absent_from_p5": [n for n, e in by_element.items() if e["p5"] is None],
            "elements_with_attrs_outside_p5": elements_with_attrs_outside_p5,
            "elements_with_value_violations": elements_with_violations,
        },
        "elements": by_element,
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def main() -> None:
    payload = run(ELEMENTS_JSON, TEI_SPEC_JSON, ODD_SUMMARY_JSON, CROSS_REF_OUT)
    s = payload["summary"]
    print(f"Elements analysed:                 {s['elements_total']}")
    print(f"Elements absent from P5:           {s['elements_absent_from_p5'] or 'none'}")
    print(f"Elements with attrs outside P5:    {s['elements_with_attrs_outside_p5'] or 'none'}")
    print(f"Elements with value violations:    {s['elements_with_value_violations'] or 'none'}")
    print(f"Output:                            {CROSS_REF_OUT}")


if __name__ == "__main__":
    main()
