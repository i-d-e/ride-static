"""Walks over a parsed Review's section tree to collect document-order
sequences of figures and notes.

These aggregates feed the parallel apparate sub-blocks per
``knowledge/interface.md`` §6 (Figures and Notes columns under the
common Apparate divider). Computing them at parse time keeps the
templates pure: the renderer iterates ``review.figures`` and
``review.notes`` directly, never walks the tree itself.

References inline (``<ref>``) are not aggregated here — the references
apparate is bibliography-driven (Phase 6) plus inline-cross-ref-driven
(Phase 7 ref-resolver), and that join is more naturally built one phase
later.
"""
from __future__ import annotations

from typing import Iterator

from src.model.block import (
    Block,
    Citation,
    Figure,
    List,
    Paragraph,
    Table,
)
from src.model.inline import Emphasis, Highlight, Inline, Note, Reference
from src.model.section import Section


def collect_figures(sections: tuple[Section, ...]) -> tuple[Figure, ...]:
    """Walk the section tree depth-first and emit every ``Figure`` in
    document order. Includes figures embedded in cells and (rare) lists."""
    return tuple(_iter_figures(sections))


def collect_notes(sections: tuple[Section, ...]) -> tuple[Note, ...]:
    """Walk the section tree depth-first and emit every inline ``Note`` in
    document order. Notes live inside paragraph / heading / cell / item /
    bibl / quote inlines; the walker descends through every inline-bearing
    surface."""
    return tuple(_iter_notes(sections))


def _iter_figures(sections: tuple[Section, ...]) -> Iterator[Figure]:
    for s in sections:
        if s.heading:
            yield from _figures_in_inlines(s.heading)
        for b in s.blocks:
            yield from _figures_in_block(b)
        yield from _iter_figures(s.subsections)


def _iter_notes(sections: tuple[Section, ...]) -> Iterator[Note]:
    for s in sections:
        if s.heading:
            yield from _notes_in_inlines(s.heading)
        for b in s.blocks:
            yield from _notes_in_block(b)
        yield from _iter_notes(s.subsections)


def _figures_in_block(b: Block) -> Iterator[Figure]:
    if isinstance(b, Figure):
        yield b
    elif isinstance(b, Paragraph):
        yield from _figures_in_inlines(b.inlines)
    elif isinstance(b, List):
        for item in b.items:
            yield from _figures_in_inlines(item.inlines)
            if item.label:
                yield from _figures_in_inlines(item.label)
            for nested in item.blocks:
                yield from _figures_in_block(nested)
    elif isinstance(b, Table):
        if b.head:
            yield from _figures_in_inlines(b.head)
        for row in b.rows:
            for cell in row.cells:
                yield from _figures_in_inlines(cell.inlines)
                for nested in cell.blocks:
                    yield from _figures_in_block(nested)
    elif isinstance(b, Citation):
        yield from _figures_in_inlines(b.quote_inlines)
        if b.bibl is not None:
            yield from _figures_in_inlines(b.bibl.inlines)


def _notes_in_block(b: Block) -> Iterator[Note]:
    if isinstance(b, Figure):
        yield from _notes_in_inlines(b.head)
    elif isinstance(b, Paragraph):
        yield from _notes_in_inlines(b.inlines)
    elif isinstance(b, List):
        for item in b.items:
            yield from _notes_in_inlines(item.inlines)
            if item.label:
                yield from _notes_in_inlines(item.label)
            for nested in item.blocks:
                yield from _notes_in_block(nested)
    elif isinstance(b, Table):
        if b.head:
            yield from _notes_in_inlines(b.head)
        for row in b.rows:
            for cell in row.cells:
                yield from _notes_in_inlines(cell.inlines)
                for nested in cell.blocks:
                    yield from _notes_in_block(nested)
    elif isinstance(b, Citation):
        yield from _notes_in_inlines(b.quote_inlines)
        if b.bibl is not None:
            yield from _notes_in_inlines(b.bibl.inlines)


def _figures_in_inlines(inlines: tuple[Inline, ...]) -> Iterator[Figure]:
    """Inlines never contain Figures (the model forbids it). Empty iterator,
    kept for symmetry and as a no-op call site."""
    return iter(())


def _notes_in_inlines(inlines: tuple[Inline, ...]) -> Iterator[Note]:
    for inline in inlines:
        if isinstance(inline, Note):
            yield inline
            yield from _notes_in_inlines(inline.children)
        elif isinstance(inline, (Emphasis, Highlight, Reference)):
            yield from _notes_in_inlines(inline.children)
