"""Extract TEI P5 normative spec for elements used in the RIDE corpus.

Downloads p5subset.xml from the TEI website (cached at
inventory/_cache/p5subset.xml) and emits a slimmed spec for the elements
that actually appear in the corpus (plus the attribute classes they
reference). The output is the normative baseline against which the
empirical inventory and ride.odd are cross-referenced in Phase C.

Output (in inventory/ at repo root):
  tei-spec.json   {used_elements_total, elements_in_p5, elements_missing_from_p5,
                   attribute_classes, elements: {ident -> spec}}
"""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path
from typing import Any

from lxml import etree

TEI_NS = "http://www.tei-c.org/ns/1.0"
P5_URL = "https://tei-c.org/release/xml/tei/odd/p5subset.xml"

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "inventory"
CACHE_DIR = OUT_DIR / "_cache"
P5_CACHE = CACHE_DIR / "p5subset.xml"
ELEMENTS_JSON = OUT_DIR / "elements.json"
ATTRIBUTES_JSON = OUT_DIR / "attributes.json"
TEI_SPEC_OUT = OUT_DIR / "tei-spec.json"


def fetch_p5(url: str = P5_URL, dest: Path = P5_CACHE) -> Path:
    """Download p5subset.xml unless a non-empty cached copy already exists."""
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url} ...")
    with urllib.request.urlopen(url) as resp:
        dest.write_bytes(resp.read())
    return dest


def _normalize(s: str | None) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _first_sentence(s: str) -> str:
    s = _normalize(s)
    m = re.match(r"^(.*?[.!?])(\s|$)", s)
    return m.group(1) if m else s


def _itertext(el: etree._Element | None) -> str:
    return "".join(el.itertext()) if el is not None else ""


def _extract_attdefs(parent: etree._Element, nsmap: dict[str, str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for att in parent.iterfind(".//tei:attDef", nsmap):
        ident = att.get("ident")
        usage = att.get("usage")  # opt | req | rec | mwa
        # Collect closed value list, if any.
        vlist = att.find("tei:valList", nsmap)
        values = None
        if vlist is not None and vlist.get("type") == "closed":
            values = [vi.get("ident") for vi in vlist.iterfind("tei:valItem", nsmap)]
        out.append({"ident": ident, "usage": usage, "closed_values": values})
    return out


def _extract_elementspec(spec: etree._Element, nsmap: dict[str, str]) -> dict[str, Any]:
    gloss_el = spec.find("tei:gloss", nsmap)
    desc_el = spec.find("tei:desc", nsmap)
    classes = [m.get("key") for m in spec.iterfind("tei:classes/tei:memberOf", nsmap) if m.get("key")]
    return {
        "ident": spec.get("ident"),
        "module": spec.get("module"),
        "gloss": _normalize(_itertext(gloss_el)) or None,
        "desc": _first_sentence(_itertext(desc_el)) or None,
        "classes": classes,
        "attributes_direct": _extract_attdefs(spec, nsmap),
    }


def run(p5_xml: Path, elements_json: Path, attributes_json: Path, out_path: Path) -> dict[str, Any]:
    used_elements = {e["name"] for e in json.loads(elements_json.read_text(encoding="utf-8"))}
    used_attrs = {a["name"] for a in json.loads(attributes_json.read_text(encoding="utf-8"))}

    tree = etree.parse(str(p5_xml))
    root = tree.getroot()
    nsmap = {"tei": TEI_NS}

    elements_out: dict[str, Any] = {}
    for spec in root.iterfind(".//tei:elementSpec", nsmap):
        ident = spec.get("ident")
        if ident in used_elements:
            elements_out[ident] = _extract_elementspec(spec, nsmap)

    # Build a full atts-class index, recording each class's own memberOf to
    # support recursive resolution downstream.
    all_att_classes: dict[str, dict[str, Any]] = {}
    for cs in root.iterfind(".//tei:classSpec", nsmap):
        if cs.get("type") != "atts":
            continue
        ident = cs.get("ident")
        all_att_classes[ident] = {
            "ident": ident,
            "module": cs.get("module"),
            "classes": [m.get("key") for m in cs.iterfind("tei:classes/tei:memberOf", nsmap) if m.get("key")],
            "attributes": _extract_attdefs(cs, nsmap),
        }

    # Resolve closure: every class transitively reachable from any class
    # referenced by a used element.
    referenced_classes: set[str] = {c for e in elements_out.values() for c in e["classes"]}
    closure: set[str] = set()
    stack = list(referenced_classes)
    while stack:
        c = stack.pop()
        if c in closure or c not in all_att_classes:
            continue
        closure.add(c)
        stack.extend(all_att_classes[c]["classes"])

    attribute_classes = {ident: all_att_classes[ident] for ident in closure}

    payload = {
        "p5_source": p5_xml.name,
        "used_elements_total": len(used_elements),
        "elements_in_p5": len(elements_out),
        "elements_missing_from_p5": sorted(used_elements - elements_out.keys()),
        "used_attributes_total": len(used_attrs),
        "attribute_classes": attribute_classes,
        "elements": elements_out,
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def main() -> None:
    p5 = fetch_p5()
    payload = run(p5, ELEMENTS_JSON, ATTRIBUTES_JSON, TEI_SPEC_OUT)
    print(f"P5 source:           {p5}")
    print(f"Used elements:       {payload['used_elements_total']}")
    print(f"Elements in P5:      {payload['elements_in_p5']}")
    print(f"Missing from P5:     {payload['elements_missing_from_p5'] or 'none'}")
    print(f"Attribute classes:   {len(payload['attribute_classes'])}")
    print(f"Output:              {TEI_SPEC_OUT}")


if __name__ == "__main__":
    main()
