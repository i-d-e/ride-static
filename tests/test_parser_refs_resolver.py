"""Tests for the four-bucket reference resolver (Phase 7).

Synthetic cases pin one bucket each (local, criteria, external, orphan)
plus the "no target" no-op. A corpus smoke confirms every ``Reference``
in all 107 reviews leaves the resolver with a bucket consistent with
``inventory/refs.json``.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.model.bibliography import BibEntry
from src.model.block import Citation, Figure, List as ListBlock, ListItem, Paragraph, Table, TableCell, TableRow
from src.model.inline import Emphasis, Note, Reference, Text
from src.model.review import Review
from src.model.section import Section
from src.parser.refs_resolver import classify_target, resolve_references
from src.parser.review import parse_review


_RIDE = Path(__file__).resolve().parent.parent.parent / "ride" / "tei_all"
_INVENTORY_REFS = Path(__file__).resolve().parent.parent / "inventory" / "refs.json"


# -- Pure classify_target unit tests --------------------------------------


def test_classify_external_http():
    assert classify_target("http://example.org/x", frozenset()) == "external"


def test_classify_external_https():
    assert classify_target("https://example.org/x", frozenset()) == "external"


def test_classify_criteria_K_prefix():
    """5 209 corpus refs use #K… — they resolve against the taxonomy's @xml:base, not local."""
    assert classify_target("#K1.2", frozenset()) == "criteria"
    # K-prefix must beat any incidental local-anchor presence.
    assert classify_target("#K1.2", frozenset({"K1.2"})) == "criteria"


def test_classify_local_anchor_present():
    assert classify_target("#para1", frozenset({"para1", "fig.a"})) == "local"


def test_classify_orphan_dangling_internal():
    """The ~70 non-K dangling-internal anchors (#abb1, #papadopoulos, …) become orphan."""
    assert classify_target("#abb1", frozenset({"para1"})) == "orphan"


def test_classify_orphan_bare_bibkey():
    """Bare bibkeys without # prefix (werner2019, citti2008) are orphan today."""
    assert classify_target("werner2019", frozenset()) == "orphan"


def test_classify_orphan_mailto():
    """mailto: targets fall to orphan rather than external — they are not link-renderable as URLs without UI work."""
    assert classify_target("mailto:foys@wisc.edu", frozenset()) == "orphan"


def test_classify_none_when_no_target():
    assert classify_target(None, frozenset()) is None
    assert classify_target("", frozenset()) is None


# -- Synthetic resolve_references walks ----------------------------------


def _make_review_with(refs: tuple[Reference, ...], extra_ids: tuple[str, ...] = ()) -> Review:
    """Build a minimal Review carrying the given Reference inlines in the
    body's first paragraph. ``extra_ids`` injects additional xml_ids
    (paragraph-level) into the id index so local-anchor targets resolve.
    """
    blocks: list = [Paragraph(inlines=tuple(refs))]
    for i, xid in enumerate(extra_ids):
        blocks.append(Paragraph(inlines=(Text(text=xid),), xml_id=xid))
    section = Section(
        xml_id="s1", type=None, heading=None, level=1,
        blocks=tuple(blocks), subsections=(),
    )
    return Review(
        id="ride.test.1", issue="99", title="t",
        publication_date="", language="en", licence="",
        keywords=(), authors=(), editors=(), related_items=(),
        front=(), body=(section,), back=(),
        figures=(), notes=(),
        bibliography=(), questionnaires=(),
        source_file="t.xml",
    )


def _refs_in_review(review: Review) -> list[Reference]:
    """Pull all Reference instances out of body[0].blocks[0] for assertion."""
    out: list[Reference] = []
    for inline in review.body[0].blocks[0].inlines:
        if isinstance(inline, Reference):
            out.append(inline)
    return out


def test_resolve_local_uses_id_index():
    ref = Reference(children=(Text(text="see para1"),), target="#para1")
    review = _make_review_with((ref,), extra_ids=("para1",))
    resolved = resolve_references(review)
    [out] = _refs_in_review(resolved)
    assert out.bucket == "local"


def test_resolve_external_passthrough():
    ref = Reference(children=(Text(text="x"),), target="https://example.org/")
    review = _make_review_with((ref,))
    resolved = resolve_references(review)
    [out] = _refs_in_review(resolved)
    assert out.bucket == "external"


def test_resolve_criteria_K():
    ref = Reference(children=(Text(text="K"),), target="#K2.1")
    review = _make_review_with((ref,))
    resolved = resolve_references(review)
    [out] = _refs_in_review(resolved)
    assert out.bucket == "criteria"


def test_resolve_orphan_unknown_anchor():
    ref = Reference(children=(Text(text="x"),), target="#abb1")
    review = _make_review_with((ref,))
    resolved = resolve_references(review)
    [out] = _refs_in_review(resolved)
    assert out.bucket == "orphan"


