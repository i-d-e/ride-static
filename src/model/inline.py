"""Inline-level domain types — what lives inside a paragraph, heading, cell, quote.

Mixed content in TEI is parsed into a sequence of these. The verified-against-corpus
inline catalogue is six types: Text, Emphasis, Highlight, Reference, Note, Code.
``<note>`` and ``<code>`` are inline-only in the RIDE corpus (1900+ and 727 occurrences,
all under inline parents); see ``knowledge/data.md`` for the empirical basis.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union


@dataclass(frozen=True)
class Text:
    """A plain text run."""

    text: str


@dataclass(frozen=True)
class Emphasis:
    """``<emph>`` — emphasised text. ``rend`` carries TEI-level rendering hints."""

    children: tuple["Inline", ...]
    rend: Optional[str] = None


@dataclass(frozen=True)
class Highlight:
    """``<hi>`` — highlighted text, often distinguishing foreign or technical terms."""

    children: tuple["Inline", ...]
    rend: Optional[str] = None


@dataclass(frozen=True)
class Reference:
    """``<ref>`` — anchor or link.

    ``target`` carries the raw ``@target`` value. ``bucket`` is filled by the
    Phase-7 resolver (:func:`src.parser.refs_resolver.resolve_references`) and
    classifies the reference into one of four kinds the renderer can dispatch
    on: ``local`` (in-page anchor), ``criteria`` (``#K…`` against the
    taxonomy's external criteria document), ``external`` (``http(s)://``
    URL), or ``orphan`` (target set but unresolvable, for example
    ``#abb…``-style dangling internals or bare bibkeys like ``werner2019``).
    ``bucket`` is ``None`` when ``target`` itself is missing.
    """

    children: tuple["Inline", ...]
    target: Optional[str] = None
    type: Optional[str] = None
    bucket: Optional[str] = None


@dataclass(frozen=True)
class Note:
    """``<note>`` — footnote, always inline in the RIDE corpus.

    ``xml_id`` carries the ``@xml:id`` of the note (typically ``ftnN``); it is
    the anchor that footnote-style ``<ref target="#ftnN">`` resolves to in
    Phase 7. ``n`` is the optional ordinal label, ``place`` an optional
    rendering hint.
    """

    children: tuple["Inline", ...]
    xml_id: Optional[str] = None
    n: Optional[str] = None
    place: Optional[str] = None


@dataclass(frozen=True)
class InlineCode:
    """``<code>`` — inline code span. ``lang`` is the optional ``@lang`` attribute."""

    text: str
    lang: Optional[str] = None


Inline = Union[Text, Emphasis, Highlight, Reference, Note, InlineCode]
