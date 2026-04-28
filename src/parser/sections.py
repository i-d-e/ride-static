"""Recursive parsing of <front>, <body>, <back> into Section sequences.

Phase 2 scope: structural skeleton only. Block content inside each Section is
left as ``blocks=()`` until Phase 5 wires in the block parser. Heading text is
captured as a single ``Text`` Inline; Phase 4 will replace this with the real
mixed-content walker that preserves ``<emph>`` / ``<ref>`` inside headings.

Anomalies handled here, per the table in ``knowledge/architecture.md``:

* ``<div>`` without ``@xml:id`` — synthesised positional id (``sec-1.2.3``).
* ``<div>`` without ``<head>`` — ``heading=None``, no error.
* ``<div type="abstract|bibliography|appendix">`` — type carried through;
  any other ``@type`` value resets to ``None``.
* Nesting depth > 3 — raises, per Schematron ``ride.div-nesting``.

The body-wrap anomaly (seven reviews start ``<body>`` directly with ``<p>``
or ``<cit>``) is handled in Commit 2.2 as a separate branch in this module.
"""
from __future__ import annotations

from typing import Optional

from lxml import etree

from src.model.inline import Inline, Text
from src.model.section import Section
from src.parser.common import NS, TEI_NS, attr, itertext

_KNOWN_DIV_TYPES = frozenset({"abstract", "bibliography", "appendix"})
_MAX_DIV_DEPTH = 3
# Element local names that, when they appear as the first child of <body>,
# trigger the implicit-section-wrapper anomaly (4 + 3 = 7 reviews in the corpus).
_WRAP_TRIGGERS = frozenset({"p", "cit"})


def parse_sections(host: Optional[etree._Element]) -> tuple[Section, ...]:
    """Parse all top-level ``<div>`` children of ``host`` into Sections.

    ``host`` is typically a ``<front>``, ``<body>``, or ``<back>`` element.
    Returns the empty tuple when ``host`` is None (the seven no-back reviews).

    **Body-wrap anomaly.** Seven reviews start ``<body>`` directly with ``<p>``
    or ``<cit>`` instead of ``<div>``. For these we synthesise a single
    top-level Section whose ``blocks`` will (in Phase 5) hold the wrapped
    content. The decision is taken by inspecting the first non-comment child
    of the host: if it is a ``<div>``, normal parsing applies; otherwise the
    wrap branch fires.
    """
    if host is None:
        return ()
    if _is_body_wrap_case(host):
        return (_synthesise_wrap_section(host),)
    divs = host.findall("t:div", NS)
    return tuple(
        _parse_div(div, level=1, position=(i + 1,)) for i, div in enumerate(divs)
    )


def _is_body_wrap_case(host: etree._Element) -> bool:
    """True iff ``host`` has at least one TEI element child and the first one is not <div>.

    Keeping the check element-only (skipping comments and processing
    instructions) avoids false negatives on stylistically-formatted source
    files. The fixture in tests/test_parser_sections.py exercises both <p>
    and <cit> first-child variants.
    """
    for child in host:
        if not isinstance(child.tag, str):
            continue  # comment or PI
        local = etree.QName(child).localname
        if local == "div":
            return False
        return local in _WRAP_TRIGGERS
    return False


def _synthesise_wrap_section(host: etree._Element) -> Section:
    """Wrap all element children of ``host`` in one implicit top-level Section.

    The wrapper carries ``xml_id="sec-1"``, ``type=None``, ``heading=None``
    and ``level=1``. Block content remains empty in Phase 2 — Phase 5
    integrates the block parser, at which point this wrapper will hold the
    direct ``<p>``/``<cit>`` children as block instances.
    """
    return Section(
        xml_id="sec-1",
        type=None,
        heading=None,
        level=1,
        blocks=(),
        subsections=(),
    )


def _parse_div(
    div: etree._Element,
    level: int,
    position: tuple[int, ...],
) -> Section:
    """Recursively parse one ``<div>`` element."""
    if level > _MAX_DIV_DEPTH:
        raise ValueError(
            f"<div> nesting exceeds {_MAX_DIV_DEPTH} (Schematron ride.div-nesting); "
            f"position={position}, xml:id={attr(div, 'xml:id')!r}"
        )

    xml_id = attr(div, "xml:id") or _synthesise_id(position)
    div_type = _classify_type(attr(div, "type"))
    heading = _heading_inlines(div)
    subsections = tuple(
        _parse_div(child, level + 1, position + (i + 1,))
        for i, child in enumerate(div.findall("t:div", NS))
    )

    return Section(
        xml_id=xml_id,
        type=div_type,
        heading=heading,
        level=level,
        blocks=(),  # Phase 5 will populate via the block parser
        subsections=subsections,
    )


def _synthesise_id(position: tuple[int, ...]) -> str:
    """Build a stable positional id like ``sec-1`` or ``sec-1.2.3``."""
    return "sec-" + ".".join(str(p) for p in position)


def _classify_type(raw: Optional[str]) -> Optional[str]:
    """Keep only the three known ``@type`` values; everything else becomes None."""
    if raw in _KNOWN_DIV_TYPES:
        return raw
    return None


def _heading_inlines(div: etree._Element) -> Optional[tuple[Inline, ...]]:
    """First ``<head>`` child of ``div`` as a single-Text inline tuple, or None.

    Phase 4 replaces this with a real mixed-content walker. For now we keep
    only the normalised text — sufficient for Phase 2 round-tripping and for
    rendering plain headings in the smoke tests.
    """
    head = div.find("t:head", NS)
    if head is None:
        return None
    text = itertext(head)
    if not text:
        return None
    return (Text(text=text),)
