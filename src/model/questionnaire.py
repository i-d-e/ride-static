"""Domain types for the per-review questionnaire (factsheet).

Each RIDE review embeds one or more ``<taxonomy>`` elements in its
``<classDecl>``. The taxonomy mirrors a criteria set hosted at the
URL referenced by ``@xml:base``; ``<num value="0"|"1">`` markers
inside the ``<catDesc>`` of leaf categories encode the review's
boolean answers.

The Frontend's Factsheet (``interface.md`` §5) renders the per-criterion
selected leaves; the Data page (``requirements.md`` R9) aggregates
across reviews. Both consumers iterate ``Review.questionnaires``.

The boolean schema admits ``"0"`` and ``"1"``. One corpus occurrence
uses ``value="3"`` (per ``knowledge/data.md``); the model preserves
the raw string so renderers can flag the anomaly rather than coercing
it to an integer and losing the signal.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QuestionnaireAnswer:
    """One ``<num>``-bearing ``<category>`` and its raw answer value.

    ``category_xml_id`` is the leaf category's ``@xml:id`` (e.g.
    ``se002`` for "Yes" under question ``se001``). ``value`` is the
    raw ``@value`` of the ``<num>`` inside that category's
    ``<catDesc>``: canonically ``"0"`` or ``"1"``. The single
    ``"3"`` corpus anomaly is preserved verbatim.
    """

    category_xml_id: str
    value: str


@dataclass(frozen=True)
class Questionnaire:
    """One ``<taxonomy>`` instance from a review's ``<classDecl>``.

    ``criteria_url`` is the ``@xml:base`` value, identifying which
    criteria set this taxonomy mirrors (one of four URLs per
    ``inventory/taxonomy.json``).

    ``answers`` is an ordered tuple of :class:`QuestionnaireAnswer`,
    in document order — i.e. in the order the categories appear in
    the criteria set.
    """

    criteria_url: str
    answers: tuple[QuestionnaireAnswer, ...]
