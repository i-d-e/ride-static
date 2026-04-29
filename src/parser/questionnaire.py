"""Parser for the per-review questionnaire (factsheet).

Walks ``<teiHeader>/<encodingDesc>/<classDecl>/<taxonomy>`` and emits
one :class:`~src.model.questionnaire.Questionnaire` per ``<taxonomy>``
element. Within each taxonomy, every ``<category>`` whose ``<catDesc>``
contains a ``<num>`` becomes one
:class:`~src.model.questionnaire.QuestionnaireAnswer`.

The script under ``scripts/taxonomy.py`` aggregates the same data
corpus-wide for the Data page; this module produces the per-review
view consumed by the Factsheet renderer.
"""
from __future__ import annotations

from typing import Optional

from lxml import etree

from src.model.questionnaire import Questionnaire, QuestionnaireAnswer, TaxonomySection
from src.parser.common import NS, TEI_NS, attr


def parse_questionnaires(
    root: Optional[etree._Element],
) -> tuple[Questionnaire, ...]:
    """Walk a TEI ``<TEI>`` root and return one Questionnaire per
    ``<taxonomy>`` found in the header.

    Returns ``()`` when ``root`` is None or no ``<taxonomy>`` elements
    are present. The corpus has 110 ``<taxonomy>`` elements across 107
    reviews — two reviews carry more than one (one per criteria set
    they answer): ``carlyle-addams-tei.xml`` with 2, ``collationtools-tei.xml``
    with 3."""
    if root is None:
        return ()
    taxonomies = root.findall(".//t:teiHeader//t:taxonomy", NS)
    return tuple(_parse_taxonomy(t) for t in taxonomies)


def _parse_taxonomy(tax: etree._Element) -> Questionnaire:
    """Build one Questionnaire from a ``<taxonomy>`` element.

    The corpus convention is two ``<catDesc>`` children per leaf
    category: the first carries the human-readable label ("Yes"/"No"/
    "Not applicable"), the second wraps the ``<num>`` answer marker.
    The parser scans all ``<catDesc>`` children for a num, and only
    collects from leaf categories (those without nested ``<category>``
    children) — non-leaves are sections or questions, not answers,
    and would otherwise inherit a descendant's num via tree walks.
    """
    criteria_url = attr(tax, "xml:base") or ""
    answers: list[QuestionnaireAnswer] = []
    for cat in tax.iter(f"{{{TEI_NS}}}category"):
        xid = attr(cat, "xml:id")
        if not xid:
            continue
        # Only leaf categories carry an answer. Section and question
        # categories have nested <category> children; skip them.
        if cat.find("t:category", NS) is not None:
            continue
        num = _find_num_in_any_catdesc(cat)
        if num is None:
            continue
        value = num.get("value")
        if value is None:
            continue
        answers.append(QuestionnaireAnswer(category_xml_id=xid, value=value))
    return Questionnaire(criteria_url=criteria_url, answers=tuple(answers))


def parse_taxonomy_sections(
    root: Optional[etree._Element],
) -> dict[str, tuple[TaxonomySection, ...]]:
    """Per criteria URL, the top-level sections and their leaf xml:ids.

    The Data-Charts page aggregates answers by top-level section
    (``aims``, ``content``, "Documentation", …); the per-review
    :class:`Questionnaire` only holds flat leaf answers, so the
    renderer needs the structural mapping. This walker visits one
    ``<taxonomy>`` per criteria URL and reads the section structure
    once — every review pointing at the same criteria URL has the
    same tree, so duplicates are skipped.

    The "label" for each top-level section is its first ``<catDesc>``
    text (preferred) or its ``@xml:id``. The text-collections set
    relies on xml:ids (``aims``, ``content``); digital-editions uses
    catDesc headings ("Documentation", "Contents"). One walker handles
    both shapes.
    """
    if root is None:
        return {}
    # Order-preserving merge: for each URL, the first taxonomy seen sets
    # the section ordering; later taxonomies (same URL within the same
    # review — e.g. carlyle-addams-tei.xml carries two, with rev1-* and
    # rev2-* leaves under the same headings) extend the leaf list under
    # matching section labels.
    section_order: dict[str, list[str]] = {}
    leaves: dict[str, dict[str, list[str]]] = {}
    for tax in root.findall(".//t:teiHeader//t:taxonomy", NS):
        url = attr(tax, "xml:base") or ""
        url_leaves = leaves.setdefault(url, {})
        url_order = section_order.setdefault(url, [])
        for top_cat in tax.findall("t:category", NS):
            label = _section_label(top_cat)
            new_leaves = _collect_leaf_ids(top_cat)
            if not new_leaves:
                continue
            if label not in url_leaves:
                url_leaves[label] = []
                url_order.append(label)
            url_leaves[label].extend(new_leaves)
    return {
        url: tuple(
            TaxonomySection(label=label, leaf_xml_ids=tuple(leaves[url][label]))
            for label in section_order[url]
            if leaves[url][label]
        )
        for url in leaves
    }


def _section_label(cat: etree._Element) -> str:
    """Display label for a top-level section: first <catDesc> text, then xml:id."""
    cat_desc = cat.find("t:catDesc", NS)
    if cat_desc is not None:
        text = "".join(cat_desc.itertext()).strip()
        # Strip any residual num-marker text (e.g. trailing "0"/"1") — top-level
        # sections do not carry an answer, but the corpus has occasional
        # whitespace artefacts inside catDesc.
        if text:
            return text
    xid = attr(cat, "xml:id")
    return xid or "(unnamed)"


def _collect_leaf_ids(cat: etree._Element) -> list[str]:
    """All leaf-category xml:ids underneath a top-level section."""
    leaves: list[str] = []
    for sub in cat.iter(f"{{{TEI_NS}}}category"):
        if sub is cat:
            continue
        if sub.find("t:category", NS) is not None:
            continue
        if _find_num_in_any_catdesc(sub) is None:
            continue
        xid = attr(sub, "xml:id")
        if xid:
            leaves.append(xid)
    return leaves


def _find_num_in_any_catdesc(cat: etree._Element) -> Optional[etree._Element]:
    """Return the first ``<num>`` found in any ``<catDesc>`` direct child.

    The corpus uses both single-catDesc form (label and num inside one
    element) and the dominant two-catDesc form (label in the first,
    num in the second). Either layout resolves to the same answer.
    """
    for cat_desc in cat.findall("t:catDesc", NS):
        num = cat_desc.find("t:num", NS)
        if num is not None:
            return num
    return None
