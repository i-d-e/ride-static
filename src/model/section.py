"""Section domain type — recursive divs.

A Section is the structural unit between Review.{front,body,back} and the
individual blocks. Schematron (``ride.div-nesting``) caps the depth at 3.
``xml_id`` is synthesised from position when ``<div>`` lacks ``@xml:id``;
``heading`` is None when ``<div>`` has no ``<head>`` (a non-trivial fraction
of the corpus). See ``knowledge/data.md`` for the empirical basis.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.model.block import Block
from src.model.inline import Inline


@dataclass(frozen=True)
class Section:
    """One ``<div>`` in front, body, or back."""

    xml_id: str
    type: Optional[str]
    heading: Optional[tuple[Inline, ...]]
    level: int
    blocks: tuple[Block, ...]
    subsections: tuple["Section", ...]
