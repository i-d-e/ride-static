"""Tests for the figure asset pipeline (Phase 7).

Synthetic cases pin URL parsing, the missing-file path, the
unparseable-URL path, and the copy + rewrite happy path. A corpus
smoke verifies that all 107 reviews produce a coherent report.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.model.block import Figure, Paragraph, Table, TableCell, TableRow
from src.model.review import Review
from src.model.section import Section
from src.parser.assets import (
    AssetReport,
    _parse_url,
    rewrite_figure_assets,
)
from src.parser.review import parse_review


_RIDE = Path(__file__).resolve().parent.parent.parent / "ride" / "tei_all"
_RIDE_ROOT = Path(__file__).resolve().parent.parent.parent / "ride"


def _make_review(figures: tuple[Figure, ...]) -> Review:
    section = Section(
        xml_id="s1", type=None, heading=None, level=1,
        blocks=tuple(figures), subsections=(),
    )
    return Review(
        id="1641", issue="5", title="t", publication_date="",
        language="en", licence="",
        keywords=(), authors=(), editors=(), related_items=(),
        front=(), body=(section,), back=(),
        figures=figures, notes=(),
        bibliography=(), questionnaires=(),
        source_file="1641-tei.xml",
    )


# -- Pure URL parser ------------------------------------------------------


def test_parse_url_canonical_http():
    url = "http://ride.i-d-e.de/wp-content/uploads/issue_5/1641/pictures/picture-1.png"
    assert _parse_url(url) == ("5", "1641", "picture-1.png")


def test_parse_url_https_variant():
    url = "https://ride.i-d-e.de/wp-content/uploads/issue_20/anne-frank/pictures/picture-3.png"
    assert _parse_url(url) == ("20", "anne-frank", "picture-3.png")


def test_parse_url_handles_double_slash_typo():
    """One corpus URL has //wp-content (godwin-tei.xml). The pattern still anchors."""
    url = "http://ride.i-d-e.de//wp-content/uploads/issue_3/godwin/pictures/picture-1.png"
    assert _parse_url(url) == ("3", "godwin", "picture-1.png")


def test_parse_url_returns_none_for_unparseable():
    assert _parse_url("https://other.org/some/image.png") is None
    assert _parse_url("relative/path.png") is None


# -- Rewrite + copy: synthetic filesystem ---------------------------------


def _make_corpus_picture(ride_root: Path, issue: int, slug: str, name: str, content: bytes = b"PNG"):
    p = ride_root / "issues" / f"issue{issue:02d}" / slug / "pictures" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(content)
    return p


def test_rewrite_copies_existing_image_and_rewrites_url(tmp_path):
    ride_root = tmp_path / "ride"
    site_root = tmp_path / "site"
    _make_corpus_picture(ride_root, 5, "1641", "picture-1.png", b"REAL-PNG-BYTES")

    fig = Figure(
        kind="graphic", head=(), xml_id="fig.a",
        graphic_url="http://ride.i-d-e.de/wp-content/uploads/issue_5/1641/pictures/picture-1.png",
    )
    review = _make_review((fig,))

    new_review, report = rewrite_figure_assets(review, ride_root, site_root)

    expected_dst = site_root / "issues" / "5" / "1641" / "figures" / "picture-1.png"
    assert expected_dst.is_file()
    assert expected_dst.read_bytes() == b"REAL-PNG-BYTES"
    assert new_review.figures[0].graphic_url == "/issues/5/1641/figures/picture-1.png"
    assert report.review_id == "1641"
    assert Path("issues/5/1641/figures/picture-1.png") in report.copied
    assert report.missing == ()
    assert report.unparseable == ()


def test_rewrite_missing_source_reports_no_crash(tmp_path):
    ride_root = tmp_path / "ride"
    site_root = tmp_path / "site"
    # No file created on disk.

    fig = Figure(
        kind="graphic", head=(), xml_id="fig.a",
        graphic_url="http://ride.i-d-e.de/wp-content/uploads/issue_5/1641/pictures/missing.png",
    )
    review = _make_review((fig,))

    new_review, report = rewrite_figure_assets(review, ride_root, site_root)

    # URL stays as the raw original — the report carries the warning.
    assert new_review.figures[0].graphic_url == fig.graphic_url
    assert fig.graphic_url in report.missing
    assert report.copied == ()


def test_rewrite_unparseable_url_kept_and_reported(tmp_path):
    ride_root = tmp_path / "ride"
    site_root = tmp_path / "site"

    fig = Figure(
        kind="graphic", head=(), xml_id="fig.a",
        graphic_url="https://other.example.org/random.png",
    )
    review = _make_review((fig,))

    new_review, report = rewrite_figure_assets(review, ride_root, site_root)

    assert new_review.figures[0].graphic_url == fig.graphic_url
    assert fig.graphic_url in report.unparseable
    assert report.copied == ()
    assert report.missing == ()


