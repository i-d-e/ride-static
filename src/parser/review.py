"""Top-level entry point: parse one TEI file into a Review.

Stage 2.A scope: header metadata only. Body-layer parsing arrives in
later stages.
"""
from __future__ import annotations

from pathlib import Path

from lxml import etree

from src.model.review import Review
from src.parser.common import attr, find, itertext
from src.parser.metadata import (
    parse_authors,
    parse_editors,
    parse_keywords,
    parse_related_items,
)


def parse_review(path: Path) -> Review:
    """Parse the TEI file at ``path`` and return its header metadata as a Review."""
    tree = etree.parse(str(path))
    root = tree.getroot()

    file_desc = find(root, "t:teiHeader/t:fileDesc")
    profile_desc = find(root, "t:teiHeader/t:profileDesc")

    pub_date_el = find(file_desc, "t:publicationStmt/t:date")
    publication_date = attr(pub_date_el, "when") or itertext(pub_date_el)

    return Review(
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
        source_file=path.name,
    )
