"""Parsers for <teiHeader> metadata.

Each function reads its slice of the header and returns immutable
domain objects. Parsers do not mutate the source XML.
"""
from __future__ import annotations

from typing import Optional

from lxml import etree

from src.model.review import Affiliation, Author, Editor, Person, RelatedItem
from src.parser.common import attr, find, findall, itertext


def _person_from_name_or_text(host: etree._Element, orcid: Optional[str] = None) -> Person:
    """Build a Person from a host element that either contains <name> or is a textual node.

    Falls back to the host's own text when neither <name> nor <forename>/<surname>
    children are present (the common shape for <editor> in seriesStmt).
    """
    name_el = find(host, "t:name")
    if name_el is None:
        name_el = host
    forename = itertext(find(name_el, "t:forename")) or None
    surname = itertext(find(name_el, "t:surname")) or None
    if forename and surname:
        full = f"{forename} {surname}"
    else:
        full = itertext(name_el)
    return Person(full_name=full, forename=forename, surname=surname, orcid=orcid)


def parse_authors(file_desc: Optional[etree._Element]) -> list[Author]:
    out: list[Author] = []
    for author_el in findall(file_desc, "t:titleStmt/t:author"):
        person = _person_from_name_or_text(author_el, orcid=attr(author_el, "ref"))

        affiliation_el = find(author_el, "t:affiliation")
        affiliation: Optional[Affiliation] = None
        if affiliation_el is not None:
            affiliation = Affiliation(
                org_name=itertext(find(affiliation_el, "t:orgName")) or None,
                place_name=itertext(find(affiliation_el, "t:placeName")) or None,
            )
        email = itertext(find(author_el, "t:email")) or None

        out.append(Author(person=person, affiliation=affiliation, email=email))
    return out


def parse_editors(file_desc: Optional[etree._Element]) -> list[Editor]:
    out: list[Editor] = []
    for editor_el in findall(file_desc, "t:seriesStmt/t:editor"):
        person = _person_from_name_or_text(editor_el, orcid=attr(editor_el, "ref"))
        out.append(Editor(person=person, role=attr(editor_el, "role")))
    return out


def parse_keywords(profile_desc: Optional[etree._Element]) -> list[str]:
    return [
        text
        for term_el in findall(profile_desc, "t:textClass/t:keywords/t:term")
        if (text := itertext(term_el))
    ]


def parse_related_items(file_desc: Optional[etree._Element]) -> list[RelatedItem]:
    out: list[RelatedItem] = []
    for ri_el in findall(file_desc, "t:notesStmt/t:relatedItem"):
        bibl_el = find(ri_el, "t:bibl")
        # Targets come from any <ref> nested under the relatedItem (or its <bibl>).
        targets = tuple(
            t for r in findall(ri_el, ".//t:ref")
            if (t := attr(r, "target"))
        )
        out.append(RelatedItem(
            type=attr(ri_el, "type") or "",
            bibl_text=itertext(bibl_el) if bibl_el is not None else itertext(ri_el),
            bibl_targets=targets,
            xml_id=attr(ri_el, "xml:id"),
        ))
    return out
