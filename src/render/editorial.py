"""Editorial page rendering — Phase 9.

Loads Markdown files under ``content/`` with YAML frontmatter, converts
the body to HTML via the ``markdown`` library, and renders the result
through ``templates/html/editorial.html``.

Per requirements.md A3, editorial files are Markdown with frontmatter
maintained directly in the repository. Editors push commits via the
GitHub web UI; the build picks them up on the next workflow run.

Frontmatter is parsed with PyYAML (already a build dependency for the
per-issue config). We avoid `python-frontmatter` to keep the dependency
footprint slim — the parser below is ~20 lines and handles the only
format editors use.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import markdown
import yaml
from jinja2 import Environment

from src.render.html import (
    REPO_ROOT,
    SiteConfig,
    make_env,
    media_path_factory,
    static_path_factory,
)

CONTENT_DIR = REPO_ROOT / "content"

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


@dataclass(frozen=True)
class EditorialPage:
    """A loaded Markdown editorial page with its frontmatter."""

    slug: str
    title: str
    language: str
    last_updated: Optional[str]
    body_md: str


def parse_editorial(path: Path) -> EditorialPage:
    """Read a Markdown file with YAML frontmatter; return its parts."""
    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError(
            f"{path.name}: editorial file must start with --- ... --- frontmatter"
        )
    meta = yaml.safe_load(match.group(1)) or {}
    body = match.group(2)
    last_updated = meta.get("last_updated")
    # PyYAML auto-coerces ISO date strings to datetime.date — stringify so the
    # template prints the canonical ISO form regardless of source.
    if last_updated is not None:
        last_updated = str(last_updated)
    return EditorialPage(
        slug=meta.get("slug") or path.stem,
        title=meta.get("title") or path.stem.title(),
        language=meta.get("language") or "en",
        last_updated=last_updated,
        body_md=body,
    )


CHART_MARKER = "<!-- ride:charts -->"


def render_editorial(
    page: EditorialPage,
    site: Optional[SiteConfig] = None,
    env: Optional[Environment] = None,
    chart_html: str = "",
) -> str:
    """Render one EditorialPage to a full HTML page string.

    ``chart_html`` is a pre-rendered HTML block that replaces the
    ``<!-- ride:charts -->`` marker in the page body. Empty string
    leaves the marker untouched so editors can preview the page
    without the build pipeline; ``content/data-charts.md`` carries
    the marker (see :func:`src.render.charts.render_charts_block`)."""
    site = site or SiteConfig()
    env = env or make_env()

    body_html = markdown.markdown(
        page.body_md,
        extensions=["extra", "sane_lists", "smarty"],
        output_format="html5",
    )
    if chart_html and CHART_MARKER in body_html:
        body_html = body_html.replace(CHART_MARKER, chart_html)

    template = env.get_template("editorial.html")
    return template.render(
        site=site,
        page_lang=page.language,
        page_title=page.title,
        page_url=f"{site.base_url}/{page.slug}/" if site.base_url else None,
        page_description=None,
        og=None,
        json_ld=None,
        static_path=static_path_factory(site.base_url),
        media_path=media_path_factory(site.base_url),
        page_html=body_html,
        last_updated=page.last_updated,
    )


def discover_editorials(content_dir: Path = CONTENT_DIR) -> list[EditorialPage]:
    """Load every top-level ``content/*.md`` file as an EditorialPage.

    Files inside subdirectories (e.g. ``content/home/``) are widgets, not
    standalone editorial pages — those live under :func:`discover_widgets`.
    """
    if not content_dir.exists():
        return []
    return [parse_editorial(p) for p in sorted(content_dir.glob("*.md"))]


@dataclass(frozen=True)
class HomeWidget:
    """A widget block on the homepage, loaded from ``content/home/*.md``.

    Filename prefix (``01-welcome.md``, ``02-news.md``) drives ordering;
    the renderer hands the widgets to the home template in sorted order.
    """

    slug: str
    title: str
    body_html: str
    order: int


def discover_home_widgets(content_dir: Path = CONTENT_DIR) -> list[HomeWidget]:
    """Load every ``content/home/*.md`` file as a HomeWidget."""
    home_dir = content_dir / "home"
    if not home_dir.exists():
        return []
    out: list[HomeWidget] = []
    for path in sorted(home_dir.glob("*.md")):
        page = parse_editorial(path)
        prefix, _, _ = page.slug.partition("-")
        order = int(prefix) if prefix.isdigit() else 999
        body_html = markdown.markdown(
            page.body_md,
            extensions=["extra", "sane_lists", "smarty"],
            output_format="html5",
        )
        out.append(
            HomeWidget(
                slug=page.slug,
                title=page.title,
                body_html=body_html,
                order=order,
            )
        )
    return sorted(out, key=lambda w: (w.order, w.slug))
