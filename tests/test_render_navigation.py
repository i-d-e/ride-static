"""Tests for the global-navigation loader (Welle 3).

Test-data philosophy per CLAUDE.md hard rule:

* ``load_navigation`` and ``resolve_navigation`` are pure-function
  units — both take a config plus a Review sequence and return a
  tuple of NavItem. The function signature is the only data form
  richer than that, so synthetic fixtures are the appropriate choice
  per the documented exception. Two real-corpus integration tests at
  the bottom anchor the live YAML against the parsed corpus so a
  drift in either side surfaces immediately.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.model.review import Review
from src.parser.review import parse_review
from src.render.navigation import (
    NavItem,
    NavLink,
    load_navigation,
    resolve_navigation,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
RIDE_TEI_DIR = REPO_ROOT.parent / "ride" / "tei_all"
NAV_PATH = REPO_ROOT / "config" / "navigation.yaml"

needs_corpus = pytest.mark.skipif(
    not RIDE_TEI_DIR.is_dir(), reason="../ride/ corpus not available"
)


def _write_yaml(tmp_path: Path, payload: dict) -> Path:
    out = tmp_path / "navigation.yaml"
    out.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return out


def _stub_review(issue: str, review_id: str = "ride.x") -> Review:
    """Minimal Review with the only fields the navigation reads: issue."""
    return Review(
        id=review_id,
        issue=issue,
        title="t",
        publication_date="",
        language="en",
        licence="",
    )


# -- load_navigation ------------------------------------------------------


def test_load_navigation_parses_explicit_children(tmp_path: Path) -> None:
    cfg = _write_yaml(tmp_path, {
        "items": [
            {
                "label": "About",
                "fallback_url": "/about/",
                "children": [
                    {"label": "Editorial", "url": "/editorial/"},
                    {"label": "Team", "url": "/team/"},
                ],
            }
        ]
    })
    items = load_navigation(cfg)
    assert len(items) == 1
    assert items[0].label == "About"
    assert items[0].fallback_url == "/about/"
    assert items[0].children == (
        NavLink("Editorial", "/editorial/"),
        NavLink("Team", "/team/"),
    )
    assert items[0].children_kind is None


def test_load_navigation_parses_data_driven_kind(tmp_path: Path) -> None:
    cfg = _write_yaml(tmp_path, {
        "items": [{
            "label": "Issues",
            "fallback_url": "/issues/",
            "children_kind": "issues",
            "children_count": 3,
        }]
    })
    items = load_navigation(cfg)
    assert items[0].children_kind == "issues"
    assert items[0].children_count == 3
    assert items[0].children == ()
    assert items[0].has_dropdown is True


def test_load_navigation_parses_leaf_only_link(tmp_path: Path) -> None:
    cfg = _write_yaml(tmp_path, {
        "items": [{"label": "Reviewing Criteria", "url": "/criteria/"}]
    })
    items = load_navigation(cfg)
    assert items[0].url == "/criteria/"
    assert items[0].has_dropdown is False


def test_load_navigation_missing_items_yields_empty(tmp_path: Path) -> None:
    cfg = _write_yaml(tmp_path, {})
    assert load_navigation(cfg) == ()


# -- resolve_navigation ---------------------------------------------------


def test_resolve_navigation_passes_explicit_items_through() -> None:
    items = (
        NavItem(
            label="About",
            fallback_url="/about/",
            children=(NavLink("Editorial", "/editorial/"),),
        ),
    )
    out = resolve_navigation(items, reviews=())
    assert out[0].url == "/about/"
    assert out[0].children == (NavLink("Editorial", "/editorial/"),)


def test_resolve_navigation_resolves_issues_kind() -> None:
    items = (
        NavItem(
            label="Issues",
            fallback_url="/issues/",
            children_kind="issues",
            children_count=2,
        ),
    )
    reviews = (
        _stub_review("12", "a"),
        _stub_review("12", "b"),
        _stub_review("13", "c"),
        _stub_review("9", "d"),
    )
    [resolved] = resolve_navigation(items, reviews=reviews)
    # First child is always the "All Issues" link.
    assert resolved.children[0] == NavLink("All Issues", "/issues/")
    # Last two issues, descending by numeric value: 13, 12.
    assert resolved.children[1] == NavLink("Issue 13", "/issues/13/")
    assert resolved.children[2] == NavLink("Issue 12", "/issues/12/")
    assert len(resolved.children) == 3
    # Top-level URL falls back to the configured fallback_url.
    assert resolved.url == "/issues/"


def test_resolve_navigation_issues_default_count_is_four() -> None:
    items = (NavItem(label="Issues", fallback_url="/issues/", children_kind="issues"),)
    reviews = tuple(_stub_review(str(n), f"r{n}") for n in range(1, 7))
    [resolved] = resolve_navigation(items, reviews=reviews)
    # 1 "All Issues" + 4 most recent issues (6, 5, 4, 3).
    assert len(resolved.children) == 5
    assert [c.url for c in resolved.children[1:]] == [
        "/issues/6/", "/issues/5/", "/issues/4/", "/issues/3/"
    ]


def test_resolve_navigation_issues_dedupes_per_issue() -> None:
    """Multiple reviews per issue must collapse to a single submenu entry."""
    items = (NavItem(label="Issues", fallback_url="/issues/", children_kind="issues", children_count=3),)
    reviews = (
        _stub_review("11", "a"), _stub_review("11", "b"), _stub_review("11", "c"),
        _stub_review("10", "d"),
    )
    [resolved] = resolve_navigation(items, reviews=reviews)
    issue_urls = [c.url for c in resolved.children if c.label.startswith("Issue ")]
    assert issue_urls == ["/issues/11/", "/issues/10/"]


def test_resolve_navigation_unknown_kind_raises() -> None:
    """A typo in the YAML should be loud, not silent."""
    items = (NavItem(label="Bad", children_kind="not_a_kind"),)
    with pytest.raises(ValueError, match="not_a_kind"):
        resolve_navigation(items)


# -- Real-config and real-corpus pins -------------------------------------


def test_real_navigation_yaml_carries_five_top_level_items() -> None:
    """Spec pin: requirements.md R11.5 + interface.md §4 mandate five
    top-level entries — About, Issues, Data, Reviewers, Reviewing Criteria.
    """
    items = load_navigation(NAV_PATH)
    labels = [i.label for i in items]
    assert labels == [
        "About",
        "Issues",
        "Data",
        "Reviewers",
        "Reviewing Criteria",
    ]


def test_real_navigation_yaml_issues_is_data_driven() -> None:
    """The Issues entry must be ``children_kind: issues`` so the
    submenu is populated from the corpus, not hand-maintained."""
    items = load_navigation(NAV_PATH)
    issues_item = next(i for i in items if i.label == "Issues")
    assert issues_item.children_kind == "issues"
    assert issues_item.fallback_url == "/issues/"


def test_real_navigation_yaml_reviewing_criteria_is_leaf_only() -> None:
    """Per interface.md §4, Reviewing Criteria is a direct link, not a dropdown."""
    items = load_navigation(NAV_PATH)
    crit = next(i for i in items if i.label == "Reviewing Criteria")
    assert crit.has_dropdown is False
    assert crit.url == "/criteria/"


@needs_corpus
def test_real_corpus_resolves_issues_submenu() -> None:
    """Resolve the live navigation YAML against a slice of the corpus
    so YAML drift, parser drift, and resolver drift each surface here."""
    files = sorted(RIDE_TEI_DIR.glob("*-tei.xml"))[:30]
    reviews = tuple(parse_review(f) for f in files)
    items = load_navigation(NAV_PATH)
    resolved = resolve_navigation(items, reviews=reviews)
    issues = next(i for i in resolved if i.label == "Issues")
    # The first submenu entry is "All Issues"; the rest are real issues.
    assert issues.children[0] == NavLink("All Issues", "/issues/")
    assert len(issues.children) >= 2
    assert all(c.url.startswith("/issues/") for c in issues.children)
