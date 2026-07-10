"""Tests for src.render.issues_config — Phase 11 R11 Issue-YAML."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.model.review import Review
from src.render.issues_config import (
    IssueConfig,
    discover_issue_configs,
    expected_id_from_doi,
    find_duplicate_review_dois,
    order_reviews,
    parse_issue_config,
    validate_issue_configs,
    validate_review_ids,
    validate_review_locations,
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
    (tmp_path / "1").mkdir()
    (tmp_path / "2").mkdir()
    (tmp_path / "1" / "metadata.yaml").write_text("issue: 1\n", encoding="utf-8")
    (tmp_path / "2" / "metadata.yaml").write_text(
        "issue: 2\nstatus: rolling\n", encoding="utf-8"
    )
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


# ── validate_review_locations ───────────────────────────────────────


def _place(corpus_root: Path, issue: str, slug: str) -> Path:
    """Create an empty TEI file at issues/{issue}/reviews/{slug}-tei.xml."""
    p = corpus_root / issue / "reviews" / f"{slug}-tei.xml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("<TEI/>", encoding="utf-8")
    return p


def test_validate_review_locations_clean_when_folder_matches_biblscope(tmp_path: Path):
    """File at issues/22/reviews/ + Review.issue='22' = silent pass."""
    path = _place(tmp_path, "22", "arendt")
    review = _review("ride.22.1", "22")
    assert validate_review_locations([(path, review)], corpus_root=tmp_path) == []


def test_validate_review_locations_flags_wrong_folder(tmp_path: Path):
    """File at issues/5/reviews/ but biblScope says issue 22 — must surface."""
    path = _place(tmp_path, "5", "arendt")
    review = _review("ride.22.1", "22")
    errors = validate_review_locations([(path, review)], corpus_root=tmp_path)
    assert len(errors) == 1
    assert "arendt-tei.xml" in errors[0]
    assert "issues/5/reviews/" in errors[0]
    assert "'22'" in errors[0]


def test_validate_review_locations_flags_missing_reviews_subdir(tmp_path: Path):
    """File at issues/22/foo-tei.xml (no reviews/ subdir) — unexpected layout."""
    path = tmp_path / "22" / "foo-tei.xml"
    path.parent.mkdir(parents=True)
    path.write_text("<TEI/>", encoding="utf-8")
    review = _review("ride.22.1", "22")
    errors = validate_review_locations([(path, review)], corpus_root=tmp_path)
    assert len(errors) == 1
    assert "unexpected path" in errors[0]


def test_validate_review_locations_skips_files_outside_corpus(tmp_path: Path):
    """Synthetic test paths outside the corpus root fall through silently."""
    path = tmp_path / "elsewhere" / "foo-tei.xml"
    path.parent.mkdir(parents=True)
    path.write_text("<TEI/>", encoding="utf-8")
    review = _review("ride.22.1", "22")
    # corpus_root is a sibling tree the file is not in
    other_root = tmp_path / "issues"
    other_root.mkdir()
    assert validate_review_locations([(path, review)], corpus_root=other_root) == []


def test_validate_review_locations_collects_multiple_errors(tmp_path: Path):
    """All mismatches reported, not just the first — editor sees the full list."""
    p1 = _place(tmp_path, "5", "arendt")
    p2 = _place(tmp_path, "7", "bayeux")
    errors = validate_review_locations(
        [
            (p1, _review("ride.22.1", "22")),
            (p2, _review("ride.20.3", "20")),
        ],
        corpus_root=tmp_path,
    )
    assert len(errors) == 2


def test_validate_review_locations_real_corpus_is_clean(corpus_parsed):
    """Every TEI in the shipped corpus must live in the folder its
    biblScope @n points to. Catches regressions of the migration mapping."""
    errors = validate_review_locations(list(corpus_parsed))
    assert errors == [], "\n".join(errors)


# ── expected_id_from_doi (pure function) ────────────────────────────


def test_expected_id_from_doi_derives_local_form():
    """Pure function — the signature (a DOI string) is the only data form,
    so synthetic inputs are appropriate here (CLAUDE.md test philosophy)."""
    assert expected_id_from_doi("10.18716/ride.a.21.1") == "ride.21.1"
    assert expected_id_from_doi("10.18716/ride.a.3.5") == "ride.3.5"


def test_expected_id_from_doi_returns_none_for_non_review_doi():
    """Issue-level DOI, empty, and foreign DOIs have no derivable xml:id."""
    assert expected_id_from_doi("10.18716/ride.a.21") is None  # issue, not review
    assert expected_id_from_doi(None) is None
    assert expected_id_from_doi("") is None
    assert expected_id_from_doi("10.1000/xyz") is None


# ── validate_review_ids ─────────────────────────────────────────────


def _rev(rid: str, doi: str | None) -> Review:
    return Review(
        id=rid, issue="", title="t", publication_date="", language="en",
        licence="", doi=doi,
    )


def test_validate_review_ids_clean_when_id_matches_doi():
    """Classifier over the (xml:id, DOI) pair — synthetic Review values are
    the function's data form, used here per CLAUDE.md's pure-function rule."""
    parsed = [
        (Path("a-tei.xml"), _rev("ride.21.1", "10.18716/ride.a.21.1")),
        (Path("b-tei.xml"), _rev("ride.3.5", "10.18716/ride.a.3.5")),
    ]
    assert validate_review_ids(parsed) == []


def test_validate_review_ids_flags_id_contradicting_doi():
    """A copied header: xml:id ride.1.1 but the DOI says issue 21, n 1."""
    parsed = [(Path("everynamecounts-tei.xml"), _rev("ride.1.1", "10.18716/ride.a.21.1"))]
    errors = validate_review_ids(parsed)
    assert len(errors) == 1
    assert "everynamecounts-tei.xml" in errors[0]
    assert "ride.21.1" in errors[0]


def test_validate_review_ids_flags_missing_or_non_review_doi():
    parsed = [(Path("x-tei.xml"), _rev("ride.21.1", None))]
    errors = validate_review_ids(parsed)
    assert len(errors) == 1
    assert "cannot derive" in errors[0]


# ── find_duplicate_review_dois ──────────────────────────────────────


def test_find_duplicate_review_dois_detects_shared_doi():
    parsed = [
        (Path("crowdsourcingwien-tei.xml"), _rev("ride.21.2", "10.18716/ride.a.21.2")),
        (Path("papyrieditor-tei.xml"), _rev("ride.21.2", "10.18716/ride.a.21.2")),
        (Path("solo-tei.xml"), _rev("ride.21.3", "10.18716/ride.a.21.3")),
    ]
    dups = find_duplicate_review_dois(parsed)
    assert len(dups) == 1
    assert "10.18716/ride.a.21.2" in dups[0]
    assert "crowdsourcingwien-tei.xml" in dups[0]
    assert "papyrieditor-tei.xml" in dups[0]


# ── real-corpus integration: the id↔DOI fix and the known anomaly ───


def test_real_corpus_every_xml_id_matches_its_doi(corpus_parsed):
    """After the id↔DOI correction every shipped review's xml:id is the
    local form of its registered DOI. Locks the fix and guards regressions
    of the everynamecounts/godwin copied-header class."""
    errors = validate_review_ids(list(corpus_parsed))
    assert errors == [], "\n".join(errors)


def test_real_corpus_only_known_duplicate_doi_remains(corpus_parsed):
    """Documented editorial anomaly (CLAUDE.md: anomalies are explicit):
    crowdsourcing.wien and papyrieditor share DOI 10.18716/ride.a.21.2.
    Until the editors re-register one, this is the *only* duplicate DOI.
    When they fix it this test fails, signalling that the build's soft
    warning can be promoted to a hard check."""
    dups = find_duplicate_review_dois(list(corpus_parsed))
    assert len(dups) == 1
    assert "10.18716/ride.a.21.2" in dups[0]
    assert "crowdsourcingwien-tei.xml" in dups[0]
    assert "papyrieditor-tei.xml" in dups[0]
