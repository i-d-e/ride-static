"""Shared pytest fixtures.

Path bootstrap plus the real-corpus fixtures the render tests share.

Per the CLAUDE.md hard rule, integration tests drive the *real* TEI
corpus through ``src.parser`` rather than constructing ``Review`` /
``Section`` / ``Block`` instances from synthetic dataclass values. These
fixtures parse the corpus once per session so every consumer sees the
same domain objects the build sees, and they skip cleanly when the
corpus is absent so the unit suite still runs on a partial checkout.

Fixtures:

* ``corpus_reviews`` — every review, parsed once (session-scoped).
* ``corpus_review`` — one stable, metadata-rich review
  (``makingandknowing`` / ``ride.21.4``: authors with email, keywords,
  DOI, a questionnaire, figures, notes, bibliography, and the
  conventional ``p1`` / ``ftn1`` / ``img1`` anchors).
* ``corpus_issue_reviews`` — every review of one complete issue
  (issue 21), for aggregation-style tests that need a small but real set.

Edge cases the corpus does not carry are built with
``dataclasses.replace()`` on a real parsed instance where possible;
genuine pure-function / pure-formatter unit tests may keep a synthetic
builder, documented as such in the test's docstring.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Make scripts/ importable as top-level modules.
sys.path.insert(0, str(REPO_ROOT / "scripts"))
# Make the src/ package importable as `src.*`.
sys.path.insert(0, str(REPO_ROOT))

# A stable, metadata-rich review present in every corpus checkout.
STABLE_SLUG = "makingandknowing"  # ride.21.4
STABLE_ISSUE = "21"


@pytest.fixture(scope="session")
def corpus_reviews():
    """Every corpus review, parsed once via the real parser.

    Skips when the in-repo corpus is absent (partial checkout)."""
    from src._corpus import iter_tei_files
    from src.parser.review import parse_review

    files = list(iter_tei_files())
    if not files:
        pytest.skip("in-repo TEI corpus not present")
    return tuple(parse_review(p) for p in files)


@pytest.fixture(scope="session")
def corpus_parsed():
    """Every review as a ``(path, Review)`` pair, for consumers that need
    the source path (location / id-vs-DOI validators, redirect slugs)."""
    from src._corpus import iter_tei_files
    from src.parser.review import parse_review

    files = list(iter_tei_files())
    if not files:
        pytest.skip("in-repo TEI corpus not present")
    return tuple((p, parse_review(p)) for p in files)


@pytest.fixture(scope="session")
def corpus_review():
    """One stable, metadata-rich review (makingandknowing / ride.21.4)."""
    from src._corpus import find_tei
    from src.parser.review import parse_review

    try:
        path = find_tei(STABLE_SLUG)
    except FileNotFoundError:
        pytest.skip(f"stable fixture review {STABLE_SLUG!r} not in corpus")
    return parse_review(path)


@pytest.fixture(scope="session")
def corpus_issue_reviews(corpus_reviews):
    """Every review of one complete issue (issue 21)."""
    reviews = tuple(r for r in corpus_reviews if r.issue == STABLE_ISSUE)
    if not reviews:
        pytest.skip(f"issue {STABLE_ISSUE} not in corpus")
    return reviews
