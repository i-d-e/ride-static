"""Metadata formats of the OAI-PMH snapshot: oai_dc, oai_marcxml, oai_doajxml.

The live endpoint ride.i-d-e.de/apis/oai (eXist app ``ride-oai``) offers these
three formats. Each builder here reproduces the field mapping of the recorded
live responses (``tests/fixtures/oai/``) from the domain model, so harvesters
that know the live records find the same values: identifier ``ride.{N}.{M}``,
surname-first creators, ISO 639-2/B language codes, the DOI as
``tel:DOI`` identifier, keywords as subjects, the abstract as description.

Deliberate departures from the live mapping, each because the live value is
wrong or stale for a static host:

* The page URL is the review's current address, not the WordPress address.
* ``dc:isPartOf`` (a ``dcterms`` element, invalid inside ``oai_dc``) is written
  as ``dc:source`` with the same journal title.
* MARC 005 carries the build time instead of the constant 2015 value the live
  endpoint sends; 008 positions 0-5 carry the build date as live does.
* The MARC 520 abstract is not cut after a thousand characters.
* The second 856 points at the static PDF instead of a GitHub raw URL.

String templates are used on purpose, like the rest of the snapshot: the
output is diffable and byte-stable between builds.
"""

from __future__ import annotations

from typing import Optional
from xml.sax.saxutils import escape, quoteattr

from src.model.review import Author, Review
from src.render.feed import _date_parts
from src.render.html import abstract_first_paragraph_text

PUBLISHER = "Institut für Dokumentologie und Editorik e.V."
PUBLISHER_GND = "(DE-588)6521152-2"
PUBLISHER_PLACE = "Köln"
JOURNAL_TITLE_DC = "RIDE - A review journal for digital editions and resources"
JOURNAL_TITLE_DOAJ = "RIDE – A review journal for digital editions and resources"
EISSN = "2363-4952"
LICENCE_LABEL = "Creative Commons - Namensnennung 4.0 International"

# ISO 639-1 (TEI langUsage) -> ISO 639-2/B, the codes the live records use.
LANGUAGE_639_2 = {"en": "eng", "de": "ger", "fr": "fre", "it": "ita", "es": "spa"}

FORMATS: dict[str, tuple[str, str]] = {
    # prefix -> (schema, metadataNamespace), as the live ListMetadataFormats
    "oai_marcxml": (
        "http://www.loc.gov/MARC21/slim http://www.loc.gov/standards/marcxml/schema/MARC21slim.xsd",
        "http://www.loc.gov/MARC21/slim",
    ),
    "oai_dc": (
        "http://www.openarchives.org/OAI/2.0/oai_dc/ http://www.openarchives.org/OAI/2.0/oai_dc.xsd",
        "http://www.openarchives.org/OAI/2.0/oai_dc/",
    ),
    "oai_doajxml": (
        "https://doaj.org/static/doaj/doajArticles.xsd",
        "https://doaj.org/static/doaj/doajArticles",
    ),
}


def language_code(review: Review) -> str:
    return LANGUAGE_639_2.get(review.language, review.language or "und")


def surname_first(author_or_person) -> str:
    person = getattr(author_or_person, "person", author_or_person)
    if person.surname and person.forename:
        return f"{person.surname}, {person.forename}"
    return person.full_name


def forename_first(author: Author) -> str:
    p = author.person
    if p.surname and p.forename:
        return f"{p.forename} {p.surname}"
    return p.full_name


def datestamp(review: Review) -> str:
    year, month, day = _date_parts(review.publication_date)
    return f"{year:04d}-{month:02d}-{day:02d}"


def _orcid_id(author: Author) -> Optional[str]:
    p = author.person
    if p.identifier_authority == "orcid" and p.identifier_url:
        return p.identifier_url.rstrip("/").rsplit("/", 1)[-1]
    return None


def _e(value: str) -> str:
    return escape(value or "")


