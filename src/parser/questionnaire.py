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

from src.model.questionnaire import Questionnaire, QuestionnaireAnswer
from src.parser.common import NS, TEI_NS, attr


def parse_questionnaires(
    root: Optional[etree._Element],
) -> tuple[Questionnaire, ...]:
    """Walk a TEI ``<TEI>`` root and return one Questionnaire per
    ``<taxonomy>`` found in the header.

    Returns ``()`` when ``root`` is None or no ``<taxonomy>`` elements
    are present. The corpus has 110 ``<taxonomy>`` elements across 107
    reviews — three reviews carry more than one (one per criteria set
    they answer)."""
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