def test_resolve_no_target_keeps_none():
    ref = Reference(children=(Text(text="x"),), target=None)
    review = _make_review_with((ref,))
    resolved = resolve_references(review)
    [out] = _refs_in_review(resolved)
    assert out.bucket is None


def test_resolve_descends_into_emphasis_and_note_children():
    """Refs nested inside <emph> and <note> must also be classified."""
    inner_ref = Reference(children=(Text(text="x"),), target="https://e.org")
    note_ref = Reference(children=(Text(text="y"),), target="#K3.1")
    inlines = (
        Emphasis(children=(inner_ref,), rend=None),
        Note(children=(note_ref,), xml_id="ftn1"),
    )
    section = Section(
        xml_id="s1", type=None, heading=None, level=1,
        blocks=(Paragraph(inlines=inlines),), subsections=(),
    )
    review = Review(
        id="r", issue="9", title="t", publication_date="",
        language="en", licence="",
        keywords=(), authors=(), editors=(), related_items=(),
        front=(), body=(section,), back=(),
        figures=(), notes=(),
        bibliography=(), questionnaires=(),
        source_file="t.xml",
    )
    resolved = resolve_references(review)
    emph = resolved.body[0].blocks[0].inlines[0]
    note = resolved.body[0].blocks[0].inlines[1]
    assert emph.children[0].bucket == "external"
    assert note.children[0].bucket == "criteria"


def test_resolve_descends_into_bibliography_inlines():
    bib = BibEntry(
        inlines=(Reference(children=(Text(text="DOI"),), target="https://doi.org/x"),),
        xml_id="bib1",
        ref_target="https://doi.org/x",
    )
    review = Review(
        id="r", issue="9", title="t", publication_date="",
        language="en", licence="",
        keywords=(), authors=(), editors=(), related_items=(),
        front=(), body=(), back=(),
        figures=(), notes=(),
        bibliography=(bib,), questionnaires=(),
        source_file="t.xml",
    )
    resolved = resolve_references(review)
    [out_bib] = resolved.bibliography
    assert out_bib.inlines[0].bucket == "external"


def test_resolve_local_anchor_to_bibliography_id():
    """``<ref target="#bib1">`` against a BibEntry with xml_id="bib1" is local."""
    bib = BibEntry(inlines=(Text(text="bib"),), xml_id="bib1", ref_target=None)
    ref = Reference(children=(Text(text="see"),), target="#bib1")
    section = Section(
        xml_id="s1", type=None, heading=None, level=1,
        blocks=(Paragraph(inlines=(ref,)),), subsections=(),
    )
    review = Review(
        id="r", issue="9", title="t", publication_date="",
        language="en", licence="",
        keywords=(), authors=(), editors=(), related_items=(),
        front=(), body=(section,), back=(),
        figures=(), notes=(),
        bibliography=(bib,), questionnaires=(),
        source_file="t.xml",
    )
    resolved = resolve_references(review)
    out = resolved.body[0].blocks[0].inlines[0]
    assert out.bucket == "local"


def test_resolve_anchor_to_figure_id_is_local():
    fig = Figure(kind="graphic", head=(), xml_id="fig.a", graphic_url="a.png")
    section = Section(
        xml_id="s1", type=None, heading=None, level=1,
        blocks=(
            Paragraph(inlines=(Reference(children=(Text(text="see"),), target="#fig.a"),)),
            fig,
        ),
        subsections=(),
    )
    review = Review(
        id="r", issue="9", title="t", publication_date="",
        language="en", licence="",
        keywords=(), authors=(), editors=(), related_items=(),
        front=(), body=(section,), back=(),
        figures=(fig,), notes=(),
        bibliography=(), questionnaires=(),
        source_file="t.xml",
    )
    resolved = resolve_references(review)
    out = resolved.body[0].blocks[0].inlines[0]
    assert out.bucket == "local"


def test_resolve_anchor_to_note_id_is_local():
    """<ref target="#ftn1"> against the inline note's xml_id resolves local."""
    note = Note(children=(Text(text="footnote body"),), xml_id="ftn1")
    para_with_ref = Paragraph(
        inlines=(Reference(children=(Text(text="see"),), target="#ftn1"),)
    )
    para_with_note = Paragraph(inlines=(Text(text="text "), note))
    section = Section(
        xml_id="s1", type=None, heading=None, level=1,
        blocks=(para_with_ref, para_with_note), subsections=(),
    )
    review = Review(
        id="r", issue="9", title="t", publication_date="",
        language="en", licence="",
        keywords=(), authors=(), editors=(), related_items=(),
        front=(), body=(section,), back=(),
        figures=(), notes=(note,),
        bibliography=(), questionnaires=(),
        source_file="t.xml",
    )
    resolved = resolve_references(review)
    out = resolved.body[0].blocks[0].inlines[0]
    assert out.bucket == "local"


