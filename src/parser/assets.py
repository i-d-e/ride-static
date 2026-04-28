"""Asset pipeline — copies figure images from the corpus to the site
output and rewrites :attr:`src.model.block.Figure.graphic_url` to the
deployed, site-root-relative URL.

The corpus stores figure URLs in the original WordPress form that the
old eXist-based site served:

* ``http(s)://ride.i-d-e.de/wp-content/uploads/issue_{N}/{slug}/pictures/{filename}``

The new static site serves them under the URL scheme defined in
``docs/url-scheme.md``:

* ``/issues/{N}/{review_id}/figures/{filename}``

The on-disk source is in the sibling corpus repo:

* ``{ride_root}/issues/issue{NN:02d}/{slug}/pictures/{filename}``

(zero-padded issue dir on disk vs. unpadded ``issue_N`` in the URL).

A figure whose source file is missing on disk leaves the original
``graphic_url`` untouched and is reported via :class:`AssetReport`.
The build CLI logs the report; nothing here raises.

Module placement note. The Workplan offered ``src/build/assets.py``
as a sibling to the Frontend's ``src/build.py`` — but a directory
``src/build/`` cannot coexist with the file ``src/build.py`` in
Python's import system. ``src/parser/assets.py`` keeps the module
inside the Backend's owned tree without colliding.
"""
from __future__ import annotations

import dataclasses
import re
import shutil
from pathlib import Path
from typing import Optional

from src.model.block import (
    Block,
    Citation,
    Figure,
    List as ListBlock,
    ListItem,
    Paragraph,
    Table,
    TableCell,
    TableRow,
)
from src.model.review import Review
from src.model.section import Section
from src.parser.aggregate import collect_figures, collect_notes


# Matches the canonical RIDE figure URL from anywhere in the string. The
# match is anchored to the ``wp-content/uploads/issue_N/slug/pictures/file``
# segment, so leading scheme/host (and the lone ``//wp-content`` typo in
# godwin-tei) all parse the same way.
_URL_PATTERN = re.compile(
    r"wp-content/uploads/issue_(\d+)/([^/]+)/pictures/([^/]+)"
)


@dataclasses.dataclass(frozen=True)
class AssetReport:
    """Outcome of rewriting one review's figure assets.

    Frontend-/CLI-consumed: the build prints the report and aggregates
    counts across all reviews. Phase 13 will surface the per-review
    missing list as a build warning.
    """

    review_id: str
    copied: tuple[Path, ...]
    """Destination paths of files that were copied (relative to ``site_root``)."""
    missing: tuple[str, ...]
    """Raw graphic URLs whose source file was not found on disk."""
    unparseable: tuple[str, ...]
    """Raw graphic URLs that did not match the canonical RIDE URL pattern."""


def rewrite_figure_assets(
    review: Review,
    ride_root: Path,
    site_root: Path,
    *,
    copy: bool = True,
) -> tuple[Review, AssetReport]:
    """Copy figure images for ``review`` into ``site_root`` and return a
    new ``Review`` with rewritten URLs plus an :class:`AssetReport`.

    Parameters
    ----------
    review : Review
        The fully-parsed review.
    ride_root : Path
        Path to the corpus repo (``../ride/``). Sources are read from
        ``ride_root/issues/issue{NN:02d}/{slug}/pictures/...``.
    site_root : Path
        Path to the site output (``site/``). Destinations are written
        under ``site_root/issues/{N}/{review_id}/figures/...``.
    copy : bool, default True
        When False, only the URL rewrite happens — useful for
        tests that want to validate URL form without filesystem
        side effects.
    """
    copied: list[Path] = []
    missing: list[str] = []
    unparseable: list[str] = []
    rewritten_urls: dict[str, str] = {}

    for fig in review.figures:
        src_url = fig.graphic_url
        if not src_url:
            continue
        parsed = _parse_url(src_url)
        if parsed is None:
            unparseable.append(src_url)
            continue
        issue_n, slug, filename = parsed
        src_path = (
            ride_root / "issues" / f"issue{int(issue_n):02d}" / slug / "pictures" / filename
        )
        if not src_path.is_file():
            missing.append(src_url)
            continue
        rel_dst = Path("issues") / review.issue / review.id / "figures" / filename
        if copy:
            dst_path = site_root / rel_dst
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dst_path)
        # "copied" tracks files whose source existed and whose URL would
        # be rewritten — the report stays meaningful in copy=False mode
        # too, so test runs and dry-runs can inspect the outcome without
        # duplicating ~800 images on disk.
        copied.append(rel_dst)
        rewritten_urls[src_url] = "/" + rel_dst.as_posix()

    new_review = _rewrite_urls(review, rewritten_urls)
    report = AssetReport(
        review_id=review.id,
        copied=tuple(copied),
        missing=tuple(missing),
        unparseable=tuple(unparseable),
    )
    return new_review, report


def _parse_url(url: str) -> Optional[tuple[str, str, str]]:
    m = _URL_PATTERN.search(url)
    if m is None:
        return None
    return m.group(1), m.group(2), m.group(3)


# ---------- URL-rewrite walker --------------------------------------------
#
# Same pattern as the ref-resolver: rebuild the section tree with new
# Figure instances, then re-aggregate so the ``Review.figures`` view
# stays identity-equal to the in-tree counterparts.


def _rewrite_urls(review: Review, mapping: dict[str, str]) -> Review:
    if not mapping:
        return review
    new_front = tuple(_walk_section(s, mapping) for s in review.front)
    new_body = tuple(_walk_section(s, mapping) for s in review.body)
    new_back = tuple(_walk_section(s, mapping) for s in review.back)
    all_sections = new_front + new_body + new_back
    return dataclasses.replace(
        review,
        front=new_front,
        body=new_body,
        back=new_back,
        figures=collect_figures(all_sections),
        notes=collect_notes(all_sections),
    )


def _walk_section(sec: Section, mapping: dict[str, str]) -> Section:
    return dataclasses.replace(
        sec,
        blocks=tuple(_walk_block(b, mapping) for b in sec.blocks),
        subsections=tuple(_walk_section(s, mapping) for s in sec.subsections),
    )


def _walk_block(block: Block, mapping: dict[str, str]) -> Block:
    if isinstance(block, Figure):
        return _maybe_rewrite_figure(block, mapping)
    if isinstance(block, Paragraph):
        return block
    if isinstance(block, ListBlock):
        return dataclasses.replace(
            block,
            items=tuple(_walk_list_item(i, mapping) for i in block.items),
        )
    if isinstance(block, Table):
        return dataclasses.replace(
            block,
            rows=tuple(
                dataclasses.replace(
                    row,
                    cells=tuple(_walk_table_cell(c, mapping) for c in row.cells),
                )
                for row in block.rows
            ),
        )
    if isinstance(block, Citation):
        return block
    raise TypeError(f"unhandled block kind {type(block).__name__!r}")


def _walk_list_item(item: ListItem, mapping: dict[str, str]) -> ListItem:
    return dataclasses.replace(
        item,
        blocks=tuple(_walk_block(b, mapping) for b in item.blocks),
    )


def _walk_table_cell(cell: TableCell, mapping: dict[str, str]) -> TableCell:
    return dataclasses.replace(
        cell,
        blocks=tuple(_walk_block(b, mapping) for b in cell.blocks),
    )


def _maybe_rewrite_figure(fig: Figure, mapping: dict[str, str]) -> Figure:
    if fig.graphic_url and fig.graphic_url in mapping:
        return dataclasses.replace(fig, graphic_url=mapping[fig.graphic_url])
    return fig
