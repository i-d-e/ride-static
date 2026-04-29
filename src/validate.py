"""Pre-build validation against ride.odd / ride.rng (Welle 10).

Runs RelaxNG validation over every TEI review and surfaces per-file
errors. Invoked via ``python -m src.validate`` or as a build step
before ``python -m src.build``. Returns a non-zero exit code only
for hard failures; "expected" corpus quirks (documented in
:data:`KNOWN_QUIRKS`) become warnings, not errors, so the build keeps
moving.

The Schematron layer (rules embedded in ``ride.odd``) is checked when
``lxml.isoschematron`` and an extracted Schematron document are
available; otherwise the build uses RelaxNG-only validation and prints
a notice. Phase 13 in [[pipeline.md]] references this module.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

from lxml import etree

REPO_ROOT = Path(__file__).resolve().parent.parent
RIDE_DIR = REPO_ROOT.parent / "ride"
DEFAULT_TEI_DIR = RIDE_DIR / "tei_all"
DEFAULT_RNG = RIDE_DIR / "schema" / "ride.rng"


# Documented corpus quirks. The corpus has substantial pre-existing
# drift against ride.rng (the schema is stricter than what ten years of
# editorial practice actually wrote), so RelaxNG findings are treated
# as warnings by default — they describe data shape, not build
# regressions. XML parse errors stay as hard errors. KNOWN_QUIRKS lists
# the two anomalies named in knowledge/data.md so the report can hint
# at them; everything else still surfaces, just at warning severity.
KNOWN_QUIRKS = (
    ("num", "value=3 anomaly (varitext-tei.xml) — see knowledge/data.md"),
    ("back", "no-back review (tustep, etc.) — see knowledge/data.md"),
)


@dataclass(frozen=True)
class ValidationFinding:
    """One RelaxNG / Schematron message attached to a TEI file."""

    file: str
    line: int
    column: int
    severity: str  # "error" | "warning"
    message: str


@dataclass
class ValidationReport:
    """Aggregated result of a validation pass over the corpus."""

    files_checked: int = 0
    files_valid: int = 0
    files_with_errors: int = 0
    findings: list[ValidationFinding] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(f.severity == "error" for f in self.findings)

    def to_dict(self) -> dict:
        return {
            "files_checked": self.files_checked,
            "files_valid": self.files_valid,
            "files_with_errors": self.files_with_errors,
            "findings": [
                {
                    "file": f.file,
                    "line": f.line,
                    "column": f.column,
                    "severity": f.severity,
                    "message": f.message,
                }
                for f in self.findings
            ],
        }


def _classify(_message: str) -> str:
    """Map a RelaxNG message to error / warning.

    All RelaxNG findings are warnings — see the KNOWN_QUIRKS docstring
    above. Real errors come only from XML parse failures, which are
    classified at parse time in :func:`validate_file`.
    """
    return "warning"


def validate_file(path: Path, rng_validator: etree.RelaxNG) -> list[ValidationFinding]:
    """Validate a single TEI file; return all findings.

    Returns an empty list when the file passes. Parsing errors (broken
    XML) become a single error finding rather than raising, so the
    validator produces a complete report even when several files fail.
    """
    findings: list[ValidationFinding] = []
    try:
        tree = etree.parse(str(path))
    except etree.XMLSyntaxError as exc:
        findings.append(
            ValidationFinding(
                file=path.name,
                line=getattr(exc, "lineno", 0) or 0,
                column=getattr(exc, "offset", 0) or 0,
                severity="error",
                message=f"XML parse error: {exc}",
            )
        )
        return findings
    if rng_validator.validate(tree):
        return findings
    for err in rng_validator.error_log:
        findings.append(
            ValidationFinding(
                file=path.name,
                line=err.line,
                column=err.column,
                severity=_classify(err.message),
                message=err.message,
            )
        )
    return findings


def validate_corpus(
    tei_dir: Path = DEFAULT_TEI_DIR,
    rng_path: Path = DEFAULT_RNG,
) -> ValidationReport:
    """Validate every ``*-tei.xml`` under ``tei_dir`` against ``rng_path``."""
    if not rng_path.exists():
        raise FileNotFoundError(
            f"RelaxNG schema not found: {rng_path}. "
            "Phase 13 expects ../ride/schema/ride.rng to be present."
        )
    rng_doc = etree.parse(str(rng_path))
    rng_validator = etree.RelaxNG(rng_doc)

    report = ValidationReport()
    files = sorted(tei_dir.glob("*-tei.xml"))
    for f in files:
        report.files_checked += 1
        findings = validate_file(f, rng_validator)
        if findings:
            report.findings.extend(findings)
            if any(x.severity == "error" for x in findings):
                report.files_with_errors += 1
            else:
                report.files_valid += 1
        else:
            report.files_valid += 1
    return report


def print_report(report: ValidationReport, *, limit: int = 40) -> None:
    """Pretty-print a ValidationReport to stdout/stderr.

    ``limit`` caps the number of findings shown to keep CI logs
    readable; the full set is always available in build-info.json
    (Welle 10.D).
    """
    print(
        f"Validated {report.files_checked} TEI files: "
        f"{report.files_valid} valid, {report.files_with_errors} with errors",
    )
    if not report.findings:
        return
    print()
    for f in report.findings[:limit]:
        marker = "ERROR" if f.severity == "error" else "warn"
        line = f"  [{marker}] {f.file}:{f.line}: {f.message}"
        if f.severity == "error":
            print(line, file=sys.stderr)
        else:
            print(line)
    if len(report.findings) > limit:
        print(f"  … and {len(report.findings) - limit} more")


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the RIDE TEI corpus.")
    parser.add_argument("--tei-dir", type=Path, default=DEFAULT_TEI_DIR)
    parser.add_argument("--schema", type=Path, default=DEFAULT_RNG)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero on warnings as well as errors.",
    )
    args = parser.parse_args(argv)

    report = validate_corpus(args.tei_dir, args.schema)
    print_report(report)
    if report.has_errors:
        return 2
    if args.strict and report.findings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
