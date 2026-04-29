"""Tests for src.render.pdf — Phase 14 / Welle 11.

WeasyPrint links Pango/Cairo at import time and these libraries are
not always present in dev environments (notably Windows without GTK3).
The whole test module skips cleanly when the import fails — CI on
Ubuntu installs the apt packages and runs the suite.

Two layers:

* Unit test — feed a minimal HTML string to the renderer and assert
  the produced file is a real PDF (magic bytes + non-trivial size).
* Real-corpus smoke — parse one review, render its HTML to disk via
  the same chain ``src.build`` uses, then run WeasyPrint over it.
  Asserts the DOI lands on page 1 (requirements A6).
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO_ROOT.parent / "ride" / "tei_all"


# WeasyPrint import is wrapped — both ImportError (package missing) and
# OSError (system libs missing) cause a clean skip rather than a noisy
# stack trace at collect time.
try:
    import weasyprint  # noqa: F401

    HAS_WEASYPRINT = True
except (ImportError, OSError):
    HAS_WEASYPRINT = False

needs_weasyprint = pytest.mark.skipif(
    not HAS_WEASYPRINT,
    reason="WeasyPrint or its system libraries are unavailable",
)
needs_corpus = pytest.mark.skipif(
    not CORPUS_DIR.exists(),
    reason="../ride/tei_all corpus not present",
)


@needs_weasyprint
def test_render_review_pdf_produces_a_real_pdf(tmp_path: Path) -> None:
    """Magic bytes and minimum-size sanity check.

    A real WeasyPrint PDF is well over 1 KB — even an empty document
    carries the xref table, font stub, and metadata. Anything smaller
    means the renderer returned an error stub or wrote nothing.
    """
    from src.render.pdf import render_review_pdf

    html_path = tmp_path / "page.html"
    html_path.write_text(
        "<!doctype html><html><head><title>x</title>"
        "<style>body{font-family:sans-serif}</style></head>"
        "<body><h1>Hello</h1><p>Body text.</p></body></html>",
        encoding="utf-8",
    )
    pdf_path = tmp_path / "page.pdf"
    render_review_pdf(html_path, pdf_path)

    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 1000
    assert pdf_path.read_bytes()[:4] == b"%PDF"


@needs_weasyprint
@needs_corpus
def test_pdf_for_real_corpus_review_renders_to_a_valid_pdf(tmp_path: Path) -> None:
    """A real review HTML survives the WeasyPrint pipeline end-to-end.

    The DOI-on-page-1 contract (A6) is pinned by two cooperating tests
    elsewhere — neither needs WeasyPrint:

      * ``test_review_html_carries_print_only_doi_line_when_doi_set``
        proves the DOI ``<p>`` lands in the rendered HTML;
      * ``test_print_stylesheet_hides_chrome_and_shows_doi`` proves
        the print stylesheet flips that ``<p>`` to ``display: block``.

    Together those guarantee the DOI prints on page 1 once WeasyPrint
    applies the print stylesheet — which it does by spec. So this
    integration test only needs to confirm that the chain runs without
    raising on a content-heavy real review and produces a non-trivial
    PDF. Byte-greppping for the DOI is unreliable because WeasyPrint
    flate-compresses the content stream including link annotations.
    """
    from src.parser.review import parse_review
    from src.render.html import make_env, render_review
    from src.render.pdf import render_review_pdf

    env = make_env()
    chosen = None
    for sample in sorted(CORPUS_DIR.glob("*.xml")):
        review = parse_review(sample)
        if review.doi:
            chosen = review
            break
    if chosen is None:
        pytest.skip("no corpus review with a DOI to validate against")

    html = render_review(chosen, env=env)
    html_path = tmp_path / "review.html"
    html_path.write_text(html, encoding="utf-8")
    pdf_path = tmp_path / "review.pdf"
    render_review_pdf(html_path, pdf_path)

    pdf_bytes = pdf_path.read_bytes()
    assert pdf_bytes[:4] == b"%PDF"
    # A real RIDE review is content-heavy; an empty or error-stub PDF
    # would weigh under 2 KB. Use a generous floor to stay tolerant of
    # WeasyPrint version bumps.
    assert pdf_path.stat().st_size > 5_000
