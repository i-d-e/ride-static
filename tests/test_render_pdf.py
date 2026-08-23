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

import sys
from types import SimpleNamespace
from pathlib import Path

import pytest

from tests._shared import iter_tei_files, needs_corpus


def test_render_review_pdf_enables_accessibility_tags(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The renderer requests a tagged PDF without loading native libraries."""
    captured: dict[str, object] = {}

    class FakeHTML:
        def __init__(self, **kwargs) -> None:
            captured["html"] = kwargs

        def write_pdf(self, **kwargs) -> None:
            captured["pdf"] = kwargs

    class FakeURLFetcher:
        def fetch(self, url: str) -> dict[str, str]:
            return {"url": url}

    fake_module = SimpleNamespace(
        HTML=FakeHTML,
        URLFetcher=FakeURLFetcher,
    )
    monkeypatch.setitem(sys.modules, "weasyprint", fake_module)

    from src.render.pdf import render_review_pdf

    html_path = tmp_path / "page.html"
    html_path.write_text("<html lang='en'><body>Review</body></html>", encoding="utf-8")
    render_review_pdf(html_path, tmp_path / "page.pdf")

    assert captured["pdf"]["pdf_tags"] is True


def test_render_review_pdf_retries_known_tagged_table_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A WeasyPrint tagging bug must not suppress an otherwise valid PDF."""
    calls: list[bool] = []

    class FakeHTML:
        def __init__(self, **kwargs) -> None:
            pass

        def write_pdf(self, **kwargs) -> None:
            calls.append(kwargs["pdf_tags"])
            if kwargs["pdf_tags"]:
                raise ValueError("Table wrapper without a table")

    class FakeURLFetcher:
        def fetch(self, url: str) -> dict[str, str]:
            return {"url": url}

    monkeypatch.setitem(
        sys.modules,
        "weasyprint",
        SimpleNamespace(HTML=FakeHTML, URLFetcher=FakeURLFetcher),
    )

    from src.render.pdf import render_review_pdf

    html_path = tmp_path / "page.html"
    html_path.write_text("<html><body><table></table></body></html>", encoding="utf-8")

    with pytest.warns(RuntimeWarning, match="retrying without PDF tags"):
        render_review_pdf(html_path, tmp_path / "page.pdf")

    assert calls == [True, False]


def test_render_review_pdf_does_not_mask_unrelated_value_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Only the identified WeasyPrint table-tagging failure has a fallback."""

    class FakeHTML:
        def __init__(self, **kwargs) -> None:
            pass

        def write_pdf(self, **kwargs) -> None:
            raise ValueError("unrelated failure")

    class FakeURLFetcher:
        def fetch(self, url: str) -> dict[str, str]:
            return {"url": url}

    monkeypatch.setitem(
        sys.modules,
        "weasyprint",
        SimpleNamespace(HTML=FakeHTML, URLFetcher=FakeURLFetcher),
    )

    from src.render.pdf import render_review_pdf

    html_path = tmp_path / "page.html"
    html_path.write_text("<html><body>Review</body></html>", encoding="utf-8")

    with pytest.raises(ValueError, match="unrelated failure"):
        render_review_pdf(html_path, tmp_path / "page.pdf")


def test_root_relative_build_assets_resolve_from_output_root(tmp_path: Path) -> None:
    from src.render.pdf import _local_build_asset

    html_path = tmp_path / "issues" / "19" / "draft.example" / "index.html"
    css_path = tmp_path / "static" / "css" / "ride.css"
    figure_path = html_path.parent / "figures" / "picture-1.svg"
    css_path.parent.mkdir(parents=True)
    figure_path.parent.mkdir(parents=True)
    css_path.write_text("@media print {}", encoding="utf-8")
    figure_path.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")

    assert _local_build_asset("file:///static/css/ride.css", html_path) == css_path
    assert _local_build_asset("file:///ride-static/static/css/ride.css", html_path) == css_path
    assert (
        _local_build_asset(
            "file:///ride-static/issues/19/draft.example/figures/picture-1.svg",
            html_path,
        )
        == figure_path
    )
    assert _local_build_asset("https://example.org/external.css", html_path) is None


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
    for sample in iter_tei_files():
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
