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

from src.render.html import REPO_ROOT, SiteConfig, _static_path_factory, make_env

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


def render_editorial(
    page: EditorialPage,
    site: Optional[SiteConfig] = None,
    env: Optional[Environment] = None,
) -> str:
    """Render one EditorialPage to a full HTML page string."""
    site = site or SiteConfig()
    env = env or make_env()

    body_html = markdown.markdown(
        page.body_md,
        extensions=["extra", "sane_lists", "smarty"],
        output_format="html5",
    )

    template = env.get_template("editorial.html")
    return template.render(
        site=site,
        page_lang=page.language,
        page_title=page.title,
        page_url=f"{site.base_url}/{page.slug}/" if site.base_url else None,
        page_description=None,
        og=None,
        json_ld=None,
        static_path=_static_path_factory(site.base_url),
        page_html=body_html,
        last_updated=page.last_updated,
    )


def discover_editorials(content_dir: Path = CONTENT_DIR) -> list[EditorialPage]:
    """Load every ``content/*.md`` file as an EditorialPage."""
    if not content_dir.exists():
        return []
    return [parse_editorial(p) for p in sorted(content_dir.glob("*.md"))]
