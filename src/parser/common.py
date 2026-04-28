"""Shared TEI parsing helpers.

Centralises namespace handling, attribute fetches with the ``xml:`` prefix,
and whitespace-normalised text extraction so the per-region parsers stay
declarative.
"""
from __future__ import annotations

import re
from typing import Optional

from lxml import etree

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
