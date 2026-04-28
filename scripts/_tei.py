"""Shared TEI helpers for the Stage 0/1 discovery scripts.

Centralises the namespace constants, Clark-notation helpers, and the
common attribute names every extractor needs. Underscore prefix marks
this as an internal module — it is not runnable on its own.

The Stage 2 parser under ``src/parser/`` walks XML differently
(namespace-prefixed ``find()`` calls instead of ``iter()`` + Clark
notation) and has its own helpers in ``src/parser/common.py``.
"""
from __future__ import annotations

import re
from typing import Optional

from lxml import etree

TEI_NS = "http://www.tei-c.org/ns/1.0"
XML_NS = "http://www.w3.org/XML/1998/namespace"

_TEI_TAG_PREFIX = f"{{{TEI_NS}}}"
_XML_TAG_PREFIX = f"{{{XML_NS}}}"

# Frequently-fetched attributes in Clark notation. Lookup with
# ``el.get(XML_ID_ATTR)`` instead of building the string per script.
XML_ID_ATTR = f"{{{XML_NS}}}id"
XML_BASE_ATTR = f"{{{XML_NS}}}base"
XML_LANG_ATTR = f"{{{XML_NS}}}lang"

_WS = re.compile(r"\s+")


def localname(tag: str) -> str:
    """Strip the namespace from a Clark-notation tag (``{ns}name`` -> ``name``)."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def attr_localname(name: str) -> str:
    """Render an attribute name with ``xml:`` prefix preserved, others stripped."""
    if name.startswith(_XML_TAG_PREFIX):
        return "xml:" + name[len(_XML_TAG_PREFIX):]
    return localname(name)


def is_tei_element(node: etree._Element) -> bool:
    """True iff ``node`` is an element node in the TEI namespace."""
    return isinstance(node.tag, str) and node.tag.startswith(_TEI_TAG_PREFIX)


def normalize(text: Optional[str]) -> str:
    """Collapse runs of whitespace and trim."""
    if not text:
        return ""
    return _WS.sub(" ", text).strip()
