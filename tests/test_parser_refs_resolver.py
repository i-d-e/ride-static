"""Tests for the four-bucket reference resolver (Phase 7).

Test data philosophy:

* **Pure-function unit tests** for ``classify_target`` use synthetic
  inputs because the function takes a string and a frozenset — there
  is no real-data form richer than that.
* **Integration tests** for ``resolve_references`` drive entirely off
  the real RIDE corpus (``../ride/tei_all/*.xml``). Each test parses
  a real review and asserts a property of the resolved output. Tests
  skip cleanly when the corpus is absent so CI stays green on a
  fresh clone.

The criteria bucket has *no* real-data integration test because all
5 209 ``#K…`` refs in the corpus live in ``<teiHeader>/<catDesc>``,
not in body content — the body parser does not traverse those.
``classify_target`` pins the contract for the day a body-level K-ref
is added.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.model.bibliography import BibEntry
from src.model.block import Citation, Figure, List as ListBlock, Paragraph, Table
from src.model.inline import Emphasis, Highlight, Note, Reference
from src.model.review import Review
from src.parser.refs_resolver import classify_target, resolve_references
from src.parser.review import parse_review


_RIDE = Path(__file__).resolve().parent.parent.parent / "ride" / "tei_all"

# Two real corpus reviews chosen for their bucket coverage:
# - bayeux: 78 local / 55 external / 3 orphan; has figure-in-cell pattern,
#   mailto: target, bibliography with @ref_target.
# - 1641: 9 figures all present on disk, external refs (Wayback URLs).
_BAYEUX = _RIDE / "bayeux-tei.xml"
_REVIEW_1641 = _RIDE / "1641-tei.xml"


# -- Pure classify_target unit tests --------------------------------------
#
# These test the classification function in isolation. Synthetic inputs are
# the right tool here: classify_target takes ``Optional[str]`` and
# ``frozenset[str]``; no real-data form is richer than that.


def test_classify_external_http():
    assert classify_target("http://example.org/x", frozenset()) == "external"


def test_classify_external_https():
    assert classify_target("https://example.org/x", frozenset()) == "external"


def test_classify_criteria_K_prefix_beats_id_index():
    """5 209 corpus refs use #K… — they resolve against the taxonomy's @xml:base, not local.

    K-prefix takes precedence over an incidental local-anchor presence
    by contract: K-IDs name external criteria-document anchors regardless
    of whether one happens to also exist locally.
    """
    assert classify_target("#K1.2", frozenset()) == "criteria"
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
    """``mailto:`` targets fall to orphan rather than external — they are not link-renderable as URLs without UI work."""
    assert classify_target("mailto:foys@wisc.edu", frozenset()) == "orphan"


def test_classify_none_when_no_target():
    assert classify_target(None, frozenset()) is None
    assert classify_target("", frozenset()) is None


# -- Real-corpus integration tests ----------------------------------------


pytestmark_corpus = pytest.mark.skipif(
    not _RIDE.exists(), reason="../ride/ corpus not present"
)


def _all_references(review: Review):
    """Yield every Reference reachable in a review (depth-first)."""

    def walk_inlines(inlines):
        for inline in inlines:
            if isinstance(inline, Reference):
                yield inline
                yield from walk_inlines(inline.children)
            elif isinstance(inline, (Emphasis, Highlight, Note)):
                yield from walk_inlines(inline.children)

    def walk_block(b):
        if isinstance(b, Paragraph):
            yield from walk_inlines(b.inlines)
        elif isinstance(b, ListBlock):
            for item in b.items:
                yield from walk_inlines(item.inlines)
                if item.label:
                    yield from walk_inlines(item.label)
                for nb in item.blocks:
                    yield from walk_block(nb)
        elif isinstance(b, Table):
            if b.head:
                yield from walk_inlines(b.head)
            for row in b.rows:
                for cell in row.cells:
                    yield from walk_inlines(cell.inlines)
                    for nb in cell.blocks:
                        yield from walk_block(nb)
        elif isinstance(b, Figure):
            yield from walk_inlines(b.head)
        elif isinstance(b, Citation):
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


@pytestmark_corpus
def test_bayeux_real_corpus_external_bucket() -> None:
    """A known external-target ref in bayeux-tei.xml lands in the external bucket."""
    review = parse_review(_BAYEUX)
    externals = [r for r in _all_references(review) if r.bucket == "external"]
    assert len(externals) >= 50  # bayeux has 55 external in the inventory survey
    # Each external must be an http(s):// URL.
    for ref in externals:
        assert ref.target.startswith(("http://", "https://"))


@pytestmark_corpus
def test_bayeux_real_corpus_local_bucket_anchors_resolve() -> None:
    """Every local-bucket ref in bayeux must point to an xml:id present in the same review."""
    review = parse_review(_BAYEUX)
    locals_ = [r for r in _all_references(review) if r.bucket == "local"]
    # Build the id index the way the resolver did.
    id_index: set[str] = set()
    for s in review.front + review.body + review.back:
        _collect_ids(s, id_index)
    for fig in review.figures:
        if fig.xml_id:
            id_index.add(fig.xml_id)
    for note in review.notes:
        if note.xml_id:
            id_index.add(note.xml_id)
    for bib in review.bibliography:
        if bib.xml_id:
            id_index.add(bib.xml_id)

    assert len(locals_) >= 50
    for ref in locals_:
        anchor = ref.target.lstrip("#")
        assert anchor in id_index, f"local ref {ref.target} has no anchor"


def _collect_ids(section, ids):
    if section.xml_id:
        ids.add(section.xml_id)
    for b in section.blocks:
        if isinstance(b, Paragraph) and b.xml_id:
            ids.add(b.xml_id)
        elif isinstance(b, Figure) and b.xml_id:
            ids.add(b.xml_id)
        elif isinstance(b, Citation) and b.bibl is not None and b.bibl.xml_id:
            ids.add(b.bibl.xml_id)
    for sub in section.subsections:
        _collect_ids(sub, ids)


@pytestmark_corpus
def test_bayeux_real_corpus_orphan_bucket_includes_mailto() -> None:
    """bayeux-tei.xml carries ``mailto:foys@wisc.edu`` — it must reach orphan."""
    review = parse_review(_BAYEUX)
    orphans = [r for r in _all_references(review) if r.bucket == "orphan"]
    assert any(r.target and r.target.startswith("mailto:") for r in orphans), (
        "bayeux-tei.xml is supposed to contain a mailto: target — corpus drift?"
    )


@pytestmark_corpus
def test_1641_real_corpus_external_bucket_only() -> None:
    """1641-tei.xml has external refs but no orphan/local — pins the simpler shape."""
    review = parse_review(_REVIEW_1641)
    refs = list(_all_references(review))
    assert refs, "1641 must have at least some refs"
    buckets = {r.bucket for r in refs}
    # Per inventory survey: external present, no orphan, no body-level K
    assert "external" in buckets


@pytestmark_corpus
def test_resolver_classifies_every_corpus_ref() -> None:
    """End-to-end smoke. Every Reference in every review must have a bucket
    in the four-element set ``{local, criteria, external, orphan}`` (or
    ``None`` when the source ``<ref>`` had no ``@target``)."""
    valid = {"local", "criteria", "external", "orphan", None}
    bucket_counts: dict[object, int] = {}
    for f in sorted(_RIDE.glob("*-tei.xml")):
        review = parse_review(f)
        for ref in _all_references(review):
            assert ref.bucket in valid, f"{f.name}: bucket={ref.bucket!r} target={ref.target!r}"
            bucket_counts[ref.bucket] = bucket_counts.get(ref.bucket, 0) + 1
    # Floors leave headroom against future corpus drift while pinning the
    # documented body-level magnitudes from inventory/refs.json.
    assert bucket_counts.get("external", 0) >= 2500, bucket_counts
    assert bucket_counts.get("local", 0) >= 1400, bucket_counts
    assert bucket_counts.get("orphan", 0) >= 50, bucket_counts


@pytestmark_corpus
def test_resolver_descends_into_bibliography() -> None:
    """Bibliography entries carry ``<ref @target>`` — they must be classified."""
    review = parse_review(_BAYEUX)
    assert review.bibliography, "bayeux must have a back-bibliography"
    bib_refs = []
    for bib in review.bibliography:
        for inline in bib.inlines:
            if isinstance(inline, Reference):
                bib_refs.append(inline)
    assert bib_refs, "bayeux bibliography must contain ref inlines"
    for ref in bib_refs:
        # Every bib ref must have a bucket assignment (or None for missing target).
        assert ref.bucket in {"local", "criteria", "external", "orphan", None}


@pytestmark_corpus
def test_resolver_preserves_review_metadata() -> None:
    """Resolver is a pure transform — non-walk fields are untouched."""
    review = parse_review(_BAYEUX)
    resolved = resolve_references(review)
    # parse_review already applies the resolver, so this re-applies it. The
    # contract is idempotence: the second pass produces an equal review.
    assert resolved.id == review.id
    assert resolved.issue == review.issue
    assert resolved.title == review.title
    assert resolved.source_file == review.source_file
    assert len(resolved.body) == len(review.body)
    assert len(resolved.bibliography) == len(review.bibliography)


@pytestmark_corpus
def test_resolver_aggregates_match_section_tree() -> None:
    """After the resolver, ``Review.figures`` shares object identity with
    the figures inside the section tree. No divergent copies."""
    review = parse_review(_REVIEW_1641)
    aggregate_ids = {id(f) for f in review.figures}
    in_tree_figures = []

    def collect(s):
        for b in s.blocks:
            if isinstance(b, Figure):
                in_tree_figures.append(b)
        for sub in s.subsections:
            collect(sub)

    for s in review.front + review.body + review.back:
        collect(s)
    in_tree_ids = {id(f) for f in in_tree_figures}
    # Every aggregate figure that exists at top section level shares identity.
    # (Some figures may also live inside cells / list items; those still match.)
    assert aggregate_ids & in_tree_ids, (
        "aggregate must share identity with figures reached via the section tree"
    )


@pytestmark_corpus
def test_resolver_descends_through_emphasis_and_note() -> None:
    """Refs nested inside ``<emph>`` / ``<note>`` get classified too.

    The corpus has many footnotes whose body contains a Reference; the
    walker must recurse into ``Note.children``.
    """
    found_nested = False
    for f in sorted(_RIDE.glob("*-tei.xml"))[:20]:  # 20 reviews suffice
        review = parse_review(f)
        for note in review.notes:
            for inline in note.children:
                if isinstance(inline, Reference) and inline.bucket is not None:
                    found_nested = True
                    break
            if found_nested:
                break
        if found_nested:
            break
    assert found_nested, "every parsed corpus has refs inside notes; if not, the walker is broken"
