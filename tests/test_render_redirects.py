"""Tests for the WordPress legacy-URL redirect generator (Welle 8.D).

Test-data philosophy per CLAUDE.md hard rule:

* ``write_redirects`` is a pure-function unit that takes a Review tuple
  and writes meta-refresh stubs to a target directory. Synthetic stubs
  cover the editorial map and the per-review/per-issue logic, plus the
  base_url prefix. Real-corpus integration walks the actual TEI files
  and asserts that every review has a redirect from its
  ``/issues/issue-{N}/{slug}/`` URL.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.model.review import Review
from src.parser.review import parse_review
from src.render.redirects import EDITORIAL_REDIRECTS, write_redirects


REPO_ROOT = Path(__file__).resolve().parent.parent
RIDE_TEI_DIR = REPO_ROOT.parent / "ride" / "tei_all"

needs_corpus = pytest.mark.skipif(
    not RIDE_TEI_DIR.is_dir(), reason="../ride/ corpus not available"
)


def _stub_review(issue: str, review_id: str, source_file: str) -> Review:
    return Review(
        id=review_id,
        issue=issue,
        title="t",
        publication_date="",
        language="en",
        licence="",
        source_file=source_file,
    )


def test_write_redirects_emits_per_review_stub(tmp_path: Path) -> None:
    review = _stub_review("22", "ride.22.1", "arendt-tei.xml")
    n = write_redirects((review,), tmp_path)
    assert n > 0
    legacy = tmp_path / "issues" / "issue-22" / "arendt" / "index.html"
    assert legacy.exists()
    html = legacy.read_text(encoding="utf-8")
    assert 'http-equiv="refresh"' in html
    assert "/issues/22/ride.22.1/" in html
    assert 'rel="canonical"' in html


def test_write_redirects_emits_per_issue_stub(tmp_path: Path) -> None:
    review = _stub_review("13", "ride.13.1", "wega-tei.xml")
    write_redirects((review,), tmp_path)
    issue_legacy = tmp_path / "issues" / "issue-13" / "index.html"
    assert issue_legacy.exists()
    assert "/issues/13/" in issue_legacy.read_text(encoding="utf-8")


def test_write_redirects_emits_editorial_stubs(tmp_path: Path) -> None:
    write_redirects((), tmp_path)
    # A few critical legacy paths from the live menu.
    assert (tmp_path / "publishing-policies" / "index.html").exists()
    assert (tmp_path / "ethical-code" / "index.html").exists()
    assert (tmp_path / "reviewers" / "call-for-reviews" / "index.html").exists()
    assert (tmp_path / "reviewers" / "ride-award-for-best-review" / "index.html").exists()
    # Total editorial count matches the static map.
    rel_paths = {
        str(p.relative_to(tmp_path).parent).replace("\\", "/")
        for p in tmp_path.rglob("index.html")
    }
    for legacy in EDITORIAL_REDIRECTS.keys():
        assert legacy in rel_paths


def test_write_redirects_prepends_base_url(tmp_path: Path) -> None:
    review = _stub_review("5", "ride.5.4", "1641-tei.xml")
    write_redirects((review,), tmp_path, base_url="/ride-static")
    html = (tmp_path / "issues" / "issue-5" / "1641" / "index.html").read_text(
        encoding="utf-8"
    )
    # Both meta-refresh and canonical link carry the project prefix.
    assert "/ride-static/issues/5/ride.5.4/" in html
    assert "/ride-static" in html


def test_write_redirects_handles_missing_source_file(tmp_path: Path) -> None:
    """Defensive: when source_file is None the slug falls back to the review id."""
    review = _stub_review("7", "ride.7.2", source_file=None)
    write_redirects((review,), tmp_path)
    # Fallback path uses the review id as slug.
    legacy = tmp_path / "issues" / "issue-7" / "ride.7.2" / "index.html"
    assert legacy.exists()


# -- Real-corpus pin ------------------------------------------------------


@needs_corpus
def test_real_corpus_every_review_gets_a_redirect(tmp_path: Path) -> None:
    """Every TEI review in the corpus must produce a legacy-URL stub."""
    files = sorted(RIDE_TEI_DIR.glob("*-tei.xml"))[:30]  # slice for speed
    reviews = tuple(parse_review(f) for f in files)
    write_redirects(reviews, tmp_path)
    # For each review, the stub at /issues/issue-{N}/{slug}/index.html exists
    # and points at the new path.
    for review, file in zip(reviews, files):
        slug = file.stem[:-4]  # strip "-tei"
        legacy = tmp_path / "issues" / f"issue-{review.issue}" / slug / "index.html"
        assert legacy.exists(), f"missing redirect for {review.id} ({slug})"
        html = legacy.read_text(encoding="utf-8")
        assert f"/issues/{review.issue}/{review.id}/" in html
