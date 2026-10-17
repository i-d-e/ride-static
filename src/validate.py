"""Pre-build validation against ride.odd / ride.rng (Welle 10).

Runs RelaxNG validation over every TEI review and surfaces per-file
errors. Invoked via ``python -m src.validate`` or as a build step
before ``python -m src.build``. New review bundles follow the current
ODD contract strictly. Findings in historical flat reviews remain
warnings so pre-existing corpus drift does not block the build.

The script pipeline also compiles the XPath-1-compatible context and
identifier-type rules directly from the existing ODD with lxml's ISO
Schematron engine. This bounded profile adds no editorial rules. The
remaining XPath 2 / XSLT-dependent constraints are outside this profile.
See knowledge/pipeline.md for the executed rule identifiers.
"""

from __future__ import annotations

import argparse
import sys
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

from lxml import etree, isoschematron

from src._corpus import is_review_bundle, iter_tei_files

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEI_DIR = REPO_ROOT / "issues"
DEFAULT_RNG = REPO_ROOT / "schema" / "ride.rng"
DEFAULT_ODD = REPO_ROOT / "schema" / "ride.odd"
SCHEMATRON_RULES = (
    "ride.sch-add-context",
    "jtei.sch-graphic-context",
    "ride.sch-idno-publicationStmt",
)
_TEI = "http://www.tei-c.org/ns/1.0"
_SCH = "http://purl.oclc.org/dsdl/schematron"
_SVRL = "http://purl.oclc.org/dsdl/svrl"


def compile_schematron(odd_path: Path = DEFAULT_ODD) -> isoschematron.Schematron:
    """Compile the explicit profile from ODD, failing if its source drifts.

    ISO Schematron is the deliberate XPath exception to the XML traversal
    convention. The engine evaluates existing assertions rather than a
    separate Python implementation of their meaning.
    """
    odd = etree.parse(str(odd_path))
    schema = etree.Element(f"{{{_SCH}}}schema", nsmap={"sch": _SCH}, queryBinding="xslt")
    etree.SubElement(schema, f"{{{_SCH}}}ns", prefix="tei", uri=_TEI)
    for identifier in SCHEMATRON_RULES:
        matches = odd.findall(f".//{{{_TEI}}}constraintSpec[@ident='{identifier}']")
        if len(matches) != 1:
            raise ValueError(f"Expected one ODD constraint {identifier}, found {len(matches)}")
        rules = matches[0].findall(f"{{{_TEI}}}constraint/{{{_SCH}}}rule")
        if not rules:
            raise ValueError(f"ODD constraint {identifier} has no executable rules")
        pattern = etree.SubElement(schema, f"{{{_SCH}}}pattern", id=identifier)
        for rule in rules:
            copied = deepcopy(rule)
            for assertion in copied.findall(f"{{{_SCH}}}assert"):
                assertion.set("id", identifier + "-assert")
            pattern.append(copied)
    return isoschematron.Schematron(schema, store_report=True)


@dataclass(frozen=True)
class ValidationFinding:
    """One XML or Relax NG message attached to a TEI file."""

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
            "schematron_rules": list(SCHEMATRON_RULES),
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


def _classify(_message: str, *, strict: bool = False) -> str:
    """Map a RelaxNG message to error / warning.

    Historical flat reviews retain the documented corpus-drift warning
    policy. Review bundles use the current ODD contract, so any Relax NG
    finding is a hard error.
    """
    return "error" if strict else "warning"


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.name


def validate_file(
    path: Path,
    rng_validator: etree.RelaxNG,
    *,
    strict: bool = False,
    schematron_validator: isoschematron.Schematron | None = None,
) -> list[ValidationFinding]:
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
                file=_display_path(path),
                line=getattr(exc, "lineno", 0) or 0,
                column=getattr(exc, "offset", 0) or 0,
                severity="error",
                message=f"XML parse error: {exc}",
            )
        )
        return findings
    rng_validator.validate(tree)
    for err in rng_validator.error_log:
        findings.append(
            ValidationFinding(
                file=_display_path(path),
                line=err.line,
                column=err.column,
                severity=_classify(err.message, strict=strict),
                message=err.message,
            )
        )
    if schematron_validator is not None and not schematron_validator.validate(tree):
        report = schematron_validator.validation_report
        for failure in report.iter(f"{{{_SVRL}}}failed-assert"):
            text = failure.find(f"{{{_SVRL}}}text")
            message = " ".join("".join(text.itertext()).split()) if text is not None else ""
            findings.append(
                ValidationFinding(
                    file=_display_path(path),
                    line=0,
                    column=0,
                    severity=_classify(message, strict=strict),
                    message=f"Schematron [{failure.get('id')}]: {message} "
                    f"at {failure.get('location')}",
                )
            )
    return findings


def validate_corpus(
    tei_dir: Path = DEFAULT_TEI_DIR,
    rng_path: Path = DEFAULT_RNG,
) -> ValidationReport:
    """Validate every legacy review and bundle TEI against ``rng_path``."""
    if not rng_path.exists():
        raise FileNotFoundError(
            f"RelaxNG schema not found: {rng_path}. Expected schema/ride.rng in the repo root."
        )
    rng_doc = etree.parse(str(rng_path))
    rng_validator = etree.RelaxNG(rng_doc)
    schematron_validator = compile_schematron()

    report = ValidationReport()
    files = list(iter_tei_files(tei_dir))
    for f in files:
        report.files_checked += 1
        findings = validate_file(
            f,
            rng_validator,
            strict=is_review_bundle(f),
            schematron_validator=schematron_validator,
        )
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
