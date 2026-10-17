"""Compare a build report with the recorded legacy validation findings.

This script-pipeline check records inherited schema drift without granting
editorial acceptance. New or multiplied findings and unresolved images fail;
resolved findings are allowed. Run after a complete build with picture sources.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE = ROOT / "config/legacy-findings.json"


def check(report: dict, baseline: dict) -> list[str]:
    """Return regressions while allowing existing findings to disappear."""
    if baseline["schema_version"] != 1:
        raise ValueError("Unsupported legacy baseline version")
    validation = report["validation"]
    if validation is None:
        raise ValueError("Legacy check requires a build with validation enabled")
    observed = Counter(
        (item["file"], item["message"])
        for item in validation["findings"]
        if item["severity"] == "warning"
    )
    known = Counter(
        {(item["file"], item["message"]): item["occurrences"] for item in baseline["findings"]}
    )
    errors = [
        f"New legacy finding ({count}): {file}: {message}"
        for (file, message), count in sorted((observed - known).items())
    ]
    if validation["files_with_errors"]:
        errors.append("Validation contains hard errors")
    for kind in ("missing", "unparseable"):
        if report["assets"][kind]:
            errors.append(f"Unresolved figure assets: {kind}={report['assets'][kind]}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=ROOT / "site/api/build-info.json")
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    args = parser.parse_args()
    errors = check(
        json.loads(args.report.read_text(encoding="utf-8")),
        json.loads(args.baseline.read_text(encoding="utf-8")),
    )
    for error in errors:
        print(f"ERROR: {error}")
    if not errors:
        print("Legacy diagnostics match the recorded findings; all figure sources resolved.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
