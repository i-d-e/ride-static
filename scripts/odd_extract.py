"""Extract structured information from ride.odd.

Walks the RIDE ODD customisation file and emits a JSON summary of:

- the TEI P5 modules pulled in (with optional include lists)
- elementSpec customisations (deleted attributes, changed attributes,
  closed value lists)
- every Schematron constraintSpec (rule context, test, message, owner
  element/attribute)

Output (in inventory/ at repo root):
  odd-summary.json
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lxml import etree

from _tei import TEI_NS, normalize

REPO_ROOT = Path(__file__).resolve().parent.parent
ODD = REPO_ROOT.parent / "ride" / "schema" / "ride.odd"
OUT_DIR = REPO_ROOT / "inventory"
ODD_SUMMARY_OUT = OUT_DIR / "odd-summary.json"

NSMAP = {
    "tei": TEI_NS,
    "sch": "http://purl.oclc.org/dsdl/schematron",
    "rng": "http://relaxng.org/ns/structure/1.0",
}


def _extract_modules(root: etree._Element) -> list[dict[str, Any]]:
    return [
        {
            "key": mod.get("key"),
            "include": (mod.get("include") or "").split() if mod.get("include") else None,
        }
        for mod in root.iterfind(".//tei:moduleRef", NSMAP)
    ]


def _extract_elementspecs(root: etree._Element) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for spec in root.iterfind(".//tei:elementSpec", NSMAP):
        deleted_atts: list[str] = []
        changed_atts: list[dict[str, Any]] = []
        value_lists: dict[str, dict[str, Any]] = {}
        for att in spec.iterfind("tei:attList/tei:attDef", NSMAP):
            a_ident = att.get("ident")
            a_mode = att.get("mode")
            if a_mode == "delete":
                deleted_atts.append(a_ident)
                continue
            changed_atts.append({"ident": a_ident, "mode": a_mode, "usage": att.get("usage")})
            vlist = att.find("tei:valList", NSMAP)
            if vlist is not None:
                value_lists[a_ident] = {
                    "type": vlist.get("type"),
                    "mode": vlist.get("mode"),
                    "values": [vi.get("ident") for vi in vlist.iterfind("tei:valItem", NSMAP)],
                }
        out.append({
            "ident": spec.get("ident"),
            "mode": spec.get("mode"),
            "module": spec.get("module"),
            "deleted_atts": deleted_atts,
            "changed_atts": changed_atts,
            "value_lists": value_lists,
        })
    return out


def _resolve_constraint_owner(cs: etree._Element) -> tuple[str | None, str | None]:
    """Walk up to find the owning elementSpec or attDef + element pair."""
    owner = cs
    tei_elementspec = f"{{{TEI_NS}}}elementSpec"
    tei_attdef = f"{{{TEI_NS}}}attDef"
    while owner is not None:
        if owner.tag == tei_elementspec:
            return "elementSpec", owner.get("ident")
        if owner.tag == tei_attdef:
            attr_ident = owner.get("ident")
            p = owner.getparent()
            while p is not None and p.tag != tei_elementspec:
                p = p.getparent()
            if p is not None:
                return "attDef", f"{p.get('ident')}/@{attr_ident}"
            return "attDef", attr_ident
        owner = owner.getparent()
    return None, None


def _extract_schematron_rules(root: etree._Element) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    for cs in root.iterfind(".//tei:constraintSpec", NSMAP):
        if cs.get("scheme") != "schematron":
            continue
        ident = cs.get("ident")
        resp = cs.get("resp")
        owner_kind, owner_ident = _resolve_constraint_owner(cs)
        for rule in cs.iterfind(".//sch:rule", NSMAP):
            ctx = rule.get("context")
            for child in rule:
                if not isinstance(child.tag, str):
                    continue
                tag = etree.QName(child).localname
                if tag in ("assert", "report"):
                    rules.append({
                        "constraint_id": ident,
                        "owner_kind": owner_kind,
                        "owner_ident": owner_ident,
                        "kind": tag,
                        "context": ctx,
                        "test": child.get("test"),
                        "message": normalize(" ".join(child.itertext())),
                        "resp": resp,
                    })
    return rules


def run(odd_path: Path, out_path: Path) -> dict[str, Any]:
    """Parse ``odd_path`` and write the summary JSON to ``out_path``."""
    if not odd_path.is_file():
        raise SystemExit(f"ODD not found: {odd_path}")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    tree = etree.parse(str(odd_path))
    root = tree.getroot()

    modules = _extract_modules(root)
    elementspecs = _extract_elementspecs(root)
    rules = _extract_schematron_rules(root)

    payload = {
        "modules": modules,
        "element_count": len(elementspecs),
        "elementspecs": elementspecs,
        "schematron_rule_count": len(rules),
        "schematron_rules": rules,
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def main() -> None:
    payload = run(ODD, ODD_SUMMARY_OUT)
    print(f"Modules:           {len(payload['modules'])}")
    print(f"ElementSpecs:      {payload['element_count']}")
    print(f"Schematron rules:  {payload['schematron_rule_count']}")
    print(f"Output:            {ODD_SUMMARY_OUT}")


if __name__ == "__main__":
    main()