def dc_metadata(review: Review, page_url: str) -> str:
    year = datestamp(review)[:4]
    lines = [f"<dc:title>{_e(review.title)}</dc:title>"]
    lines += [f"<dc:creator>{_e(surname_first(a))}</dc:creator>" for a in review.authors]
    lines.append(f"<dc:publisher>{_e(PUBLISHER)}</dc:publisher>")
    lines.append(f"<dc:date>{year}</dc:date>")
    lines.append(f'<dc:identifier xsi:type="tel:URL">{_e(page_url)}</dc:identifier>')
    if review.doi:
        lines.append(f'<dc:identifier xsi:type="tel:DOI">{_e(review.doi)}</dc:identifier>')
    if review.licence:
        lines.append(f"<dc:rights>{_e(review.licence)}</dc:rights>")
    lines.append(f"<dc:source>{_e(JOURNAL_TITLE_DC)}</dc:source>")
    lines += [f"<dc:contributor>{_e(surname_first(e))}</dc:contributor>" for e in review.editors]
    for item in review.related_items:
        if item.type == "reviewed_resource":
            lines += [f"<dc:relation>{_e(t)}</dc:relation>" for t in item.bibl_targets[:1]]
    lines.append(f"<dc:language>{language_code(review)}</dc:language>")
    lines += [f"<dc:subject>{_e(k)}</dc:subject>" for k in review.keywords]
    abstract = abstract_first_paragraph_text(review)
    if abstract:
        lines.append(f"<dc:description>{_e(abstract)}</dc:description>")
    lines += ["<dc:type>Text</dc:type>", "<dc:type>Image</dc:type>", "<dc:format>html</dc:format>"]
    body = "\n".join(f"          {line}" for line in lines)
    return (
        '        <oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"\n'
        '                   xmlns:dc="http://purl.org/dc/elements/1.1/"\n'
        '                   xmlns:tel="http://krait.kb.nl/coop/tel/handbook/telterms.html"\n'
        '                   xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/oai_dc/'
        ' http://www.openarchives.org/OAI/2.0/oai_dc.xsd">\n'
        f"{body}\n"
        "        </oai_dc:dc>"
    )


def _datafield(tag: str, ind1: str, ind2: str, subfields: list[tuple[str, str]]) -> str:
    subs = "".join(
        f'\n              <marc:subfield code="{code}">{_e(value)}</marc:subfield>'
        for code, value in subfields
        if value
    )
    return (
        f'            <marc:datafield tag="{tag}" ind1="{ind1}" ind2="{ind2}">{subs}\n'
        "            </marc:datafield>"
    )


def _marc_author(tag: str, author: Author) -> str:
    aff = author.affiliation
    place = ", ".join(
        x for x in ((aff.org_name if aff else None), (aff.place_name if aff else None)) if x
    )
    return _datafield(
        tag,
        "1",
        " ",
        [
            ("a", surname_first(author)),
            ("4", "aut"),
            ("0", _marc_authority(author)),
            ("u", place),
        ],
    )


# MARC $0 source codes the live records use per authority.
_MARC_SOURCE = {"orcid": "(orcid)", "viaf": "(viaf)", "gnd": "(DE-588)"}


def _marc_authority(author: Author) -> str:
    p = author.person
    source = _MARC_SOURCE.get(p.identifier_authority or "")
    if not source or not p.identifier_url:
        return ""
    return f"{source}{p.identifier_url.rstrip('/').rsplit('/', 1)[-1]}"


def marc_metadata(review: Review, page_url: str, build_stamp: str) -> str:
    """MARCXML record. ``build_stamp`` is ``YYYYMMDDhhmmss`` of the build."""
    year, month, _ = _date_parts(review.publication_date)
    lang = language_code(review)
    fields = [
        "            <marc:leader>00000naa a22000007u 4500</marc:leader>",
        f'            <marc:controlfield tag="005">{build_stamp}.0</marc:controlfield>',
        '            <marc:controlfield tag="007">cr||||||||||||</marc:controlfield>',
        f'            <marc:controlfield tag="008">{build_stamp[2:8]}s{year:04d}||||gw |||||oo||| 00||||{lang}||</marc:controlfield>',
    ]
    if review.doi:
        fields.append(_datafield("024", "7", " ", [("a", review.doi), ("2", "doi")]))
    fields.append(_datafield("041", " ", " ", [("a", lang)]))
    fields.append(_datafield("093", " ", " ", [("b", "b")]))
    if review.authors:
        fields.append(_marc_author("100", review.authors[0]))
    fields.append(_datafield("245", "0", "0", [("a", review.title)]))
    fields.append(_datafield("264", " ", " ", [("c", f"{year:04d}")]))
    fields.append(_datafield("506", "0", " ", [("a", "open-access")]))
    abstract = abstract_first_paragraph_text(review)
    if abstract:
        fields.append(_datafield("520", "3", " ", [("a", abstract)]))
    if review.licence:
        fields.append(
            _datafield(
                "540",
                " ",
                " ",
                [("a", LICENCE_LABEL), ("f", "cc-by-4.0"), ("u", review.licence), ("2", "cc")],
            )
        )
    fields += [_datafield("653", " ", " ", [("a", k)]) for k in review.keywords]
    fields += [_marc_author("700", a) for a in review.authors[1:]]
    fields.append(
        _datafield(
            "710",
            "1",
            "2",
            [("a", PUBLISHER), ("g", PUBLISHER_PLACE), ("0", PUBLISHER_GND), ("4", "edt")],
        )
    )
    fields.append(
        _datafield(
            "773",
            "1",
            " ",
            [
                ("g", f"volume:{review.issue}"),
                ("g", f"month:{month:02d}"),
                ("g", f"year:{year:04d}"),
                ("7", "nnas"),
            ],
        )
    )
    fields.append(_datafield("773", "1", "8", [("x", EISSN)]))
    fields.append(_datafield("856", "4", " ", [("u", page_url), ("q", "html")]))
    fields.append(
        _datafield(
            "856",
            "4",
            "0",
            [("u", f"{page_url}{review.id}.pdf"), ("q", "pdf"), ("x", "Transfer-URL")],
        )
    )
    body = "\n".join(fields)
    return (
        '        <marc:collection xmlns:marc="http://www.loc.gov/MARC21/slim"'
        ' xsi:schemaLocation="http://www.loc.gov/MARC21/slim'
        ' http://www.loc.gov/standards/marcxml/schema/MARC21slim.xsd">\n'
        "          <marc:record>\n"
        f"{body}\n"
        "          </marc:record>\n"
        "        </marc:collection>"
    )


