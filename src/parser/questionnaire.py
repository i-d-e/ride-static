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

from src.model.questionnaire import (
    Questionnaire,
    QuestionnaireAnswer,
    QuestionnaireQuestion,
    TaxonomySection,
)
from src.parser.common import NS, TEI_NS, attr, itertext


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


def parse_questionnaire_questions(
    root: Optional[etree._Element],
) -> tuple[tuple[str, tuple[QuestionnaireQuestion, ...]], ...]:
    """Per ``<taxonomy>``, the question-by-question view for the Factsheet
    full page (R18).

    Returns one ``(criteria_url, questions)`` pair per taxonomy, in
    document order, so a review with several taxonomies yields several
    blocks. ``()`` for missing input. Kept as a standalone walker (rather
    than folded only into :class:`Questionnaire`) so the renderer and tests
    can reach the question structure without re-reading the flat answers.
    """
    if root is None:
        return ()
    taxonomies = root.findall(".//t:teiHeader//t:taxonomy", NS)
    return tuple(
        (attr(t, "xml:base") or "", _parse_questions(t)) for t in taxonomies
    )


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
    return Questionnaire(
        criteria_url=criteria_url,
        answers=tuple(answers),
        questions=_parse_questions(tax),
    )


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


# ── Question-by-question view (R18) ───────────────────────────────────


def _parse_questions(tax: etree._Element) -> tuple[QuestionnaireQuestion, ...]:
    """Walk a ``<taxonomy>`` into one :class:`QuestionnaireQuestion` per
    criterion, carrying section, labels, K-ref and resolved selection.

    The corpus runs two taxonomy shapes. The digital-editions/tools sets
    nest Yes/No option leaves under each question category; the
    text-collections set carries the ``<num>`` directly in a question's
    own ``<catDesc>`` for binary criteria and uses (often label-less)
    option leaves for categorical ones. One walker handles both: a
    question is any category that bears question text or holds option
    leaves, and selection is read from whichever shape applies.
    """
    questions: list[QuestionnaireQuestion] = []
    for top_cat in tax.findall("t:category", NS):
        section_label = _section_label(top_cat)
        for q_cat in _iter_question_categories(top_cat):
            questions.append(_build_question(q_cat, section_label))
    return tuple(questions)


def _iter_question_categories(section: etree._Element):
    """Yield the question-level categories under a top-level section.

    A question category either carries question text in a ``<catDesc>``
    or directly holds option leaves; a leaf option (only a ``<num>`` /
    short label, no nested category) is never a question. Walks one level
    of nesting beyond the immediate children to reach text-collections
    sections that wrap their questions in an extra intermediate category.
    """
    for child in section.findall("t:category", NS):
        if _is_question(child):
            yield child
        elif child.find("t:category", NS) is not None:
            # Intermediate wrapper — descend one level for its questions.
            for grandchild in child.findall("t:category", NS):
                if _is_question(grandchild):
                    yield grandchild


def _is_question(cat: etree._Element) -> bool:
    """A category is a question when it has option-leaf children or carries
    its own answer ``<num>`` alongside descriptive text."""
    has_option_children = any(
        _find_num_in_any_catdesc(sub) is not None
        for sub in cat.findall("t:category", NS)
    )
    has_own_num = _find_num_in_any_catdesc(cat) is not None
    return has_option_children or has_own_num


def _build_question(q_cat: etree._Element, section_label: str) -> QuestionnaireQuestion:
    label, question_text, criteria_ref, criteria_ref_label = _question_texts(q_cat)
    selected: list[str] = []
    anomaly = False

    option_cats = [
        sub
        for sub in q_cat.findall("t:category", NS)
        if _find_num_in_any_catdesc(sub) is not None
    ]
    if option_cats:
        # Nested option leaves (Yes/No or categorical). One label each.
        for opt in option_cats:
            num = _find_num_in_any_catdesc(opt)
            value = num.get("value") if num is not None else None
            if value == "3":
                anomaly = True
                continue
            if value == "1":
                selected.append(_option_label(opt))
    else:
        # Inline-num binary question (text-collections boolean shape).
        num = _find_num_in_any_catdesc(q_cat)
        value = num.get("value") if num is not None else None
        if value == "3":
            anomaly = True
        elif value == "1":
            selected.append("Yes")
        elif value == "0":
            selected.append("No")

    return QuestionnaireQuestion(
        section_label=section_label,
        question_label=label,
        question_text=question_text,
        criteria_ref=criteria_ref,
        criteria_ref_label=criteria_ref_label,
        selected=tuple(selected),
        anomaly=anomaly,
    )


def _question_texts(q_cat: etree._Element) -> tuple[str, str, Optional[str], Optional[str]]:
    """Resolve (short_label, full_text, criteria_ref, criteria_ref_label).

    The descriptive ``<catDesc>`` children of a question (those without a
    ``<num>``) carry the texts. The short-label catDesc holds an optional
    ``<ref @target>`` K-ref; ``criteria_ref`` is its target, ``criteria_ref_label``
    its visible text ("cf. Catalogue 1.2"). The question-text catDesc is the
    longest plain description. Either may be absent; the xml:id is the
    last-resort label.
    """
    descs = [
        cd
        for cd in q_cat.findall("t:catDesc", NS)
        if cd.find("t:num", NS) is None
    ]
    criteria_ref: Optional[str] = None
    criteria_ref_label: Optional[str] = None
    texts: list[str] = []
    for cd in descs:
        ref = cd.find("t:ref", NS)
        if ref is not None and criteria_ref is None:
            criteria_ref = attr(ref, "target")
            criteria_ref_label = "".join(ref.itertext()).strip() or None
        # Label text excludes the K-ref boilerplate ("cf. Catalogue …").
        own = _catdesc_text_without_ref(cd)
        texts.append(own)

    texts = [t for t in texts if t]
    label = texts[0] if texts else (attr(q_cat, "xml:id") or "")
    # The full question text is the longest descriptive catDesc, which is
    # the question prompt in both shapes; falls back to the label.
    question_text = max(texts, key=len) if texts else ""
    if question_text == label and len(texts) > 1:
        question_text = texts[1]
    return label, question_text, criteria_ref, criteria_ref_label


def _catdesc_text_without_ref(cat_desc: etree._Element) -> str:
    """catDesc text with any nested ``<ref>`` content removed."""
    parts: list[str] = []
    if cat_desc.text:
        parts.append(cat_desc.text)
    for child in cat_desc:
        if etree.QName(child).localname == "ref":
            if child.tail:
                parts.append(child.tail)
            continue
        parts.append("".join(child.itertext()))
        if child.tail:
            parts.append(child.tail)
    text = "".join(parts)
    import re

    return re.sub(r"\s+", " ", text).strip()


def _option_label(opt: etree._Element) -> str:
    """Label of a leaf option: its first non-num catDesc text, else the
    suffix of its xml:id (``selection_language`` → "language")."""
    for cd in opt.findall("t:catDesc", NS):
        if cd.find("t:num", NS) is not None:
            continue
        text = _catdesc_text_without_ref(cd)
        if text:
            return text
    xid = attr(opt, "xml:id") or ""
    return xid.rsplit("_", 1)[-1] if xid else "(option)"
