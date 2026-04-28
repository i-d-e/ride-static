"""Classify ``<ref @target>`` targets and detect dangling internal anchors.

For every ``<ref>`` in the corpus, classifies the target into:

- ``internal`` — starts with ``#`` (anchor within the same file)
- ``external_url`` — starts with ``http://`` or ``https://``
- ``other`` — relative paths, ``mailto:`` schemes, doi: prefixes, etc.

For internal references, the script also checks whether the anchored
``xml:id`` exists in the same file. Dangling internal anchors break HTML
rendering and need to be surfaced before the build phase.

Output (in inventory/ at repo root):
  refs.json
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from lxml import etree

from _tei import XML_ID_ATTR, is_tei_element, localname

REPO_ROOT = Path(__file__).resolve().parent.parent
TEI_DIR = REPO_ROOT.parent / "ride" / "tei_all"
OUT_DIR = REPO_ROOT / "inventory"

DANGLING_SAMPLE_LIMIT = 50
OTHER_SAMPLE_LIMIT = 15

# Pull the leading alphabetic segment from `#name1.2` so dangling targets can
# be bucketed by family (e.g. K, div, fn, table) — useful when many dangling
# refs follow the same naming scheme (typically external-criteria references).
_PREFIX_RX = re.compile(r"^#([A-Za-z_]+)")


def _dangling_prefix(target: str) -> str:
    m = _PREFIX_RX.match(target)
    return m.group(1) if m else "(other)"


def _classify(target: str) -> str:
    if target.startswith("#"):
        return "internal"
    if target.startswith(("http://", "https://")):
        return "external_url"
    return "other"


def run(tei_dir: Path, out_dir: Path) -> dict[str, Any]:
    if not tei_dir.is_dir():
        raise SystemExit(f"TEI dir not found: {tei_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(tei_dir.glob("*.xml"))
    if not files:
        raise SystemExit(f"No .xml files in {tei_dir}")

    per_file: list[dict[str, Any]] = []
    cat_counts: Counter = Counter()
    domain_counts: Counter = Counter()
    other_samples: list[dict[str, Any]] = []
    dangling_samples: list[dict[str, Any]] = []
    dangling_prefix_buckets: Counter = Counter()
    distinct_external: set[str] = set()
    dangling_total = 0

    for path in files:
        try:
            tree = etree.parse(str(path))
        except etree.XMLSyntaxError as e:
            print(f"PARSE ERROR {path.name}: {e}")
            continue
        root = tree.getroot()

        ids_in_file: set[str] = {
            el.get(XML_ID_ATTR)
            for el in root.iter()
            if is_tei_element(el) and el.get(XML_ID_ATTR)
        }

        file_internal = file_external = file_other = file_dangling = 0
        for ref in root.iter():
            if not is_tei_element(ref) or localname(ref.tag) != "ref":
                continue
            target = ref.get("target")
            if not target:
                continue
            cat = _classify(target)
            cat_counts[cat] += 1
            if cat == "internal":
                file_internal += 1
                anchor = target[1:]
                if anchor not in ids_in_file:
                    dangling_total += 1
                    file_dangling += 1
                    dangling_prefix_buckets[_dangling_prefix(target)] += 1
                    if len(dangling_samples) < DANGLING_SAMPLE_LIMIT:
                        dangling_samples.append({
                            "file": path.name,
                            "target": target,
                            "ref_type": ref.get("type"),
                        })
            elif cat == "external_url":
                file_external += 1
                distinct_external.add(target)
                try:
                    domain = urlparse(target).netloc
                except Exception:
                    domain = ""
                if domain:
                    domain_counts[domain] += 1
            else:
                file_other += 1
                if len(other_samples) < OTHER_SAMPLE_LIMIT:
                    other_samples.append({
                        "file": path.name,
                        "target": target,
                        "ref_type": ref.get("type"),
                    })

        per_file.append({
            "file": path.name,
            "internal": file_internal,
            "external_url": file_external,
            "other": file_other,
            "dangling": file_dangling,
        })

    payload = {
        "summary": {
            "files_total": len(per_file),
            "ref_total": sum(cat_counts.values()),
            "internal_total": cat_counts.get("internal", 0),
            "external_url_total": cat_counts.get("external_url", 0),
            "other_total": cat_counts.get("other", 0),
            "dangling_internal_total": dangling_total,
            "external_distinct_targets": len(distinct_external),
        },
        "external_top_domains": domain_counts.most_common(20),
        "dangling_prefix_buckets": dangling_prefix_buckets.most_common(),
        "dangling_samples": dangling_samples,
        "other_samples": other_samples,
        "per_file": per_file,
    }
    (out_dir / "refs.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return payload


def main() -> None:
    payload = run(TEI_DIR, OUT_DIR)
    s = payload["summary"]
    print(f"Files scanned:           {s['files_total']}")
    print(f"<ref> total:             {s['ref_total']}")
    print(f"  internal:              {s['internal_total']}")
    print(f"    dangling:            {s['dangling_internal_total']}")
    print(f"  external URL:          {s['external_url_total']} ({s['external_distinct_targets']} distinct)")
    print(f"  other:                 {s['other_total']}")
    print(f"Top external domains:    {payload['external_top_domains'][:5]}")
    print(f"Dangling prefix buckets: {payload['dangling_prefix_buckets'][:5]}")
    print(f"Output:                  {OUT_DIR / 'refs.json'}")


if __name__ == "__main__":
    main()
