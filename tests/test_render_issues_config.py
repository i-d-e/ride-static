"""Tests for src.render.issues_config — Phase 11 R11 Issue-YAML."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.model.review import Review
from src.render.issues_config import (
    IssueConfig,
    IssueEditor,
    discover_issue_configs,
    order_reviews,
    parse_issue_config,
    validate_issue_configs,
)


# ── parse_issue_config ──────────────────────────────────────────────


def test_parse_issue_config_minimal(tmp_path: Path):
    p = tmp_path / "13.yaml"
    p.write_text("issue: 13\n", encoding="utf-8")
    cfg = parse_issue_config(p)
    assert cfg.issue == "13"
    assert cfg.status == "regular"
    assert cfg.is_rolling is False
    assert cfg.editors == ()
    assert cfg.contribution_order is None


def test_parse_issue_config_full(tmp_path: Path):
    p = tmp_path / "13.yaml"
    p.write_text(
        "issue: 13\n"
        "title: \"Issue 13\"\n"
        "doi: 10.18716/ride.13\n"
        "status: rolling\n"
        "publication_date: 2024-06-01\n"
        "description: A free-text description.\n"
        "editors:\n"
        "  - name: Jane Editor\n"
        "    affiliation: Some Uni\n"
        "    orcid: https://orcid.org/0000-0000-0000-0000\n"
        "contribution_order:\n"
        "  - ride.13.1\n"
        "  - ride.13.2\n",
        encoding="utf-8",
    )
    cfg = parse_issue_config(p)
    assert cfg.issue == "13"
    assert cfg.title == "Issue 13"
    assert cfg.doi == "10.18716/ride.13"
    assert cfg.is_rolling is True
    assert cfg.publication_date == "2024-06-01"
    assert cfg.description == "A free-text description."
    assert len(cfg.editors) == 1
    assert cfg.editors[0].name == "Jane Editor"
    assert cfg.editors[0].orcid.endswith("0000")
    assert cfg.contribution_order == ("ride.13.1", "ride.13.2")


def test_parse_issue_config_rejects_unknown_field(tmp_path: Path):
    p = tmp_path / "13.yaml"
    p.write_text("issue: 13\nfoo_bar: nope\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unknown field"):
        parse_issue_config(p)


def test_parse_issue_config_rejects_invalid_status(tmp_path: Path):
    p = tmp_path / "13.yaml"
    p.write_text("issue: 13\nstatus: maybe\n", encoding="utf-8")
    with pytest.raises(ValueError, match="status must be"):
        parse_issue_config(p)


def test_parse_issue_config_rejects_unknown_editor_field(tmp_path: Path):
    p = tmp_path / "13.yaml"
    p.write_text(
        "issue: 13\neditors:\n  - name: Jane\n    twitter: '@x'\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unknown editor field"):
        parse_issue_config(p)


# ── discover_issue_configs ──────────────────────────────────────────


def test_discover_issue_configs_empty_when_dir_missing(tmp_path: Path):
    assert discover_issue_configs(tmp_path / "nonexistent") == {}


def test_discover_issue_configs_loads_all(tmp_path: Path):
    (tmp_path / "1.yaml").write_text("issue: 1\n", encoding="utf-8")
    (tmp_path / "2.yaml").write_text("issue: 2\nstatus: rolling\n", encoding="utf-8")
    configs = discover_issue_configs(tmp_path)
    assert set(configs.keys()) == {"1", "2"}
    assert configs["2"].is_rolling


# ── validate_issue_configs ──────────────────────────────────────────


def _review(rid: str, issue: str) -> Review:
    return Review(
        id=rid, issue=issue, title="t", publication_date="", language="en", licence=""
    )


def test_validate_issue_configs_clean_when_no_order():
    cfg = IssueConfig(issue="13")
    reviews = (_review("ride.13.7", "13"),)
    assert validate_issue_configs({"13": cfg}, reviews) == []


def test_validate_issue_configs_flags_missing_review_in_order():
    """contribution_order misses a TEI review."""
    cfg = IssueConfig(issue="13", contribution_order=("ride.13.1",))
    reviews = (_review("ride.13.1", "13"), _review("ride.13.2", "13"))
    errors = validate_issue_configs({"13": cfg}, reviews)
    assert errors
    assert "ride.13.2" in errors[0]


def test_validate_issue_configs_flags_id_in_order_missing_from_tei():
    cfg = IssueConfig(issue="13", contribution_order=("ride.13.1", "ride.13.99"))
    reviews = (_review("ride.13.1", "13"),)
    errors = validate_issue_configs({"13": cfg}, reviews)
    assert errors
    assert any("ride.13.99" in e for e in errors)


def test_validate_issue_configs_flags_orphan_yaml():
    """YAML for an issue that has no reviews in the TEI corpus."""
    cfg = IssueConfig(issue="99")
    errors = validate_issue_configs({"99": cfg}, ())
    assert errors
    assert "99" in errors[0]


# ── order_reviews ───────────────────────────────────────────────────


def test_order_reviews_uses_config_order_when_present():
    cfg = IssueConfig(
        issue="13",
        contribution_order=("ride.13.7", "ride.13.1", "ride.13.4"),
    )
    revs = [_review("ride.13.1", "13"), _review("ride.13.7", "13"), _review("ride.13.4", "13")]
    out = order_reviews("13", revs, cfg)
    assert [r.id for r in out] == ["ride.13.7", "ride.13.1", "ride.13.4"]


def test_order_reviews_falls_back_to_id_sort_without_config():
    revs = [_review("ride.13.7", "13"), _review("ride.13.1", "13")]
    out = order_reviews("13", revs, None)
    assert [r.id for r in out] == ["ride.13.1", "ride.13.7"]
