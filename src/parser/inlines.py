"""Inline-level parsing — mixed-content walker plus per-kind helpers.

Phase 4 scope: ``parse_inlines(host)`` walks the text and element children of
a host element (``<p>``, ``<head>``, ``<quote>``, ``<cell>``, ``<item>``,
``<note>``, ``<bibl>``-as-inline-context) and produces a tuple of
:class:`~src.model.inline.Inline` values.

Whitespace strategy:

* Internal runs of whitespace inside a text segment are collapsed to a single
  space.
* The whole sequence is left-stripped on its first text run and right-stripped
  on its last, so leading and trailing whitespace at the host's edges does not
  surface as empty ``Text`` inlines. Whitespace *between* a text run and an
  element child is preserved because it carries word boundaries.

Six inline kinds are handled (Text, Emphasis, Highlight, Reference, Note,
InlineCode), matching the verified-against-corpus catalogue. ``<lb/>`` is
soft-skipped as a single space — it is the only known inline element in the
corpus that the model deliberately does not represent. Anything else raises
:class:`~src.parser.blocks.UnknownTeiElement` with the offending localname
and the nearest ``<div xml:id=...>`` for locatability.

The single ``<ref type="crosssref">`` typo in the corpus is silently
normalised to ``crossref`` — a one-occurrence data quirk, named explicitly
here per the "anomalies are explicit" rule in CLAUDE.md.
"""
from __future__ import annotations

import re
from typing import Optional

from lxml import etree

from src.model.inline import (
    Emphasis,
    Highlight,
    Inline,
    InlineCode,
    Note,
    Reference,
    Text,
)
from src.parser.blocks import UnknownTeiElement, _locate_hint
from src.parser.common import attr

_WS_RUN = re.compile(r"\s+")

# Elements that appear in mixed content but are not modelled as separate
# inlines. Currently only <lb/> qualifies (~30 occurrences corpus-wide,
# mostly inside <quote>). We render them as a single space so that word
# boundaries survive but the surrounding text remains a single Text run.
_SOFT_SKIP = frozenset({"lb"})

# <ref @type> normalisation: the corpus has 1704× "crossref" and exactly
# 1× "crosssref" (data typo). Map the typo to the canonical value at parse
# time; do not preserve it in the model.
_REF_TYPE_NORMALISE = {"crosssref": "crossref"}


def parse_inlines(host: etree._Element) -> tuple[Inline, ...]:
    """Parse a host's mixed content into a tuple of Inline values.

    The host itself is not represented in the output — only its text and
    children are. Comments and processing instructions are skipped, but
    their tails are preserved as text.
    """
    raw: list = []

    if host.text:
        raw.append(_collapse(host.text))

    for child in host:
        if isinstance(child, (etree._Comment, etree._ProcessingInstruction)):
            if child.tail:
                raw.append(_collapse(child.tail))
            continue
        local = etree.QName(child).localname
        if local in _SOFT_SKIP:
            raw.append(" ")
        else:
            raw.append(_parse_inline(child, local))
        if child.tail:
            raw.append(_collapse(child.tail))

    return _finalise(raw)


def _parse_inline(el: etree._Element, local: str) -> Inline:
    """Dispatch one element child of a mixed-content host to the right kind."""
    if local == "emph":
        return Emphasis(children=parse_inlines(el), rend=attr(el, "rend"))
    if local == "hi":
        return Highlight(children=parse_inlines(el), rend=attr(el, "rend"))
    if local == "ref":
        return _parse_ref(el)
    if local == "note":
        return Note(
            children=parse_inlines(el),
            xml_id=attr(el, "xml:id"),
            n=attr(el, "n"),
            place=attr(el, "place"),
        )
    if local == "code":
        return _parse_code(el)
    raise UnknownTeiElement(local, hint=_locate_hint(el))


def _parse_ref(el: etree._Element) -> Reference:
    """``<ref>`` — anchor or link.

    ``@target`` is captured raw (resolution is a Phase-7 concern). ``@type``
    is normalised through :data:`_REF_TYPE_NORMALISE`; unknown values pass
    through unchanged so that future RIDE submissions adding new types do
    not break the parser.
    """
    raw_type = attr(el, "type")
    norm_type = _REF_TYPE_NORMALISE.get(raw_type, raw_type) if raw_type else None
    return Reference(
        children=parse_inlines(el),
        target=attr(el, "target"),
        type=norm_type,
    )


def _parse_code(el: etree._Element) -> InlineCode:
    """``<code>`` — inline code span.

    The corpus has no nested elements inside ``<code>`` (verified via
    structure.json: empty children list), so a plain text concatenation
    is sufficient — we do not collapse whitespace because code content is
    significant in its raw form.
    """
    parts: list[str] = []
    if el.text:
        parts.append(el.text)
    for sub in el:
        if sub.tail:
            parts.append(sub.tail)
    return InlineCode(text="".join(parts), lang=attr(el, "lang"))


def _collapse(text: str) -> str:
    """Collapse runs of whitespace to a single space; do not strip the edges."""
    return _WS_RUN.sub(" ", text)


def _finalise(raw: list) -> tuple[Inline, ...]:
    """Coalesce adjacent text strings, strip the sequence's outer edges,
    drop empty text runs, and wrap remaining strings as ``Text`` inlines.

    Coalescing matters for cases where a comment sits between two text
    nodes — after the comment is dropped its surrounding text segments are
    adjacent in ``raw`` and would otherwise become two separate ``Text``
    inlines that share a single normalised space across the boundary.
    """
    merged: list = []
    for item in raw:
        if isinstance(item, str):
            if merged and isinstance(merged[-1], str):
                merged[-1] += item
            else:
                merged.append(item)
        else:
            merged.append(item)

    if merged and isinstance(merged[0], str):
        merged[0] = merged[0].lstrip()
    if merged and isinstance(merged[-1], str):
        merged[-1] = merged[-1].rstrip()

    out: list[Inline] = []
    for item in merged:
        if isinstance(item, str):
            if item:
                out.append(Text(text=item))
        else:
            out.append(item)
    return tuple(out)
