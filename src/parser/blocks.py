"""Block-level parsing — one function per kind, plus a dispatcher.

Phase 5 wires the inline parser into every per-kind function so block
content carries real ``Inline`` sequences (Phase 3 left them as ``()``).
The dispatcher ``parse_block`` raises :class:`UnknownTeiElement` on
anything not in the verified-present set (Paragraph, List, Table,
Figure, Citation), per the hard rule in CLAUDE.md.
"""
from __future__ import annotations

from typing import Optional

from lxml import etree

from src.model.block import (
    Block,
    Citation,
    Figure,
    List,
    ListItem,
    Paragraph,
    Table,
    TableCell,
    TableRow,
)
from src.model.inline import Inline
from src.parser.common import (
    NS,
    UnknownTeiElement,
    attr,
    itertext,
    locate_hint,
)
from src.parser.inlines import parse_inlines

# -- List rend normalisation ---------------------------------------------

_LIST_REND_NORMAL = frozenset({"bulleted", "ordered", "labeled"})
_LIST_REND_NORMALISE = {
    "numbered": "ordered",
    "unordered": "bulleted",
}


# -- Per-kind parsers -----------------------------------------------------


def parse_paragraph(p: etree._Element) -> Paragraph:
    """``<p>`` — paragraph. ``@xml:id`` is the citation anchor, ``@n`` the visible number."""
    return Paragraph(
        inlines=parse_inlines(p),
        xml_id=attr(p, "xml:id"),
        n=attr(p, "n"),
    )


def parse_list(lst: etree._Element) -> List:
    """``<list>`` with three kinds, after normalisation.

    ``rend="numbered"`` and ``"unordered"`` are silently normalised to
    ``ordered`` and ``bulleted``; ``labeled`` passes through and triggers
    extraction of the optional ``<label>`` per item.
    """
    rend = attr(lst, "rend") or "bulleted"
    rend = _LIST_REND_NORMALISE.get(rend, rend)
    if rend not in _LIST_REND_NORMAL:
        # Unknown variant — keep as-is for renderer to flag, do not silently coerce.
        # No raise: it is a known data quirk in long-tail RIDE submissions.
        pass
    items = tuple(_parse_list_item(it, kind=rend) for it in lst.findall("t:item", NS))
    return List(items=items, kind=rend)


def _parse_list_item(item: etree._Element, kind: str) -> ListItem:
    """Build a ListItem; for ``kind="labeled"`` extract the optional ``<label>``."""
    label: Optional[tuple[Inline, ...]] = None
    if kind == "labeled":
        lab = item.find("t:label", NS)
        if lab is not None:
            label_inlines = parse_inlines(lab)
            if label_inlines:
                label = label_inlines
            # The <label> element is consumed; the item's remaining mixed content
            # carries the definition. We re-parse the item with the label child
            # detached so its text does not appear twice.
            parent_item = lab.getparent()
            if parent_item is not None:
                parent_item.remove(lab)
    return ListItem(inlines=parse_inlines(item), label=label)


def parse_table(tbl: etree._Element) -> Table:
    """``<table>`` — flat in the RIDE corpus (``@rows="1"``, ``@cols="1"`` always)."""
    head_inlines = _head_inlines_or_none(tbl)
    rows = tuple(_parse_table_row(r) for r in tbl.findall("t:row", NS))
    return Table(rows=rows, head=head_inlines)


def _parse_table_row(row: etree._Element) -> TableRow:
    cells = tuple(_parse_table_cell(c) for c in row.findall("t:cell", NS))
    return TableRow(cells=cells)


def _parse_table_cell(cell: etree._Element) -> TableCell:
    """Header detection via ``@role="label"``; the corpus uses this convention."""
    is_header = (attr(cell, "role") == "label")
    return TableCell(inlines=parse_inlines(cell), is_header=is_header)


def parse_figure(fig: etree._Element) -> Figure:
    """``<figure>`` with two kinds.

    The corpus has 833 figures with ``<graphic>`` (kind=graphic) and 41 with
    ``<eg>`` instead (kind=code_example, typically TEI-markup samples).
    ``<figDesc>`` does not occur in the corpus; ``alt`` is therefore always
    ``None`` today, but the field is set up for the build-bericht in Phase 13.
    """
    head = _head_inlines_or_none(fig) or ()
    xml_id = attr(fig, "xml:id")
    alt = _figdesc_text(fig)
    graphic = fig.find("t:graphic", NS)
    if graphic is not None:
        return Figure(
            kind="graphic",
            head=head,
            xml_id=xml_id,
            graphic_url=attr(graphic, "url"),
            alt=alt,
        )
    eg = fig.find("t:eg", NS)
    if eg is not None:
        return Figure(
            kind="code_example",
            head=head,
            xml_id=xml_id,
            code=itertext(eg) or None,
            code_lang=attr(eg, "lang"),
            alt=alt,
        )
    # Neither <graphic> nor <eg> — empty figure. Render as headed placeholder.
    return Figure(kind="graphic", head=head, xml_id=xml_id, alt=alt)


def parse_cit(cit: etree._Element) -> Citation:
    """``<cit>`` — quotation with optional ``<bibl>`` attribution.

    ``<quote>`` is always present (84/84 in the corpus); ``<bibl>`` in 64
    of those. The first ``<ref>`` descendant of ``<bibl>`` (if any) carries
    the canonical citation target; we surface its ``@target`` separately so
    the renderer can build the citation link without re-walking the inline
    tree.
    """
    quote_el = cit.find("t:quote", NS)
    quote_inlines = parse_inlines(quote_el) if quote_el is not None else ()

    bibl_el = cit.find("t:bibl", NS)
    bibl: Optional[tuple[Inline, ...]] = parse_inlines(bibl_el) if bibl_el is not None else None
    bibl_target = attr(_first_ref(bibl_el), "target") if bibl_el is not None else None

    return Citation(
        quote_inlines=quote_inlines,
        bibl=bibl,
        bibl_target=bibl_target,
    )


def _first_ref(el: Optional[etree._Element]) -> Optional[etree._Element]:
    """Helper: first ``<ref>`` descendant of ``el``, or None."""
    if el is None:
        return None
    return el.find(".//t:ref", NS)


# -- Dispatcher -----------------------------------------------------------


_DISPATCH = {
    "p": parse_paragraph,
    "list": parse_list,
    "table": parse_table,
    "figure": parse_figure,
    "cit": parse_cit,
}


def parse_block(el: etree._Element) -> Block:
    """Dispatch to the right per-kind parser based on local name.

    Raises :class:`UnknownTeiElement` for anything outside the verified set.
    """
    local = etree.QName(el).localname
    fn = _DISPATCH.get(local)
    if fn is None:
        raise UnknownTeiElement(local, hint=locate_hint(el))
    return fn(el)


# -- Helpers --------------------------------------------------------------


def _head_inlines_or_none(parent: etree._Element) -> Optional[tuple[Inline, ...]]:
    """First ``<head>`` child as a tuple of inlines, or None."""
    head = parent.find("t:head", NS)
    if head is None:
        return None
    inlines = parse_inlines(head)
    return inlines or None


def _figdesc_text(fig: etree._Element) -> Optional[str]:
    """Text of the optional ``<figDesc>`` child for accessibility (alt text).

    Zero occurrences in the corpus today — Phase 13 will surface this as a
    build warning aggregated at corpus level rather than once per figure.
    """
    desc = fig.find("t:figDesc", NS)
    if desc is None:
        return None
    text = itertext(desc)
    return text or None
