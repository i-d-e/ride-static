"""Block-level domain types — the children of a section.

Verified against the corpus: five block kinds suffice — Paragraph, List, Table,
Figure, Citation. ``<head>`` is consumed by the section parser as section heading
and is never a block on its own. ``<note>`` and ``<code>`` are inline-only.
``<eg>`` exists exclusively inside ``<figure>`` and is modelled as
``Figure(kind="code_example")`` rather than a separate block kind.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Union

from src.model.inline import Inline

if TYPE_CHECKING:
    from src.model.bibliography import BibEntry


@dataclass(frozen=True)
class Paragraph:
    """``<p>`` — the dominant block.

    ``xml_id`` is the citation-anchor target referenced by copy-link (3590 of
    3809 paragraphs in the corpus carry one). When ``@xml:id`` is missing, the
    field stays ``None`` and the renderer is free to synthesise a positional
    fallback at render time.

    ``n`` carries the optional ``@n`` value, the human-visible paragraph number
    rendered in the margin per ``knowledge/interface.md`` §11.
    """

    inlines: tuple[Inline, ...]
    xml_id: Optional[str] = None
    n: Optional[str] = None


@dataclass(frozen=True)
class ListItem:
    """``<item>``. ``label`` is set only when the parent list has ``rend="labeled"``.

    ``blocks`` carries any block-level children of ``<item>`` (3 corpus
    occurrences of nested ``<list>`` inside ``<item>``). Renderers emit
    ``inlines`` first, then ``blocks`` — the conventional reading order
    when the source intersperses them is preserved by this convention.
    """

    inlines: tuple[Inline, ...]
    label: Optional[tuple[Inline, ...]] = None
    blocks: tuple["Block", ...] = ()


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
    """``<cell>``. The corpus has flat tables (``@rows="1"``, ``@cols="1"`` always).

    ``blocks`` carries embedded block-level children (22 figures and 2 lists
    in cells corpus-wide), rendered after the cell's inline content.
    """

    inlines: tuple[Inline, ...]
    is_header: bool = False
    blocks: tuple["Block", ...] = ()


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

    ``xml_id`` carries the figure's ``@xml:id`` for bidirectional linking from
    the parallel-apparate Figures sub-block (``knowledge/interface.md`` §6).

    ``alt`` is the accessibility text from a ``<figDesc>`` child. The corpus
    has zero ``<figDesc>`` elements as of stage-0 inventory; the field is in
    place so Phase 13 can emit a single aggregated build warning instead of
    rendering 874 silent fallbacks. Renderers should fall back to ``head``
    text or ``"Figure N"`` when ``alt`` is None.
    """

    kind: str
    head: tuple[Inline, ...]
    xml_id: Optional[str] = None
    graphic_url: Optional[str] = None
    code: Optional[str] = None
    code_lang: Optional[str] = None
    alt: Optional[str] = None


@dataclass(frozen=True)
class Citation:
    """``<cit>`` — a quotation with optional bibliographic attribution.

    ``bibl`` is a :class:`~src.model.bibliography.BibEntry` (the same shape
    used by ``Review.bibliography``), so the rendering of inline citations
    and the back-bibliography share one path. ``bibl_target`` mirrors
    ``bibl.ref_target`` for renderer convenience and stays for backwards
    compatibility with the Phase-3 contract.
    """

    quote_inlines: tuple[Inline, ...]
    bibl: "Optional[BibEntry]" = None
    bibl_target: Optional[str] = None


Block = Union[Paragraph, List, Table, Figure, Citation]