def doaj_metadata(review: Review, page_url: str) -> str:
    lang = language_code(review)
    affiliations: list[str] = []
    author_lines: list[str] = []
    for author in review.authors:
        parts = [f"              <d:name>{_e(forename_first(author))}</d:name>"]
        org = author.affiliation.org_name if author.affiliation else None
        if org:
            if org not in affiliations:
                affiliations.append(org)
            parts.append(
                f"              <d:affiliationId>{affiliations.index(org) + 1}</d:affiliationId>"
            )
        orcid = _orcid_id(author)
        if orcid:
            parts.append(f"              <d:orcid_id>https://orcid.org/{_e(orcid)}</d:orcid_id>")
        author_lines.append(
            "            <d:author>\n" + "\n".join(parts) + "\n            </d:author>"
        )
    lines = [
        f"<d:language>{lang}</d:language>",
        f"<d:publisher>{_e(PUBLISHER)}</d:publisher>",
        f"<d:journalTitle>{_e(JOURNAL_TITLE_DOAJ)}</d:journalTitle>",
        f"<d:eissn>{EISSN}</d:eissn>",
        f"<d:publicationDate>{datestamp(review)}</d:publicationDate>",
        f"<d:volume>{_e(review.issue)}</d:volume>",
    ]
    if review.doi:
        lines.append(f"<d:doi>{_e(review.doi)}</d:doi>")
    lines.append("<d:documentType>article</d:documentType>")
    lines.append(f'<d:title language="{lang}">{_e(review.title)}</d:title>')
    body = "\n".join(f"          {line}" for line in lines)
    body += "\n          <d:authors>\n" + "\n".join(author_lines) + "\n          </d:authors>"
    if affiliations:
        body += (
            "\n          <d:affiliationsList>\n"
            + "\n".join(
                f'            <d:affiliationName affiliationId="{i}">{_e(name)}</d:affiliationName>'
                for i, name in enumerate(affiliations, 1)
            )
            + "\n          </d:affiliationsList>"
        )
    abstract = abstract_first_paragraph_text(review)
    if abstract:
        body += f'\n          <d:abstract language="{lang}">{_e(abstract)}</d:abstract>'
    body += f'\n          <d:fullTextUrl format="html">{_e(page_url)}</d:fullTextUrl>'
    if review.keywords:
        body += (
            f"\n          <d:keywords language={quoteattr(lang)}>\n"
            + "\n".join(f"            <d:keyword>{_e(k)}</d:keyword>" for k in review.keywords)
            + "\n          </d:keywords>"
        )
    return (
        '        <d:record xmlns:d="https://doaj.org/static/doaj/doajArticles">\n'
        f"{body}\n"
        "        </d:record>"
    )


def metadata(prefix: str, review: Review, page_url: str, build_stamp: str) -> str:
    if prefix == "oai_dc":
        return dc_metadata(review, page_url)
    if prefix == "oai_marcxml":
        return marc_metadata(review, page_url, build_stamp)
    if prefix == "oai_doajxml":
        return doaj_metadata(review, page_url)
    raise ValueError(f"unknown metadata prefix {prefix!r}")
