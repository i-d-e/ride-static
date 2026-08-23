"""Corpus discovery tests for legacy reviews and review bundles."""

from __future__ import annotations

from src._corpus import find_tei, iter_tei_files
from tests._shared import needs_corpus


@needs_corpus
def test_bundle_review_is_discovered_by_folder_slug() -> None:
    """The teiCrafter pilot is the real-corpus fixture for the bundle layout."""
    path = find_tei("teicrafter-pilot")

    assert path.name == "review.xml"
    assert path.parent.name == "teicrafter-pilot"
    assert path in tuple(iter_tei_files())
