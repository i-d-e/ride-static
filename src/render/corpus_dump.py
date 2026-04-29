"""Full-corpus JSON dump — Phase 12 R15 / A5.

Serialises every parsed :class:`~src.model.review.Review` into a single
JSON document at ``site/api/corpus.json``. Intended consumers are
offline tools (Zotero, OpenAlex crawlers, researchers running their own
analyses) who want the corpus as one self-contained file rather than
107 individual TEI parses.

The dump format is intentionally a thin transcription of the immutable
domain model: every dataclass becomes an object whose keys mirror the
field names; tuples become arrays; ``None`` stays ``None``. The two
discriminated unions in the model — ``Block`` (Paragraph / List /
Table / Figure / Citation) and ``Inline`` (Text / Emphasis / Highlight
/ Reference / Note / InlineCode) — carry an extra ``__type`` field so
consumers can dispatch without inspecting field names.

Schema version is the constant :data:`VERSION`; bump on any
backwards-incompatible change.
"""
from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from typing import Any, Optional, Sequence

from src.model.block import Citation, Figure, List, Paragraph, Table
from src.model.inline import (
    Emphasis,
    Highlight,
    InlineCode,
    Note,
    Reference,
    Text,
)
from src.model.review import Review


VERSION = 1

# Discriminated-union members get a ``__type`` field so consumers can
# dispatch on it. All other dataclasses have a deterministic shape.
_UNION_TYPES: tuple[type, ...] = (
    Paragraph,
    List,
    Table,
    Figure,
    Citation,
    Text,
    Emphasis,
    Highlight,
    Reference,
    Note,
    InlineCode,
)


def to_corpus_dump(
    reviews: Sequence[Review],
    *,
    base_url: str = "",
    build_date: Optional[str] = None,
) -> dict[str, Any]:
    """Build the full corpus dictionary ready for JSON serialisation.

    ``base_url`` and ``build_date`` are surfaced at the top level so a
    downloaded ``corpus.json`` is self-describing — a consumer who only
    has the file knows which deploy and which build it was generated
    from. Empty values pass through unchanged.
    """
    return {
        "version": VERSION,
        "generated_at": build_date,
        "base_url": base_url,
        "review_count": len(reviews),
        "reviews": [_to_dict(r) for r in reviews],
    }


def to_corpus_dump_string(
    reviews: Sequence[Review],
    *,
    base_url: str = "",
    build_date: Optional[str] = None,
    indent: Optional[int] = 2,
) -> str:
    """Serialise :func:`to_corpus_dump` to a JSON string.

    Default indent is two spaces, matching the project-wide JSON style.
    Pass ``indent=None`` for a compact production dump (smaller transfers).
    """
    return json.dumps(
        to_corpus_dump(reviews, base_url=base_url, build_date=build_date),
        ensure_ascii=False,
        indent=indent,
    )


def _to_dict(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (tuple, list)):
        return [_to_dict(x) for x in obj]
    if is_dataclass(obj):
        out: dict[str, Any] = {}
        if isinstance(obj, _UNION_TYPES):
            out["__type"] = type(obj).__name__
        for f in fields(obj):
            out[f.name] = _to_dict(getattr(obj, f.name))
        return out
    raise TypeError(f"Cannot serialise {type(obj).__name__} to corpus JSON")
