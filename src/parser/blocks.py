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
from src.parser.inlines import (
    _PASSTHROUGH_TEXT,
    _SOFT_SKIP,
    _collapse,
    _finalise,
    _parse_inline,
    parse_inlines,
)

# Block-level local names that may appear as direct children of <p> in the
# RIDE corpus. ``parse_paragraph_or_split`` slices the paragraph at these
# boundaries so each block becomes a sibling block in the section's block
# sequence rather than disappearing inside an inline tree.
# Counts in the corpus: figure 850, list 116, cit 81, table 7.
_BLOCK_LOCALS_IN_P = frozenset({"figure", "list", "cit", "table"})

# Block-level elements deliberately not parsed at the section block level.
# ``<listBibl>`` carries the back-bibliography; rather than promote it to
# a Block kind, the bibliography lives on ``Review.bibliography`` as its
# own typed sequence (parsed by ``src.parser.bibliography``). The section
# ``<div type="bibliography">`` retains its heading so the section tree
# stays consistent, but its ``blocks`` are intentionally empty.
_SKIPPED_BLOCKS = frozenset({"listBibl"})


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
    """Build a ListItem; for ``kind="labeled"`` extract the optional ``<label>``.

    ``<item>`` may contain nested ``<list>`` elements (3 corpus occurrences);
    those are parsed via ``_walk_inline_with_blocks`` and surfaced on
    ``ListItem.blocks`` rather than raised as unknown inline elements.
    """
    label: Optional[tuple[Inline, ...]] = None
    if kind == "labeled":
        lab = item.find("t:label", NS)
        if lab is not None:
            label_inlines = parse_inlines(lab)
            if label_inlines:
                label = label_inlines
            # The <label> element is consumed; the item's remaining mixed content
            # carries the definition. We detach the label child so its text
            # does not appear twice in the inline walk.
            item.remove(lab)
    inlines, blocks = _walk_inline_with_blocks(item)
    return ListItem(inlines=inlines, label=label, blocks=blocks)


def parse_table(tbl: etree._Element) -> Table:
    """``<table>`` — flat in the RIDE corpus (``@rows="1"``, ``@cols="1"`` always)."""
    head_inlines = _head_inlines_or_none(tbl)
    rows = tuple(_parse_table_row(r) for r in tbl.findall("t:row", NS))
    return Table(rows=rows, head=head_inlines)


def _parse_table_row(row: etree._Element) -> TableRow:
    cells = tuple(_parse_table_cell(c) for c in row.findall("t:cell", NS))
    return TableRow(cells=cells)


def _parse_table_cell(cell: etree._Element) -> TableCell:
    """Header detection via ``@role="label"``; the corpus uses this convention.

    Cells may contain block-level children — 22 ``<figure>`` and 2 ``<list>``
    occurrences corpus-wide — which surface on ``TableCell.blocks``.
    """
    is_header = (attr(cell, "role") == "label")
    inlines, blocks = _walk_inline_with_blocks(cell)
    return TableCell(inlines=inlines, is_header=is_header, blocks=blocks)


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


# -- Paragraph splitting --------------------------------------------------


