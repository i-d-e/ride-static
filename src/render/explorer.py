"""Explorer data dump — the data basis for the interactive ``/data/explore/`` view.

See ``knowledge/exploration.md``. One flat, denormalised row per review feeds
the facet browser (P1), the issue timeline (P3) and the companion views. This
is intentionally distinct from the full corpus dump (``corpus_dump.py``): a
small analysis table of numbers-per-review rather than a complete transcription
of the domain model.

Two load-bearing data rules from the analysis (``knowledge/exploration.md`` §2):

* The criteria **set is a per-review property** — every issue is set-homogeneous.
  The set-internal yes-ratio (``value="1"`` over ``value="0"+"1"``, ``value="3"``
  excluded per ``knowledge/data.md``) is only comparable within one set, so each
  row carries ``set_slug`` and the consumer must keep comparisons set-internal.
* Apparatus counts are right-skewed (``code``/``table`` mostly zero), so the dump
  carries raw counts plus presence flags, never a corpus-wide mean.
"""
from __future__ import annotations

import json
from typing import Any, Optional, Sequence

from src.model.block import Citation, Figure, List, Paragraph, Table
from src.model.inline import InlineCode, Reference, Text
from src.model.review import Review
from src.render.charts import criteria_label, criteria_slug
from src.render.corpus_dump import LICENCE_NAME, LICENCE_URL

VERSION = 1


# ── text-content helpers ──────────────────────────────────────────────


def _block_inline_groups(block: Any):
    """Yield every inline-tuple reachable from a block, recursing into the
    block-level children that ``List``/``Table`` cells may carry."""
    if isinstance(block, Paragraph):
        yield block.inlines
    elif isinstance(block, List):
        for item in block.items:
            yield item.inlines
            if item.label:
                yield item.label
            for sub in item.blocks:
                yield from _block_inline_groups(sub)
    elif isinstance(block, Table):
        if block.head:
            yield block.head
        for row in block.rows:
            for cell in row.cells:
                yield cell.inlines
                for sub in cell.blocks:
                    yield from _block_inline_groups(sub)
    elif isinstance(block, Citation):
        yield block.quote_inlines
    elif isinstance(block, Figure):
        if block.head:
            yield block.head


def _walk_inlines(inlines):
    """Depth-first walk over an inline tuple, descending into ``children``."""
    for inl in inlines:
        yield inl
        children = getattr(inl, "children", None)
        if children:
            yield from _walk_inlines(children)


def _iter_blocks(sections):
    """Every block in a section tree, including nested subsections."""
    for sec in sections:
        for block in sec.blocks:
            yield block
        yield from _iter_blocks(sec.subsections)


def _content_metrics(review: Review) -> dict[str, int]:
    """Characters, paragraphs, inline-code and external-ref counts across
    front+body. Pure measurement, no side effects."""
    chars = 0
    paragraphs = 0
    code = 0
    external_refs = 0
    for block in _iter_blocks(review.front + review.body):
        if isinstance(block, Paragraph):
            paragraphs += 1
        for group in _block_inline_groups(block):
            for inl in _walk_inlines(group):
                if isinstance(inl, (Text, InlineCode)):
                    chars += len(inl.text)
                if isinstance(inl, InlineCode):
                    code += 1
                if isinstance(inl, Reference) and inl.bucket == "external":
                    external_refs += 1
    return {
        "chars": chars,
        "paragraphs": paragraphs,
        "code": code,
        "external_refs": external_refs,
    }


# ── questionnaire helpers ─────────────────────────────────────────────


def _set_and_yes_ratio(review: Review) -> dict[str, Any]:
    """The review's criteria set plus its set-internal yes-ratio.

    Aggregates over every questionnaire answer (issues are set-homogeneous,
    so all answers share one set). ``value="3"`` is excluded from the
    denominator. Returns ``set_slug=None`` for the rare review without a
    questionnaire."""
    yes = 0
    total = 0
    slug: Optional[str] = None
    label: Optional[str] = None
    for q in review.questionnaires:
        if slug is None:
            slug = criteria_slug(q.criteria_url)
            label = criteria_label(q.criteria_url)
        for ans in q.answers:
            if ans.value == "1":
                yes += 1
                total += 1
            elif ans.value == "0":
                total += 1
    return {
        "set_slug": slug,
        "set_label": label,
        "yes": yes,
        "answered": total,
        "yes_pct": round(100.0 * yes / total, 1) if total else None,
    }


