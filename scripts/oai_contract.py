"""Field contract between the live OAI-PMH endpoint and the static snapshot.

Used by ``scripts/parity.py`` (every record of every format) and by
``tests/test_render_oai_pmh.py`` (recorded live responses). A record is
reduced to the fields a harvester relies on; values are normalised with
the same token folding as the page comparison, so typography and element
order do not count while a different name, code or identifier does.

Fields deliberately outside the contract: the page URL (the live endpoint
prints the WordPress address, the snapshot the current one), MARC 005/008
(build dates), affiliation strings (the TEI gained ROR and GeoNames
references after the live records were last generated) and the abstract
beyond its first words (the live MARC field is cut at a thousand characters).
"""

from __future__ import annotations

import re
import unicodedata

from lxml import etree

NS = {
    "o": "http://www.openarchives.org/OAI/2.0/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "marc": "http://www.loc.gov/MARC21/slim",
    "d": "https://doaj.org/static/doaj/doajArticles",
}
XSI_TYPE = "{http://www.w3.org/2001/XMLSchema-instance}type"


def _norm(text: str | None) -> str:
    folded = unicodedata.normalize("NFKC", text or "").casefold()
    return " ".join(re.findall(r"\w+", folded))


def _abstract_head(text: str | None, words: int = 25) -> str:
    return " ".join(_norm(text).split()[:words])


def _texts(el: etree._Element, xpath: str) -> list[str]:
    return [_norm("".join(x.itertext())) for x in el.xpath(xpath, namespaces=NS)]


def record_fields(record: etree._Element, prefix: str) -> dict[str, tuple]:
    """Contract fields of one ``<record>`` element of the given format."""
    f: dict[str, tuple] = {
        "identifier": tuple(_texts(record, "./o:header/o:identifier")),
        "datestamp": tuple(_texts(record, "./o:header/o:datestamp")),
    }
    if prefix == "oai_dc":
        dois = [
            _norm(x.text)
            for x in record.xpath(".//dc:identifier", namespaces=NS)
            if (x.get(XSI_TYPE) or "").endswith("DOI")
        ]
        f |= {
            "title": tuple(_texts(record, ".//dc:title")),
            "creator": tuple(_texts(record, ".//dc:creator")),
            "doi": tuple(dois),
            "rights": tuple(_texts(record, ".//dc:rights")),
            "language": tuple(_texts(record, ".//dc:language")),
            "date": tuple(_texts(record, ".//dc:date")),
            "subject": tuple(sorted(_texts(record, ".//dc:subject"))),
            # The live endpoint writes an empty element when there is no abstract.
            "description": tuple(
                h
                for x in record.xpath(".//dc:description", namespaces=NS)
                if (h := _abstract_head(x.text))
            ),
        }
    elif prefix == "oai_marcxml":

        def sub(tag: str, code: str) -> tuple:
            return tuple(
                _texts(record, f".//marc:datafield[@tag='{tag}']/marc:subfield[@code='{code}']")
            )

        f |= {
            "024a": sub("024", "a"),
            "041a": sub("041", "a"),
            "100a": sub("100", "a"),
            "100_0": sub("100", "0"),
            "700a": sub("700", "a"),
            "245a": sub("245", "a"),
            "264c": sub("264", "c"),
            "540u": sub("540", "u"),
            "653a": tuple(sorted(sub("653", "a"))),
            "773g": sub("773", "g"),
            "773x": sub("773", "x"),
            "leader": tuple(_texts(record, ".//marc:leader")),
        }
    elif prefix == "oai_doajxml":
        f |= {
            "language": tuple(_texts(record, ".//d:language")),
            "eissn": tuple(_texts(record, ".//d:eissn")),
            "publicationDate": tuple(_texts(record, ".//d:publicationDate")),
            "volume": tuple(_texts(record, ".//d:volume")),
            "doi": tuple(_texts(record, ".//d:doi")),
            "documentType": tuple(_texts(record, ".//d:documentType")),
            "title": tuple(_texts(record, ".//d:title")),
            "author": tuple(_texts(record, ".//d:author/d:name")),
            "orcid": tuple(_texts(record, ".//d:author/d:orcid_id")),
            "keyword": tuple(sorted(_texts(record, ".//d:keyword"))),
            "abstract": tuple(
                h
                for x in record.xpath(".//d:abstract", namespaces=NS)
                if (h := _abstract_head(x.text))
            ),
        }
    else:
        raise ValueError(f"unknown metadata prefix {prefix!r}")
    return f


def records_by_id(root: etree._Element) -> dict[str, etree._Element]:
    out: dict[str, etree._Element] = {}
    for rec in root.iter(f"{{{NS['o']}}}record"):
        ident = rec.findtext("o:header/o:identifier", namespaces=NS)
        if ident:
            out[ident.strip()] = rec
    return out


def differing_fields(live: etree._Element, static: etree._Element, prefix: str) -> dict:
    """Contract fields whose values differ, as ``{field: (live, static)}``."""
    lf, sf = record_fields(live, prefix), record_fields(static, prefix)
    return {k: (lf[k], sf.get(k)) for k in lf if lf[k] != sf.get(k)}
