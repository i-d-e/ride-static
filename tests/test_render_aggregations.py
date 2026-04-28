"""Tests for src.render.aggregations — Phase 10 page builders.

Synthetic Reviews exercise each render function; assertions cover the
data-flow contract (right tag/reviewer/issue groupings) and the markup
contract (key BEM classes and the navigation skeleton).
"""
from __future__ import annotations

import pytest

from src.model.review import Author, Person, Review
from src.parser.datasets import (
    aggregate_reviewed_resources,
    aggregate_reviewers,
    aggregate_tags,
)
from src.render.aggregations import (
    group_reviews_by_issue,
    render_index,
    render_issue,
    render_issues_overview,
    render_resources,
    render_reviewer,
    render_reviewers_overview,
    render_tag,
    render_tags_overview,
    reviewer_slug,
)
from src.render.html import SiteConfig, make_env


def _review(
    rid: str = "ride.13.7",
    issue: str = "13",
    title: str = "A Sample Review",
    date: str = "2026-04-29",
    keywords: tuple = ("digital editions", "test"),
    author_name: str = "Jane Reviewer",
    author_surname: str = "Reviewer",
    author_forename: str = "Jane",
) -> Review:
    return Review(
        id=rid,
        issue=issue,
        title=title,
        publication_date=date,
        language="en",
        licence="https://creativecommons.org/licenses/by/4.0/",
        keywords=keywords,
        authors=(
            Author(
                person=Person(
                    full_name=author_name,
                    forename=author_forename,
                    surname=author_surname,
                )
            ),
        ),
    )


def _site() -> SiteConfig:
    return SiteConfig(title="RIDE", base_url="", default_language="en")


@pytest.fixture()
def env():
    return make_env()


@pytest.fixture()
def reviews():
    """A small but varied corpus: two issues, two authors, three tags."""
    return (
        _review("ride.13.7", "13", "First Review", "2026-04-29",
                ("editions", "tei"), "Jane Reviewer", "Reviewer", "Jane"),
        _review("ride.13.8", "13", "Second Review", "2026-04-15",
                ("tei", "xml"), "John Other", "Other", "John"),
        _review("ride.12.3", "12", "Older Review", "2025-10-01",
                ("editions",), "Jane Reviewer", "Reviewer", "Jane"),
    )


# ── Helper functions ──────────────────────────────────────────────────


def test_group_reviews_by_issue(reviews):
    grouped = group_reviews_by_issue(reviews)
    assert set(grouped.keys()) == {"13", "12"}
    assert len(grouped["13"]) == 2
    assert len(grouped["12"]) == 1


# ── render_index ──────────────────────────────────────────────────────


def test_render_index_picks_latest_issue_as_current(reviews, env):
    html = render_index(reviews, _site(), env)
    assert "Current issue · 13" in html
    assert "First Review" in html
    assert "Second Review" in html
    assert "Older Review" not in html  # belongs to the older issue
    assert "ride-home" in html
    assert "/issues/" in html
    assert "/tags/" in html
    assert "/reviewers/" in html


def test_render_index_handles_empty_corpus(env):
    html = render_index((), _site(), env)
    assert "Current issue" not in html
    assert "0 reviews across 0 issues" in html


# ── render_issues_overview ────────────────────────────────────────────


def test_render_issues_overview_lists_issues_newest_first(reviews, env):
    html = render_issues_overview(reviews, _site(), env)
    assert "Issue 13" in html
    assert "Issue 12" in html
    # Issue 13 should appear before Issue 12 in the document
    assert html.index("Issue 13") < html.index("Issue 12")


# ── render_issue ──────────────────────────────────────────────────────


def test_render_issue_lists_only_that_issue(reviews, env):
    html = render_issue("13", reviews, _site(), env)
    assert "First Review" in html
    assert "Second Review" in html
    assert "Older Review" not in html
    assert "Issue 13" in html


# ── render_tags ───────────────────────────────────────────────────────


def test_render_tags_overview_lists_alphabetical(reviews, env):
    html = render_tags_overview(reviews, _site(), env)
    # Three distinct tags — case-insensitive merge keeps "editions" once.
    assert "editions" in html
    assert "tei" in html
    assert "xml" in html
    # Tag links use the slug
    assert "/tags/editions/" in html


def test_render_tag_lists_member_reviews(reviews, env):
    tags = aggregate_tags(reviews)
    editions_tag = next(t for t in tags if t.name == "editions")
    html = render_tag(editions_tag, reviews, _site(), env)
    assert "First Review" in html
    assert "Older Review" in html
    assert "Second Review" not in html  # not tagged editions


# ── render_reviewers ──────────────────────────────────────────────────


def test_render_reviewers_overview_alphabetical(reviews, env):
    html = render_reviewers_overview(reviews, _site(), env)
    assert "Jane Reviewer" in html
    assert "John Other" in html
    # Sort by surname: Other before Reviewer
    assert html.index("John Other") < html.index("Jane Reviewer")
    assert "2 reviews" in html  # Jane has two
    assert "1 review" in html   # John has one — singular


def test_render_reviewer_lists_their_reviews(reviews, env):
    rvs = aggregate_reviewers(reviews)
    jane = next(r for r in rvs if r.person.full_name == "Jane Reviewer")
    html = render_reviewer(jane, reviews, _site(), env)
    assert "Jane Reviewer" in html
    assert "First Review" in html
    assert "Older Review" in html


def test_reviewer_slug_uses_surname_forename(reviews):
    rvs = aggregate_reviewers(reviews)
    jane = next(r for r in rvs if r.person.full_name == "Jane Reviewer")
    assert reviewer_slug(jane) == "reviewer-jane"


# ── render_resources ──────────────────────────────────────────────────


def test_render_resources_renders_table(env):
    from src.model.review import RelatedItem

    review = Review(
        id="ride.1.1",
        issue="1",
        title="Test",
        publication_date="2024-01-01",
        language="en",
        licence="cc",
        related_items=(
            RelatedItem(
                type="reviewed_resource",
                bibl_text="The Edition Project",
                bibl_targets=("https://edition.example",),
            ),
        ),
    )
    html = render_resources((review,), _site(), env)
    assert "Reviewed resources" in html
    assert "The Edition Project" in html
    assert "https://edition.example" in html
    assert "<table" in html


def test_render_resources_resource_review_link_uses_review_index(env):
    """The reviews-cell renders a link with the actual review title, not just the id."""
    from src.model.review import RelatedItem

    rev = Review(
        id="ride.1.1",
        issue="1",
        title="The Reviewing Article",
        publication_date="2024-01-01",
        language="en",
        licence="cc",
        related_items=(
            RelatedItem(
                type="reviewed_resource",
                bibl_text="Edition X",
                bibl_targets=("https://x.example",),
            ),
        ),
    )
    html = render_resources((rev,), _site(), env)
    # The review link uses the review title as anchor text, not the bare id.
    assert ">The Reviewing Article<" in html
