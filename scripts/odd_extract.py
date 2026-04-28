"""Extract structured information from ride.odd.

Outputs to .inventory/odd-summary.json:
  - included modules with element subsets
  - elementSpec customizations: deleted/added/changed attributes, closed value lists
  - all Schematron rules with context, assertion, message
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from lxml import etree

REPO_ROOT = Path(__file__).resolve().parent.parent
ODD = REPO_ROOT.parent / "ride" / "schema" / "ride.odd"
OUT = REPO_ROOT / ".inventory" / "odd-summary.json"

NSMAP = {
    "tei": "http://www.tei-c.org/ns/1.0",
    "sch": "http://purl.oclc.org/dsdl/schematron",
    "rng": "http://relaxng.org/ns/structure/1.0",
}


def normalize(s: str | None) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", s).strip()


def main() -> None:
    tree = etree.parse(str(ODD))
    root = tree.getroot()

    # Modules ---------------------------------------------------------------
    modules = []
    for mod in root.iterfind(".//tei:moduleRef", NSMAP):
        modules.append(
            {
                "key": mod.get("key"),
                "include": (mod.get("include") or "").split() if mod.get("include") else None,
            }
        )

    # Element specs ---------------------------------------------------------
    elementspecs = []
    for spec in root.iterfind(".//tei:elementSpec", NSMAP):
        ident = spec.get("ident")
        mode = spec.get("mode")
        module = spec.get("module")
        deleted_atts = []
        changed_atts = []
        added_value_lists = {}
        for att in spec.iterfind("tei:attList/tei:attDef", NSMAP):
            a_ident = att.get("ident")
            a_mode = att.get("mode")
            if a_mode == "delete":
                deleted_atts.append(a_ident)
            else:
                changed_atts.append({"ident": a_ident, "mode": a_mode, "usage": att.get("usage")})
                vlist = att.find("tei:valList", NSMAP)
                if vlist is not None:
                    items = [vi.get("ident") for vi in vlist.iterfind("tei:valItem", NSMAP)]
                    added_value_lists[a_ident] = {
                        "type": vlist.get("type"),
                        "mode": vlist.get("mode"),
                        "values": items,
                    }
        elementspecs.append(
            {
                "ident": ident,
                "mode": mode,
                "module": module,
                "deleted_atts": deleted_atts,
                "changed_atts": changed_atts,
                "value_lists": added_value_lists,
            }
        )

    # Schematron rules ------------------------------------------------------
    rules = []
    for cs in root.iterfind(".//tei:constraintSpec", NSMAP):
        if cs.get("scheme") != "schematron":
            continue
        ident = cs.get("ident")
        resp = cs.get("resp")
        # find ancestor elementSpec for context
        owner = cs
        owner_kind, owner_ident = None, None
        while owner is not None:
            if owner.tag == f"{{{NSMAP['tei']}}}elementSpec":
                owner_kind = "elementSpec"
                owner_ident = owner.get("ident")
                break
            if owner.tag == f"{{{NSMAP['tei']}}}attDef":
                owner_kind = "attDef"
                owner_ident = owner.get("ident")
                # walk further to find owning elementSpec
                p = owner.getparent()
                while p is not None and p.tag != f"{{{NSMAP['tei']}}}elementSpec":
                    p = p.getparent()
                if p is not None:
                    owner_ident = f"{p.get('ident')}/@{owner.get('ident')}"
                break
            owner = owner.getparent()

        for rule in cs.iterfind(".//sch:rule", NSMAP):
            ctx = rule.get("context")
            for child in rule:
                if not isinstance(child.tag, str):
                    continue
                tag = etree.QName(child).localname
                if tag in ("assert", "report"):
                    msg = normalize(" ".join(child.itertext()))
                    rules.append(
                        {
                            "constraint_id": ident,
                            "owner_kind": owner_kind,
                            "owner_ident": owner_ident,
                            "kind": tag,
                            "context": ctx,
                            "test": child.get("test"),
                            "message": msg,
                            "resp": resp,
                        }
                    )

    out = {
        "modules": modules,
        "element_count": len(elementspecs),
        "elementspecs": elementspecs,
        "schematron_rule_count": len(rules),
        "schematron_rules": rules,
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Modules:           {len(modules)}")
    print(f"ElementSpecs:      {len(elementspecs)}")
    print(f"Schematron rules:  {len(rules)}")
    print(f"Output:            {OUT}")


if __name__ == "__main__":
    main()
