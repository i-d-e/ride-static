"""TEI corpus inventory for ride-static.

Walks all TEI/XML files under ride/tei_all/ and emits structured JSON
inventories used as the source of truth for knowledge/data.md.

Outputs (in inventory/ at repo root):
  elements.json      element name -> {count, files, parents, attributes, langs, samples}
  attributes.json    attribute name -> {count, on_elements, distinct_values}
  corpus-stats.json  high-level corpus statistics

Run from repo root or anywhere; paths are derived from this file's location.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from lxml import etree

TEI_NS = "http://www.tei-c.org/ns/1.0"
XML_NS = "http://www.w3.org/XML/1998/namespace"

REPO_ROOT = Path(__file__).resolve().parent.parent
TEI_DIR = REPO_ROOT.parent / "ride" / "tei_all"
OUT_DIR = REPO_ROOT / "inventory"

MAX_SAMPLES_PER_ELEMENT = 3
MAX_FILES_LISTED = 10
MAX_DISTINCT_VALUES = 50
MAX_VALUES_PER_ELEMENT_ATTR = 10
SAMPLE_TEXT_LEN = 120

# Structuring attributes whose values should never be truncated, since they
# define section types, roles, and other classifiers consumed downstream.
STRUCTURING_ATTRS = frozenset({"type", "subtype", "role", "cert", "n"})


def localname(tag: str) -> str:
    """Strip namespace from a Clark-notation tag."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def attr_localname(name: str) -> str:
    """Render attribute name with `xml:` prefix preserved, others stripped."""
    if name.startswith(f"{{{XML_NS}}}"):
        return "xml:" + name[len(XML_NS) + 2 :]
    return localname(name)


def normalize_text(s: str | None) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", s).strip()


def text_sample(el: etree._Element) -> str:
    text = normalize_text("".join(el.itertext()))
    if len(text) > SAMPLE_TEXT_LEN:
        text = text[:SAMPLE_TEXT_LEN].rstrip() + "…"
    return text


def run(tei_dir: Path, out_dir: Path) -> dict[str, Any]:
    """Scan ``tei_dir`` and write inventory JSON files into ``out_dir``.

    Returns the corpus_stats dict so callers (tests, CLIs) can assert on it.
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

    file_stats: list[dict[str, Any]] = []
    root_langs: Counter = Counter()
    publication_dates: list[str] = []
    issue_numbers: Counter = Counter()
    review_languages: Counter = Counter()
    licences: Counter = Counter()
    editor_orcids: set[str] = set()

    files = sorted(tei_dir.glob("*.xml"))
    if not files:
        raise SystemExit(f"No .xml files in {tei_dir}")

    for path in files:
        try:
            tree = etree.parse(str(path))
        except etree.XMLSyntaxError as e:
            print(f"PARSE ERROR {path.name}: {e}")
            continue

        root = tree.getroot()
        nsmap = {"t": TEI_NS}
        file_record: dict[str, Any] = {
            "file": path.name,
            "elements": 0,
            "depth": 0,
            "lang": None,
        }

        # Per-file metadata
        lang_el = root.find(".//t:profileDesc/t:langUsage/t:language", nsmap)
        if lang_el is not None and lang_el.get("ident"):
            file_record["lang"] = lang_el.get("ident")
            review_languages[lang_el.get("ident")] += 1

        for date_el in root.findall(".//t:publicationStmt/t:date", nsmap):
            when = date_el.get("when") or normalize_text(date_el.text)
            if when:
                publication_dates.append(when)

        for biblscope in root.findall(".//t:seriesStmt/t:biblScope", nsmap):
            n = biblscope.get("n")
            if n:
                issue_numbers[n] += 1

        for licence in root.findall(".//t:availability/t:licence", nsmap):
            target = licence.get("target")
            if target:
                licences[target] += 1

        for editor in root.findall(".//t:seriesStmt/t:editor", nsmap):
            ref = editor.get("ref")
            if ref:
                editor_orcids.add(ref)

        if (xml_lang := root.get(f"{{{XML_NS}}}lang")):
            root_langs[xml_lang] += 1

        max_depth = 0
        for el in root.iter():
            if not isinstance(el.tag, str):
                continue  # comments, PIs
            if not el.tag.startswith(f"{{{TEI_NS}}}"):
                continue  # only TEI elements

            name = localname(el.tag)
            rec = elements[name]
            rec["count"] += 1
            rec["files"].add(path.name)
            file_record["elements"] += 1

            parent = el.getparent()
            if parent is not None and isinstance(parent.tag, str):
                rec["parents"][localname(parent.tag)] += 1

            depth = 0
            cur = el
            while cur.getparent() is not None:
                cur = cur.getparent()
                depth += 1
            if depth > max_depth:
                max_depth = depth

            el_lang = el.get(f"{{{XML_NS}}}lang")
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

        file_record["depth"] = max_depth
        file_stats.append(file_record)

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

    corpus_stats = {
        "files_total": len(file_stats),
        "elements_total": sum(f["elements"] for f in file_stats),
        "distinct_elements": len(elements),
        "distinct_attributes": len(attributes),
        "review_languages": review_languages.most_common(),
        "issues": sorted(issue_numbers.most_common(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 0),
        "publication_dates_min": min(publication_dates) if publication_dates else None,
        "publication_dates_max": max(publication_dates) if publication_dates else None,
        "licences": licences.most_common(),
        "distinct_editors": len(editor_orcids),
        "files_size": [
            {"file": f["file"], "elements": f["elements"], "depth": f["depth"], "lang": f["lang"]}
            for f in sorted(file_stats, key=lambda x: -x["elements"])
        ],
    }

    (out_dir / "elements.json").write_text(
        json.dumps(elements_out, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (out_dir / "attributes.json").write_text(
        json.dumps(attributes_out, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (out_dir / "corpus-stats.json").write_text(
        json.dumps(corpus_stats, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    return corpus_stats


def main() -> None:
    corpus_stats = run(TEI_DIR, OUT_DIR)
    print(f"Files scanned:        {corpus_stats['files_total']}")
    print(f"Distinct elements:    {corpus_stats['distinct_elements']}")
    print(f"Distinct attributes:  {corpus_stats['distinct_attributes']}")
    print(f"Total elements:       {corpus_stats['elements_total']}")
    print(f"Review languages:     {corpus_stats['review_languages']}")
    print(f"Date range:           {corpus_stats['publication_dates_min']} .. {corpus_stats['publication_dates_max']}")
    print(f"Output:               {OUT_DIR}")


if __name__ == "__main__":
    main()
