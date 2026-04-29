"""Domain types for a RIDE review.

Header-layer types from Stage 2.A and body-layer Section sequences from
Stage 2.B Phase 1. ``BibEntry`` and ``Questionnaire`` arrive in Phase 6
(Stage 2.C); their fields are present here as empty defaults so that
existing call-sites never need to reach into the dataclass to construct
a Review.

All types are immutable so a parsed Review can be passed around and
cached without surprises. Use ``dataclasses.replace`` to derive variants.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from src.model.bibliography import BibEntry
from src.model.block import Figure
from src.model.inline import Note
from src.model.questionnaire import Questionnaire
from src.model.section import Section


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
    """An entry in <notesStmt>/<relatedItem> — typed link to reviewed work or criteria.

    ``bibl_targets`` collects all reachable URLs from the inner ``<bibl>``:
    ``<idno type="URI">`` and ``<idno type="DOI">`` for ``reviewed_resource``
    (the canonical RIDE shape), plus ``<ref @target>`` for ``reviewing_criteria``
    (which uses a ``<ref>`` instead of an ``<idno>``). The ``last_accessed``
    field carries ``<date type="accessed">`` from inside ``<bibl>`` and feeds
    the rendered "(Last Accessed: …)" suffix in the review header.
    """

    type: str
    bibl_text: str
    bibl_targets: tuple[str, ...] = field(default_factory=tuple)
    xml_id: Optional[str] = None
    last_accessed: Optional[str] = None


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

    doi: Optional[str] = None
    """Canonical persistent identifier from ``<publicationStmt>/<idno type="DOI">``.

    Per [requirements R2](../knowledge/requirements.md), the DOI is the
    citation anchor for every review and feeds the sidebar Meta box, the
    Citation Suggestion (R2 format), JSON-LD ``@id``/``identifier``, and
    the OAI-PMH ``dc:identifier``. Phase 13 validation will refuse builds
    that ship a review without a DOI.
    """

    keywords: tuple[str, ...] = field(default_factory=tuple)
    authors: tuple[Author, ...] = field(default_factory=tuple)
    editors: tuple[Editor, ...] = field(default_factory=tuple)
    related_items: tuple[RelatedItem, ...] = field(default_factory=tuple)

    front: tuple[Section, ...] = field(default_factory=tuple)
    """Sections under <front> (often empty in RIDE)."""

    body: tuple[Section, ...] = field(default_factory=tuple)
    """Sections under <body>. The seven body-wraps-direct-p reviews collapse to
    a single implicit Section here; see knowledge/architecture.md anomaly table."""

    back: tuple[Section, ...] = field(default_factory=tuple)
    """Sections under <back> (bibliography, appendix). Empty for the seven
    no-back reviews listed in knowledge/data.md."""

    figures: tuple[Figure, ...] = field(default_factory=tuple)
    """All ``<figure>`` blocks reachable from front/body/back, in document
    order. Materialised at parse time so the parallel apparate sub-block
    (interface.md §6) and the figure-list aggregations get a stable
    sequence without re-walking the section tree."""

    notes: tuple[Note, ...] = field(default_factory=tuple)
    """All ``<note>`` inlines reachable from front/body/back, in document
    order. Footnote anchors live in ``Note.xml_id``; renderers use this
    tuple for the apparate Notes sub-block and for build-time validation
    that every ``<ref target="#ftnN">`` resolves to a known note."""

    bibliography: tuple[BibEntry, ...] = field(default_factory=tuple)
    """The back-bibliography as a flat sequence of ``BibEntry`` values.
    Empty for the seven no-back reviews and any review that omits
    ``<listBibl>``. Section ``<div type="bibliography">`` retains its
    heading in ``back`` but its ``blocks`` are intentionally empty —
    bibliography content lives here, not in the Section tree."""

    questionnaires: tuple[Questionnaire, ...] = field(default_factory=tuple)
    """One Questionnaire per ``<taxonomy>`` element in the review's
    classDecl. Most reviews carry exactly one; three carry two. Feeds
    the Factsheet (``interface.md`` §5) and the cross-corpus Data page
    (``requirements.md`` R9)."""

    source_file: Optional[str] = None
    """Basename of the source TEI file, for diagnostics."""