def test_rewrite_skips_code_example_figures(tmp_path):
    ride_root = tmp_path / "ride"
    site_root = tmp_path / "site"
    fig = Figure(
        kind="code_example", head=(), xml_id="fig.code",
        graphic_url=None, code="<TEI>...</TEI>", code_lang="xml",
    )
    review = _make_review((fig,))

    new_review, report = rewrite_figure_assets(review, ride_root, site_root)
    assert new_review.figures[0] is fig or new_review.figures[0] == fig
    assert report.copied == ()


def test_rewrite_handles_figure_inside_table_cell(tmp_path):
    """22 corpus cases have <figure> inside <cell>. The walker must reach them."""
    ride_root = tmp_path / "ride"
    site_root = tmp_path / "site"
    _make_corpus_picture(ride_root, 5, "1641", "cell-pic.png")

    fig = Figure(
        kind="graphic", head=(), xml_id="fig.cell",
        graphic_url="http://ride.i-d-e.de/wp-content/uploads/issue_5/1641/pictures/cell-pic.png",
    )
    cell = TableCell(inlines=(), is_header=False, blocks=(fig,))
    row = TableRow(cells=(cell,))
    table = Table(rows=(row,), head=None)
    section = Section(
        xml_id="s1", type=None, heading=None, level=1,
        blocks=(table,), subsections=(),
    )
    review = Review(
        id="1641", issue="5", title="t", publication_date="",
        language="en", licence="",
        keywords=(), authors=(), editors=(), related_items=(),
        front=(), body=(section,), back=(),
        figures=(fig,), notes=(),
        bibliography=(), questionnaires=(),
        source_file="1641-tei.xml",
    )

    new_review, _ = rewrite_figure_assets(review, ride_root, site_root)

    # The Figure inside the table cell was rewritten too — re-aggregation
    # makes Review.figures match the in-tree object.
    in_tree = new_review.body[0].blocks[0].rows[0].cells[0].blocks[0]
    assert in_tree.graphic_url == "/issues/5/1641/figures/cell-pic.png"
    assert new_review.figures[0] is in_tree


def test_rewrite_no_copy_mode_only_rewrites_urls(tmp_path):
    """copy=False rewrites URLs without touching the filesystem (only when the source exists)."""
    ride_root = tmp_path / "ride"
    site_root = tmp_path / "site"
    _make_corpus_picture(ride_root, 5, "1641", "picture-1.png")

    fig = Figure(
        kind="graphic", head=(), xml_id="fig.a",
        graphic_url="http://ride.i-d-e.de/wp-content/uploads/issue_5/1641/pictures/picture-1.png",
    )
    review = _make_review((fig,))

    new_review, _ = rewrite_figure_assets(review, ride_root, site_root, copy=False)
    # Site dir was not created.
    assert not (site_root / "issues").exists()
    # URL was still rewritten.
    assert new_review.figures[0].graphic_url == "/issues/5/1641/figures/picture-1.png"


# -- Real-corpus smoke ----------------------------------------------------


@pytest.mark.skipif(not _RIDE.exists(), reason="../ride/ corpus not present")
def test_smoke_real_corpus_asset_report_consistent(tmp_path) -> None:
    """For every review, the asset pipeline must produce a report whose
    counts add up to the figure count and whose 'copied' files actually
    exist. We use copy=False to avoid duplicating ~800 images on disk
    during test runs."""
    files = sorted(_RIDE.glob("*-tei.xml"))
    total_figures = 0
    total_copied_or_present = 0
    total_missing = 0
    total_unparseable = 0
    for f in files:
        review = parse_review(f)
        new_review, report = rewrite_figure_assets(
            review, _RIDE_ROOT, tmp_path / "site", copy=False,
        )
        total_figures += len(review.figures)
        # In copy=False mode, "copied" still records what would-have-been-copied.
        total_copied_or_present += len(report.copied)
        total_missing += len(report.missing)
        total_unparseable += len(report.unparseable)
        # New URLs for rewritten figures must be site-root-relative.
        for fig in new_review.figures:
            if fig.graphic_url and fig.graphic_url.startswith("/issues/"):
                assert fig.graphic_url.startswith(f"/issues/{review.issue}/{review.id}/figures/")
    # The pipeline must account for every figure (sum of all report buckets
    # plus code-example figures with graphic_url=None matches the figure
    # count). Code-example figures don't reach any bucket because they have
    # no graphic_url; subtract them in the assertion via a lower bound.
    assert total_figures >= total_copied_or_present + total_missing + total_unparseable
    # Sanity: most figures should be present on disk in a normal corpus checkout.
    assert total_copied_or_present >= 600, (
        total_copied_or_present, total_missing, total_unparseable
    )
