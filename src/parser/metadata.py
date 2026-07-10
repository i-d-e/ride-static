"""Parsers for <teiHeader> metadata.

Each function reads its slice of the header and returns immutable
domain objects. Parsers do not mutate the source XML.
"""
from __future__ import annotations

import re
from typing import Optional

from lxml import etree

from src.model.review import Affiliation, Author, Editor, Person, RelatedItem
from src.parser.common import attr, find, findall, itertext

# Bare ORCID id (no URL prefix), e.g. "0000-0002-4618-9481"; final block
# may end in a check digit "X". Present in the corpus, see knowledge/data.md.
_BARE_ORCID = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")


def classify_identifier(ref: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Classify an author/editor ``@ref`` into ``(identifier_url, authority)``.

    The corpus mixes authorities and carries junk in this attribute
    (see knowledge/data.md): ORCID URLs, bare ORCID ids, VIAF URLs, GND URLs,
    plus ``"/"``, ``"none"``, empty, a leading space, and one doubled value.
    Each recognised authority is a named branch; anything unrecognised
    degrades to ``(None, None)`` so junk never crashes the parse and simply
    renders no identifier link.
    """
    if not ref:
        return None, None
    ref = ref.strip()
    if not ref:
        return None, None
    # Doubled values ("<url> <id>", "<id> <id>") appear once; take the first token.
    ref = ref.split()[0]
    low = ref.lower()
    if "orcid.org" in low:
        return ref, "orcid"
    if _BARE_ORCID.match(ref):
        # Named branch: normalise a bare ORCID id to its canonical URL.
        return f"https://orcid.org/{ref}", "orcid"
    if "viaf.org" in low:
        return ref, "viaf"
    if "d-nb.info/gnd" in low:
        return ref, "gnd"
    return None, None  # "/", "none", or any unrecognised value → no identifier


def _person_from_name_or_text(host: etree._Element, ref: Optional[str] = None) -> Person:
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
    identifier_url, identifier_authority = classify_identifier(ref)
    return Person(
        full_name=full,
        forename=forename,
        surname=surname,
        identifier_url=identifier_url,
        identifier_authority=identifier_authority,
    )


def parse_authors(file_desc: Optional[etree._Element]) -> list[Author]:
    out: list[Author] = []
    for author_el in findall(file_desc, "t:titleStmt/t:author"):
        person = _person_from_name_or_text(author_el, ref=attr(author_el, "ref"))

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
        person = _person_from_name_or_text(editor_el, ref=attr(editor_el, "ref"))
        out.append(Editor(person=person, role=attr(editor_el, "role")))
    return out


def parse_keywords(profile_desc: Optional[etree._Element]) -> list[str]:
    return [
        text
        for term_el in findall(profile_desc, "t:textClass/t:keywords/t:term")
        if (text := itertext(term_el))
    ]


def parse_doi(file_desc: Optional[etree._Element]) -> Optional[str]:
    """Read ``<publicationStmt>/<idno type="DOI">`` and return its text.

    Every RIDE review in the corpus carries this idno in the standard
    publicationStmt triplet (URI / DOI / archive — see knowledge/data.md).
    Returns ``None`` when the field is missing so the caller can decide
    whether to error out (Phase 13 validation will).
    """
    for idno_el in findall(file_desc, "t:publicationStmt/t:idno"):
        if attr(idno_el, "type") == "DOI":
            text = itertext(idno_el)
            return text or None
    return None


def parse_related_items(file_desc: Optional[etree._Element]) -> list[RelatedItem]:
    """Parse ``<notesStmt>/<relatedItem>`` entries.

    The two RIDE relatedItem types use different conventions for the
    target URL: ``reviewed_resource`` carries it as ``<bibl>/<idno type="URI">``
    (often paired with a ``<date type="accessed">``), while ``reviewing_criteria``
    carries it as ``<bibl>/<ref @target>``. Both shapes are collected into
    ``bibl_targets`` so the rendered bibliography can link either way.
    """
    out: list[RelatedItem] = []
    for ri_el in findall(file_desc, "t:notesStmt/t:relatedItem"):
        bibl_el = find(ri_el, "t:bibl")

        # Collect targets from <ref @target> (reviewing_criteria) and
        # from <idno type="URI"|"DOI"> (reviewed_resource) — both shapes
        # appear in the corpus, see knowledge/data.md.
        targets: list[str] = []
        for r in findall(ri_el, ".//t:ref"):
            t = attr(r, "target")
            if t:
                targets.append(t)
        for idno in findall(ri_el, ".//t:idno"):
            if attr(idno, "type") in {"URI", "DOI"}:
                t = itertext(idno)
                if t:
                    targets.append(t)

        # Dates inside <bibl>: type="accessed" is the last-access date for
        # online sources, type="publication" is the reviewed work's own
        # publication date (both shapes appear in the corpus).
        last_accessed: Optional[str] = None
        publication_date: Optional[str] = None
        for date_el in findall(ri_el, ".//t:date"):
            dtype = attr(date_el, "type")
            if dtype == "accessed" and last_accessed is None:
                last_accessed = itertext(date_el) or None
            elif dtype == "publication" and publication_date is None:
                publication_date = itertext(date_el) or None

        # Canonical title — first <title> directly under <bibl>.
        title: Optional[str] = None
        if bibl_el is not None:
            title_el = find(bibl_el, "t:title")
            if title_el is not None:
                title = itertext(title_el) or None

        # Reviewed-project contributors from <bibl>/<respStmt> — one
        # (resp, persName) pair each, document order, duplicates kept
        # (the corpus repeats persons across roles).
        personnel: list[tuple[str, str]] = []
        if bibl_el is not None:
            for resp_stmt in findall(bibl_el, "t:respStmt"):
                resp = itertext(find(resp_stmt, "t:resp"))
                for pers in findall(resp_stmt, "t:persName"):
                    name = itertext(pers)
                    if resp or name:
                        personnel.append((resp, name))

        out.append(RelatedItem(
            type=attr(ri_el, "type") or "",
            bibl_text=itertext(bibl_el) if bibl_el is not None else itertext(ri_el),
            bibl_targets=tuple(targets),
            xml_id=attr(ri_el, "xml:id"),
            last_accessed=last_accessed,
            publication_date=publication_date,
            title=title,
            personnel=tuple(personnel),
        ))
    return out
