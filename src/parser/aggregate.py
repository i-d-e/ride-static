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

from src.model.block import Figure
from src.model.inline import Amendment, Emphasis, Highlight, Inline, Note, Reference
from src.model.section import Section
from src.model.walk import iter_blocks, iter_inline_groups


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


def collect_amendments(sections: tuple[Section, ...]) -> tuple[Amendment, ...]:
    """Walk the section tree depth-first and emit every ``Amendment`` inline
    (``<mod>``) in document order. Amendments live inside paragraph / heading /
    figure-caption inlines and, in the sandrart case, nested inside a ``<note>``,
    so the walker descends through Note children as well. ``date`` / ``resp``
    are filled later in :func:`src.parser.review.parse_review`; here the raw
    parsed inlines are gathered unchanged."""
    return tuple(_iter_amendments(sections))


def _iter_figures(sections: tuple[Section, ...]) -> Iterator[Figure]:
    for s in sections:
        for b in iter_blocks(s.blocks):
            if isinstance(b, Figure):
                yield b
        yield from _iter_figures(s.subsections)


def _iter_notes(sections: tuple[Section, ...]) -> Iterator[Note]:
    for s in sections:
        if s.heading:
            yield from _notes_in_inlines(s.heading)
        for group in iter_inline_groups(s.blocks):
            yield from _notes_in_inlines(group)
        yield from _iter_notes(s.subsections)


def _notes_in_inlines(inlines: tuple[Inline, ...]) -> Iterator[Note]:
    for inline in inlines:
        if isinstance(inline, Note):
            yield inline
            yield from _notes_in_inlines(inline.children)
        elif isinstance(inline, (Emphasis, Highlight, Reference)):
            yield from _notes_in_inlines(inline.children)
        # Amendment is intentionally not descended: the <note> child of a
        # <mod> is an amendment note and must stay out of the footnotes
        # apparate (per the legacy-parity contract).


def _iter_amendments(sections: tuple[Section, ...]) -> Iterator[Amendment]:
    for s in sections:
        if s.heading:
            yield from _amendments_in_inlines(s.heading)
        for group in iter_inline_groups(s.blocks):
            yield from _amendments_in_inlines(group)
        yield from _iter_amendments(s.subsections)


def _amendments_in_inlines(inlines: tuple[Inline, ...]) -> Iterator[Amendment]:
    for inline in inlines:
        if isinstance(inline, Amendment):
            yield inline
        elif isinstance(inline, (Emphasis, Highlight, Reference, Note)):
            yield from _amendments_in_inlines(inline.children)
