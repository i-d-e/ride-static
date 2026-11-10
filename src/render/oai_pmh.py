"""OAI-PMH snapshot in all three formats of the live endpoint (R15 / A5).

OAI-PMH is a query protocol (``?verb=…&metadataPrefix=…``). GitHub Pages
ignores the query string, so the build pre-renders every response a
harvester can ask for and writes it at a fixed path. A small request router
in front of the static files (``deploy/oai-router/``) can then answer the
protocol at a real base URL by mapping parameters to these files; without
it the files serve as a documented export. See ``knowledge/oai-pmh-statisch.md``.

Layout under ``site/oai/`` (``routes.json`` records the same mapping):

* ``identify.xml``, ``list-metadata-formats.xml``, ``list-sets.xml``
* ``{prefix}/list-identifiers.xml``, ``{prefix}/list-records.xml`` and
  ``{prefix}/records/{id}.xml`` for ``oai_dc``, ``oai_marcxml``, ``oai_doajxml``
* ``list-identifiers.xml``, ``list-records.xml``, ``records/{id}.xml``: the
  ``oai_dc`` responses at their earlier paths, kept so existing links work
* ``static-repository.xml``: the same records as one OAI Static Repository
  file, the form a Static Repository Gateway reads

Identifiers follow the live endpoint (``ride.4.2``), so a harvester that has
already collected RIDE keeps its record identities. The lists are complete
responses without ``resumptionToken``: the corpus is small, and a token is
the repository's option for splitting long lists, which the router can add
later if a harvester needs it. Issue editorials (``ride.{N}.0``) are records
as on the live endpoint.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Sequence
from xml.sax.saxutils import escape, quoteattr

from src.model.review import Review
from src.render.html import review_url
from src.render.oai_formats import FORMATS, datestamp, metadata

REPOSITORY_NAME = "ride. A review journal for digital editions and resources"
ADMIN_EMAIL = "ride-editor@i-d-e.de"
GRANULARITY = "YYYY-MM-DD"
DELETED_RECORD = "no"
PROTOCOL_VERSION = "2.0"
EARLIEST_DATESTAMP = "2014-06-01"  # first RIDE issue
PREFIXES = tuple(FORMATS)
NL = "\n"


def oai_identifier(review: Review) -> str:
    """OAI identifier as the live endpoint issues it: the TEI ``xml:id``."""
    return review.id


def _request(base: str, verb: str, **args: str) -> str:
    attrs = "".join(f" {k}={quoteattr(v)}" for k, v in args.items() if v)
    return f'  <request verb="{verb}"{attrs}>{escape(base)}</request>'


def _wrap(base: str, response_date: str, request: str, body: str) -> str:
    return NL.join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"',
            '         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
            '         xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/'
            ' http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd">',
            f"  <responseDate>{escape(response_date)}</responseDate>",
            request,
            body,
            "</OAI-PMH>",
            "",
        ]
    )


def _identify_body(base: str, outer: str = "", p: str = "") -> str:
    """``outer`` prefixes the wrapper, ``p`` the OAI elements (Static Repository)."""
    fields = (
        ("repositoryName", escape(REPOSITORY_NAME)),
        ("baseURL", escape(base)),
        ("protocolVersion", PROTOCOL_VERSION),
        ("adminEmail", escape(ADMIN_EMAIL)),
        ("earliestDatestamp", EARLIEST_DATESTAMP),
        ("deletedRecord", DELETED_RECORD),
        ("granularity", GRANULARITY),
    )
    inner = [f"    <{p}{tag}>{value}</{p}{tag}>" for tag, value in fields]
    return NL.join([f"  <{outer}Identify>", *inner, f"  </{outer}Identify>"])


def _formats_body(outer: str = "", p: str = "") -> str:
    lines = [f"  <{outer}ListMetadataFormats>"]
    for prefix, (schema, ns) in FORMATS.items():
        lines += [
            f"    <{p}metadataFormat>",
            f"      <{p}metadataPrefix>{prefix}</{p}metadataPrefix>",
            f"      <{p}schema>{escape(schema)}</{p}schema>",
            f"      <{p}metadataNamespace>{escape(ns)}</{p}metadataNamespace>",
            f"    </{p}metadataFormat>",
        ]
    lines.append(f"  </{outer}ListMetadataFormats>")
    return NL.join(lines)


def _header(review: Review, p: str = "") -> str:
    return NL.join(
        [
            f"    <{p}header>",
            f"      <{p}identifier>{escape(oai_identifier(review))}</{p}identifier>",
            f"      <{p}datestamp>{datestamp(review)}</{p}datestamp>",
            f"    </{p}header>",
        ]
    )


def _record(review: Review, prefix: str, page_url: str, stamp: str, p: str = "") -> str:
    return NL.join(
        [
            f"    <{p}record>",
            _header(review, p),
            f"      <{p}metadata>",
            metadata(prefix, review, page_url, stamp),
            f"      </{p}metadata>",
            f"    </{p}record>",
        ]
    )


def build_identify(oai_base: str, response_date: str = "") -> str:
    return _wrap(oai_base, response_date, _request(oai_base, "Identify"), _identify_body(oai_base))


def build_list_metadata_formats(oai_base: str, response_date: str = "") -> str:
    return _wrap(
        oai_base, response_date, _request(oai_base, "ListMetadataFormats"), _formats_body()
    )


def build_list_sets(oai_base: str, response_date: str = "") -> str:
    """The live endpoint has no sets and answers ListSets with this error."""
    return _wrap(
        oai_base,
        response_date,
        _request(oai_base, "ListSets"),
        '  <error code="noSetHierarchy">No set structure available</error>',
    )


def build_list(
    verb: str,
    reviews: Sequence[Review],
    prefix: str,
    oai_base: str,
    site_base: str,
    response_date: str = "",
    stamp: str = "",
) -> str:
    if verb == "ListIdentifiers":
        items = [_header(r) for r in reviews]
    else:
        items = [_record(r, prefix, review_url(r, site_base), stamp) for r in reviews]
    return _wrap(
        oai_base,
        response_date,
        _request(oai_base, verb, metadataPrefix=prefix),
        NL.join([f"  <{verb}>", *items, f"  </{verb}>"]),
    )


def build_get_record(
    review: Review,
    prefix: str,
    oai_base: str,
    site_base: str,
    response_date: str = "",
    stamp: str = "",
) -> str:
    record = _record(review, prefix, review_url(review, site_base), stamp)
    return _wrap(
        oai_base,
        response_date,
        _request(oai_base, "GetRecord", identifier=oai_identifier(review), metadataPrefix=prefix),
        NL.join(["  <GetRecord>", record, "  </GetRecord>"]),
    )


def build_static_repository(
    reviews: Sequence[Review], oai_base: str, site_base: str, stamp: str = ""
) -> str:
    """One file in the OAI Static Repository format (Identify, formats, records).

    The specification asks for a MIME type GitHub Pages cannot set; a gateway
    that reads this file is one of the router options, not part of the build.
    """
    blocks: list[str] = []
    for prefix in PREFIXES:
        blocks.append(f'  <sr:ListRecords metadataPrefix="{prefix}">')
        blocks += [_record(r, prefix, review_url(r, site_base), stamp, "oai:") for r in reviews]
        blocks.append("  </sr:ListRecords>")
    return NL.join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<sr:Repository xmlns:sr="http://www.openarchives.org/OAI/2.0/static-repository"',
            '               xmlns:oai="http://www.openarchives.org/OAI/2.0/"',
            '               xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">',
            _identify_body(oai_base, "sr:", "oai:"),
            _formats_body("sr:", "oai:"),
            *blocks,
            "</sr:Repository>",
            "",
        ]
    )


def routes(reviews: Sequence[Review]) -> dict:
    """Request -> file mapping, the contract the request router implements."""
    return {
        "Identify": "identify.xml",
        "ListMetadataFormats": "list-metadata-formats.xml",
        "ListSets": "list-sets.xml",
        "ListIdentifiers": {p: f"{p}/list-identifiers.xml" for p in PREFIXES},
        "ListRecords": {p: f"{p}/list-records.xml" for p in PREFIXES},
        "GetRecord": {p: f"{p}/records/{{identifier}}.xml" for p in PREFIXES},
        "identifiers": {oai_identifier(r): datestamp(r) for r in reviews if r.id},
    }


def write_oai_pmh(
    reviews: Sequence[Review],
    base_url: str,
    out_root: Path,
    build_date: Optional[str] = None,
    oai_base_url: Optional[str] = None,
) -> int:
    """Write the snapshot under ``out_root/oai/``; return the number of files.

    ``oai_base_url`` is the address harvesters use, i.e. the request router
    when one is deployed; it defaults to the snapshot directory.
    """
    if not base_url:
        raise ValueError("OAI-PMH snapshot requires an absolute base_url")
    oai_base = oai_base_url or f"{base_url}/oai/"
    date = build_date or ""
    stamp = "".join(ch for ch in date[:19] if ch.isdigit()) or "00000000000000"
    reviews = [r for r in reviews if r.id]
    files: dict[str, str] = {
        "identify.xml": build_identify(oai_base, date),
        "list-metadata-formats.xml": build_list_metadata_formats(oai_base, date),
        "list-sets.xml": build_list_sets(oai_base, date),
        "static-repository.xml": build_static_repository(reviews, oai_base, base_url, stamp),
        "routes.json": json.dumps(routes(reviews), indent=2, ensure_ascii=False) + NL,
    }
    for prefix in PREFIXES:
        for verb, name in (
            ("ListIdentifiers", "list-identifiers"),
            ("ListRecords", "list-records"),
        ):
            files[f"{prefix}/{name}.xml"] = build_list(
                verb, reviews, prefix, oai_base, base_url, date, stamp
            )
        for r in reviews:
            files[f"{prefix}/records/{r.id}.xml"] = build_get_record(
                r, prefix, oai_base, base_url, date, stamp
            )
    # Earlier oai_dc paths stay valid.
    files["list-identifiers.xml"] = files["oai_dc/list-identifiers.xml"]
    files["list-records.xml"] = files["oai_dc/list-records.xml"]
    for r in reviews:
        files[f"records/{r.id}.xml"] = files[f"oai_dc/records/{r.id}.xml"]
    oai_dir = out_root / "oai"
    for rel, text in files.items():
        path = oai_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return len(files)
