"""Structural inventory of the TEI corpus.

For each TEI element name, records what its children look like in practice:
direct child element names, the most common ordered child sequences, the
typical first/last child, the ancestor paths it appears under, and its
depth distribution. Output drives template/content-model decisions.

Output (in inventory/ at repo root):
  structure.json   element name -> {count, children, child_sequences,
                                   first_child, last_child, ancestor_paths,
                                   depth}
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from lxml import etree

TEI_NS = "http://www.tei-c.org/ns/1.0"

REPO_ROOT = Path(__file__).resolve().parent.parent
TEI_DIR = REPO_ROOT.parent / "ride" / "tei_all"
OUT_DIR = REPO_ROOT / "inventory"

TOP_CHILD_SEQUENCES = 20
TOP_ANCESTOR_PATHS = 10
TOP_CHILDREN = 30


def localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def is_tei_element(node: etree._Element) -> bool:
    return isinstance(node.tag, str) and node.tag.startswith(f"{{{TEI_NS}}}")


def child_element_names(node: etree._Element) -> list[str]:
    return [localname(c.tag) for c in node if is_tei_element(c)]


def ancestor_path(node: etree._Element) -> str:
    """Slash-joined names of TEI ancestors (root-to-parent), parent included."""
    names: list[str] = []
    cur = node.getparent()
    while cur is not None and is_tei_element(cur):
        names.append(localname(cur.tag))
        cur = cur.getparent()
    return "/".join(reversed(names))


def run(tei_dir: Path, out_dir: Path) -> dict[str, Any]:
    if not tei_dir.is_dir():
        raise SystemExit(f"TEI dir not found: {tei_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    by_element: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "count": 0,
            "children": Counter(),
            "child_sequences": Counter(),
            "first_child": Counter(),
            "last_child": Counter(),
            "ancestor_paths": Counter(),
            "depth": Counter(),
            "leaf_count": 0,
        }
    )

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

        for el in root.iter():
            if not is_tei_element(el):
                continue
            name = localname(el.tag)
            rec = by_element[name]
            rec["count"] += 1

            kids = child_element_names(el)
            if kids:
                rec["children"].update(kids)
                # Tuples are JSON-incompatible as keys but Counter keys are hashable;
                # we serialize them later.
                rec["child_sequences"][tuple(kids)] += 1
                rec["first_child"][kids[0]] += 1
                rec["last_child"][kids[-1]] += 1
            else:
                rec["leaf_count"] += 1

            depth = 0
            cur = el
            while cur.getparent() is not None:
                cur = cur.getparent()
                depth += 1
            rec["depth"][depth] += 1
            rec["ancestor_paths"][ancestor_path(el)] += 1

    out: dict[str, Any] = {}
    for name, rec in sorted(by_element.items(), key=lambda kv: -kv[1]["count"]):
        out[name] = {
            "count": rec["count"],
            "leaf_count": rec["leaf_count"],
            "children": rec["children"].most_common(TOP_CHILDREN),
            "child_sequences": [
                {"sequence": list(seq), "count": n}
                for seq, n in rec["child_sequences"].most_common(TOP_CHILD_SEQUENCES)
            ],
            "first_child": rec["first_child"].most_common(10),
            "last_child": rec["last_child"].most_common(10),
            "ancestor_paths": rec["ancestor_paths"].most_common(TOP_ANCESTOR_PATHS),
            "depth": sorted(rec["depth"].items()),
        }

    payload = {"element_count": len(out), "by_element": out}
    (out_dir / "structure.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return payload


def main() -> None:
    payload = run(TEI_DIR, OUT_DIR)
    print(f"Elements analyzed: {payload['element_count']}")
    print(f"Output:            {OUT_DIR / 'structure.json'}")


if __name__ == "__main__":
    main()
