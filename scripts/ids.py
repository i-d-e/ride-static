"""Per-file xml:id audit: parse-validity and format conformance.

Walks every TEI file and:

- Surfaces XML parse errors (lxml validates ``xml:id`` uniqueness at parse
  time as part of the XML spec — duplicate IDs raise ``XMLSyntaxError``,
  so the only files we cannot scan are exactly those that violate the
  uniqueness constraint).
- Validates the format of IDs that carry a known pattern from ``ride.odd``'s
  Schematron rules (``TEI/@xml:id``, ``div/@xml:id``).

Output (in inventory/ at repo root):
  ids.json   {summary, parse_errors, per_file}
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from lxml import etree

from _tei import XML_ID_ATTR, is_tei_element, localname

REPO_ROOT = Path(__file__).resolve().parent.parent
TEI_DIR = REPO_ROOT.parent / "ride" / "tei_all"
OUT_DIR = REPO_ROOT / "inventory"

# Format patterns extracted from ride.odd's Schematron. Keys are element
# names; values are compiled Python regexes. Add new patterns here as we
# discover/validate them in odd-summary.json.
FORMAT_PATTERNS: dict[str, re.Pattern[str]] = {
    "TEI": re.compile(r"^ride\.\d{1,2}\.\d{1,2}$"),
    "div": re.compile(r"^div\d{1,2}(\.\d{1,2}){0,2}$"),
}


def run(tei_dir: Path, out_dir: Path) -> dict[str, Any]:
    if not tei_dir.is_dir():
        raise SystemExit(f"TEI dir not found: {tei_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(tei_dir.glob("*.xml"))
    if not files:
        raise SystemExit(f"No .xml files in {tei_dir}")

    per_file: list[dict[str, Any]] = []
    parse_errors: list[dict[str, str]] = []
    files_with_format_violations = 0
    violations_by_element: Counter = Counter()
    ids_total = 0

    for path in files:
        try:
            tree = etree.parse(str(path))
        except etree.XMLSyntaxError as e:
            parse_errors.append({"file": path.name, "error": str(e)})
            continue
        root = tree.getroot()

        format_violations: list[dict[str, Any]] = []
        file_id_count = 0
        for el in root.iter():
            if not is_tei_element(el):
                continue
            id_value = el.get(XML_ID_ATTR)
            if id_value is None:
                continue
            file_id_count += 1
            ids_total += 1
            elem_name = localname(el.tag)
            pattern = FORMAT_PATTERNS.get(elem_name)
            if pattern is not None and not pattern.match(id_value):
                format_violations.append({
                    "id": id_value,
                    "element": elem_name,
                    "expected": pattern.pattern,
                })
                violations_by_element[elem_name] += 1

        if format_violations:
            files_with_format_violations += 1

        per_file.append({
            "file": path.name,
            "ids_total": file_id_count,
            "format_violations": format_violations,
        })

    payload = {
        "summary": {
            "files_total": len(per_file),
            "files_unparseable": len(parse_errors),
            "ids_total": ids_total,
            "files_with_format_violations": files_with_format_violations,
            "format_violations_total": sum(violations_by_element.values()),
            "violations_by_element": dict(violations_by_element.most_common()),
            "patterns_checked": {k: v.pattern for k, v in FORMAT_PATTERNS.items()},
        },
        "parse_errors": parse_errors,
        "per_file": per_file,
    }
    (out_dir / "ids.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return payload


def main() -> None:
    payload = run(TEI_DIR, OUT_DIR)
    s = payload["summary"]
    print(f"Files scanned:               {s['files_total']}")
    print(f"Files unparseable:           {s['files_unparseable']}")
    print(f"Total xml:ids:               {s['ids_total']}")
    print(f"Files with format issues:    {s['files_with_format_violations']}")
    print(f"Format violations by elem:   {s['violations_by_element'] or 'none'}")
    print(f"Output:                      {OUT_DIR / 'ids.json'}")


if __name__ == "__main__":
    main()