def parse_paragraph_or_split(p: etree._Element) -> tuple[Block, ...]:
    """Parse a ``<p>`` that may contain block-level children.

    The TEI corpus has 1054 cases where ``<figure>``, ``<list>``, ``<cit>``,
    or ``<table>`` appear directly inside ``<p>``. Rather than embedding
    blocks inside inlines (which the model rejects, the rendering rejects,
    and the spec rejects), this function slices the paragraph at every
    block boundary, emitting an alternating sequence of ``Paragraph``
    chunks and the extracted blocks.

    The first chunk inherits ``@xml:id`` and ``@n`` from the source ``<p>``;
    continuation chunks have ``xml_id=None`` and ``n=None`` because they are
    synthetic. Empty chunks (e.g. when the paragraph starts or ends with a
    block) are dropped — there is no point in a Paragraph with no inlines.

    The fast path (no block children) returns a single-element tuple
    containing one ``Paragraph``, identical to ``parse_paragraph(p)``.
    """
    if not _has_block_children(p):
        return (parse_paragraph(p),)

    p_xml_id = attr(p, "xml:id")
    p_n = attr(p, "n")
    out: list[Block] = []
    raw_inlines: list = []
    is_first_chunk = True

    if p.text:
        raw_inlines.append(_collapse(p.text))

    for child in p:
        if not isinstance(child.tag, str):  # comment or PI
            if child.tail:
                raw_inlines.append(_collapse(child.tail))
            continue
        local = etree.QName(child).localname
        if local in _BLOCK_LOCALS_IN_P:
            # Flush accumulated inlines as a Paragraph chunk, then the block.
            chunk = _finalise(raw_inlines)
            if chunk:
                out.append(Paragraph(
                    inlines=chunk,
                    xml_id=p_xml_id if is_first_chunk else None,
                    n=p_n if is_first_chunk else None,
                ))
                is_first_chunk = False
            out.append(parse_block(child))
            raw_inlines = []
        elif local in _SOFT_SKIP:
            raw_inlines.append(" ")
        elif local in _PASSTHROUGH_TEXT:
            text = itertext(child)
            if text:
                raw_inlines.append(text)
        else:
            raw_inlines.append(_parse_inline(child, local))
        if child.tail:
            raw_inlines.append(_collapse(child.tail))

    chunk = _finalise(raw_inlines)
    if chunk:
        out.append(Paragraph(
            inlines=chunk,
            xml_id=p_xml_id if is_first_chunk else None,
            n=p_n if is_first_chunk else None,
        ))

    return tuple(out)


def _has_block_children(p: etree._Element) -> bool:
    """True iff ``p`` contains at least one block-level child element."""
    for child in p:
        if not isinstance(child.tag, str):
            continue
        if etree.QName(child).localname in _BLOCK_LOCALS_IN_P:
            return True
    return False


def _walk_inline_with_blocks(
    host: etree._Element,
) -> tuple[tuple[Inline, ...], tuple[Block, ...]]:
    """Walk ``host`` once, returning ``(inlines, blocks)`` separately.

    Used by ``_parse_list_item`` and ``_parse_table_cell``: both have a
    primary inline content payload but may carry a small number of nested
    block-level children that the model surfaces on a sibling field rather
    than embedding in the inline tree. Document-order interleaving between
    text and blocks is intentionally collapsed — inlines first, blocks
    second — because the renderer convention follows that order.
    """
    if not _has_block_children(host):
        return (parse_inlines(host), ())

    raw_inlines: list = []
    blocks: list[Block] = []

    if host.text:
        raw_inlines.append(_collapse(host.text))

    for child in host:
        if not isinstance(child.tag, str):
            if child.tail:
                raw_inlines.append(_collapse(child.tail))
            continue
        local = etree.QName(child).localname
        if local in _BLOCK_LOCALS_IN_P:
            blocks.append(parse_block(child))
        elif local in _SOFT_SKIP:
            raw_inlines.append(" ")
        elif local in _PASSTHROUGH_TEXT:
            text = itertext(child)
            if text:
                raw_inlines.append(text)
        else:
            raw_inlines.append(_parse_inline(child, local))
        if child.tail:
            raw_inlines.append(_collapse(child.tail))

    return (_finalise(raw_inlines), tuple(blocks))


def parse_block_sequence(host: etree._Element) -> tuple[Block, ...]:
    """Parse the direct block-level children of a section host (``<div>`` or
    body-wrap ``<body>``).

    Skips ``<div>`` (handled by the section parser's recursion) and
    ``<head>`` (consumed as section heading). For ``<p>`` children, calls
    :func:`parse_paragraph_or_split` to handle block-in-paragraph cases.
    Everything else dispatches through :func:`parse_block`.
    """
    out: list[Block] = []
    for child in host:
        if not isinstance(child.tag, str):
            continue
        local = etree.QName(child).localname
        if local in {"div", "head"}:
            continue
        if local in _SKIPPED_BLOCKS:
            # ``<listBibl>`` lives on Review.bibliography, not in section blocks.
            continue
        if local == "p":
            out.extend(parse_paragraph_or_split(child))
        else:
            out.append(parse_block(child))
    return tuple(out)


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
