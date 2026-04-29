"""Tests for ``src.build`` — focused on the build-report writer.

The full ``build()`` orchestrator is exercised by the real-corpus
integration runs in CI. These tests pin the small but load-bearing
contracts that callers (CI, downstream consumers of build-info.json)
depend on, without spinning up a full corpus parse.
"""
from __future__ import annotations

import json
from pathlib import Path

from src.build import _write_build_info
from src.render.corpus_dump import LICENCE_NAME, LICENCE_URL
from src.render.html import BuildInfo, SiteConfig


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
    assert {"schema_version", "licence", "site", "build", "reviews", "assets",
            "validation", "linkcheck"} <= set(payload.keys())
