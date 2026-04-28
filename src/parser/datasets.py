"""Cross-corpus aggregations — tags, reviewers, reviewed resources.

These feed the Aggregations-Seiten in Phase 10 (``interface.md`` §4):

- **Tag-Übersicht** (``requirements.md`` R6) — every keyword and the
  reviews that carry it, used by the tag index and per-tag detail page.
- **Reviewer-Liste** (``requirements.md`` R8) — every author and their
  authored reviews, deduplicated by ORCID where available.
- **Reviewed Resources** (``requirements.md`` R7) — every reviewed
  resource and the reviews about it, deduplicated by canonical target.

Each aggregation function takes the full corpus as
``tuple[Review, ...]`` and returns a flat ``tuple`` of typed entries
sorted alphabetically (tags) or by surname (reviewers) or by title
(resources). Order is stable so per-build URLs stay reproducible.

The complementary per-review walkers (``collect_figures``,
``collect_notes``) live in :mod:`src.parser.aggregate`.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from src.model.review import Author, Person, Review


# -- Tags -----------------------------------------------------------------


@dataclass(frozen=True)
class TagAggregate:
    """One keyword and the reviews that carry it.

    ``name`` is the lowercased canonical form; ``display_name`` is the
    first surface form encountered, preserved for rendering.
    """

    name: str
    display_name: str
    review_ids: tuple[str, ...]

    @property
    def count(self) -> int:
        return len(self.review_ids)


def aggregate_tags(reviews: tuple[Review, ...]) -> tuple[TagAggregate, ...]:
    """Group reviews by keyword. Case-insensitive merge ('TEI' == 'tei')."""
    by_key: dict[str, dict] = {}
    for review in reviews:
        for kw in review.keywords:
            key = kw.strip().lower()
            if not key:
                continue
            entry = by_key.setdefault(key, {"display": kw.strip(), "ids": []})
            entry["ids"].append(review.id)
    return tuple(
        TagAggregate(
            name=key,
            display_name=info["display"],
            review_ids=tuple(info["ids"]),
        )
        for key, info in sorted(by_key.items())
    )


# -- Reviewers ------------------------------------------------------------


@dataclass(frozen=True)
class ReviewerAggregate:
    """One reviewer (Author across the corpus) and their authored reviews.

    Deduplication preference: ORCID first (if both reviews provide one
    that matches), full_name as fallback. The first encountered
    :class:`~src.model.review.Author` is kept as the canonical record;
    later occurrences contribute review_ids only.
    """

    person: Person
    review_ids: tuple[str, ...]
    affiliation_hint: str = ""  # first non-empty affiliation org_name seen

    @property
    def count(self) -> int:
        return len(self.review_ids)


def aggregate_reviewers(reviews: tuple[Review, ...]) -> tuple[ReviewerAggregate, ...]:
    """Group reviews by author. Sort by surname (case-insensitive),
    falling back to full_name when no surname is parsed out."""
    by_key: dict[str, dict] = {}
    for review in reviews:
        for author in review.authors:
            key = _reviewer_key(author)
            entry = by_key.setdefault(
                key,
                {"person": author.person, "ids": [], "aff": ""},
            )
            entry["ids"].append(review.id)
            if not entry["aff"] and author.affiliation and author.affiliation.org_name:
                entry["aff"] = author.affiliation.org_name
    return tuple(
        ReviewerAggregate(
            person=info["person"],
            review_ids=tuple(info["ids"]),
            affiliation_hint=info["aff"],
        )
        for _, info in sorted(
            by_key.items(),
            key=lambda kv: (
                (kv[1]["person"].surname or kv[1]["person"].full_name).lower()
            ),
        )
    )


def _reviewer_key(author: Author) -> str:
    """Stable identity key for a reviewer: ORCID if present, else name."""
    if author.person.orcid:
        return f"orcid:{author.person.orcid}"
    return f"name:{author.person.full_name.lower()}"


# -- Reviewed resources ---------------------------------------------------


@dataclass(frozen=True)
class ReviewedResourceAggregate:
    """One reviewed resource and the reviews about it.

    The corpus carries reviewed resources in
    ``Review.related_items[type='reviewed_resource']``. Deduplication
    uses the first ``bibl_targets`` URL when available, falling back
    to the bibl text. Some resources are reviewed more than once
    (rolling-issue updates); those collect multiple review IDs.
    """

    title: str
    targets: tuple[str, ...]
    review_ids: tuple[str, ...]

    @property
    def count(self) -> int:
        return len(self.review_ids)


def aggregate_reviewed_resources(
    reviews: tuple[Review, ...],
) -> tuple[ReviewedResourceAggregate, ...]:
    """Group reviews by reviewed resource. Sort alphabetically by title."""
    by_key: dict[str, dict] = {}
    for review in reviews:
        for ri in review.related_items:
            if ri.type != "reviewed_resource":
                continue
            key = _resource_key(ri.bibl_targets, ri.bibl_text)
            entry = by_key.setdefault(
                key,
                {
                    "title": ri.bibl_text.strip() or "(untitled)",
                    "targets": ri.bibl_targets,
                    "ids": [],
                },
            )
            entry["ids"].append(review.id)
    return tuple(
        ReviewedResourceAggregate(
            title=info["title"],
            targets=info["targets"],
            review_ids=tuple(info["ids"]),
        )
        for _, info in sorted(
            by_key.items(),
            key=lambda kv: kv[1]["title"].lower(),
        )
    )


def _resource_key(targets: tuple[str, ...], bibl_text: str) -> str:
    """Stable identity key for a reviewed resource: first target URL if
    present, else a normalised prefix of the bibl text."""
    if targets:
        return f"target:{targets[0]}"
    return f"text:{bibl_text.strip().lower()[:120]}"
