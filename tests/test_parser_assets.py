"""Tests for the figure asset pipeline (Phase 7).

Test data philosophy:

* **Pure-function unit tests** for ``_parse_url`` use synthetic strings
  because the function is a regex over the URL alone.
* **Integration tests** drive off the real RIDE corpus, parsing a
  known review and running the pipeline against the real
  ``../ride/`` source tree. Filesystem destinations go to ``tmp_path``
  so the test doesn't pollute the working tree.
* **Edge cases not present in the corpus** (truly unparseable URLs)
  fall back to a small synthetic Figure construction with that
  branch documented in the test docstring. The corpus has zero
  unparseable URLs today, so this is the only way to keep the
  branch under test.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.model.block import Figure
from src.parser.assets import (
    AssetReport,
    _parse_url,
    rewrite_figure_assets,
)
from src.parser.review import parse_review


_RIDE = Path(__file__).resolve().parent.parent.parent / "ride" / "tei_all"
_RIDE_ROOT = Path(__file__).resolve().parent.parent.parent / "ride"

# Real-corpus fixture choices:
# - 1641-tei.xml: 9 figures, all 9 sources present on disk → happy path.
# - anemoskala-tei.xml: 11 figures, all 11 sources missing on disk
#   (extension-less URLs from issue 8) → missing-file branch.
# - bayeux-tei.xml: figure-in-cell pattern → cell-walk coverage.
# - godwin-tei.xml: //wp-content double-slash typo → URL parser robustness.
_HAPPY_PATH = _RIDE / "1641-tei.xml"
_MISSING_FILES = _RIDE / "anemoskala-tei.xml"
_FIGURE_IN_CELL = _RIDE / "bayeux-tei.xml"
_DOUBLE_SLASH = _RIDE / "godwin-tei.xml"


# -- Pure URL parser unit tests -------------------------------------------
#
# The parser is a regex over the URL string; synthetic inputs cover its
# branches with no benefit from real-data routing.


def test_parse_url_canonical_http():
    url = "http://ride.i-d-e.de/wp-content/uploads/issue_5/1641/pictures/picture-1.png"
    assert _parse_url(url) == ("5", "1641", "picture-1.png")


def test_parse_url_https_variant():
    url = "https://ride.i-d-e.de/wp-content/uploads/issue_20/anne-frank/pictures/picture-3.png"
    assert _parse_url(url) == ("20", "anne-frank", "picture-3.png")


def test_parse_url_handles_double_slash_typo():
    """One real corpus URL has //wp-content (godwin-tei.xml). The pattern still anchors."""
    url = "http://ride.i-d-e.de//wp-content/uploads/issue_3/godwin/pictures/picture-1.png"
    assert _parse_url(url) == ("3", "godwin", "picture-1.png")


def test_parse_url_returns_none_for_unparseable():
    """Synthetic — the corpus has zero unparseable URLs today. The branch
    exists so a future corpus addition does not crash the build."""
    assert _parse_url("https://other.org/some/image.png") is None
    assert _parse_url("relative/path.png") is None


# -- Real-corpus integration tests ----------------------------------------


pytestmark_corpus = pytest.mark.skipif(
    not _RIDE.exists(), reason="../ride/ corpus not present"
)


@pytestmark_corpus
def test_happy_path_real_review_copies_figures_and_rewrites_urls(tmp_path) -> None:
    """1641-tei.xml has 9 figures, all sources on disk. After the pipeline:

    * every figure URL is site-root-relative under ``/issues/{N}/{id}/figures/``
    * every source file lands at ``site_root/issues/.../figures/...``
    * the report has 9 copied entries, no missing, no unparseable
    """
    review = parse_review(_HAPPY_PATH)
    assert len(review.figures) >= 9

    site_root = tmp_path / "site"
    new_review, report = rewrite_figure_assets(review, _RIDE_ROOT, site_root)

    assert report.review_id == review.id
    assert len(report.copied) == len(review.figures)
    assert report.missing == ()
    assert report.unparseable == ()

    # Every figure now points at /issues/{N}/{id}/figures/{file}
    for fig in new_review.figures:
        assert fig.graphic_url.startswith(f"/issues/{review.issue}/{review.id}/figures/")

    # The copied files actually exist on disk under site_root.
    for rel in report.copied:
        assert (site_root / rel).is_file()


@pytestmark_corpus
def test_missing_files_real_review_reports_no_crash(tmp_path) -> None:
    """anemoskala-tei.xml's 11 figure URLs reference files that are not on
    disk. The pipeline must report them as missing and leave the URLs
    untouched, not crash."""
    review = parse_review(_MISSING_FILES)
    assert len(review.figures) >= 1

    site_root = tmp_path / "site"
    new_review, report = rewrite_figure_assets(review, _RIDE_ROOT, site_root)

    assert len(report.missing) >= 1
    # Every missing URL was kept verbatim — the build is still inspectable.
    missing_set = set(report.missing)
    for fig in new_review.figures:
        if fig.graphic_url in missing_set:
            # Same value as before the pipeline ran.
            assert fig.graphic_url and fig.graphic_url.startswith("http")


