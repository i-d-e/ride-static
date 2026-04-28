"""Shared TEI parsing helpers.

Centralises namespace handling, attribute fetches with the ``xml:`` prefix,
whitespace-normalised text extraction, and the cross-module
``UnknownTeiElement`` exception so the per-region parsers stay declarative
and the inline / block parsers can both use the same diagnostic without
forming an import cycle.
"""
from __future__ import annotations

import re
from typing import Optional

from lxml import etree


class UnknownTeiElement(ValueError):
    """Raised when a parser sees an element it has no branch for.

    Carries the offending local name plus an optional locator hint
    (typically the nearest ``<div xml:id=...>`` ancestor) so the
    misplaced element is findable in the source.
    """

    def __init__(self, localname: str, hint: Optional[str] = None) -> None:
        msg = f"unknown TEI element: <{localname}>"
        if hint:
            msg += f" ({hint})"
        super().__init__(msg)
        self.localname = localname
        self.hint = hint


def locate_hint(el: etree._Element) -> Optional[str]:
    """Walk up to the nearest ``<div>`` and report its ``@xml:id``, if any."""
    cur: Optional[etree._Element] = el.getparent()
    while cur is not None:
        if etree.QName(cur).localname == "div":
            xid = cur.get(f"{{{XML_NS}}}id")
            if xid:
                return f"inside <div xml:id={xid!r}>"
            return "inside <div> (no xml:id)"
        cur = cur.getparent()
    return None

TEI_NS = "http://www.tei-c.org/ns/1.0"
XML_NS = "http://www.w3.org/XML/1998/namespace"

# Default namespace map used in every find/findall throughout the parser.
NS: dict[str, str] = {"t": TEI_NS}


_WS = re.compile(r"\s+")


def normalize(text: Optional[str]) -> str:
    if not text:
        return ""
    return _WS.sub(" ", text).strip()


def itertext(el: Optional[etree._Element]) -> str:
    """Whitespace-normalised concatenation of all descendant text nodes."""
    if el is None:
        return ""
    return normalize("".join(el.itertext()))


def attr(el: Optional[etree._Element], name: str) -> Optional[str]:
    """Read an attribute, supporting the ``xml:`` namespace prefix."""
    if el is None:
        return None
    if name.startswith("xml:"):
        return el.get(f"{{{XML_NS}}}{name[4:]}")
    return el.get(name)


def find(parent: Optional[etree._Element], xpath: str) -> Optional[etree._Element]:
    if parent is None:
        return None
    return parent.find(xpath, NS)


def findall(parent: Optional[etree._Element], xpath: str) -> list[etree._Element]:
    if parent is None:
        return []
    return list(parent.findall(xpath, NS))
