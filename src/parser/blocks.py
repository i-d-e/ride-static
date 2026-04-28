"""Block-level parsing — one function per kind, plus a dispatcher.

Phase 3 scope: structural skeleton. Inlines remain ``()`` until Phase 4 wires
in the mixed-content walker; ``Paragraph.inlines`` is therefore empty even
when the source ``<p>`` contains text. This is by design — the contract here
is "the right block kind with the right structural metadata", and Phase 5
re-runs every parsed block through the inline parser before integration.

The dispatcher ``parse_block`` raises :class:`UnknownTeiElement` on anything
not in the verified-present set (Paragraph, List, Table, Figure, Citation),
per the hard rule in CLAUDE.md: anomalies are explicit, unknowns must raise.
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
from src.parser.common import NS, attr, itertext

# -- List rend normalisation ---------------------------------------------

_LIST_REND_NORMAL = frozenset({"bulleted", "ordered", "labeled"})
_LIST_REND_NORMALISE = {
    "numbered": "ordered",
    "unordered": "bulleted",
}


class UnknownTeiElement(ValueError):
    """Raised when ``parse_block`` sees an element it has no branch for."""

    def __init__(self, localname: str, hint: Optional[str] = None) -> None:
        msg = f"unknown block-level element: <{localname}>"
        if hint:
            msg += f" ({hint})"
        super().__init__(msg)
        self.localname = localname
        self.hint = hint


# -- Per-kind parsers -----------------------------------------------------


def parse_paragraph(p: etree._Element) -> Paragraph:
    """``<p>`` — paragraph. ``@n`` carries the citation-anchor number."""
    return Paragraph(inlines=(), n=attr(p, "n"))


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
    label: Optional[tuple] = None
    if kind == "labeled":
        lab = item.find("t:label", NS)
        if lab is not None:
            text = itertext(lab)
            if text:
                from src.model.inline import Text
                label = (Text(text=text),)
    return ListItem(inlines=(), label=label)


def parse_table(tbl: etree._Element) -> Table:
    """``<table>`` — flat in the RIDE corpus (``@rows="1"``, ``@cols="1"`` always)."""
    head_text = _head_inlines_or_none(tbl)
    rows = tuple(_parse_table_row(r) for r in tbl.findall("t:row", NS))
    return Table(rows=rows, head=head_text)


def _parse_table_row(row: etree._Element) -> TableRow:
    cells = tuple(_parse_table_cell(c) for c in row.findall("t:cell", NS))
    return TableRow(cells=cells)


def _parse_table_cell(cell: etree._Element) -> TableCell:
    """Header detection via ``@role="label"``; the corpus uses this convention."""
    is_header = (attr(cell, "role") == "label")
    return TableCell(inlines=(), is_header=is_header)


def parse_figure(fig: etree._Element) -> Figure:
    """``<figure>`` with two kinds.

    The corpus has 833 figures with ``<graphic>`` (kind=graphic) and 41 with
    ``<eg>`` instead (kind=code_example, typically TEI-markup samples).
    """
    head = _head_inlines_or_none(fig) or ()
    graphic = fig.find("t:graphic", NS)
    if graphic is not None:
        return Figure(
            kind="graphic",
            head=head,
            graphic_url=attr(graphic, "url"),
        )
    eg = fig.find("t:eg", NS)
    if eg is not None:
        return Figure(
            kind="code_example",
            head=head,
            code=itertext(eg) or None,
            code_lang=attr(eg, "lang"),
        )
    # Neither <graphic> nor <eg> — empty figure. Render as headed placeholder.
    return Figure(kind="graphic", head=head)


def parse_cit(cit: etree._Element) -> Citation:
    """``<cit>`` — quotation with optional ``<bibl>`` attribution.

    ``<quote>`` is always present (84/84 in the corpus); ``<bibl>`` in 64
    of those. The bibl child is captured as an empty inline tuple in Phase 3
    and filled with mixed-content inlines in Phase 4.
    """
    bibl_el = cit.find("t:bibl", NS)
    bibl: Optional[tuple] = () if bibl_el is not None else None
    bibl_target = attr(find_first_ref(bibl_el), "target") if bibl_el is not None else None
    return Citation(
        quote_inlines=(),
        bibl=bibl,
        bibl_target=bibl_target,
    )


def find_first_ref(el: Optional[etree._Element]) -> Optional[etree._Element]:
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
    The error message carries the element's local name and an optional hint
    (the nearest ancestor ``<div>``'s ``@xml:id``) so the offending element is
    locatable in the source.
    """
    local = etree.QName(el).localname
    fn = _DISPATCH.get(local)
    if fn is None:
        raise UnknownTeiElement(local, hint=_locate_hint(el))
    return fn(el)


def _locate_hint(el: etree._Element) -> Optional[str]:
    """Walk up to the nearest ``<div>`` and report its ``@xml:id``, if any."""
    cur: Optional[etree._Element] = el.getparent()
    while cur is not None:
        if etree.QName(cur).localname == "div":
            xid = attr(cur, "xml:id")
            if xid:
                return f"inside <div xml:id={xid!r}>"
            return "inside <div> (no xml:id)"
        cur = cur.getparent()
    return None


# -- Helpers --------------------------------------------------------------


def _head_inlines_or_none(parent: etree._Element) -> Optional[tuple]:
    """First ``<head>`` child as a single Text inline, or None.

    Phase 4 will replace the placeholder with the real mixed-content walker.
    """
    head = parent.find("t:head", NS)
    if head is None:
        return None
    text = itertext(head)
    if not text:
        return None
    from src.model.inline import Text
    return (Text(text=text),)
