"""Block-level domain types — the children of a section.

Verified against the corpus: five block kinds suffice — Paragraph, List, Table,
Figure, Citation. ``<head>`` is consumed by the section parser as section heading
and is never a block on its own. ``<note>`` and ``<code>`` are inline-only.
``<eg>`` exists exclusively inside ``<figure>`` and is modelled as
``Figure(kind="code_example")`` rather than a separate block kind.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union

from src.model.inline import Inline


@dataclass(frozen=True)
class Paragraph:
    """``<p>`` — the dominant block.

    ``n`` carries the optional ``@n`` value. RIDE uses it for citation-anchor
    paragraph numbers; see ``knowledge/interface.md`` §11 (copy-link affordance).
    """

    inlines: tuple[Inline, ...]
    n: Optional[str] = None


@dataclass(frozen=True)
class ListItem:
    """``<item>``. ``label`` is set only when the parent list has ``rend="labeled"``."""

    inlines: tuple[Inline, ...]
    label: Optional[tuple[Inline, ...]] = None


@dataclass(frozen=True)
class List:
    """``<list>`` with three kinds, after normalisation of ``numbered`` and ``unordered``.

    ``kind`` ∈ {``bulleted``, ``ordered``, ``labeled``}. The corpus also contains
    ``rend="numbered"`` (8) and ``rend="unordered"`` (2), normalised to ``ordered``
    and ``bulleted`` at parse time with a warning.
    """

    items: tuple[ListItem, ...]
    kind: str = "bulleted"


@dataclass(frozen=True)
class TableCell:
    """``<cell>``. The corpus has flat tables (``@rows="1"``, ``@cols="1"`` always)."""

    inlines: tuple[Inline, ...]
    is_header: bool = False


@dataclass(frozen=True)
class TableRow:
    """``<row>``."""

    cells: tuple[TableCell, ...]


@dataclass(frozen=True)
class Table:
    """``<table>`` with optional ``<head>`` rendered above the rows."""

    rows: tuple[TableRow, ...]
    head: Optional[tuple[Inline, ...]] = None


@dataclass(frozen=True)
class Figure:
    """``<figure>`` with two kinds.

    ``kind="graphic"`` covers the regular case (833 of 874 in the corpus): a
    ``<graphic>`` child with ``@url``. ``kind="code_example"`` covers the 41
    figures that contain ``<eg>`` instead — typically TEI markup samples.
    """

    kind: str
    head: tuple[Inline, ...]
    graphic_url: Optional[str] = None
    code: Optional[str] = None
    code_lang: Optional[str] = None


@dataclass(frozen=True)
class Citation:
    """``<cit>`` — a quotation with optional bibliographic attribution.

    ``bibl`` keeps the inline children of ``<bibl>`` (emph, ref, date, …) rather
    than flattening to a string, so the renderer preserves emphasis and links.
    """

    quote_inlines: tuple[Inline, ...]
    bibl: Optional[tuple[Inline, ...]] = None
    bibl_target: Optional[str] = None


Block = Union[Paragraph, List, Table, Figure, Citation]
