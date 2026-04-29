"""OAI-PMH static snapshot — Phase 12 R15 / A5.

OAI-PMH is normally a dynamic protocol: a harvester issues HTTP requests
with ``?verb=…`` query parameters. GitHub Pages cannot dispatch on query
parameters, so we ship a *static snapshot*: one pre-rendered XML file
per verb at deterministic paths under ``site/oai/``. Harvesters that
support file-based ingestion (or a thin proxy that maps query verbs to
paths) consume the snapshot directly; the snapshot reflects the corpus
state at build time, no runtime needed.

Layout under ``site/oai/``:

* ``identify.xml`` — repository metadata
* ``list-metadata-formats.xml`` — supported metadata prefixes (oai_dc only)
* ``list-identifiers.xml`` — header-only listing of every record
* ``list-records.xml`` — full Dublin Core records for every review
* ``records/{review_id}.xml`` — one ``<GetRecord>`` per review

The module exposes two layers:

* ``build_*`` — pure functions that take Reviews and produce XML strings.
* ``write_oai_pmh`` — driver that wraps ``build_*`` and writes the files.

The Dublin Core mapping follows the standard ``oai_dc`` schema; each
``<dc:identifier>`` carries the deployed page URL so a harvester can
trace a record back to its rendered form.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional, Sequence
from xml.sax.saxutils import escape

from src.model.block import Paragraph
from src.model.review import Review
from src.model.section import Section


REPOSITORY_NAME = "RIDE — Reviews in Digital Editions"
ADMIN_EMAIL = "ride@i-d-e.de"
GRANULARITY = "YYYY-MM-DD"
DELETED_RECORD = "no"
PROTOCOL_VERSION = "2.0"
EARLIEST_DATESTAMP = "2014-06-01"  # first RIDE issue


def oai_identifier(review: Review, host: str = "ride.i-d-e.de") -> str:
    """OAI identifier for a review — ``oai:{host}:{review.id}``."""
    return f"oai:{host}:{review.id}"


def build_identify(base_url: str, build_date: Optional[str] = None) -> str:
    """``<Identify>`` response.

    ``base_url`` becomes the ``baseURL`` field; harvesters use it to
    construct hypothetical query URLs even if they consume the static
    files directly.
    """
    response_date = build_date or ""
    return _wrap_response(
        verb="Identify",
        base_url=base_url,
        response_date=response_date,
        body=(
            "  <Identify>\n"
            f"    <repositoryName>{escape(REPOSITORY_NAME)}</repositoryName>\n"
            f"    <baseURL>{escape(base_url)}/oai/</baseURL>\n"
            f"    <protocolVersion>{PROTOCOL_VERSION}</protocolVersion>\n"
            f"    <adminEmail>{escape(ADMIN_EMAIL)}</adminEmail>\n"
            f"    <earliestDatestamp>{EARLIEST_DATESTAMP}</earliestDatestamp>\n"
            f"    <deletedRecord>{DELETED_RECORD}</deletedRecord>\n"
            f"    <granularity>{GRANULARITY}</granularity>\n"
            "  </Identify>"
        ),
    )


def build_list_metadata_formats(
    base_url: str, build_date: Optional[str] = None
) -> str:
    """``<ListMetadataFormats>`` — only ``oai_dc`` is supported."""
    return _wrap_response(
        verb="ListMetadataFormats",
        base_url=base_url,
        response_date=build_date or "",
        body=(
            "  <ListMetadataFormats>\n"
            "    <metadataFormat>\n"
            "      <metadataPrefix>oai_dc</metadataPrefix>\n"
            "      <schema>http://www.openarchives.org/OAI/2.0/oai_dc.xsd</schema>\n"
            "      <metadataNamespace>http://www.openarchives.org/OAI/2.0/oai_dc/</metadataNamespace>\n"
            "    </metadataFormat>\n"
            "  </ListMetadataFormats>"
        ),
    )


def build_list_identifiers(
    reviews: Sequence[Review], base_url: str, build_date: Optional[str] = None
) -> str:
    """``<ListIdentifiers>`` — header-only listing of every record."""
    headers = "\n".join(_header_xml(r) for r in reviews)
    return _wrap_response(
        verb="ListIdentifiers",
        base_url=base_url,
        response_date=build_date or "",
        body=f"  <ListIdentifiers>\n{headers}\n  </ListIdentifiers>",
    )


def build_list_records(
    reviews: Sequence[Review], base_url: str, build_date: Optional[str] = None
) -> str:
    """``<ListRecords>`` — full Dublin Core records for every review."""
    records = "\n".join(_record_xml(r, base_url) for r in reviews)
    return _wrap_response(
        verb="ListRecords",
        base_url=base_url,
        response_date=build_date or "",
        body=f"  <ListRecords>\n{records}\n  </ListRecords>",
    )


def build_get_record(
    review: Review, base_url: str, build_date: Optional[str] = None
) -> str:
    """``<GetRecord>`` — one Dublin Core record."""
    return _wrap_response(
        verb="GetRecord",
        base_url=base_url,
        response_date=build_date or "",
        body=(
            "  <GetRecord>\n"
            f"{_record_xml(review, base_url)}\n"
            "  </GetRecord>"
        ),
    )


def write_oai_pmh(
    reviews: Sequence[Review],
    base_url: str,
    out_root: Path,
    build_date: Optional[str] = None,
) -> int:
    """Driver — writes the full snapshot under ``out_root/oai/``.

    Returns the number of files written. ``base_url`` must be set;
    OAI-PMH identifiers and ``baseURL`` need an absolute origin.
    """
    if not base_url:
        raise ValueError("OAI-PMH snapshot requires an absolute base_url")

    oai_dir = out_root / "oai"
    oai_dir.mkdir(parents=True, exist_ok=True)
    records_dir = oai_dir / "records"
    records_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    (oai_dir / "identify.xml").write_text(
        build_identify(base_url, build_date), encoding="utf-8"
    )
    written += 1
    (oai_dir / "list-metadata-formats.xml").write_text(
        build_list_metadata_formats(base_url, build_date), encoding="utf-8"
    )
    written += 1
    (oai_dir / "list-identifiers.xml").write_text(
        build_list_identifiers(reviews, base_url, build_date), encoding="utf-8"
    )
    written += 1
    (oai_dir / "list-records.xml").write_text(
        build_list_records(reviews, base_url, build_date), encoding="utf-8"
    )
    written += 1
    for review in reviews:
        if not review.id:
            continue
        (records_dir / f"{review.id}.xml").write_text(
            build_get_record(review, base_url, build_date), encoding="utf-8"
        )
        written += 1
    return written


# ── XML composition helpers ─────────────────────────────────────────


def _wrap_response(*, verb: str, base_url: str, response_date: str, body: str) -> str:
    """Wrap a verb body in the OAI-PMH envelope.

    The envelope (root element ``<OAI-PMH>``) is mandatory in every
    response; it carries the ``responseDate`` and the ``request`` echo
    that lets a harvester correlate the response with its request.
    """
    response_date_clean = escape(response_date) if response_date else ""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"\n'
        '         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'
        '         xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/\n'
        '             http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd">\n'
        f"  <responseDate>{response_date_clean}</responseDate>\n"
        f'  <request verb="{verb}">{escape(base_url)}/oai/</request>\n'
        f"{body}\n"
        "</OAI-PMH>\n"
    )


def _header_xml(review: Review) -> str:
    identifier = oai_identifier(review)
    datestamp = _datestamp_or_default(review.publication_date)
    return (
        "    <header>\n"
        f"      <identifier>{escape(identifier)}</identifier>\n"
        f"      <datestamp>{escape(datestamp)}</datestamp>\n"
        "    </header>"
    )


def _record_xml(review: Review, base_url: str) -> str:
    """One ``<record>`` containing ``<header>`` + Dublin Core ``<metadata>``."""
    return (
        "    <record>\n"
        f"{_header_xml(review)}\n"
        f"{_metadata_xml(review, base_url)}\n"
        "    </record>"
    )


def _metadata_xml(review: Review, base_url: str) -> str:
    dc_lines: list[str] = []

    if review.title:
        dc_lines.append(f"          <dc:title>{escape(review.title)}</dc:title>")

    for author in review.authors:
        dc_lines.append(
            f"          <dc:creator>{escape(author.person.full_name)}</dc:creator>"
        )

    for editor in review.editors:
        dc_lines.append(
            f"          <dc:contributor>{escape(editor.person.full_name)}</dc:contributor>"
        )

    if review.publication_date:
        dc_lines.append(
            f"          <dc:date>{escape(review.publication_date)}</dc:date>"
        )

    if review.language:
        dc_lines.append(
            f"          <dc:language>{escape(review.language)}</dc:language>"
        )

    if review.licence:
        dc_lines.append(
            f"          <dc:rights>{escape(review.licence)}</dc:rights>"
        )

    # Dublin Core allows multiple <dc:identifier> elements; emit DOI first
    # (persistent) and the page URL second (mutable). When the DOI is
    # missing (corpus in transition), the page URL stays the only one.
    if review.doi:
        dc_lines.append(
            f"          <dc:identifier>{escape(f'https://doi.org/{review.doi}')}</dc:identifier>"
        )
    page_url = _page_url(review, base_url)
    if page_url:
        dc_lines.append(
            f"          <dc:identifier>{escape(page_url)}</dc:identifier>"
        )

    for kw in review.keywords:
        dc_lines.append(
            f"          <dc:subject>{escape(kw)}</dc:subject>"
        )

    abstract = _abstract_text(review)
    if abstract:
        dc_lines.append(
            f"          <dc:description>{escape(abstract)}</dc:description>"
        )

    dc_lines.append("          <dc:type>article</dc:type>")
    dc_lines.append(f"          <dc:publisher>{escape(REPOSITORY_NAME)}</dc:publisher>")

    if review.issue:
        dc_lines.append(
            f"          <dc:source>RIDE Issue {escape(review.issue)}</dc:source>"
        )

    for item in review.related_items:
        if item.type != "reviewed_resource":
            continue
        for target in item.bibl_targets:
            dc_lines.append(
                f"          <dc:relation>{escape(target)}</dc:relation>"
            )

    dc_body = "\n".join(dc_lines)
    return (
        "      <metadata>\n"
        '        <oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"\n'
        '                   xmlns:dc="http://purl.org/dc/elements/1.1/"\n'
        '                   xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'
        '                   xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/oai_dc/\n'
        '                       http://www.openarchives.org/OAI/2.0/oai_dc.xsd">\n'
        f"{dc_body}\n"
        "        </oai_dc:dc>\n"
        "      </metadata>"
    )


def _page_url(review: Review, base_url: str) -> Optional[str]:
    if not review.id or not review.issue:
        return None
    return f"{base_url}/issues/{review.issue}/{review.id}/"


def _datestamp_or_default(publication_date: str) -> str:
    """OAI-PMH datestamps must be ``YYYY-MM-DD`` per the protocol.

    Reviews with year-only or year-month dates are widened to the first
    of the month/year; freeform strings fall back to a fixed sentinel
    so a harvester sees a parseable value.
    """
    if not publication_date:
        return EARLIEST_DATESTAMP
    parts = publication_date.split("T")[0].split("-")
    if len(parts) == 3 and all(p.isdigit() for p in parts):
        return publication_date.split("T")[0]
    if len(parts) == 2 and all(p.isdigit() for p in parts):
        return f"{parts[0]}-{parts[1]}-01"
    if len(parts) == 1 and parts[0].isdigit() and len(parts[0]) == 4:
        return f"{parts[0]}-01-01"
    return EARLIEST_DATESTAMP


def _abstract_text(review: Review) -> Optional[str]:
    """Mirror the JSON-LD/HTML rule: front first, then body."""
    for source in (review.front, review.body):
        for sec in source:
            if sec.type == "abstract":
                text = _section_first_paragraph_text(sec)
                if text:
                    return text
    return None


def _section_first_paragraph_text(section: Section) -> Optional[str]:
    for block in section.blocks:
        if isinstance(block, Paragraph):
            return _inlines_to_text(block.inlines).strip() or None
    return None


def _inlines_to_text(inlines: Iterable) -> str:
    """Flatten inlines to plain text — Dublin Core literals carry no markup."""
    from src.model.inline import Emphasis, Highlight, InlineCode, Reference, Text

    parts: list[str] = []
    for inline in inlines or ():
        if isinstance(inline, Text):
            parts.append(inline.text)
        elif isinstance(inline, (Emphasis, Highlight, Reference)):
            parts.append(_inlines_to_text(inline.children))
        elif isinstance(inline, InlineCode):
            parts.append(inline.text)
    return "".join(parts)
