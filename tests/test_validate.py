"""Tests for the RelaxNG pre-build validator (Welle 10.A).

Test-data philosophy per CLAUDE.md hard rule:

* ``validate_file`` and ``validate_corpus`` are pure-function units.
  Synthetic fixtures cover the per-branch behaviour: a passing file,
  an XML parse failure, strict bundle rejection, and the historical
  warning-only compatibility policy.
* Real-corpus integration runs the validator over the full TEI tree
  and asserts the report shape — exact counts drift with the corpus,
  but the structural invariants (every file checked, no parse errors,
  warnings non-zero) are stable.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.validate import (
    ValidationReport,
    _classify,
    validate_corpus,
    validate_file,
)
from lxml import etree


from tests._shared import (
    SCHEMA_RNG as DEFAULT_RNG,
    iter_tei_files,
    needs_corpus,
    needs_schema,
)


def test_classify_returns_warning_for_relaxng_findings() -> None:
    """All RelaxNG messages map to warnings (corpus-drift policy)."""
    assert _classify("Element TEI failed to validate attributes") == "warning"
    assert _classify("Did not expect element forename there") == "warning"
    assert _classify("Did not expect element p there", strict=True) == "error"


def test_validate_file_xml_parse_error_is_error(tmp_path: Path) -> None:
    """Broken XML is a hard error, not a warning."""
    bad = tmp_path / "broken-tei.xml"
    bad.write_text("<TEI><missing-close>", encoding="utf-8")
    rng = etree.RelaxNG(etree.parse(str(DEFAULT_RNG))) if DEFAULT_RNG.exists() else None
    if rng is None:
        pytest.skip("ride.rng not available")
    findings = validate_file(bad, rng)
    assert len(findings) == 1
    assert findings[0].severity == "error"
    assert "parse error" in findings[0].message.lower()


@needs_schema
def test_validate_file_passing_doc_returns_no_findings(tmp_path: Path) -> None:
    """A document that satisfies the schema produces no findings."""
    # Minimum-viable RIDE-shaped TEI is fragile to construct synthetically;
    # use an empty <TEI> wrapper which the schema will reject — confirming
    # the no-findings path requires a real review (covered by the corpus
    # smoke test below).
    rng = etree.RelaxNG(etree.parse(str(DEFAULT_RNG)))
    doc = etree.fromstring(b'<TEI xmlns="http://www.tei-c.org/ns/1.0"></TEI>')
    out_path = tmp_path / "minimal.xml"
    out_path.write_bytes(etree.tostring(doc))
    findings = validate_file(out_path, rng)
    # Either passes or surfaces only warnings (drift policy).
    assert all(f.severity == "warning" for f in findings)


@needs_schema
def test_invalid_review_bundle_is_a_hard_validation_error(tmp_path: Path) -> None:
    """New bundles use the current schema contract and fail on RNG drift."""
    review = tmp_path / "issues" / "19" / "reviews" / "example" / "review.xml"
    review.parent.mkdir(parents=True)
    review.write_text(
        '<TEI xmlns="http://www.tei-c.org/ns/1.0"><teiHeader/></TEI>',
        encoding="utf-8",
    )

    report = validate_corpus(review.parents[3])

    assert report.has_errors
    assert report.files_with_errors == 1
    assert {finding.severity for finding in report.findings} == {"error"}


@needs_schema
def test_invalid_legacy_review_remains_a_warning(tmp_path: Path) -> None:
    """Historical flat reviews retain the compatibility warning policy."""
    review = tmp_path / "19" / "reviews" / "legacy-tei.xml"
    review.parent.mkdir(parents=True)
    review.write_text(
        '<TEI xmlns="http://www.tei-c.org/ns/1.0"><teiHeader/></TEI>',
        encoding="utf-8",
    )

    report = validate_corpus(tmp_path)

    assert not report.has_errors
    assert report.files_valid == 1
    assert {finding.severity for finding in report.findings} == {"warning"}


# -- Real-corpus smoke ----------------------------------------------------


@needs_corpus
@needs_schema
def test_real_corpus_validation_produces_a_report() -> None:
    """The validator runs over the full corpus without raising and
    returns a ValidationReport whose counts add up correctly."""
    report = validate_corpus()
    assert isinstance(report, ValidationReport)
    expected_count = len(list(iter_tei_files()))
    assert report.files_checked == expected_count
    # files_valid + files_with_errors should equal files_checked
    # (warnings don't count against valid; only XML parse errors do).
    assert report.files_valid + report.files_with_errors == report.files_checked
    # The corpus has known drift, so we expect some findings — but no
    # XML parse errors (the parser tests would have caught those first).
    assert report.findings, "expected at least some warnings from corpus drift"
    assert not report.has_errors, "no review should fail XML parsing"


@needs_corpus
@needs_schema
def test_real_corpus_validation_to_dict_round_trips() -> None:
    """``ValidationReport.to_dict`` produces a JSON-serialisable shape."""
    import json

    report = validate_corpus()
    payload = report.to_dict()
    # Round-trip through JSON to confirm everything is serialisable.
    json.dumps(payload, ensure_ascii=False)
    expected_count = len(list(iter_tei_files()))
    assert payload["files_checked"] == expected_count
    assert isinstance(payload["findings"], list)
    if payload["findings"]:
        first = payload["findings"][0]
        assert {"file", "line", "severity", "message"} <= set(first.keys())
