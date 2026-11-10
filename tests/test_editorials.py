"""Issue editorials and the OpenRefine review taken over from i-d-e/ride.

The live site publishes five issue editorials (``ride.{N}.0``) and the
OpenRefine review (ride.19.3) with DOI and OAI record; the parity check of
2026-11-10 found them missing from this corpus. Real-corpus tests per
CLAUDE.md: they parse the copied TEI files.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src._corpus import CORPUS_ROOT
from src.parser.datasets import aggregate_reviewers
from src.parser.review import parse_review
from src.render.html import render_review
from src.render.redirects import LegacyUrls, write_redirects

EDITORIAL_ISSUES = (6, 8, 9, 16, 21)


def _editorial(issue: int):
    path = CORPUS_ROOT / str(issue) / "reviews" / "editorial-tei.xml"
    if not path.is_file():
        pytest.skip("editorial TEI not in corpus")
    return parse_review(path)


@pytest.mark.parametrize("issue", EDITORIAL_ISSUES)
def test_editorials_parse_with_doi_and_text(issue: int) -> None:
    review = _editorial(issue)
    assert review.id == f"ride.{issue}.0"
    assert review.doi == f"10.18716/ride.a.{issue}.0"
    assert review.is_editorial
    assert review.body and review.authors


def test_openrefine_is_a_review_with_questionnaire() -> None:
    path = CORPUS_ROOT / "19" / "reviews" / "openrefine-tei.xml"
    if not path.is_file():
        pytest.skip("openrefine TEI not in corpus")
    review = parse_review(path)
    assert review.id == "ride.19.3" and review.doi == "10.18716/ride.a.19.3"
    assert not review.is_editorial
    assert review.questionnaires and review.figures


def test_editors_of_editorials_are_not_listed_as_reviewers() -> None:
    editorial = _editorial(16)
    names = {r.person.full_name for r in aggregate_reviewers((editorial,))}
    assert names == set()


def test_editorial_page_says_by_and_links_no_factsheet() -> None:
    html = render_review(_editorial(16))
    assert "Reviewed by" not in html
    assert ">By" in html or " By\n" in html or "By " in html
    assert 'href="factsheet/"' not in html
    assert 'id="factsheet"' not in html


def test_editorial_factsheet_address_lands_on_the_editorial(tmp_path: Path) -> None:
    write_redirects((_editorial(16),), tmp_path, legacy_urls=LegacyUrls())
    stub = tmp_path / "issues" / "issue-16" / "editorial" / "factsheet" / "index.html"
    html = stub.read_text(encoding="utf-8")
    assert "/issues/16/ride.16.0/" in html and "factsheet/" not in html.split("url=")[1][:40]