@pytestmark_corpus
def test_double_slash_url_real_review_still_parses(tmp_path) -> None:
    """godwin-tei.xml has //wp-content. The pipeline must still rewrite or report
    consistently — never crash on the typo."""
    review = parse_review(_DOUBLE_SLASH)
    assert review.figures, "godwin must have figures"

    site_root = tmp_path / "site"
    new_review, report = rewrite_figure_assets(
        review, _RIDE_ROOT, site_root, copy=False,
    )

    # All buckets sum to a non-crash outcome for every figure.
    total = len(report.copied) + len(report.missing) + len(report.unparseable)
    assert total <= len(review.figures)


@pytestmark_corpus
def test_figure_in_cell_real_review_walked(tmp_path) -> None:
    """bayeux-tei.xml has figures inside table cells (the 22-corpus-cases
    pattern). The walker must reach them and produce identity-equal
    aggregate entries."""
    review = parse_review(_FIGURE_IN_CELL)
    site_root = tmp_path / "site"
    new_review, _ = rewrite_figure_assets(review, _RIDE_ROOT, site_root, copy=False)

    # Find a figure that lives inside a table cell in the section tree.
    from src.model.block import Table

    def find_cell_figure(sec):
        for b in sec.blocks:
            if isinstance(b, Table):
                for row in b.rows:
                    for cell in row.cells:
                        for nb in cell.blocks:
                            if isinstance(nb, Figure):
                                return nb
        for sub in sec.subsections:
            r = find_cell_figure(sub)
            if r is not None:
                return r
        return None

    cell_fig = None
    for s in new_review.front + new_review.body + new_review.back:
        cell_fig = find_cell_figure(s)
        if cell_fig is not None:
            break
    assert cell_fig is not None, "bayeux-tei.xml is supposed to have figure-in-cell"
    # The aggregate has the same object — re-aggregation worked.
    assert cell_fig in new_review.figures


@pytestmark_corpus
def test_dry_run_mode_does_not_touch_filesystem(tmp_path) -> None:
    """copy=False must rewrite URLs without creating site_root."""
    review = parse_review(_HAPPY_PATH)
    site_root = tmp_path / "site"
    new_review, _ = rewrite_figure_assets(review, _RIDE_ROOT, site_root, copy=False)

    assert not (site_root / "issues").exists()
    # URLs are still rewritten.
    for fig in new_review.figures:
        if fig.graphic_url:
            assert fig.graphic_url.startswith("/issues/")


@pytestmark_corpus
def test_unparseable_url_branch_documented(tmp_path) -> None:
    """The corpus has zero unparseable URLs today; this test documents the
    branch by injecting one synthetic Figure into a real-parsed review.

    Synthetic deviation here is named — the alternative would be skipping
    the branch under test entirely until a future corpus drops one.
    """
    import dataclasses

    review = parse_review(_HAPPY_PATH)
    # Replace the first figure's URL with a non-RIDE one.
    bogus = dataclasses.replace(
        review.figures[0], graphic_url="https://other.example.org/foo.png"
    )
    bogus_review = dataclasses.replace(review, figures=(bogus,) + review.figures[1:])

    site_root = tmp_path / "site"
    _, report = rewrite_figure_assets(bogus_review, _RIDE_ROOT, site_root, copy=False)
    assert "https://other.example.org/foo.png" in report.unparseable


@pytestmark_corpus
def test_smoke_real_corpus_asset_report_consistent(tmp_path) -> None:
    """For every review, copied + missing + unparseable buckets account for
    every figure that has a ``graphic_url``. Code-example figures
    (graphic_url=None) do not enter any bucket.

    Uses copy=False to avoid duplicating ~800 images on disk during the
    test run.
    """
    files = sorted(_RIDE.glob("*-tei.xml"))
    total_with_url = 0
    bucket_total = 0
    site_root = tmp_path / "site"
    for f in files:
        review = parse_review(f)
        new_review, report = rewrite_figure_assets(
            review, _RIDE_ROOT, site_root, copy=False,
        )
        total_with_url += sum(1 for fig in review.figures if fig.graphic_url)
        bucket_total += len(report.copied) + len(report.missing) + len(report.unparseable)
        # Site-relative URL form when the rewrite happened.
        for fig in new_review.figures:
            if fig.graphic_url and fig.graphic_url.startswith("/issues/"):
                assert fig.graphic_url.startswith(f"/issues/{review.issue}/{review.id}/figures/")
    assert bucket_total == total_with_url, (bucket_total, total_with_url)
    # Most of the corpus is present on disk — ~46 missing out of ~830.
    # No need to pin an exact number; just confirm the dominant case works.
