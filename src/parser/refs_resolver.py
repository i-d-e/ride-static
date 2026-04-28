"""Reference-Resolver — fills ``Reference.bucket`` on every ``<ref>`` in a parsed review.

Phase 7 scope. Each ``Reference.target`` is classified into one of four
buckets:

* ``local`` — ``#xml-id`` and the anchor exists in the same review's
  ``xml:id`` index (Section, Paragraph, Figure, Note, BibEntry).
* ``criteria`` — ``#K…`` (5 209 corpus occurrences). The K-IDs live on
  the criteria document referenced by the taxonomy's ``@xml:base`` and
  are not local anchors. The renderer dispatches to an external link
  using the questionnaire's ``criteria_url``.
* ``external`` — target starts with ``http://`` or ``https://``.
* ``orphan`` — target is set but matches none of the above. Includes
  bare bibkeys (``werner2019``), ``mailto:`` URIs, the ~70
  non-K dangling-internal anchors (``#abb…`` etc.), and any other
  unresolvable form. The renderer's job is to emit them as plain text;
  Phase 13 will surface aggregated counts as a build warning.

If ``Reference.target`` itself is ``None`` (no ``@target`` on the source
``<ref>``), ``bucket`` stays ``None`` — the renderer treats that as a
non-link span.

The resolver is a pure transform: it returns a new ``Review`` with all
``Reference`` instances rebuilt via ``dataclasses.replace``. The original
parse output is not mutated.
"""
from __future__ import annotations

import dataclasses
from typing import Optional

from src.model.bibliography import BibEntry
from src.model.block import (
    Block,
    Citation,
    Figure,
    List as ListBlock,
    ListItem,
    Paragraph,
    Table,
    TableCell,
    TableRow,
)
from src.model.inline import (
    Emphasis,
    Highlight,
    Inline,
    Note,
    Reference,
)
from src.model.review import Review
from src.model.section import Section
from src.parser.aggregate import collect_figures, collect_notes


def classify_target(target: Optional[str], id_index: frozenset[str]) -> Optional[str]:
    """Return the bucket name for ``target`` against ``id_index``.

    ``None`` if ``target`` is empty. Otherwise one of
    ``"local" | "criteria" | "external" | "orphan"``.
    """
    if not target:
        return None
    if target.startswith(("http://", "https://")):
        return "external"
    if target.startswith("#"):
        anchor = target[1:]
        # The K-prefix check sits before the local-anchor check on
        # purpose: K-IDs are external by contract (they live on the
        # criteria document). If a K-ID happened to also appear as a
        # local xml:id it would still be a criteria reference, not a
        # local anchor.
        if anchor.startswith("K"):
            return "criteria"
        if anchor in id_index:
            return "local"
        return "orphan"
    return "orphan"


def resolve_references(review: Review) -> Review:
    """Return a copy of ``review`` with every ``Reference.bucket`` filled.

    The walker descends through every inline-bearing surface — section
    headings, blocks, list items, table cells, figure heads, citations,
    bibliography entries — and rebuilds the dataclasses with the bucket
    set. ``id_index`` is built once and shared across the walk.

    ``Review.figures`` and ``Review.notes`` are then **re-aggregated** from
    the resolved section tree rather than walked separately, so the
    aggregate-view objects keep identity with their counterparts inside
    sections. Walking them as an independent pass would create a divergent
    second copy of every figure / note.
    """
    id_index = _build_id_index(review)
    new_front = tuple(_walk_section(s, id_index) for s in review.front)
    new_body = tuple(_walk_section(s, id_index) for s in review.body)
    new_back = tuple(_walk_section(s, id_index) for s in review.back)
    new_bibliography = tuple(_walk_bib(b, id_index) for b in review.bibliography)
    all_sections = new_front + new_body + new_back
    return dataclasses.replace(
        review,
        front=new_front,
        body=new_body,
        back=new_back,
        figures=collect_figures(all_sections),
        notes=collect_notes(all_sections),
        bibliography=new_bibliography,
    )


