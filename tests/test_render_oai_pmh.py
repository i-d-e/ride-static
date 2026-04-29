"""Tests for ``src.render.oai_pmh`` — Phase 12 R15 / A5.

Two layers (matching JSON-LD and sitemap modules):

* Pure-formatter tests — synthetic Reviews into the ``build_*``
  functions, then parse the resulting XML and pin the OAI-PMH /
  Dublin Core structure.
* Real-corpus integration — walk a few real reviews through the full
  ``write_oai_pmh`` driver and verify the snapshot files parse.

Because OAI-PMH XML uses three namespaces (OAI-PMH, oai_dc, dc), tests
use full namespaced ElementTree queries to avoid false positives from
substring matching.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from src.model.review import (
    Author,
    Editor,
    Person,
    RelatedItem,
    Review,
)
from src.render.oai_pmh import (
    EARLIEST_DATESTAMP,
    REPOSITORY_NAME,
    _datestamp_or_default,
    build_get_record,
    build_identify,
    build_list_identifiers,
    build_list_metadata_formats,
    build_list_records,
    oai_identifier,
    write_oai_pmh,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO_ROOT.parent / "ride" / "tei_all"

NS = {
    "oai": "http://www.openarchives.org/OAI/2.0/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/",
}


def _r(**overrides) -> Review:
    base = dict(
        id="ride.13.7",
        issue="13",
        title="A Test Review",
        publication_date="2024-06-01",
        language="en",
        licence="http://creativecommons.org/licenses/by/4.0/",
    )
    base.update(overrides)
    return Review(**base)


# ── Identifier scheme ────────────────────────────────────────────────


def test_oai_identifier_uses_repo_host_and_review_id():
    review = _r(id="ride.13.7")
    assert oai_identifier(review) == "oai:ride.i-d-e.de:ride.13.7"


# ── Identify ─────────────────────────────────────────────────────────


def test_identify_emits_required_repository_fields():
    xml = build_identify("https://x.de", build_date="2024-08-01")
    root = ET.fromstring(xml)
    identify = root.find("oai:Identify", NS)
    assert identify is not None
    assert identify.find("oai:repositoryName", NS).text == REPOSITORY_NAME
    assert identify.find("oai:baseURL", NS).text == "https://x.de/oai/"
    assert identify.find("oai:protocolVersion", NS).text == "2.0"
    assert identify.find("oai:granularity", NS).text == "YYYY-MM-DD"
    assert identify.find("oai:deletedRecord", NS).text == "no"
    assert identify.find("oai:earliestDatestamp", NS).text == EARLIEST_DATESTAMP


def test_identify_response_envelope_carries_request_verb():
    xml = build_identify("https://x.de", build_date="2024-08-01")
    root = ET.fromstring(xml)
    request = root.find("oai:request", NS)
    assert request.attrib["verb"] == "Identify"


# ── ListMetadataFormats ─────────────────────────────────────────────


def test_list_metadata_formats_advertises_oai_dc_only():
    xml = build_list_metadata_formats("https://x.de", build_date="2024-08-01")
    root = ET.fromstring(xml)
    formats = root.findall("oai:ListMetadataFormats/oai:metadataFormat", NS)
    assert len(formats) == 1
    [fmt] = formats
    assert fmt.find("oai:metadataPrefix", NS).text == "oai_dc"


# ── ListIdentifiers ─────────────────────────────────────────────────


def test_list_identifiers_emits_one_header_per_review():
    reviews = [_r(id="ride.13.1"), _r(id="ride.13.2")]
    xml = build_list_identifiers(reviews, "https://x.de", build_date="2024-08-01")
    root = ET.fromstring(xml)
    headers = root.findall("oai:ListIdentifiers/oai:header", NS)
    assert len(headers) == 2
    ids = [h.find("oai:identifier", NS).text for h in headers]
    assert ids == ["oai:ride.i-d-e.de:ride.13.1", "oai:ride.i-d-e.de:ride.13.2"]


# ── ListRecords / GetRecord ─────────────────────────────────────────


def test_list_records_emits_dublin_core_record_per_review():
    review = _r(
        id="ride.13.7",
        title="A Test Review",
        keywords=("digital editions", "TEI"),
        authors=(Author(person=Person(full_name="Jane Doe")),),
        editors=(Editor(person=Person(full_name="E. Editor")),),
    )
    xml = build_list_records([review], "https://x.de", build_date="2024-08-01")
    root = ET.fromstring(xml)
    records = root.findall("oai:ListRecords/oai:record", NS)
    assert len(records) == 1
    [record] = records

    # Header
    assert (
        record.find("oai:header/oai:identifier", NS).text
        == "oai:ride.i-d-e.de:ride.13.7"
    )
    assert record.find("oai:header/oai:datestamp", NS).text == "2024-06-01"

    # Dublin Core core fields
    dc = record.find("oai:metadata/oai_dc:dc", NS)
    assert dc.find("dc:title", NS).text == "A Test Review"
    assert [c.text for c in dc.findall("dc:creator", NS)] == ["Jane Doe"]
    assert [c.text for c in dc.findall("dc:contributor", NS)] == ["E. Editor"]
    assert dc.find("dc:date", NS).text == "2024-06-01"
    assert dc.find("dc:language", NS).text == "en"
    assert dc.find("dc:rights", NS).text.startswith("http://")
    assert dc.find("dc:identifier", NS).text == "https://x.de/issues/13/ride.13.7/"
    assert sorted(s.text for s in dc.findall("dc:subject", NS)) == [
        "TEI",
        "digital editions",
    ]
    assert dc.find("dc:type", NS).text == "article"
    assert dc.find("dc:source", NS).text == "RIDE Issue 13"


def test_dc_identifier_emits_doi_first_then_page_url():
    """When a DOI is set, two <dc:identifier> elements are emitted: the
    DOI as ``https://doi.org/{doi}`` first (persistent), the page URL
    second (mutable). Order matters for DC harvesters that take the
    first identifier as canonical."""
    review = _r(doi="10.18716/ride.a.5.4")
    xml = build_get_record(review, "https://x.de", build_date="2024-08-01")
    root = ET.fromstring(xml)
    dc = root.find("oai:GetRecord/oai:record/oai:metadata/oai_dc:dc", NS)
    identifiers = [el.text for el in dc.findall("dc:identifier", NS)]
    assert identifiers == [
        "https://doi.org/10.18716/ride.a.5.4",
        "https://x.de/issues/13/ride.13.7/",
    ]


def test_dc_identifier_without_doi_emits_only_page_url():
    """Reviews without a DOI fall back to a single page-URL identifier —
    heutiges Verhalten bleibt rückwärtskompatibel."""
    xml = build_get_record(_r(), "https://x.de", build_date="2024-08-01")
    root = ET.fromstring(xml)
    dc = root.find("oai:GetRecord/oai:record/oai:metadata/oai_dc:dc", NS)
    identifiers = [el.text for el in dc.findall("dc:identifier", NS)]
    assert identifiers == ["https://x.de/issues/13/ride.13.7/"]


def test_reviewed_resource_targets_become_dc_relation():
    review = _r(
        related_items=(
            RelatedItem(
                type="reviewed_resource",
                bibl_text="Some Edition",
                bibl_targets=("https://example.org/edition", "https://doi.org/10.x/y"),
            ),
            RelatedItem(
                type="reviewing_criteria",
                bibl_text="Criteria",
                bibl_targets=("https://example.org/criteria",),
            ),
        ),
    )
    xml = build_list_records([review], "https://x.de", build_date="2024-08-01")
    root = ET.fromstring(xml)
    relations = [
        r.text
        for r in root.findall("oai:ListRecords/oai:record/oai:metadata/oai_dc:dc/dc:relation", NS)
    ]
    # Both reviewed_resource targets land; criteria is filtered out.
    assert relations == ["https://example.org/edition", "https://doi.org/10.x/y"]


def test_get_record_wraps_a_single_record():
    xml = build_get_record(_r(), "https://x.de", build_date="2024-08-01")
    root = ET.fromstring(xml)
    records = root.findall("oai:GetRecord/oai:record", NS)
    assert len(records) == 1


def test_special_characters_in_title_are_escaped():
    review = _r(title='Edition <of> "Beowulf" & Co.')
    xml = build_get_record(review, "https://x.de", build_date="2024-08-01")
    root = ET.fromstring(xml)  # raises if the escape leaked
    assert (
        root.find("oai:GetRecord/oai:record/oai:metadata/oai_dc:dc/dc:title", NS).text
        == 'Edition <of> "Beowulf" & Co.'
    )


# ── Datestamp normalisation ─────────────────────────────────────────


def test_datestamp_year_only_widens_to_first_of_january():
    assert _datestamp_or_default("2017") == "2017-01-01"


def test_datestamp_year_month_widens_to_first_of_month():
    assert _datestamp_or_default("2017-02") == "2017-02-01"


def test_datestamp_year_month_day_passes_through():
    assert _datestamp_or_default("2017-02-15") == "2017-02-15"


def test_datestamp_freeform_falls_back_to_earliest():
    assert _datestamp_or_default("forthcoming") == EARLIEST_DATESTAMP


def test_datestamp_iso_with_time_strips_time():
    assert _datestamp_or_default("2017-02-15T12:00:00Z") == "2017-02-15"


# ── write_oai_pmh driver ────────────────────────────────────────────


def test_write_requires_absolute_base_url(tmp_path):
    with pytest.raises(ValueError):
        write_oai_pmh([], base_url="", out_root=tmp_path)


def test_write_produces_all_verbs(tmp_path):
    reviews = [_r(id="ride.13.1"), _r(id="ride.13.2")]
    written = write_oai_pmh(
        reviews, base_url="https://x.de", out_root=tmp_path, build_date="2024-08-01"
    )
    # 4 verb files + one record per review
    assert written == 4 + 2

    oai_dir = tmp_path / "oai"
    for name in (
        "identify.xml",
        "list-metadata-formats.xml",
        "list-identifiers.xml",
        "list-records.xml",
    ):
        assert (oai_dir / name).exists(), f"{name} missing"
    assert (oai_dir / "records" / "ride.13.1.xml").exists()
    assert (oai_dir / "records" / "ride.13.2.xml").exists()

    # Every file is well-formed XML.
    for path in oai_dir.rglob("*.xml"):
        ET.parse(path)


def test_write_skips_review_with_empty_id(tmp_path):
    review = Review(
        id="",
        issue="13",
        title="Anonymous fragment",
        publication_date="2024-06-01",
        language="en",
        licence="http://creativecommons.org/licenses/by/4.0/",
    )
    written = write_oai_pmh(
        [review], base_url="https://x.de", out_root=tmp_path, build_date="2024-08-01"
    )
    # 4 verb files + 0 per-record files
    assert written == 4
    records_dir = tmp_path / "oai" / "records"
    assert list(records_dir.iterdir()) == []


# ── Real-corpus integration ─────────────────────────────────────────


@pytest.mark.skipif(not CORPUS_DIR.exists(), reason="../ride/ corpus not checked out")
def test_real_corpus_oai_snapshot_is_well_formed(tmp_path):
    """Walk the first 10 reviews through the full driver and verify XML.

    The snapshot must be parseable by an OAI-PMH harvester; ElementTree
    parsing is the cheapest proxy for that. Per-review ``<dc:title>``
    must round-trip the actual title.
    """
    from src.parser.review import parse_review

    reviews = [
        parse_review(p) for p in sorted(CORPUS_DIR.glob("*.xml"))[:10]
    ]
    written = write_oai_pmh(
        reviews,
        base_url="https://ride.i-d-e.de",
        out_root=tmp_path,
        build_date="2024-08-01",
    )
    assert written == 4 + len(reviews)

    # Spot-check one record file for the round-tripped title.
    record_path = tmp_path / "oai" / "records" / f"{reviews[0].id}.xml"
    root = ET.parse(record_path).getroot()
    title = root.find(
        "oai:GetRecord/oai:record/oai:metadata/oai_dc:dc/dc:title", NS
    ).text
    assert title == reviews[0].title

    # Welle 1.B/C: DOI surfaces as the first dc:identifier when present.
    identifiers = [
        el.text
        for el in root.findall(
            "oai:GetRecord/oai:record/oai:metadata/oai_dc:dc/dc:identifier", NS
        )
    ]
    if reviews[0].doi:
        assert identifiers[0] == f"https://doi.org/{reviews[0].doi}"