# ── reviewed-resource helpers ─────────────────────────────────────────


def _year(value: Optional[str]) -> Optional[int]:
    """Leading four-digit year from a date-ish string, else None."""
    if not value:
        return None
    head = value.strip()[:4]
    return int(head) if head.isdigit() else None


def _resource_fields(review: Review) -> dict[str, Any]:
    """Title, year, age-delta, DOI flag and URI host of the reviewed resource."""
    resource = next(
        (ri for ri in review.related_items if ri.type == "reviewed_resource"),
        None,
    )
    review_year = _year(review.publication_date)
    if resource is None:
        return {
            "resource_title": None,
            "resource_year": None,
            "resource_age": None,
            "resource_has_doi": False,
            "resource_host": None,
        }
    targets = tuple(resource.bibl_targets)
    has_doi = any("doi.org" in t or t.startswith("10.") for t in targets)
    host = None
    for t in targets:
        if t.startswith("http"):
            host = t.split("/")[2] if "/" in t[8:] else t.split("//")[-1]
            break
    res_year = _year(resource.publication_date)
    age = (
        review_year - res_year
        if review_year is not None and res_year is not None
        else None
    )
    return {
        "resource_title": resource.title or (resource.bibl_text or None),
        "resource_year": res_year,
        "resource_age": age,
        "resource_has_doi": has_doi,
        "resource_host": host,
    }


# ── row + dump ────────────────────────────────────────────────────────


def review_row(review: Review, *, base_url: str = "") -> dict[str, Any]:
    """One flat explorer row for a single review."""
    metrics = _content_metrics(review)
    quest = _set_and_yes_ratio(review)
    resource = _resource_fields(review)
    issue = review.issue or "0"
    rid = review.id or (review.source_file or "").replace("-tei.xml", "")
    return {
        "id": rid,
        "issue": issue,
        "title": review.title,
        "year": _year(review.publication_date),
        "date": review.publication_date,
        "language": review.language,
        "url": f"{base_url}/issues/{issue}/{rid}/",
        "set_slug": quest["set_slug"],
        "set_label": quest["set_label"],
        "yes": quest["yes"],
        "answered": quest["answered"],
        "yes_pct": quest["yes_pct"],
        "chars": metrics["chars"],
        "paragraphs": metrics["paragraphs"],
        "figures": len(review.figures),
        "notes": len(review.notes),
        "bibl": len(review.bibliography),
        "code": metrics["code"],
        "code_present": metrics["code"] > 0,
        "external_refs": metrics["external_refs"],
        **resource,
    }


def to_explorer_dump(
    reviews: Sequence[Review],
    *,
    base_url: str = "",
    build_date: Optional[str] = None,
) -> dict[str, Any]:
    """Build the explorer payload: meta block plus one row per review.

    The criteria-set legend lets the client label and colour by set without
    re-deriving the slug→label map.
    """
    rows = [review_row(r, base_url=base_url) for r in reviews]
    set_legend: dict[str, str] = {}
    for row in rows:
        if row["set_slug"] and row["set_slug"] not in set_legend:
            set_legend[row["set_slug"]] = row["set_label"] or row["set_slug"]
    return {
        "version": VERSION,
        "generated_at": build_date,
        "base_url": base_url,
        "licence": {"name": LICENCE_NAME, "url": LICENCE_URL},
        "review_count": len(rows),
        "sets": set_legend,
        "reviews": rows,
    }


def to_explorer_dump_string(
    reviews: Sequence[Review],
    *,
    base_url: str = "",
    build_date: Optional[str] = None,
    indent: Optional[int] = 2,
) -> str:
    """Serialise :func:`to_explorer_dump` to a JSON string (project JSON style)."""
    return json.dumps(
        to_explorer_dump(reviews, base_url=base_url, build_date=build_date),
        ensure_ascii=False,
        indent=indent,
    )
