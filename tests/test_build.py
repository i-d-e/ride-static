"""Tests for ``src.build`` — focused on the build-report writer.

The full ``build()`` orchestrator is exercised by the real-corpus
integration runs in CI. These tests pin the small but load-bearing
contracts that callers (CI, downstream consumers of build-info.json)
depend on, without spinning up a full corpus parse.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.build import (
    BuildFailure,
    REPO_ROOT,
    _raise_for_hard_failures,
    _remove_excluded_draft_outputs,
    _run_validation_layer,
    _write_build_info,
)
from src.parser.assets import AssetReport
from src.render.corpus_dump import LICENCE_NAME, LICENCE_URL
from src.render.html import BuildInfo, SiteConfig
from src.validate import ValidationFinding, ValidationReport


def test_publication_build_removes_stale_draft_page_and_wordcloud(tmp_path: Path) -> None:
    review = SimpleNamespace(is_draft=True, issue="19", id="draft.example")
    page = tmp_path / "issues" / "19" / "draft.example" / "index.html"
    wordcloud = tmp_path / "static" / "images" / "wordclouds" / "draft.example.png"
    draft_index = tmp_path / "drafts" / "index.html"
    page.parent.mkdir(parents=True)
    wordcloud.parent.mkdir(parents=True)
    draft_index.parent.mkdir(parents=True)
    page.write_text("draft", encoding="utf-8")
    wordcloud.write_bytes(b"draft")
    draft_index.write_text("stale", encoding="utf-8")

    _remove_excluded_draft_outputs([(tmp_path / "review.xml", review)], tmp_path)

    assert not page.parent.exists()
    assert not wordcloud.exists()
    assert not draft_index.parent.exists()


def test_build_validation_uses_the_local_compiled_schema(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, Path] = {}

    def fake_validate_corpus(corpus_dir: Path, schema_path: Path) -> ValidationReport:
        captured["corpus"] = corpus_dir
        captured["schema"] = schema_path
        return ValidationReport()

    monkeypatch.setattr("src.build.validate_corpus", fake_validate_corpus)

    _run_validation_layer(tmp_path, (), validate=True, linkcheck=False)

    assert captured == {
        "corpus": tmp_path,
        "schema": REPO_ROOT / "schema" / "ride.rng",
    }


def test_build_info_json_carries_licence(tmp_path: Path) -> None:
    """N6: build-info.json names its licence explicitly so a consumer
    of the build report knows the terms without inferring from prose."""
    site = SiteConfig(
        base_url="https://example.org",
        build_info=BuildInfo(commit="abc", commit_short="abc", date="2026-04-29T00:00:00Z"),
    )
    _write_build_info(
        out_root=tmp_path,
        site=site,
        reviews=(),
        asset_reports=[],
        failed=[],
    )
    payload = json.loads((tmp_path / "api" / "build-info.json").read_text(encoding="utf-8"))
    assert payload["licence"] == {"name": LICENCE_NAME, "url": LICENCE_URL}


def test_build_info_json_pins_envelope_keys(tmp_path: Path) -> None:
    """The top-level keys of build-info.json are part of the public
    contract; downstream consumers index by name."""
    site = SiteConfig(
        build_info=BuildInfo(commit="abc", commit_short="abc", date="2026-04-29"),
    )
    _write_build_info(
        out_root=tmp_path,
        site=site,
        reviews=(),
        asset_reports=[],
        failed=[],
    )
    payload = json.loads((tmp_path / "api" / "build-info.json").read_text(encoding="utf-8"))
    assert {
        "schema_version",
        "licence",
        "site",
        "build",
        "reviews",
        "assets",
        "validation",
        "linkcheck",
    } <= set(payload.keys())


def test_historical_asset_warnings_do_not_fail_build() -> None:
    report = AssetReport(
        review_id="legacy",
        bundle=False,
        copied=(),
        missing=("https://example.org/missing.png",),
        unparseable=(),
    )

    _raise_for_hard_failures(
        failed=[],
        validation_report=None,
        asset_reports=[report],
        pdf_failed=[],
    )


def test_bundle_asset_error_fails_with_actionable_message() -> None:
    report = AssetReport(
        review_id="draft.example",
        bundle=True,
        copied=(),
        missing=("pictures/missing.png",),
        unparseable=(),
    )

    with pytest.raises(BuildFailure, match="draft.example.*pictures/missing.png"):
        _raise_for_hard_failures(
            failed=[],
            validation_report=None,
            asset_reports=[report],
            pdf_failed=[],
        )


def test_validation_and_pdf_errors_fail_after_report_is_collected() -> None:
    validation = ValidationReport(
        files_checked=1,
        files_with_errors=1,
        findings=[
            ValidationFinding(
                file="issues/19/reviews/example/review.xml",
                line=7,
                column=0,
                severity="error",
                message="Did not expect element example there",
            )
        ],
    )

    with pytest.raises(BuildFailure) as exc_info:
        _raise_for_hard_failures(
            failed=[],
            validation_report=validation,
            asset_reports=[],
            pdf_failed=[("draft.example", "renderer failed")],
        )

    message = str(exc_info.value)
    assert "issues/19/reviews/example/review.xml:7" in message
    assert "draft.example: renderer failed" in message
