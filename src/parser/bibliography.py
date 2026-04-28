"""Parser for the back-bibliography.

A review's back-bibliography sits at ``<text>/<back>/<div type="bibliography">
/<listBibl>``. Each ``<bibl>`` child becomes one :class:`~src.model.bibliography.BibEntry`.
``<bibl>`` content is mixed and falls under the inline walker's passthrough
rules for structured children (``<respStmt>``, ``<date>``, ``<title>``,
``<editor>``, ``<idno>``) — their text survives, but BibEntry does not
re-decode them into separate fields. The corpus's free-form usage
doesn't reward that effort; renderers that need richer bibliographic
metadata can later promote selected fields without rewriting this layer.

The first ``<ref>`` descendant of each ``<bibl>``, if any, surfaces as
``ref_target`` for renderer convenience (click-through link).
"""
from __future__ import annotations

from typing import Optional

from lxml import etree

from src.model.bibliography import BibEntry
from src.parser.common import NS, attr
from src.parser.inlines import parse_inlines


def parse_bibliography(text_el: Optional[etree._Element]) -> tuple[BibEntry, ...]:
    """Walk a TEI ``<text>`` element and collect every ``<bibl>`` reachable
    via ``<back>/<div>/<listBibl>/<bibl>``, in document order.

    Returns the empty tuple when ``text_el`` is None, when ``<back>`` is
    absent (seven such reviews per ``knowledge/data.md``), or when no
    ``<listBibl>`` exists in the back. Some reviews have multiple
    ``<listBibl>``s under a single bibliography ``<div>`` — all are
    flattened into one tuple here.
    """
    if text_el is None:
        return ()
    back = text_el.find("t:back", NS)
    if back is None:
        return ()
    entries: list[BibEntry] = []
    for bibl in back.iter("{http://www.tei-c.org/ns/1.0}bibl"):
        # Only top-level bibls under listBibl, not nested bibls inside cit/relatedItem.
        if not _is_listbibl_child(bibl):
            continue
        entries.append(parse_bibl(bibl))
    return tuple(entries)


def parse_bibl(bibl: etree._Element) -> BibEntry:
    """Parse one ``<bibl>`` element into a :class:`BibEntry`."""
    return BibEntry(
        inlines=parse_inlines(bibl),
        xml_id=attr(bibl, "xml:id"),
        ref_target=_first_ref_target(bibl),
    )


def _is_listbibl_child(bibl: etree._Element) -> bool:
    """True iff ``bibl``'s parent is a ``<listBibl>`` element.

    Used to filter out ``<bibl>``s that live in ``<cit>`` (inline
    citations, parsed by :func:`src.parser.blocks.parse_cit`) or in
    ``<relatedItem>`` (parsed by Stage 2.A's metadata module).
    """
    parent = bibl.getparent()
    if parent is None:
        return False
    return etree.QName(parent).localname == "listBibl"


def _first_ref_target(bibl: etree._Element) -> Optional[str]:
    """``@target`` of the first ``<ref>`` descendant, or None.

    1016 of 1670 ``<bibl>``s carry a ``<ref>`` per the corpus inventory,
    typically pointing at the cited resource's canonical URL or DOI.
    """
    ref = bibl.find(".//t:ref", NS)
    if ref is None:
        return None
    return attr(ref, "target")
