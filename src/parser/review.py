"""Top-level entry point: parse one TEI file into a Review.

Stage 2.B scope: header metadata plus the full section tree under
``<front>``, ``<body>``, ``<back>``, plus the materialised aggregates
``Review.figures`` and ``Review.notes`` for the parallel apparate
sub-blocks. Bibliography and Questionnaire arrive in Phase 6.
"""
from __future__ import annotations

from pathlib import Path

from lxml import etree

from src.model.review import Review
from src.parser.aggregate import collect_figures, collect_notes
from src.parser.bibliography import parse_bibliography
from src.parser.common import NS, attr, find, itertext
from src.parser.questionnaire import parse_questionnaires
from src.parser.metadata import (
    parse_authors,
    parse_editors,
    parse_keywords,
    parse_related_items,
)
from src.parser.refs_resolver import resolve_references
from src.parser.sections import parse_sections


def parse_review(path: Path) -> Review:
    """Parse the TEI file at ``path`` and return a fully-populated Review.

    Header metadata comes from the Stage-2.A parsers; section content from
    :func:`src.parser.sections.parse_sections`; figures and notes are
    aggregated post-parse via :mod:`src.parser.aggregate`.
    """
    tree = etree.parse(str(path))
    root = tree.getroot()

    file_desc = find(root, "t:teiHeader/t:fileDesc")
    profile_desc = find(root, "t:teiHeader/t:profileDesc")
    text_el = find(root, "t:text")

    pub_date_el = find(file_desc, "t:publicationStmt/t:date")
    publication_date = attr(pub_date_el, "when") or itertext(pub_date_el)

    front = parse_sections(find(text_el, "t:front")) if text_el is not None else ()
    body = parse_sections(find(text_el, "t:body")) if text_el is not None else ()
    back = parse_sections(find(text_el, "t:back")) if text_el is not None else ()

    # Aggregates over the full section tree, in document order.
    all_sections = front + body + back
    figures = collect_figures(all_sections)
    notes = collect_notes(all_sections)
    bibliography = parse_bibliography(text_el)
    questionnaires = parse_questionnaires(root)

    review = Review(
        id=attr(root, "xml:id") or "",
        issue=attr(find(file_desc, "t:seriesStmt/t:biblScope"), "n") or "",
        title=itertext(find(file_desc, "t:titleStmt/t:title")),
        publication_date=publication_date,
        language=attr(find(profile_desc, "t:langUsage/t:language"), "ident") or "",
        licence=attr(find(file_desc, "t:publicationStmt/t:availability/t:licence"), "target") or "",
        keywords=tuple(parse_keywords(profile_desc)),
        authors=tuple(parse_authors(file_desc)),
        editors=tuple(parse_editors(file_desc)),
        related_items=tuple(parse_related_items(file_desc)),
        front=front,
        body=body,
        back=back,
        figures=figures,
        notes=notes,
        bibliography=bibliography,
        questionnaires=questionnaires,
        source_file=path.name,
    )
    # Phase-7 post-pass: classify every Reference.target into one of
    # local / criteria / external / orphan against the review's xml:id index.
    return resolve_references(review)
