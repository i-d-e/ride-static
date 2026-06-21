"""Render a :class:`Page` (TEI editorial page) to HTML.

Parallel to :func:`src.render.editorial.render_editorial`, but the body
comes from the structured page model rather than Markdown. The page reuses
``templates/html/editorial.html`` (single column, no sidebar): this module
produces the body HTML, the template wraps it.

Heading levels: the page title is an ``<h1>`` (matching the Markdown pages,
whose body opened with ``# Title``), top-level sections are ``<h2>``, each
nesting level one deeper, capped at ``<h6>``.
"""
from __future__ import annotations

import html
from typing import Optional

from jinja2 import Environment

from src.model.page import (
    BulletList,
    Code,
    CodeBlock,
    Email,
    Hi,
    Lb,
    Page,
    Para,
    PersName,
    Ref,
    Section,
    Table,
    Text,
)
from src.render.html import (
    SiteConfig,
    make_env,
    media_path_factory,
    static_path_factory,
)

_HI_TAG = {"italic": "em", "bold": "strong"}


def _esc(s: Optional[str]) -> str:
    """Escape for an attribute value (quotes included)."""
    return html.escape(s or "", quote=True)


def _txt(s: str) -> str:
    """Escape text content (``<``, ``>``, ``&``), quotes left alone."""
    return html.escape(s or "", quote=False)


def _inlines_html(nodes: tuple) -> str:
    out: list[str] = []
    for n in nodes:
        if isinstance(n, Text):
            out.append(_txt(n.value))
        elif isinstance(n, Lb):
            out.append("<br/>")
        elif isinstance(n, Email):
            out.append(f'<span class="ride-email">{_txt(n.value)}</span>')
        elif isinstance(n, PersName):
            name = _txt(n.name)
            if n.ref:
                out.append(f'<a class="ride-persname" href="{_esc(n.ref)}">{name}</a>')
            else:
                out.append(f'<span class="ride-persname">{name}</span>')
        elif isinstance(n, Ref):
            out.append(f'<a href="{_esc(n.target)}">{_inlines_html(n.children)}</a>')
        elif isinstance(n, Code):
            out.append(f"<code>{_txt(n.value)}</code>")
        elif isinstance(n, Hi):
            tag = _HI_TAG.get(n.rend or "", "span")
            out.append(f"<{tag}>{_inlines_html(n.children)}</{tag}>")
    return "".join(out)


def _block_html(block, level: int) -> str:
    if isinstance(block, Section):
        h = min(level, 6)
        head = _inlines_html(block.head)
        inner = "".join(_block_html(b, level + 1) for b in block.blocks)
        return f"<section>\n<h{h}>{head}</h{h}>\n{inner}</section>\n"
    if isinstance(block, Para):
        return f"<p>{_inlines_html(block.inlines)}</p>\n"
    if isinstance(block, BulletList):
        items = "".join(
            f"<li>{_inlines_html(it.inlines)}</li>\n" for it in block.items
        )
        return f"<ul>\n{items}</ul>\n"
    if isinstance(block, Table):
        rows = ""
        for r in block.rows:
            cells = "".join(f"<td>{_inlines_html(c.inlines)}</td>" for c in r.cells)
            rows += f"<tr>{cells}</tr>\n"
        return f"<table>\n{rows}</table>\n"
    if isinstance(block, CodeBlock):
        return f"<pre><code>{_txt(block.text)}</code></pre>\n"
    return ""


def render_page_body(page: Page) -> str:
    """Render the page title and body blocks to an HTML fragment."""
    parts = [f"<h1>{_txt(page.title)}</h1>\n"]
    parts.extend(_block_html(b, 2) for b in page.blocks)
    return "".join(parts)


def render_page(
    page: Page,
    site: Optional[SiteConfig] = None,
    env: Optional[Environment] = None,
) -> str:
    """Render one :class:`Page` to a complete HTML page via editorial.html."""
    site = site or SiteConfig()
    env = env or make_env()
    template = env.get_template("editorial.html")
    return template.render(
        site=site,
        page_lang="en",
        page_title=page.title,
        page_url=f"{site.base_url}/{page.slug}/" if site.base_url else None,
        page_description=None,
        og=None,
        json_ld=None,
        static_path=static_path_factory(site.base_url),
        media_path=media_path_factory(site.base_url),
        page_html=render_page_body(page),
        last_updated=None,
    )
