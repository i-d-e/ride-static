"""Tests for the deterministic ODD-to-Relax-NG compiler."""

from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree

from scripts import compile_schema as compiler


TEI_NS = "http://www.tei-c.org/ns/1.0"
SCH_NS = "http://purl.oclc.org/dsdl/schematron"


def _stylesheets_fixture(root: Path, *, version: str = "7.60.0") -> Path:
    paths = (
        "VERSION",
        "lib/saxon10he.jar",
        "odds/odd2odd.xsl",
        "profiles/default/rng/to.xsl",
        "source/p5subset.xml",
    )
    for relative in paths:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(version if relative == "VERSION" else "fixture", encoding="utf-8")
    return root


def test_compiler_rejects_unpinned_stylesheets_version(tmp_path: Path) -> None:
    stylesheets = _stylesheets_fixture(tmp_path / "stylesheets", version="7.59.0")

    with pytest.raises(ValueError, match="expected 7.60.0"):
        compiler._check_stylesheets_version(stylesheets)


def test_generated_rng_normalization_is_deterministic(tmp_path: Path) -> None:
    output = tmp_path / "ride.rng"
    output.write_bytes(b"first  \r\nsecond\t\n")

    compiler._normalize_generated_rng(output)

    assert output.read_bytes() == b"first\nsecond\n"


def test_check_mode_detects_matching_and_stale_schema(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    stylesheets = _stylesheets_fixture(tmp_path / "stylesheets")
    odd = tmp_path / "ride.odd"
    output = tmp_path / "ride.rng"
    odd.write_text("odd", encoding="utf-8")
    output.write_bytes(b"generated schema")

    def fake_run_saxon(**kwargs) -> None:
        kwargs["output"].write_bytes(b"generated schema")

    monkeypatch.setattr(compiler, "_run_saxon", fake_run_saxon)

    assert compiler.compile_schema(
        stylesheets=stylesheets,
        odd=odd,
        output=output,
        check=True,
    )
    output.write_bytes(b"stale schema")
    assert not compiler.compile_schema(
        stylesheets=stylesheets,
        odd=odd,
        output=output,
        check=True,
    )
    assert output.read_bytes() == b"stale schema"


def test_write_mode_replaces_schema_with_generated_bytes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    stylesheets = _stylesheets_fixture(tmp_path / "stylesheets")
    odd = tmp_path / "ride.odd"
    output = tmp_path / "schema" / "ride.rng"
    odd.write_text("odd", encoding="utf-8")

    def fake_run_saxon(**kwargs) -> None:
        kwargs["output"].write_bytes(b"generated schema")

    monkeypatch.setattr(compiler, "_run_saxon", fake_run_saxon)

    assert compiler.compile_schema(stylesheets=stylesheets, odd=odd, output=output)
    assert output.read_bytes() == b"generated schema"
    assert not output.with_suffix(".rng.tmp").exists()


def test_odd_xml_id_constraint_distinguishes_drafts_from_publications() -> None:
    odd = etree.parse(str(compiler.DEFAULT_ODD))
    assertions = odd.xpath(
        "//tei:constraintSpec[@ident='ride.sch-tei']"
        "//sch:rule[@context='tei:TEI/@xml:id']/sch:assert",
        namespaces={"tei": TEI_NS, "sch": SCH_NS},
    )

    assert len(assertions) == 1
    expression = assertions[0].get("test", "")
    assert "revisionDesc/@status = 'draft'" in expression
    assert "^draft\\." in expression
    assert "^ride\\.\\d+\\.\\d+$" in expression


def test_odd_figure_contract_allows_one_optional_accessibility_description() -> None:
    odd = etree.parse(str(compiler.DEFAULT_ODD))
    figure_modules = odd.xpath(
        "//tei:moduleRef[@key='figures']",
        namespaces={"tei": TEI_NS},
    )
    refs = odd.xpath(
        "//tei:elementSpec[@ident='figure']/tei:content/tei:sequence/"
        "tei:elementRef[@key='figDesc']",
        namespaces={"tei": TEI_NS},
    )

    assert len(figure_modules) == 1
    assert "figDesc" in figure_modules[0].get("include", "").split()
    assert len(refs) == 1
    assert refs[0].get("minOccurs") == "0"
    assert refs[0].get("maxOccurs") == "1"
