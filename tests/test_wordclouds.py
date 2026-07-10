"""Tests for scripts/wordclouds.py.

Two layers, per the CLAUDE.md hard rule:

* Extraction and stopword-selection tests drive the *real* TEI corpus
  through the script's parser, skipping when the corpus is absent.
* The render test is guarded like ``tests/test_render_pdf.py``: the
  optional ``wordcloud`` dependency (and its numpy/PIL/matplotlib deps)
  may be missing, so the whole render layer skips cleanly rather than
  failing at import time.

``load_stopwords`` for a language without a bundled list is a genuine
pure-function edge case that the corpus does exercise (Italian, one
review, no legacy list); it is asserted with a synthetic language code
as an explicit exception, documented in the test.
"""
from __future__ import annotations

from pathlib import Path

import pytest

import wordclouds
from tests._shared import iter_tei_files, needs_corpus

# Guard the optional dependency exactly like the WeasyPrint suite: both a
# missing package (ImportError) and missing native libs (OSError) skip.
try:
    import wordcloud  # noqa: F401

    HAS_WORDCLOUD = True
except (ImportError, OSError):
    HAS_WORDCLOUD = False

needs_wordcloud = pytest.mark.skipif(
    not HAS_WORDCLOUD,
    reason="wordcloud or its native dependencies are unavailable",
)


def _first_corpus_file() -> Path:
    files = list(iter_tei_files())
    if not files:
        pytest.skip("in-repo TEI corpus not present")
    return files[0]


@needs_corpus
def test_extract_review_id_matches_root_xml_id() -> None:
    tree = wordclouds.parse_tei(_first_corpus_file())
    review_id = wordclouds.extract_review_id(tree)
    assert review_id.startswith("ride.")


@needs_corpus
def test_extract_language_returns_an_ident() -> None:
    tree = wordclouds.parse_tei(_first_corpus_file())
    lang = wordclouds.extract_language(tree)
    assert lang in {"de", "en", "fr", "it"}


@needs_corpus
def test_extract_body_text_is_lowercased_and_collapsed() -> None:
    tree = wordclouds.parse_tei(_first_corpus_file())
    text = wordclouds.extract_body_text(tree)
    assert text
    assert text == text.lower()
    assert "  " not in text  # whitespace collapsed
    assert "\n" not in text


@needs_corpus
def test_stopwords_selected_by_review_language_are_nonempty() -> None:
    """The bundled de/en/fr lists load for the review's own language."""
    tree = wordclouds.parse_tei(_first_corpus_file())
    lang = wordclouds.extract_language(tree)
    stopwords = wordclouds.load_stopwords(lang)
    if lang in {"de", "en", "fr"}:
        assert stopwords, f"expected a bundled stopword list for {lang!r}"
        assert all(w == w.strip() for w in stopwords)


def test_stopwords_missing_language_returns_empty_set() -> None:
    """Pure-function edge case: a language with no bundled list (the corpus
    has one Italian review, and the legacy repo shipped no Italian list)
    yields an empty set so the render falls back to library stopwords.
    Synthetic language code used deliberately as the documented exception.
    """
    assert wordclouds.load_stopwords("xx") == set()


@needs_wordcloud
@needs_corpus
def test_run_writes_review_id_png(tmp_path: Path) -> None:
    tei_path = _first_corpus_file()
    tree = wordclouds.parse_tei(tei_path)
    review_id = wordclouds.extract_review_id(tree)

    out_path = wordclouds.run(tei_path, tmp_path, seed=7)

    assert out_path == tmp_path / f"{review_id}.png"
    assert out_path.exists()
    assert out_path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


@needs_wordcloud
@needs_corpus
def test_run_is_reproducible_with_fixed_seed(tmp_path: Path) -> None:
    """Same seed, byte-identical output — the property the fixed
    random_state buys over the stochastic legacy script."""
    tei_path = _first_corpus_file()
    a = tmp_path / "a"
    b = tmp_path / "b"

    out_a = wordclouds.run(tei_path, a, seed=123)
    out_b = wordclouds.run(tei_path, b, seed=123)

    assert out_a.read_bytes() == out_b.read_bytes()
