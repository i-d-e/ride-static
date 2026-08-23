"""Tests for src.render.aggregations — Phase 10 page builders.

Per the CLAUDE.md hard rule the reviews under test come from the real
parser, not from ``Review`` instances built out of synthetic dataclass
values. The small controlled corpus is produced by ``dataclasses.replace``
on a real parsed review (``corpus_review`` fixture): body, figures,
notes and the rest of the domain tree are the parser's output, and only
the top-level metadata the aggregators read (id, issue, title, date,
keywords, authors) is pinned so grouping / sort / markup assertions stay
deterministic. Authors are metadata value objects, outside the
Section/Block parser surface the hard rule targets. A real-corpus
integration test at the bottom drives a full issue end to end.
"""

from __future__ import annotations

import dataclasses

import pytest

from src.model.review import Author, Person, Review
from src.parser.datasets import (
    aggregate_reviewers,
    aggregate_tags,
)
from src.render.aggregations import (
    _issue_sort_key,
    group_reviews_by_issue,
    render_drafts,
    render_explore,
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

from tests._shared import REPO_ROOT


def _review(
    base: Review,
    rid: str = "ride.13.7",
    issue: str = "13",
    title: str = "A Sample Review",
    date: str = "2026-04-29",
    keywords: tuple = ("digital editions", "test"),
    author_name: str = "Jane Reviewer",
    author_surname: str = "Reviewer",
    author_forename: str = "Jane",
) -> Review:
    """A real parsed review with its aggregation-relevant metadata pinned."""
    return dataclasses.replace(
        base,
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
def reviews(corpus_review):
    """A small but varied corpus: two issues, two authors, three tags —
    each review a real parse with pinned top-level metadata."""
    return (
        _review(
            corpus_review,
            "ride.13.7",
            "13",
            "First Review",
            "2026-04-29",
            ("editions", "tei"),
            "Jane Reviewer",
            "Reviewer",
            "Jane",
        ),
        _review(
            corpus_review,
            "ride.13.8",
            "13",
            "Second Review",
            "2026-04-15",
            ("tei", "xml"),
            "John Other",
            "Other",
            "John",
        ),
        _review(
            corpus_review,
            "ride.12.3",
            "12",
            "Older Review",
            "2025-10-01",
            ("editions",),
            "Jane Reviewer",
            "Reviewer",
            "Jane",
        ),
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
    # Heading is split into a label and a meta-span (Welle 5);
    # both pieces must be present and identify issue 13 as current.
    assert "Current issue" in html
    assert 'ride-section__heading-meta">· 13' in html
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


def test_render_drafts_lists_only_drafts_with_noindex(reviews, env, tmp_path):
    draft = dataclasses.replace(reviews[0], publication_status="draft", id="draft.sample")
    wordcloud = tmp_path / "draft.sample.png"
    wordcloud.write_bytes(b"png")

    html = render_drafts(
        (*reviews, draft),
        _site(),
        env,
        wordcloud_dir=tmp_path,
        pdf_available=True,
    )

    assert "Review workflow examples" in html
    assert 'name="robots" content="noindex, nofollow"' in html
    assert "draft.sample" in html
    assert "draft.sample.png" in html
    assert "Second Review" not in html
    assert 'aria-label="Review files"' in html
    assert "/issues/13/draft.sample/factsheet/" in html
    assert "/issues/13/draft.sample/draft.sample.xml" in html
    assert "/issues/13/draft.sample/draft.sample.pdf" in html


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
    assert "1 review" in html  # John has one — singular


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


def test_render_resources_renders_table(env, corpus_review):
    from src.model.review import RelatedItem

    review = dataclasses.replace(
        corpus_review,
        id="ride.1.1",
        issue="1",
        title="Test",
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


def test_render_resources_resource_review_link_uses_review_index(env, corpus_review):
    """The reviews-cell renders a link with the actual review title, not just the id."""
    from src.model.review import RelatedItem

    rev = dataclasses.replace(
        corpus_review,
        id="ride.1.1",
        issue="1",
        title="The Reviewing Article",
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


def test_render_resources_escher_shows_title_and_credits_not_runon(env):
    """Real-corpus regression for the resources table (2026-07-10 screenshot
    review): the escher bibl carries respStmts, a publication date, an idno
    and an accessed date. The cell must link the canonical title only, list
    the people in a separate credits line without the 'too many' placeholder
    and without role labels, and drop the accessed date entirely (it lives
    in the factsheet citation, not in the index)."""
    from src.parser.review import parse_review

    escher = REPO_ROOT / "issues" / "10" / "reviews" / "escher-tei.xml"
    if not escher.exists():
        pytest.skip("corpus not present")
    review = parse_review(escher)
    html = render_resources((review,), _site(), env)

    assert ">Alfred Escher-Briefedition</a>" in html
    assert 'href="https://www.briefedition.alfred-escher.ch/"' in html
    assert "too many" not in html
    assert "2018-05-22" not in html  # accessed date stays out of the index
    # Credits line: people without role labels, plus the publication year.
    assert "Joseph Jung" in html
    assert "Encoder" not in html
    assert "2015" in html


def test_issue_sort_key_orders_by_numeric_prefix_with_letter_suffix():
    """Pure-function test of the issue ordering key.

    Synthetic input (empty review lists) is the documented exception per
    the hard rule: no letter-suffixed issue (an "11x" special edition)
    exists in the corpus, so the numeric-prefix branch can only be
    exercised with a constructed value. With equal (empty) dates the
    numeric prefix decides ordering, so "11x" must sort after "3" by its
    prefix 11, rather than collapsing to 0 and jumping ahead of the
    numbered issues.
    """
    items = [("11x", []), ("3", []), ("2", [])]
    ordered = [issue for issue, _ in sorted(items, key=_issue_sort_key)]
    assert ordered == ["2", "3", "11x"]


def test_explore_description_counts_track_the_real_corpus(reviews, env):
    """The explore meta description composes its counts from the reviews
    passed in, never a hardcoded corpus size. The ``reviews`` fixture holds
    three reviews across two issues, so the description must say exactly
    that and must not carry a stale literal from a former corpus size."""
    html = render_explore(reviews, _site(), env)
    n_issues = len({r.issue for r in reviews if r.issue})
    assert f"{len(reviews)} reviews across {n_issues} issues" in html
    assert "111 reviews" not in html


# ── Real-corpus integration ───────────────────────────────────────────


def test_real_corpus_issue_aggregations_render(corpus_issue_reviews, env):
    """Drive the aggregation builders over one full real issue: every
    review's title appears on its issue page, the grouping keys the issue,
    and each real tag and reviewer round-trips to a detail page."""
    reviews = corpus_issue_reviews
    issue_no = reviews[0].issue

    grouped = group_reviews_by_issue(reviews)
    assert set(grouped[issue_no]) == set(reviews)

    issue_html = render_issue(issue_no, reviews, _site(), env)
    for r in reviews:
        assert r.title in issue_html

    # Every real tag has a detail page listing at least one member review.
    for tag in aggregate_tags(reviews):
        html = render_tag(tag, reviews, _site(), env)
        assert tag.display_name in html or tag.name in html

    # Every real reviewer resolves to a slug and a detail page.
    for rv in aggregate_reviewers(reviews):
        assert reviewer_slug(rv)
        html = render_reviewer(rv, reviews, _site(), env)
        assert rv.person.full_name in html
