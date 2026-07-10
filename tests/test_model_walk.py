"""Tests for ``src.model.walk`` — the shared block-tree walkers.

Real-corpus drive per the CLAUDE.md hard rule: ``iter_blocks`` and
``iter_inline_groups`` are the single source for the Paragraph / List /
Table / Citation / Figure dispatch and the descent into the block-level
children carried by List items and Table cells. The corpus is the only
place that actually nests a figure inside a table cell or a paragraph
inside a list item, so the descent can only be proven against parsed
reviews. Skips cleanly when the corpus is absent.
"""
from __future__ import annotations

from typing import Iterator

import pytest

from src.model.block import Figure
from src.model.inline import Emphasis, Highlight, Note, Reference
from src.model.section import Section
from src.model.walk import iter_blocks, iter_inline_groups


def _all_section_blocks(sections: tuple[Section, ...]) -> Iterator:
    """Top-level blocks across the whole section tree (front + body),
    without descending into a block's own List/Table children — that
    descent is exactly what ``iter_blocks`` is under test to perform."""
    for s in sections:
        yield from s.blocks
        yield from _all_section_blocks(s.subsections)


def _notes_in_groups(groups) -> Iterator[Note]:
    def walk(inlines):
        for inl in inlines:
            if isinstance(inl, Note):
                yield inl
                yield from walk(inl.children)
            elif isinstance(inl, (Emphasis, Highlight, Reference)):
                yield from walk(inl.children)

    for group in groups:
        yield from walk(group)


def test_iter_blocks_yields_every_figure_in_document_order(corpus_review):
    """The figures reachable by walking the block tree equal the parser's
    aggregated ``review.figures`` — same objects, same order."""
    walked = [
        b
        for b in iter_blocks(_all_section_blocks(corpus_review.front + corpus_review.body))
        if isinstance(b, Figure)
    ]
    assert walked == list(corpus_review.figures)


def test_iter_inline_groups_reaches_every_aggregated_note(corpus_review):
    """Notes collected from the inline groups equal the parser's
    ``review.notes`` (headings excluded — those are not block content)."""
    sections = corpus_review.front + corpus_review.body
    top_blocks = list(_all_section_blocks(sections))
    heading_notes = list(
        _notes_in_groups(s.heading for s in _iter_sections(sections) if s.heading)
    )
    body_notes = list(_notes_in_groups(iter_inline_groups(top_blocks)))
    assert set(id(n) for n in heading_notes + body_notes) == set(
        id(n) for n in corpus_review.notes
    )


def _iter_sections(sections: tuple[Section, ...]) -> Iterator[Section]:
    for s in sections:
        yield s
        yield from _iter_sections(s.subsections)


def test_walker_descends_into_nested_blocks_somewhere_in_the_corpus(corpus_reviews):
    """At least one real review nests a figure inside a table cell or list
    item, so ``iter_blocks`` must yield more figures than the flat count of
    top-level figure blocks. Guards against a walker that stops at depth 0."""
    for review in corpus_reviews:
        sections = review.front + review.body
        top = list(_all_section_blocks(sections))
        flat_figures = sum(1 for b in top if isinstance(b, Figure))
        deep_figures = sum(1 for b in iter_blocks(top) if isinstance(b, Figure))
        if deep_figures > flat_figures:
            return
    pytest.skip("no corpus review nests a figure below the top block level")
