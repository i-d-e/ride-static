"""Domain types for the back-bibliography of a review.

Each ``<bibl>`` inside ``<listBibl>`` becomes one :class:`BibEntry`. The
RIDE corpus uses ``<bibl>`` as an annotated free-form citation rather
than a highly structured ``<biblStruct>`` — children are mostly inline
embellishments (``<emph>``, ``<ref>``) interleaved with structured
hints (``<respStmt>``, ``<date>``, ``<title>``, ``<editor>``, ``<idno>``).
The model captures the full mixed content as ``inlines`` (so renderers
preserve emphasis and links verbatim) plus the canonical ``ref_target``
for one-click navigation when present.

Citation export (``R2 Rezension zitieren``) is concerned with the review
itself, not its bibliography, so a flatter model is appropriate here.
Phase 7 (ref-resolver) consumes ``ref_target`` for the four-bucket link
classification.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.model.inline import Inline


@dataclass(frozen=True)
class BibEntry:
    """One ``<bibl>`` entry in the back-bibliography.

    ``xml_id`` is the entry's ``@xml:id`` (used for in-page anchor links
    from inline ``<ref target="#bibX">``). ``inlines`` is the full
    mixed-content of the bibl, with structured children's text preserved
    via the inline walker's passthrough rules. ``ref_target`` is the
    ``@target`` of the first ``<ref>`` descendant — typically the
    canonical URL or DOI of the cited resource.
    """

    inlines: tuple[Inline, ...]
    xml_id: Optional[str] = None
    ref_target: Optional[str] = None