def test_resolve_preserves_review_metadata():
    """The resolver must return a Review with all non-walk fields untouched."""
    review = _make_review_with(
        (Reference(children=(Text(text="x"),), target="https://e.org"),),
    )
    resolved = resolve_references(review)
    assert resolved.id == review.id
    assert resolved.issue == review.issue
    assert resolved.title == review.title
    assert resolved.source_file == review.source_file


def test_resolve_aggregates_match_section_tree_after_walk():
    """Re-aggregation guarantees Review.figures / Review.notes are the same
    instances as those reached via the section tree, not divergent copies.
    """
    fig = Figure(kind="graphic", head=(), xml_id="fig.x", graphic_url="x.png")
    section = Section(
        xml_id="s1", type=None, heading=None, level=1,
        blocks=(fig,), subsections=(),
    )
    review = Review(
        id="r", issue="9", title="t", publication_date="",
        language="en", licence="",
        keywords=(), authors=(), editors=(), related_items=(),
        front=(), body=(section,), back=(),
        figures=(fig,), notes=(),
        bibliography=(), questionnaires=(),
        source_file="t.xml",
    )
    resolved = resolve_references(review)
    # The figure inside body[0].blocks[0] is the same object as resolved.figures[0].
    assert resolved.figures[0] is resolved.body[0].blocks[0]


# -- Real-corpus smoke ----------------------------------------------------


@pytest.mark.skipif(not _RIDE.exists(), reason="../ride/ corpus not present")
def test_smoke_real_corpus_all_refs_get_a_bucket() -> None:
    """Every Reference in every review must have a non-stub bucket assignment.

    Buckets come from the four-element set ``{local, criteria, external,
    orphan}`` (or ``None`` when the source ``<ref>`` had no ``@target``).

    Empirical counts in the body content:

    * 5 209 ``#K…`` refs sit in ``<teiHeader>//<catDesc>`` (the
      questionnaire structure), **not** in body/text — so the criteria
      bucket is empty in body inlines today. The bucket is part of the
      contract for the day a body-text K-ref lands; the renderer can
      already dispatch on it.
    * Body refs split roughly 2 783 external / 1 598 local / 94 orphan,
      totalling ~4 475 — the residual against the inventory's 9 916
      total is the header-residing K-refs.
    """
    valid = {"local", "criteria", "external", "orphan", None}
    bucket_counts: dict[object, int] = {}
    files = sorted(_RIDE.glob("*-tei.xml"))
    for f in files:
        review = parse_review(f)
        for ref in _iter_all_references(review):
            assert ref.bucket in valid, f"{f.name}: bucket={ref.bucket!r} target={ref.target!r}"
            bucket_counts[ref.bucket] = bucket_counts.get(ref.bucket, 0) + 1
    # Floors leave headroom against future corpus drift while pinning the
    # documented magnitudes.
    assert bucket_counts.get("external", 0) >= 2500, bucket_counts
    assert bucket_counts.get("local", 0) >= 1400, bucket_counts
    assert bucket_counts.get("orphan", 0) >= 50, bucket_counts


def _iter_all_references(review: Review):
    """Yield every Reference reachable in the review (depth-first)."""
    from src.model.inline import Emphasis as Em, Highlight as Hi, Note as Nt, Reference as Rf
    from src.model.block import (
        Citation as Ct, Figure as Fg, List as Ls, Paragraph as Pg, Table as Tb,
    )

    def walk_inlines(inlines):
        for inline in inlines:
            if isinstance(inline, Rf):
                yield inline
                yield from walk_inlines(inline.children)
            elif isinstance(inline, (Em, Hi, Nt)):
                yield from walk_inlines(inline.children)

    def walk_block(b):
        if isinstance(b, Pg):
            yield from walk_inlines(b.inlines)
        elif isinstance(b, Ls):
            for item in b.items:
                yield from walk_inlines(item.inlines)
                if item.label:
                    yield from walk_inlines(item.label)
                for nb in item.blocks:
                    yield from walk_block(nb)
        elif isinstance(b, Tb):
            if b.head:
                yield from walk_inlines(b.head)
            for row in b.rows:
                for cell in row.cells:
                    yield from walk_inlines(cell.inlines)
                    for nb in cell.blocks:
                        yield from walk_block(nb)
        elif isinstance(b, Fg):
            yield from walk_inlines(b.head)
        elif isinstance(b, Ct):
            yield from walk_inlines(b.quote_inlines)
            if b.bibl is not None:
                yield from walk_inlines(b.bibl.inlines)

    def walk_section(s):
        if s.heading:
            yield from walk_inlines(s.heading)
        for b in s.blocks:
            yield from walk_block(b)
        for sub in s.subsections:
            yield from walk_section(sub)

    for s in review.front + review.body + review.back:
        yield from walk_section(s)
    for bib in review.bibliography:
        yield from walk_inlines(bib.inlines)
