"""TEI element-coverage lock (corpus → frontend completeness guard).

Companion to the two existing completeness mechanisms:

* ``test_element_mapping`` pins the *review-body* Block/Inline dataclasses
  against ``config/element-mapping.yaml`` — every modelled body kind has a
  template binding.
* ``test_pages_schema`` proves every editorial page satisfies the page
  profile — no page carries a construct outside the grammar.

Neither answers the upstream question: *does every element that actually
occurs in the TEI corpus have a conscious destination?* An element can be
schema-legal yet silently dropped by the parser, the way the reviewed
resource's ``<date type="publication">`` was dropped before it was wired
through. This test closes that blind spot at the element granularity.

It asserts the live corpus element inventory (``pages/*.xml`` plus
``issues/**/*.xml``) is a subset of :data:`KNOWN_ELEMENTS`. Every name there
is classified with a one-word destination: ``surfaced`` (parsed and
rendered), ``passthrough`` (text preserved via ``itertext`` of a parent,
e.g. ``<add>/<subst>`` nested in ``<mod>``), ``header`` (teiHeader
administrative metadata no journal frontend renders), ``placeholder`` (an
empty element such as ``<gloss/>``), ``presentational`` (markup-only).

A new TEI element in a future submission lands outside the set and turns
this test red, forcing a decision — handle it or classify it — instead of
letting unseen content ship invisibly. The classification itself is the
audited record; the pass/fail axis is only "is anything unclassified?".

Provenance of the classification: knowledge/journal.md, TEI-Konsumtions-Audit.

LIMIT this test does *not* cover: attribute-value discrimination. ``<date>``
is ``surfaced``, but which ``@type`` values the parser reads is a finer
question (the publication-date and the ``num/@value=1`` issues both live at
that level). Value-level parity is covered by the per-field parser/render
tests, not here.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest
from lxml import etree

from tests._shared import CORPUS_DIR as ISSUES_DIR, REPO_ROOT

PAGES_DIR = REPO_ROOT / "pages"

needs_corpus = pytest.mark.skipif(
    not ISSUES_DIR.is_dir() and not PAGES_DIR.is_dir(),
    reason="TEI corpus not present",
)

# name -> destination. See module docstring for the destination vocabulary.
KNOWN_ELEMENTS: dict[str, str] = {
    # ── structural document frame ─────────────────────────────────────
    "TEI": "surfaced", "text": "surfaced", "body": "surfaced",
    "front": "header", "back": "surfaced", "div": "surfaced",
    # ── block-level body content ──────────────────────────────────────
    "head": "surfaced", "p": "surfaced", "list": "surfaced",
    "item": "surfaced", "label": "surfaced", "table": "surfaced",
    "row": "surfaced", "cell": "surfaced", "figure": "surfaced",
    "graphic": "surfaced", "quote": "surfaced", "cit": "surfaced",
    "eg": "surfaced", "code": "surfaced",
    # ── inline content ────────────────────────────────────────────────
    "emph": "surfaced", "hi": "surfaced", "ref": "surfaced",
    "note": "surfaced", "lb": "presentational",
    # ── bibliography ──────────────────────────────────────────────────
    "bibl": "surfaced", "biblScope": "surfaced", "listBibl": "surfaced",
    "relatedItem": "surfaced",
    # ── people and responsibility ─────────────────────────────────────
    "persName": "surfaced", "name": "surfaced", "forename": "surfaced",
    "surname": "surfaced", "orgName": "surfaced", "placeName": "surfaced",
    "affiliation": "passthrough", "email": "surfaced", "author": "surfaced",
    "editor": "surfaced", "resp": "surfaced", "respStmt": "surfaced",
    # ── descriptive metadata that is rendered ─────────────────────────
    "title": "surfaced", "date": "surfaced", "idno": "surfaced",
    "term": "surfaced", "keywords": "surfaced", "language": "surfaced",
    "langUsage": "header", "licence": "surfaced", "availability": "surfaced",
    # ── questionnaire taxonomy ────────────────────────────────────────
    "taxonomy": "surfaced", "category": "surfaced", "catDesc": "surfaced",
    "num": "surfaced",
    # ── editorial micro-markup: text preserved via <mod> passthrough ──
    "mod": "passthrough", "del": "passthrough", "add": "passthrough",
    "subst": "passthrough", "seg": "passthrough",
    # ── teiHeader administrative structure, not rendered ──────────────
    "teiHeader": "header", "fileDesc": "header", "titleStmt": "header",
    "publicationStmt": "header", "publisher": "header",
    "seriesStmt": "header", "sourceDesc": "header", "notesStmt": "header",
    "encodingDesc": "header", "classDecl": "header", "profileDesc": "header",
    "textClass": "header", "revisionDesc": "header", "change": "header",
    "listChange": "header",
    # ── empty placeholder elements (no content) ───────────────────────
    "gloss": "placeholder", "desc": "placeholder",
    # ── presentational-only ───────────────────────────────────────────
    "space": "presentational",
}


def _corpus_files() -> list[Path]:
    files: list[Path] = []
    if PAGES_DIR.is_dir():
        files += sorted(PAGES_DIR.glob("*.xml"))
    if ISSUES_DIR.is_dir():
        files += sorted(ISSUES_DIR.rglob("*.xml"))
    return files


def _corpus_elements() -> Counter:
    counts: Counter = Counter()
    for f in _corpus_files():
        try:
            tree = etree.parse(str(f))
        except etree.XMLSyntaxError:
            continue  # validity is test_validate's job, not coverage's
        for el in tree.iter():
            if isinstance(el.tag, str):  # skip comments / PIs
                counts[etree.QName(el.tag).localname] += 1
    return counts


@needs_corpus
def test_every_corpus_element_is_classified() -> None:
    """No TEI element occurs in the corpus without a conscious destination."""
    seen = set(_corpus_elements())
    unclassified = sorted(seen - set(KNOWN_ELEMENTS))
    assert not unclassified, (
        "TEI elements present in the corpus but not classified in "
        "KNOWN_ELEMENTS — a new element may be shipping unseen. Either wire "
        f"it through a parser or classify it: {unclassified}"
    )


def test_destination_vocabulary_is_closed() -> None:
    """Every classification uses one of the five documented destinations."""
    allowed = {"surfaced", "passthrough", "header", "placeholder", "presentational"}
    bad = {k: v for k, v in KNOWN_ELEMENTS.items() if v not in allowed}
    assert not bad, f"unknown destination(s): {bad}"
