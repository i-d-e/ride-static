"""JSON-LD serialisation — Phase 12 R15 / A5.

Maps a :class:`~src.model.review.Review` to a ``schema.org/ScholarlyArticle``
dictionary that ``base.html``'s ``{% block schema %}`` embeds in every review
page. Bibliography crawlers (Zotero connector, Google Scholar, OpenAlex) and
generic search engines pick it up via ``<script type="application/ld+json">``.

Pure formatter: no IO, no parsing. The single entry point :func:`to_jsonld`
takes a Review and an optional deploy-base-URL and returns a plain dict so
callers can serialise (with their preferred separators) or post-process.
:func:`to_jsonld_string` is the convenience wrapper used by the renderer.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from src.model.review import Affiliation, Author, Editor, Person, Review
from src.render.html import (
    abstract_first_paragraph_text,
    doi_url,
)


SCHEMA_CONTEXT = "https://schema.org"


def to_jsonld(review: Review, base_url: str = "") -> dict[str, Any]:
    """Build a schema.org/ScholarlyArticle dict for one review.

    ``base_url`` is the deploy prefix (empty in tests, ``/ride-static``
    locally, the canonical host in CI). When set, ``url`` and ``@id``
    point at the deployed page; when empty, both fields are omitted so
    consumers do not see relative or partial URIs.

    DOI handling: when ``review.doi`` is present, the DOI URL takes the
    role of the canonical ``@id`` (DOIs are designed to be persistent
    identifiers, page URLs are not), and ``identifier`` carries it as a
    PropertyValue so Crossref/OpenAlex-style harvesters can lift it
    directly. The deployed page URL stays in ``url``.
    """
    data: dict[str, Any] = {
        "@context": SCHEMA_CONTEXT,
        "@type": "ScholarlyArticle",
        "headline": review.title,
        "name": review.title,
    }

    page_url = _page_url(review, base_url)
    doi = doi_url(review.doi)
    canonical_id = doi or page_url
    if canonical_id:
        data["@id"] = canonical_id
    if page_url:
        data["url"] = page_url
    if doi:
        data["identifier"] = {
            "@type": "PropertyValue",
            "propertyID": "DOI",
            "value": review.doi,
            "url": doi,
        }

    if review.publication_date:
        data["datePublished"] = review.publication_date

    if review.language:
        data["inLanguage"] = review.language

    if review.licence:
        data["license"] = review.licence

    if review.authors:
        data["author"] = [_author_to_jsonld(a) for a in review.authors]

    if review.editors:
        data["editor"] = [_editor_to_jsonld(e) for e in review.editors]

    if review.keywords:
        data["keywords"] = list(review.keywords)

    if review.issue:
        data["isPartOf"] = {
            "@type": "PublicationIssue",
            "issueNumber": review.issue,
            "name": f"RIDE Issue {review.issue}",
        }

    abstract = abstract_first_paragraph_text(review)
    if abstract:
        data["abstract"] = abstract

    about = _reviewed_resources(review)
    if about:
        data["about"] = about

    return data


def to_jsonld_string(review: Review, base_url: str = "") -> str:
    """Serialise :func:`to_jsonld` to a JSON string suitable for embedding."""
    return json.dumps(to_jsonld(review, base_url), ensure_ascii=False, indent=2)


def _page_url(review: Review, base_url: str) -> Optional[str]:
    if not base_url or not review.issue or not review.id:
        return None
    return f"{base_url}/issues/{review.issue}/{review.id}/"


def _author_to_jsonld(author: Author) -> dict[str, Any]:
    """Author email is **deliberately not emitted** — the site obfuscates
    mailto links in the rendered HTML (see ``_obfuscate_mail`` in
    ``src.render.html``); leaking the raw address through JSON-LD would
    undo that defensive default for any structured-data crawler.
    """
    p = _person_to_jsonld(author.person)
    if author.affiliation:
        aff = _affiliation_to_jsonld(author.affiliation)
        if aff:
            p["affiliation"] = aff
    return p


def _editor_to_jsonld(editor: Editor) -> dict[str, Any]:
    p = _person_to_jsonld(editor.person)
    if editor.role:
        p["jobTitle"] = editor.role
    return p


def _person_to_jsonld(person: Person) -> dict[str, Any]:
    p: dict[str, Any] = {"@type": "Person", "name": person.full_name}
    if person.forename:
        p["givenName"] = person.forename
    if person.surname:
        p["familyName"] = person.surname
    if person.orcid:
        p["@id"] = person.orcid
        p["sameAs"] = person.orcid
    return p


def _affiliation_to_jsonld(aff: Affiliation) -> Optional[dict[str, Any]]:
    name = aff.org_name or aff.place_name
    if not name:
        return None
    out: dict[str, Any] = {"@type": "Organization", "name": name}
    if aff.org_name and aff.place_name and aff.org_name != aff.place_name:
        out["location"] = aff.place_name
    return out


def _reviewed_resources(review: Review) -> list[dict[str, Any]]:
    """schema.org/about entries built from ``RelatedItem.type == 'reviewed_resource'``.

    The corpus uses ``reviewing_criteria`` and ``reviewed_resource`` as the
    two RelatedItem types (see knowledge/data.md). Only the latter belongs
    in ``about``; the criteria document is meta-information about the
    review process, not the work being reviewed.
    """
    out: list[dict[str, Any]] = []
    for item in review.related_items:
        if item.type != "reviewed_resource":
            continue
        entry: dict[str, Any] = {"@type": "CreativeWork", "name": item.bibl_text}
        if item.bibl_targets:
            entry["url"] = item.bibl_targets[0]
        out.append(entry)
    return out


