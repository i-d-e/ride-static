"""Generic depth-first walkers over a parsed block tree.

Single source for the Paragraph / List / Table / Citation / Figure
dispatch and the descent into the block-level children that List items and
Table cells may carry. Three consumers build on these instead of
reimplementing the same recursion: figure collection and note collection
(``src.parser.aggregate``) and the explorer content metrics
(``src.render.explorer``).
"""
from __future__ import annotations

from typing import Iterable, Iterator

from src.model.block import Block, Citation, Figure, List, Paragraph, Table
from src.model.inline import Inline


def iter_blocks(blocks: Iterable[Block]) -> Iterator[Block]:
    """Every block in document order, descending into the block-level
    children carried by List items and Table cells."""
    for b in blocks:
        yield b
        if isinstance(b, List):
            for item in b.items:
                yield from iter_blocks(item.blocks)
        elif isinstance(b, Table):
            for row in b.rows:
                for cell in row.cells:
                    yield from iter_blocks(cell.blocks)


def iter_inline_groups(blocks: Iterable[Block]) -> Iterator[tuple[Inline, ...]]:
    """Every inline tuple reachable from a block sequence, in document
    order, descending into nested blocks. One tuple per inline-bearing
    surface: paragraph text, list item text and label, table head and cell
    text, citation quote and bibliography, figure caption. List item
    inlines precede the item's own nested blocks (the conventional reading
    order), so a consumer sees notes and references in document order.
    """
    for b in blocks:
        if isinstance(b, Paragraph):
            yield b.inlines
        elif isinstance(b, List):
            for item in b.items:
                yield item.inlines
                if item.label:
                    yield item.label
                yield from iter_inline_groups(item.blocks)
        elif isinstance(b, Table):
            if b.head:
                yield b.head
            for row in b.rows:
                for cell in row.cells:
                    yield cell.inlines
                    yield from iter_inline_groups(cell.blocks)
        elif isinstance(b, Citation):
            yield b.quote_inlines
            if b.bibl is not None:
                yield b.bibl.inlines
        elif isinstance(b, Figure):
            if b.head:
                yield b.head
