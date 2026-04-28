"""Section tree of every review.

Walks every TEI file and captures the nested <div> structure under
text/{front,body,back}: section type, optional @subtype, xml:id, and the
text of <head>. The output drives the table-of-contents and section
templates, and reveals the empirical canon of section types used across
RIDE.

Output (in inventory/ at repo root):
  sections.json   {files: [...], type_distribution: [...],
                   missing_head_count: int}
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from lxml import etree

from _tei import TEI_NS, XML_ID_ATTR, localname, normalize

REPO_ROOT = Path(__file__).resolve().parent.parent
TEI_DIR = REPO_ROOT.parent / "ride" / "tei_all"
OUT_DIR = REPO_ROOT / "inventory"

HEAD_TEXT_LEN = 200


def head_text(div: etree._Element) -> str | None:
    """Concatenated text of the immediate <head> child(ren), if any."""
    heads = [c for c in div if isinstance(c.tag, str) and localname(c.tag) == "head"]
    if not heads:
        return None
    text = " / ".join(normalize("".join(h.itertext())) for h in heads if "".join(h.itertext()).strip())
    if len(text) > HEAD_TEXT_LEN:
        text = text[:HEAD_TEXT_LEN].rstrip() + "…"
    return text or None


def child_divs(div: etree._Element) -> list[etree._Element]:
    return [c for c in div if isinstance(c.tag, str) and localname(c.tag) == "div"]


def section_node(div: etree._Element, depth: int, type_counter: Counter, missing_head: list[int]) -> dict[str, Any]:
    head = head_text(div)
    if head is None:
        missing_head[0] += 1
    div_type = div.get("type")
    if div_type:
        type_counter[div_type] += 1
    return {
        "type": div_type,
        "subtype": div.get("subtype"),
        "xml_id": div.get(XML_ID_ATTR),
        "head": head,
        "depth": depth,
        "children": [section_node(c, depth + 1, type_counter, missing_head) for c in child_divs(div)],
    }


def run(tei_dir: Path, out_dir: Path) -> dict[str, Any]:
    if not tei_dir.is_dir():
        raise SystemExit(f"TEI dir not found: {tei_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    files_out: list[dict[str, Any]] = []
    type_counter: Counter = Counter()
    missing_head = [0]

    files = sorted(tei_dir.glob("*.xml"))
    if not files:
        raise SystemExit(f"No .xml files in {tei_dir}")

    nsmap = {"t": TEI_NS}
    for path in files:
        try:
            tree = etree.parse(str(path))
        except etree.XMLSyntaxError as e:
            print(f"PARSE ERROR {path.name}: {e}")
            continue

        root = tree.getroot()
        file_record: dict[str, Any] = {"file": path.name, "front": [], "body": [], "back": []}
        for region in ("front", "body", "back"):
            container = root.find(f".//t:text/t:{region}", nsmap)
            if container is None:
                continue
            file_record[region] = [
                section_node(d, 1, type_counter, missing_head)
                for d in child_divs(container)
            ]
        files_out.append(file_record)

    payload = {
        "file_count": len(files_out),
        "type_distribution": type_counter.most_common(),
        "missing_head_count": missing_head[0],
        "files": files_out,
    }
    (out_dir / "sections.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return payload


def main() -> None:
    payload = run(TEI_DIR, OUT_DIR)
    print(f"Files scanned:        {payload['file_count']}")
    print(f"Section types:        {payload['type_distribution']}")
    print(f"Sections missing head: {payload['missing_head_count']}")
    print(f"Output:               {OUT_DIR / 'sections.json'}")


if __name__ == "__main__":
    main()
