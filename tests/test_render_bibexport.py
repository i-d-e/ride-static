"""Corpus-wide bibliography export — real-corpus integration tests.

Drives the real TEI corpus through the parser (via the shared
``corpus_reviews`` fixture) and asserts the two export artefacts the Zotero
mass-import channel produces. Per the CLAUDE.md hard rule the entries are
generated from real parsed reviews, not synthetic dataclass values.
"""
from __future__ import annotations

import json

from src.render.bibexport import write_bibliography_exports


def test_writes_exact_destination_paths(corpus_reviews, tmp_path):
    bib_path, csl_path = write_bibliography_exports(corpus_reviews, tmp_path)
    assert bib_path == tmp_path / "ride-corpus.bib"
    assert csl_path == tmp_path / "ride-corpus.csl.json"
    assert bib_path.is_file()
    assert csl_path.is_file()


def test_one_csl_entry_per_review(corpus_reviews, tmp_path):
    _, csl_path = write_bibliography_exports(corpus_reviews, tmp_path)
    data = json.loads(csl_path.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) == len(corpus_reviews)


def test_one_bibtex_entry_per_review(corpus_reviews, tmp_path):
    bib_path, _ = write_bibliography_exports(corpus_reviews, tmp_path)
    text = bib_path.read_text(encoding="utf-8")
    assert text.count("@article{") == len(corpus_reviews)


def test_known_review_csl_keys(corpus_reviews, tmp_path):
    _, csl_path = write_bibliography_exports(corpus_reviews, tmp_path)
    data = json.loads(csl_path.read_text(encoding="utf-8"))
    entry = next(e for e in data if e["id"] == "ride.21.4")
    assert entry["type"] == "article-journal"
    assert entry["title"]
    assert "container-title" in entry
    assert entry["author"]


def test_known_review_in_bibtex(corpus_reviews, tmp_path):
    bib_path, _ = write_bibliography_exports(corpus_reviews, tmp_path)
    text = bib_path.read_text(encoding="utf-8")
    assert "@article{ride.21.4," in text


def test_deterministic_ordering_byte_identical(corpus_reviews, tmp_path):
    first = tmp_path / "a"
    second = tmp_path / "b"
    bib1, csl1 = write_bibliography_exports(corpus_reviews, first)
    bib2, csl2 = write_bibliography_exports(corpus_reviews, second)
    assert bib1.read_bytes() == bib2.read_bytes()
    assert csl1.read_bytes() == csl2.read_bytes()


def test_csl_ordered_issue_then_id(corpus_reviews, tmp_path):
    """Deterministic order is (issue numeric prefix, review id)."""
    from src.render.html import issue_numeric_prefix

    _, csl_path = write_bibliography_exports(corpus_reviews, tmp_path)
    data = json.loads(csl_path.read_text(encoding="utf-8"))
    by_id = {r.id: r for r in corpus_reviews}
    keys = [
        (issue_numeric_prefix(by_id[e["id"]].issue or ""), e["id"])
        for e in data
        if e["id"] in by_id
    ]
    assert keys == sorted(keys)
