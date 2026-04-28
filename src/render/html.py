"""HTML rendering — Phase 8 entry point.

Given a parsed Review and a site config, produce the rendered HTML page.
Templates live in ``templates/html/`` and consume only domain objects;
custom Jinja filters provide the few text-shaping helpers that templates
cannot do cleanly themselves.

The Jinja environment is built once per build and reused for every page;
templates auto-escape HTML by default.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

from jinja2 import ChainableUndefined, Environment, FileSystemLoader, select_autoescape

from src.model.inline import Emphasis, Highlight, InlineCode, Note, Reference, Text
from src.model.review import Review
from src.model.section import Section

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = REPO_ROOT / "templates" / "html"


# ── Site configuration ────────────────────────────────────────────────


@dataclass(frozen=True)
class BuildInfo:
    """Per requirements.md N4 — embedded in every page footer."""

    commit: str = "dev"
    commit_short: str = "dev"
    date: str = ""
    corpus_version: str = ""
    schema_version: str = ""


@dataclass(frozen=True)
class SiteConfig:
    """Global site context handed to every template render.

    ``base_url`` is the deploy-time prefix; locally during tests this is
    the empty string so generated paths are relative to ``site/``.
    """

    title: str = "RIDE — Reviews in Digital Editions"
    default_language: str = "en"
    base_url: str = ""
    strings: dict = field(default_factory=dict)
    build_info: Optional[BuildInfo] = None


# ── Filters and helpers ───────────────────────────────────────────────


_SLUG_PATTERN = re.compile(r"[^\w\s-]", re.UNICODE)
_DASH_RUN = re.compile(r"[-\s]+")


def _slugify(value: str) -> str:
    """URL-safe slug. Lossless given alphanumerics, hyphens and whitespace."""
    if not value:
        return ""
    s = _SLUG_PATTERN.sub("", value).strip().lower()
    return _DASH_RUN.sub("-", s)


def _obfuscate_mail(value: str) -> str:
    """Spell ``@`` as ``[at]`` — minimal scraping deterrent per requirements.md R14."""
    if not value:
        return ""
    return value.replace("@", " [at] ").replace(".", " [dot] ")


def _inlines_to_text(seq: Optional[Iterable]) -> str:
    """Flatten an Inline sequence to plain text — used for alt and meta-description fallback."""
    if not seq:
        return ""
    out: list[str] = []
    for i in seq:
        if isinstance(i, Text):
            out.append(i.text)
        elif isinstance(i, (Emphasis, Highlight, Reference, Note)):
            out.append(_inlines_to_text(i.children))
        elif isinstance(i, InlineCode):
            out.append(i.text)
    return "".join(out).strip()


def _static_path_factory(base_url: str):
    """Returns a function the template uses to resolve static asset URLs."""
    prefix = base_url.rstrip("/")

    def static_path(rel: str) -> str:
        rel = rel.lstrip("/")
        return f"{prefix}/static/{rel}" if prefix else f"/static/{rel}"

    return static_path


# ── Environment ───────────────────────────────────────────────────────


def make_env(templates_dir: Path = TEMPLATES_DIR) -> Environment:
    """Build the Jinja environment with our filters and strict undefined."""
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html"]),
        undefined=ChainableUndefined,
        trim_blocks=False,
        lstrip_blocks=False,
    )
    env.filters["slugify"] = _slugify
    env.filters["obfuscate_mail"] = _obfuscate_mail
    env.filters["inlines_to_text"] = _inlines_to_text
    return env


# ── Public API ────────────────────────────────────────────────────────


def split_abstract(review: Review) -> tuple[Optional[Section], tuple[Section, ...]]:
    """Pull the abstract Section out of the review, return (abstract, body_rest).

    The corpus convention places the abstract under ``<front>``: 107 of 107
    reviews carry exactly one front section with ``type="abstract"`` and
    zero body abstracts. ``review.front`` is therefore the primary source.
    The body is checked as a defensive fallback in case a future review
    deviates from the convention (none do today). ``body`` is returned
    unchanged when the abstract is in front.
    """
    for sec in review.front:
        if sec.type == "abstract":
            return sec, review.body
    abstract: Optional[Section] = None
    rest: list[Section] = []
    for sec in review.body:
        if sec.type == "abstract" and abstract is None:
            abstract = sec
        else:
            rest.append(sec)
    return abstract, tuple(rest)


def render_review(
    review: Review,
    site: Optional[SiteConfig] = None,
    env: Optional[Environment] = None,
) -> str:
    """Render one Review to a complete HTML page string."""
    site = site or SiteConfig()
    env = env or make_env()

    abstract, body_sections = split_abstract(review)

    template = env.get_template("review.html")
    return template.render(
        site=site,
        review=review,
        abstract_section=abstract,
        body_sections=body_sections,
        page_lang=review.language or site.default_language,
        page_title=review.title,
        page_url=f"{site.base_url}/issues/{review.issue}/{review.id}/" if site.base_url else None,
        page_description=_inlines_to_text(_first_paragraph_inlines(review))[:200] or None,
        og=None,
        json_ld=None,
        static_path=_static_path_factory(site.base_url),
    )


def _first_paragraph_inlines(review: Review):
    """First Paragraph in the body, used for meta description fallback."""
    for sec in review.body:
        for b in sec.blocks:
            if b.__class__.__name__ == "Paragraph":
                return b.inlines
    return ()
