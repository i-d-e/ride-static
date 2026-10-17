"""Maintenance regressions driven by actual review XML and ODD rules.

Temporary copies introduce invalid variants of real data without changing
the published corpus. Asset bytes stand in for the resolver's file boundary.
"""

from pathlib import Path

import pytest
from lxml import etree

from src._corpus import find_tei
from src.parser.assets import rewrite_figure_assets
from src.parser.review import parse_review
from src.validate import validate_corpus

NS = {"t": "http://www.tei-c.org/ns/1.0"}
ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("slug", "directory"),
    [
        ("codex_sinaiticus", "codex_sinaiticus"),
        ("benjamin-digital", "benjamin-digital"),
        ("oxygen-framework", "oxygen-framework"),
        ("anemoskala", "anemoskala"),
        ("patrick-confessio", "confessio"),
    ],
)
def test_legacy_image_paths_resolve_real_corpus(tmp_path: Path, slug: str, directory: str) -> None:
    review = parse_review(find_tei(slug))
    pictures = (
        tmp_path / "ride" / "issues" / f"issue{int(review.issue):02d}" / directory / "pictures"
    )
    pictures.mkdir(parents=True)
    for figure in review.figures:
        if figure.graphic_url:
            name = figure.graphic_url.rsplit("/", 1)[-1]
            if slug == "anemoskala":
                name += ".png"
            (pictures / name).write_bytes(b"resolver boundary fixture")

    rewritten, report = rewrite_figure_assets(review, tmp_path / "ride", tmp_path / "site")
    assert report.copied
    assert not report.missing
    assert not report.unparseable
    for relative in report.copied:
        assert relative.suffix == ".png"
        assert (tmp_path / "site" / relative).read_bytes() == b"resolver boundary fixture"
    assert all(
        figure.graphic_url.startswith("/issues/")
        for figure in rewritten.figures
        if figure.graphic_url
    )


@pytest.mark.parametrize("legacy", [False, True])
@pytest.mark.parametrize(
    ("mutation", "rule"),
    [
        ("add", "ride.sch-add-context"),
        ("graphic", "jtei.sch-graphic-context"),
        ("identifier", "ride.sch-idno-publicationStmt"),
    ],
)
def test_existing_odd_rules_run_on_real_review(
    tmp_path: Path, mutation: str, rule: str, legacy: bool
) -> None:
    tree = etree.parse(str(ROOT / "issues/19/reviews/teicrafter-pilot/review.xml"))
    root = tree.getroot()
    if mutation == "identifier":
        publication = root.find("t:teiHeader/t:fileDesc/t:publicationStmt", NS)
        identifier = etree.SubElement(publication, f"{{{NS['t']}}}idno")
        identifier.set("type", "unexpected-regression-type")
        identifier.text = "Temporary invalid identifier"
    else:
        body = root.find("t:text/t:body", NS)
        element = etree.SubElement(body, f"{{{NS['t']}}}{mutation}")
        element.text = "Regression introduced in temporary copy"

    destination = tmp_path / "19/reviews" / ("legacy-tei.xml" if legacy else "test/review.xml")
    destination.parent.mkdir(parents=True)
    tree.write(str(destination), encoding="utf-8")
    report = validate_corpus(tmp_path)
    findings = [item for item in report.findings if rule in item.message]
    assert findings
    assert {item.severity for item in findings} == {"warning" if legacy else "error"}
    assert report.has_errors is (not legacy)


def test_unchanged_real_bundle_passes_odd_rules(tmp_path: Path) -> None:
    destination = tmp_path / "19/reviews/test/review.xml"
    destination.parent.mkdir(parents=True)
    destination.write_bytes((ROOT / "issues/19/reviews/teicrafter-pilot/review.xml").read_bytes())
    assert not validate_corpus(tmp_path).findings


def test_validation_does_not_silently_skip_missing_schema(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from src.build import _run_validation_layer

    def missing_schema(*args: object) -> None:
        raise FileNotFoundError("required schema missing")

    monkeypatch.setattr("src.build.validate_corpus", missing_schema)
    with pytest.raises(FileNotFoundError, match="required schema missing"):
        _run_validation_layer(tmp_path, (), validate=True, linkcheck=False)


def test_schematron_missing_source_rule_fails(tmp_path: Path) -> None:
    from src.validate import compile_schematron

    odd = tmp_path / "incomplete.odd"
    odd.write_text('<TEI xmlns="http://www.tei-c.org/ns/1.0"/>', encoding="utf-8")
    with pytest.raises(ValueError, match="Expected one ODD constraint"):
        compile_schematron(odd)


def test_preserved_legacy_figure_is_copied(tmp_path: Path) -> None:
    review = parse_review(find_tei("larepubblica"))
    _, report = rewrite_figure_assets(review, tmp_path / "absent-ride", tmp_path / "site")
    recovered = Path("issues") / review.issue / review.id / "figures/picture-8.png"
    assert recovered in report.copied
    assert (tmp_path / "site" / recovered).read_bytes().startswith(b"\x89PNG\r\n")


def test_legacy_diagnostics_detect_regression_and_allow_repairs() -> None:
    """Pure report comparison uses a real recorded validation finding."""
    import json
    from copy import deepcopy

    from scripts.check_legacy import check

    baseline = json.loads((ROOT / "config/legacy-findings.json").read_text(encoding="utf-8"))
    known = baseline["findings"][0]
    finding = {"file": known["file"], "message": known["message"], "severity": "warning"}
    report = {
        "validation": {"files_with_errors": 0, "findings": [finding] * known["occurrences"]},
        "assets": {"missing": 0, "unparseable": 0},
    }
    assert not check(report, baseline)
    repaired = deepcopy(report)
    repaired["validation"]["findings"] = []
    assert not check(repaired, baseline)
    report["validation"]["findings"].append(finding)
    assert any("New legacy finding" in error for error in check(report, baseline))
    report["assets"]["missing"] = 1
    assert any("Unresolved figure" in error for error in check(report, baseline))
    report["validation"] = None
    with pytest.raises(ValueError, match="validation enabled"):
        check(report, baseline)


def test_build_report_records_time_and_picture_checkout(tmp_path: Path) -> None:
    import json
    from datetime import datetime

    from src.build import _write_build_info
    from src.render.html import SiteConfig

    _write_build_info(out_root=tmp_path, site=SiteConfig(), reviews=(), asset_reports=[], failed=[])
    report = json.loads((tmp_path / "api/build-info.json").read_text(encoding="utf-8"))
    assert datetime.fromisoformat(report["build"]["built_at"]).tzinfo is not None
    assert set(report["build"]["picture_source"]) == {"commit", "dirty"}
