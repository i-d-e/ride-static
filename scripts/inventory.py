"""TEI corpus inventory for ride-static.

Walks all TEI/XML files under issues/*/reviews/ and emits structured JSON
inventories used as the source of truth for knowledge/data.md.

Outputs (in inventory/ at repo root):
  elements.json      element name -> {count, files, parents, attributes, langs, samples}
  attributes.json    attribute name -> {count, on_elements, distinct_values}

Run from repo root or anywhere; paths are derived from this file's location.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from lxml import etree

from _tei import TEI_NS, XML_LANG_ATTR, attr_localname, localname, normalize

REPO_ROOT = Path(__file__).resolve().parent.parent
TEI_DIR = REPO_ROOT / "issues"
OUT_DIR = REPO_ROOT / "inventory"

MAX_SAMPLES_PER_ELEMENT = 3
MAX_FILES_LISTED = 10
MAX_DISTINCT_VALUES = 50
MAX_VALUES_PER_ELEMENT_ATTR = 10
SAMPLE_TEXT_LEN = 120

# Structuring attributes whose values should never be truncated, since they
# define section types, roles, and other classifiers consumed downstream.
STRUCTURING_ATTRS = frozenset({"type", "subtype", "role", "cert", "n"})


def text_sample(el: etree._Element) -> str:
    text = normalize("".join(el.itertext()))
    if len(text) > SAMPLE_TEXT_LEN:
        text = text[:SAMPLE_TEXT_LEN].rstrip() + "…"
    return text


def run(tei_dir: Path, out_dir: Path) -> dict[str, Any]:
    """Scan ``tei_dir`` and write inventory JSON files into ``out_dir``.

    Returns a small summary dict (file, element and attribute totals) so
    callers (tests, CLI) can assert on the scan without re-reading the
    written JSON.
    """
    if not tei_dir.is_dir():
        raise SystemExit(f"TEI dir not found: {tei_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    elements: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "count": 0,
            "files": set(),
            "parents": Counter(),
            "attributes": defaultdict(Counter),
            "langs": Counter(),
            "samples": [],
        }
    )
    attributes: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "count": 0,
            "on_elements": Counter(),
            "distinct_values": Counter(),
        }
    )

    files = sorted(tei_dir.glob("**/*.xml"))
    if not files:
        raise SystemExit(f"No .xml files in {tei_dir}")

    for path in files:
        try:
            tree = etree.parse(str(path))
        except etree.XMLSyntaxError as e:
            print(f"PARSE ERROR {path.name}: {e}")
            continue

        root = tree.getroot()

        for el in root.iter():
            if not isinstance(el.tag, str):
                continue  # comments, PIs
            if not el.tag.startswith(f"{{{TEI_NS}}}"):
                continue  # only TEI elements

            name = localname(el.tag)
            rec = elements[name]
            rec["count"] += 1
            rec["files"].add(path.name)

            parent = el.getparent()
            if parent is not None and isinstance(parent.tag, str):
                rec["parents"][localname(parent.tag)] += 1

            el_lang = el.get(XML_LANG_ATTR)
            if el_lang:
                rec["langs"][el_lang] += 1

            for attr_name, attr_val in el.attrib.items():
                a_local = attr_localname(attr_name)
                rec["attributes"][a_local][attr_val] += 1
                arec = attributes[a_local]
                arec["count"] += 1
                arec["on_elements"][name] += 1
                arec["distinct_values"][attr_val] += 1

            if len(rec["samples"]) < MAX_SAMPLES_PER_ELEMENT:
                snippet = text_sample(el)
                if snippet and not any(s["text"] == snippet for s in rec["samples"]):
                    rec["samples"].append({"file": path.name, "text": snippet})

    # Serialize -------------------------------------------------------------
    def el_serialize(name: str, rec: dict[str, Any]) -> dict[str, Any]:
        files_sorted = sorted(rec["files"])
        elem_count = rec["count"]
        attrs_out: dict[str, Any] = {}
        for a, c in rec["attributes"].items():
            a_count = sum(c.values())
            is_structuring = a in STRUCTURING_ATTRS
            cap = None if is_structuring else MAX_VALUES_PER_ELEMENT_ATTR
            attrs_out[a] = {
                "count": a_count,
                "presence_ratio": round(a_count / elem_count, 3) if elem_count else 0.0,
                "distinct": len(c),
                "values_complete": is_structuring,
                "values": c.most_common(cap),
            }
        return {
            "name": name,
            "count": elem_count,
            "file_count": len(rec["files"]),
            "files_sample": files_sorted[:MAX_FILES_LISTED],
            "parents": rec["parents"].most_common(10),
            "attributes": attrs_out,
            "langs": rec["langs"].most_common(),
            "samples": rec["samples"],
        }

    elements_out = [
        el_serialize(name, rec)
        for name, rec in sorted(elements.items(), key=lambda kv: -kv[1]["count"])
    ]

    attributes_out = [
        {
            "name": a,
            "count": rec["count"],
            "on_elements": rec["on_elements"].most_common(20),
            "distinct_values": len(rec["distinct_values"]),
            "top_values": rec["distinct_values"].most_common(MAX_DISTINCT_VALUES),
        }
        for a, rec in sorted(attributes.items(), key=lambda kv: -kv[1]["count"])
    ]

    (out_dir / "elements.json").write_text(
        json.dumps(elements_out, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (out_dir / "attributes.json").write_text(
        json.dumps(attributes_out, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    return {
        "files_total": len(files),
        "distinct_elements": len(elements),
        "distinct_attributes": len(attributes),
        "elements_total": sum(rec["count"] for rec in elements.values()),
    }


def main() -> None:
    summary = run(TEI_DIR, OUT_DIR)
    print(f"Files scanned:        {summary['files_total']}")
    print(f"Distinct elements:    {summary['distinct_elements']}")
    print(f"Distinct attributes:  {summary['distinct_attributes']}")
    print(f"Total elements:       {summary['elements_total']}")
    print(f"Output:               {OUT_DIR}")


if __name__ == "__main__":
    main()
