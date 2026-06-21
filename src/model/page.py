"""Domain model for editorial pages (the non-review RIDE pages).

A :class:`Page` is parsed from a ``pages/*.xml`` TEI file (profile
``schema/ride-pages.rng``). It carries the reduced header metadata and a
structured body tree so the build can both render it and assert that the
data arrived correctly, rather than rendering an opaque HTML string.

Body grammar mirrors the page profile: a body holds blocks (Section,
Para, BulletList, Table); inline content is Text interleaved with Ref,
PersName, Email, Hi and Lb. Frozen dataclasses, consistent with the
review model.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union


# ── Inline nodes ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class Text:
    value: str


@dataclass(frozen=True)
class Lb:
    """A line break (<lb/>); carries no text."""


@dataclass(frozen=True)
class Email:
    value: str


@dataclass(frozen=True)
class PersName:
    name: str
    ref: Optional[str] = None


@dataclass(frozen=True)
class Ref:
    target: str
    children: tuple["Inline", ...] = ()


@dataclass(frozen=True)
class Hi:
    rend: Optional[str]
    children: tuple["Inline", ...] = ()


Inline = Union[Text, Lb, Email, PersName, Ref, Hi]


# ── Block nodes ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class Para:
    inlines: tuple[Inline, ...]


@dataclass(frozen=True)
class ListItem:
    inlines: tuple[Inline, ...]


@dataclass(frozen=True)
class BulletList:
    items: tuple[ListItem, ...]


@dataclass(frozen=True)
class Cell:
    inlines: tuple[Inline, ...]


@dataclass(frozen=True)
class Row:
    cells: tuple[Cell, ...]


@dataclass(frozen=True)
class Table:
    rows: tuple[Row, ...]


@dataclass(frozen=True)
class Section:
    head: tuple[Inline, ...]
    blocks: tuple["Block", ...]


Block = Union[Section, Para, BulletList, Table]


# ── Page ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PageEditor:
    name: str
    role: Optional[str] = None
    ref: Optional[str] = None


@dataclass(frozen=True)
class Page:
    slug: str
    title: str
    source_url: Optional[str]
    licence: Optional[str]
    journal_title: Optional[str]
    editors: tuple[PageEditor, ...]
    blocks: tuple[Block, ...]


# ── Text projection (for fidelity checks and assertions) ──────────────


def inline_text(nodes: tuple[Inline, ...]) -> str:
    """Concatenate the visible text of an inline sequence (Lb yields none)."""
    parts: list[str] = []
    for n in nodes:
        if isinstance(n, Text):
            parts.append(n.value)
        elif isinstance(n, Email):
            parts.append(n.value)
        elif isinstance(n, PersName):
            parts.append(n.name)
        elif isinstance(n, (Ref, Hi)):
            parts.append(inline_text(n.children))
    return "".join(parts)


def block_text(block: Block) -> str:
    if isinstance(block, Section):
        return inline_text(block.head) + "".join(block_text(b) for b in block.blocks)
    if isinstance(block, Para):
        return inline_text(block.inlines)
    if isinstance(block, BulletList):
        return "".join(inline_text(it.inlines) for it in block.items)
    if isinstance(block, Table):
        return "".join(
            inline_text(c.inlines) for r in block.rows for c in r.cells
        )
    return ""


def page_text(page: Page) -> str:
    return "".join(block_text(b) for b in page.blocks)
