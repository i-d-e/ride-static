"""Tests for the OAI-PMH snapshot (``src.render.oai_pmh``, ``oai_formats``).

Contract tests compare the snapshot with responses recorded from the live
endpoint ride.i-d-e.de/apis/oai on 2026-11-10 (``tests/fixtures/oai/``):
the GetRecord answers for ride.4.2 (one author, English), ride.6.2 (two
authors, text collection), ride.4.4 (German) and ride.16.0 (an issue
editorial) in all three formats, plus Identify, ListMetadataFormats and
ListSets. The static records are built from the real TEI of the same
reviews, so parser and mapping are tested together (CLAUDE.md real-corpus
rule). The field contract itself lives in ``scripts/oai_contract.py`` and
names the fields left out on purpose. Datestamp widening is a pure
function and takes synthetic dates.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from lxml import etree

from src._corpus import iter_tei_files
from src.parser.review import parse_review
from src.render.oai_formats import datestamp
from src.render.oai_pmh import (
    PREFIXES,
    build_get_record,
    build_identify,
    build_list,
    build_list_metadata_formats,
    build_list_sets,
    build_static_repository,
    write_oai_pmh,
)
from src.model.review import Review
from tests._shared import needs_corpus

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import oai_contract  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures" / "oai"
BASE = "https://i-d-e.github.io/ride-static"
OAI = {"o": "http://www.openarchives.org/OAI/2.0/"}
RECORDED = ("ride.4.2", "ride.6.2", "ride.4.4", "ride.16.0")


@pytest.fixture(scope="module")
def corpus() -> dict[str, Review]:
    wanted = set(RECORDED)
    out = {}
    for path in iter_tei_files():
        review = parse_review(path)
        if review.id in wanted:
            out[review.id] = review
    if len(out) != len(wanted):
        pytest.skip("recorded reviews not in corpus")
    return out


def _live(name: str) -> etree._Element:
    return etree.parse(str(FIXTURES / name)).getroot()


def _static(xml: str) -> etree._Element:
    return etree.fromstring(xml.encode("utf-8"))


@needs_corpus
@pytest.mark.parametrize("prefix", PREFIXES)
@pytest.mark.parametrize("rid", RECORDED)
def test_record_matches_recorded_live_response(corpus, rid: str, prefix: str) -> None:
    live = oai_contract.records_by_id(_live(f"getrecord-{prefix}-{rid}.xml"))[rid]
    static_xml = build_get_record(corpus[rid], prefix, f"{BASE}/oai/", BASE, "2026-11-10")
    static = oai_contract.records_by_id(_static(static_xml))[rid]
    assert oai_contract.differing_fields(live, static, prefix) == {}


def test_formats_match_live_list_metadata_formats() -> None:
    live = _live("list-metadata-formats.xml")
    static = _static(build_list_metadata_formats(f"{BASE}/oai/"))

    def formats(root):
        return {
            f.findtext("o:metadataPrefix", namespaces=OAI): (
                f.findtext("o:schema", namespaces=OAI),
                f.findtext("o:metadataNamespace", namespaces=OAI),
            )
            for f in root.iterfind(".//o:metadataFormat", OAI)
        }

    assert formats(static) == formats(live)


def test_identify_and_list_sets_match_live() -> None:
    live, static = _live("identify.xml"), _static(build_identify(f"{BASE}/oai/"))
    for tag in ("repositoryName", "protocolVersion", "adminEmail", "earliestDatestamp",
                "deletedRecord", "granularity"):  # fmt: skip
        path = f".//o:Identify/o:{tag}"
        assert static.findtext(path, namespaces=OAI) == live.findtext(path, namespaces=OAI), tag
    live_err = _live("list-sets.xml").find(".//o:error", OAI)
    static_err = _static(build_list_sets(f"{BASE}/oai/")).find(".//o:error", OAI)
    assert static_err.get("code") == live_err.get("code") == "noSetHierarchy"


@needs_corpus
def test_lists_and_static_repository_are_well_formed(corpus) -> None:
    reviews = list(corpus.values())
    for prefix in PREFIXES:
        for verb in ("ListIdentifiers", "ListRecords"):
            root = _static(build_list(verb, reviews, prefix, f"{BASE}/oai/", BASE))
            assert len(oai_contract.records_by_id(root)) in (0, len(reviews))
            assert root.find(f".//o:request[@metadataPrefix='{prefix}']", OAI) is not None
    repo = _static(build_static_repository(reviews, f"{BASE}/oai/", BASE))
    sr = "{http://www.openarchives.org/OAI/2.0/static-repository}"
    assert [b.get("metadataPrefix") for b in repo.iter(f"{sr}ListRecords")] == list(PREFIXES)


@needs_corpus
def test_write_lays_out_every_route(corpus, tmp_path: Path) -> None:
    reviews = list(corpus.values())
    write_oai_pmh(reviews, BASE, tmp_path, "2026-11-10T12:00:00")
    oai = tmp_path / "oai"
    table = json.loads((oai / "routes.json").read_text(encoding="utf-8"))
    for prefix in PREFIXES:
        assert (oai / table["ListRecords"][prefix]).is_file()
        for rid in RECORDED:
            assert (oai / table["GetRecord"][prefix].format(identifier=rid)).is_file()
    assert (oai / "records" / "ride.4.2.xml").is_file()  # earlier oai_dc path
    assert table["identifiers"]["ride.16.0"] == "2023-03-01"


def test_write_requires_absolute_base_url(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        write_oai_pmh([], "", tmp_path)


@pytest.mark.parametrize(
    "date, stamp",
    [("2016", "2016-01-01"), ("2016-06", "2016-06-01"), ("2016-06-22", "2016-06-22")],
)
def test_datestamp_widens_to_day_granularity(date: str, stamp: str) -> None:
    """Pure function: synthetic dates."""
    review = Review(id="x", issue="1", title="t", publication_date=date, language="en", licence="")
    assert datestamp(review) == stamp


@needs_corpus
def test_router_fixture_is_current_build_output(tmp_path: Path) -> None:
    """tests/oai-router.test.mjs runs on a snapshot written by write_oai_pmh;
    regenerate it and compare, so the router is tested against real output."""
    reviews = [
        parse_review(p)
        for p in iter_tei_files()
        if (p.parent.parent.name, p.name)
        in {("4", "digitalthoreau-tei.xml"), ("16", "editorial-tei.xml")}
    ]
    write_oai_pmh(reviews, BASE, tmp_path, "2026-11-10T12:00:00Z")
    fixture = Path(__file__).parent / "fixtures" / "oai-router" / "oai"
    fresh = tmp_path / "oai"
    names = sorted(p.relative_to(fresh).as_posix() for p in fresh.rglob("*") if p.is_file())
    assert names == sorted(
        p.relative_to(fixture).as_posix() for p in fixture.rglob("*") if p.is_file()
    )
    for name in names:
        assert (fresh / name).read_text(encoding="utf-8") == (fixture / name).read_text(
            encoding="utf-8"
        ), name