def _build_id_index(review: Review) -> frozenset[str]:
    """Collect every ``xml:id`` reachable inside the review.

    Sections, subsections, paragraphs, figures, notes, and bibliography
    entries all contribute. Citations and inline-only constructs do not
    expose ``xml:id`` themselves.
    """
    ids: set[str] = set()

    def visit_section(sec: Section) -> None:
        if sec.xml_id:
            ids.add(sec.xml_id)
        for block in sec.blocks:
            visit_block(block)
        for sub in sec.subsections:
            visit_section(sub)

    def visit_block(block: Block) -> None:
        if isinstance(block, Paragraph):
            if block.xml_id:
                ids.add(block.xml_id)
        elif isinstance(block, ListBlock):
            for item in block.items:
                for inner in item.blocks:
                    visit_block(inner)
        elif isinstance(block, Table):
            for row in block.rows:
                for cell in row.cells:
                    for inner in cell.blocks:
                        visit_block(inner)
        elif isinstance(block, Figure):
            if block.xml_id:
                ids.add(block.xml_id)
        # Citation has no own xml:id; its bibl entry might.
        elif isinstance(block, Citation) and block.bibl is not None and block.bibl.xml_id:
            ids.add(block.bibl.xml_id)

    for sec in review.front + review.body + review.back:
        visit_section(sec)
    for fig in review.figures:
        if fig.xml_id:
            ids.add(fig.xml_id)
    for note in review.notes:
        if note.xml_id:
            ids.add(note.xml_id)
    for bib in review.bibliography:
        if bib.xml_id:
            ids.add(bib.xml_id)

    return frozenset(ids)


# ---------- Walkers (pure dataclass transforms) ----------


def _walk_section(sec: Section, id_index: frozenset[str]) -> Section:
    return dataclasses.replace(
        sec,
        heading=_walk_inlines(sec.heading, id_index) if sec.heading is not None else None,
        blocks=tuple(_walk_block(b, id_index) for b in sec.blocks),
        subsections=tuple(_walk_section(s, id_index) for s in sec.subsections),
    )


def _walk_block(block: Block, id_index: frozenset[str]) -> Block:
    if isinstance(block, Paragraph):
        return dataclasses.replace(block, inlines=_walk_inlines(block.inlines, id_index))
    if isinstance(block, ListBlock):
        return dataclasses.replace(
            block,
            items=tuple(_walk_list_item(i, id_index) for i in block.items),
        )
    if isinstance(block, Table):
        return dataclasses.replace(
            block,
            head=_walk_inlines(block.head, id_index) if block.head is not None else None,
            rows=tuple(_walk_table_row(r, id_index) for r in block.rows),
        )
    if isinstance(block, Figure):
        return _walk_figure(block, id_index)
    if isinstance(block, Citation):
        return dataclasses.replace(
            block,
            quote_inlines=_walk_inlines(block.quote_inlines, id_index),
            bibl=_walk_bib(block.bibl, id_index) if block.bibl is not None else None,
        )
    raise TypeError(f"unhandled block kind {type(block).__name__!r}")


def _walk_list_item(item: ListItem, id_index: frozenset[str]) -> ListItem:
    return dataclasses.replace(
        item,
        inlines=_walk_inlines(item.inlines, id_index),
        label=_walk_inlines(item.label, id_index) if item.label is not None else None,
        blocks=tuple(_walk_block(b, id_index) for b in item.blocks),
    )


def _walk_table_row(row: TableRow, id_index: frozenset[str]) -> TableRow:
    return dataclasses.replace(
        row,
        cells=tuple(_walk_table_cell(c, id_index) for c in row.cells),
    )


def _walk_table_cell(cell: TableCell, id_index: frozenset[str]) -> TableCell:
    return dataclasses.replace(
        cell,
        inlines=_walk_inlines(cell.inlines, id_index),
        blocks=tuple(_walk_block(b, id_index) for b in cell.blocks),
    )


def _walk_figure(fig: Figure, id_index: frozenset[str]) -> Figure:
    return dataclasses.replace(fig, head=_walk_inlines(fig.head, id_index))


def _walk_note(note: Note, id_index: frozenset[str]) -> Note:
    return dataclasses.replace(note, children=_walk_inlines(note.children, id_index))


def _walk_bib(bib: BibEntry, id_index: frozenset[str]) -> BibEntry:
    return dataclasses.replace(bib, inlines=_walk_inlines(bib.inlines, id_index))


def _walk_inlines(
    inlines: tuple[Inline, ...], id_index: frozenset[str]
) -> tuple[Inline, ...]:
    return tuple(_walk_inline(i, id_index) for i in inlines)


def _walk_inline(inline: Inline, id_index: frozenset[str]) -> Inline:
    if isinstance(inline, Reference):
        return dataclasses.replace(
            inline,
            children=_walk_inlines(inline.children, id_index),
            bucket=classify_target(inline.target, id_index),
        )
    if isinstance(inline, Emphasis):
        return dataclasses.replace(inline, children=_walk_inlines(inline.children, id_index))
    if isinstance(inline, Highlight):
        return dataclasses.replace(inline, children=_walk_inlines(inline.children, id_index))
    if isinstance(inline, Note):
        return _walk_note(inline, id_index)
    # Text and InlineCode have no children to walk.
    return inline
