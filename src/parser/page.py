"""Parse a ``pages/*.xml`` TEI editorial page into the :class:`Page` model.

Read-only, like the review parser: it walks the validated TEI and builds
frozen domain objects, never the reverse. The header is the reduced
projection defined in ``schema/ride-pages.rng``; the body is mapped block
by block. Inline whitespace inside paragraphs is preserved verbatim;
block-level indentation whitespace is dropped (insignificant).
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import lxml.etree as ET

from src.model.page import (
    BulletList,
    Cell,
    Code,
    CodeBlock,
    Email,
    Hi,
    Lb,
    ListItem,
    Page,
    PageEditor,
    Para,
    PersName,
    Ref,
    Row,
    Section,
    Table,
    Text,
)
from src.render.html import REPO_ROOT

PAGES_DIR = REPO_ROOT / "pages"
TEI_NS = "http://www.tei-c.org/ns/1.0"

_BLOCK_TAGS = {"div", "p", "list", "table", "eg"}


def _local(tag) -> str:
    return ET.QName(tag).localname if isinstance(tag, str) else ""


def _q(name: str) -> str:
    return f"{{{TEI_NS}}}{name}"


def _text(el) -> str:
    return (el.text or "").strip() if el is not None else ""


# ── Inline ────────────────────────────────────────────────────────────


def _parse_inlines(el) -> tuple:
    """Mixed inline content of ``el``, text and tails kept verbatim."""
    out: list = []
    if el.text:
        out.append(Text(el.text))
    for ch in el:
        tag = _local(ch.tag)
        if tag == "ref":
            out.append(Ref(target=ch.get("target", ""), children=_parse_inlines(ch)))
        elif tag == "persName":
            out.append(PersName(name="".join(ch.itertext()), ref=ch.get("ref")))
        elif tag == "email":
            out.append(Email("".join(ch.itertext())))
        elif tag == "code":
            out.append(Code("".join(ch.itertext())))
        elif tag == "hi":
            out.append(Hi(rend=ch.get("rend"), children=_parse_inlines(ch)))
        elif tag == "lb":
            out.append(Lb())
        else:
            # Unknown inline: keep its text so nothing is silently dropped.
            text = "".join(ch.itertext())
            if text:
                out.append(Text(text))
        if ch.tail:
            out.append(Text(ch.tail))
    return tuple(out)


# ── Block ─────────────────────────────────────────────────────────────


def _parse_block(el):
    tag = _local(el.tag)
    if tag == "div":
        head_el = el.find(_q("head"))
        head = _parse_inlines(head_el) if head_el is not None else ()
        # head is not a block tag, so it is excluded by the filter below.
        blocks = tuple(
            b for ch in el if _local(ch.tag) in _BLOCK_TAGS for b in (_parse_block(ch),)
        )
        return Section(head=head, blocks=blocks)
    if tag == "p":
        return Para(inlines=_parse_inlines(el))
    if tag == "list":
        items = tuple(
            ListItem(inlines=_parse_inlines(it))
            for it in el
            if _local(it.tag) == "item"
        )
        return BulletList(items=items)
    if tag == "table":
        rows = tuple(
            Row(
                cells=tuple(
                    Cell(inlines=_parse_inlines(c))
                    for c in r
                    if _local(c.tag) == "cell"
                )
            )
            for r in el
            if _local(r.tag) == "row"
        )
        return Table(rows=rows)
    if tag == "eg":
        # Verbatim example. Drop the indentation the source uses to align the
        # block with the surrounding XML; keep the code's own relative layout.
        raw = "".join(el.itertext())
        return CodeBlock(text=textwrap.dedent(raw).strip("\n"))
    return None


def _parse_blocks(parent) -> tuple:
    return tuple(
        b
        for ch in parent
        if _local(ch.tag) in _BLOCK_TAGS
        for b in (_parse_block(ch),)
        if b is not None
    )


# ── Page ──────────────────────────────────────────────────────────────


def parse_page(path: Path) -> Page:
    """Parse one ``pages/*.xml`` TEI file into a :class:`Page`."""
    root = ET.parse(str(path)).getroot()
    file_desc = root.find(f"{_q('teiHeader')}/{_q('fileDesc')}")

    title = _text(file_desc.find(f"{_q('titleStmt')}/{_q('title')}"))

    source_url = None
    licence = None
    pub = file_desc.find(_q("publicationStmt"))
    if pub is not None:
        for idno in pub.findall(_q("idno")):
            if idno.get("type") == "URI":
                source_url = _text(idno)
        lic = pub.find(f"{_q('availability')}/{_q('licence')}")
        if lic is not None:
            licence = lic.get("target")

    journal_title = None
    editors: list[PageEditor] = []
    series = file_desc.find(_q("seriesStmt"))
    if series is not None:
        journal_title = _text(series.find(_q("title"))) or None
        for ed in series.findall(_q("editor")):
            editors.append(
                PageEditor(name=_text(ed), role=ed.get("role"), ref=ed.get("ref"))
            )

    body = root.find(f"{_q('text')}/{_q('body')}")
    blocks = _parse_blocks(body) if body is not None else ()

    return Page(
        slug=path.stem,
        title=title or path.stem,
        source_url=source_url,
        licence=licence,
        journal_title=journal_title,
        editors=tuple(editors),
        blocks=blocks,
    )


def discover_pages(pages_dir: Path = PAGES_DIR) -> list[Page]:
    """Parse every ``pages/*.xml`` file, sorted by slug."""
    if not pages_dir.exists():
        return []
    return [parse_page(p) for p in sorted(pages_dir.glob("*.xml"))]
