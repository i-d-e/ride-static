"""Domain types for a RIDE review.

Header-layer types only (Stage 2.A). Body-layer types — Section, Block,
Inline, BibEntry, Questionnaire — arrive in Stage 2.B and beyond.

All types are immutable so a parsed Review can be passed around and
cached without surprises. Use ``dataclasses.replace`` to derive variants.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Person:
    """A named person extracted from <name>/<forename>+<surname> or plain text."""

    full_name: str
    forename: Optional[str] = None
    surname: Optional[str] = None
    orcid: Optional[str] = None  # value of @ref on the wrapping <author>/<editor>


@dataclass(frozen=True)
class Affiliation:
    """Institutional affiliation as captured under <affiliation>."""

    org_name: Optional[str] = None
    place_name: Optional[str] = None


@dataclass(frozen=True)
class Author:
    person: Person
    affiliation: Optional[Affiliation] = None
    email: Optional[str] = None


@dataclass(frozen=True)
class Editor:
    person: Person
    role: Optional[str] = None  # managing | technical | assistant | chief | …


@dataclass(frozen=True)
class RelatedItem:
    """An entry in <notesStmt>/<relatedItem> — typed link to reviewed work or criteria."""

    type: str
    bibl_text: str
    bibl_targets: tuple[str, ...] = field(default_factory=tuple)
    xml_id: Optional[str] = None


@dataclass(frozen=True)
class Review:
    """Header metadata of a single RIDE review.

    Body content (front/body/back, bibliography, questionnaire) is not
    populated yet — see Stage 2.B+.
    """

    id: str
    """Value of <TEI/@xml:id>, e.g. 'ride.13.7'."""

    issue: str
    """Issue number from <seriesStmt>/<biblScope/@n>."""

    title: str

    publication_date: str
    """Either @when (preferred) or the textual content of <publicationStmt>/<date>."""

    language: str
    """ISO code from <profileDesc>/<langUsage>/<language/@ident>."""

    licence: str
    """@target on <availability>/<licence>."""

    keywords: tuple[str, ...] = field(default_factory=tuple)
    authors: tuple[Author, ...] = field(default_factory=tuple)
    editors: tuple[Editor, ...] = field(default_factory=tuple)
    related_items: tuple[RelatedItem, ...] = field(default_factory=tuple)

    source_file: Optional[str] = None
    """Basename of the source TEI file, for diagnostics."""
