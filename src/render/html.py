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

from src.model.block import Paragraph
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
    ``navigation`` carries the resolved top-level entries from
    ``config/navigation.yaml`` (R11.5); empty tuple means the base
    template falls back to a plain header without dropdowns.
    """

    title: str = "RIDE — Reviews in Digital Editions"
    default_language: str = "en"
    base_url: str = ""
    strings: dict = field(default_factory=dict)
    build_info: Optional[BuildInfo] = None
    navigation: tuple = ()


# ── Filters and helpers ───────────────────────────────────────────────


_SLUG_PATTERN = re.compile(r"[^\w\s-]", re.UNICODE)
_DASH_RUN = re.compile(r"[-\s]+")


def slugify(value: str) -> str:
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


def inlines_to_plain_text(seq: Optional[Iterable], *, drop_notes: bool = False) -> str:
    """Flatten an Inline sequence to plain text.

    The HTML renderer uses this for alt-text and meta-description fallbacks
    (``drop_notes=False`` — Note bodies belong in the flattened text).
    JSON-LD and OAI-PMH serialise abstracts and titles for machine consumers
    where Note bodies would only add noise, so they pass ``drop_notes=True``.
    """
    if not seq:
        return ""
    out: list[str] = []
    for i in seq:
        if isinstance(i, Text):
            out.append(i.text)
        elif isinstance(i, Note):
            if not drop_notes:
                out.append(inlines_to_plain_text(i.children, drop_notes=drop_notes))
        elif isinstance(i, (Emphasis, Highlight, Reference)):
            out.append(inlines_to_plain_text(i.children, drop_notes=drop_notes))
        elif isinstance(i, InlineCode):
            out.append(i.text)
    return "".join(out).strip()


# Backwards-compat alias — the original name is referenced in test_render_html.
_inlines_to_text = inlines_to_plain_text


def static_path_factory(base_url: str):
    """Returns a function the template uses to resolve static asset URLs."""
    prefix = base_url.rstrip("/")

    def static_path(rel: str) -> str:
        rel = rel.lstrip("/")
        return f"{prefix}/static/{rel}" if prefix else f"/static/{rel}"

    return static_path


def media_path_factory(base_url: str):
    """Returns a function that prefixes root-absolute media URLs with ``base_url``.

    The asset pipeline (``src.parser.assets.rewrite_figure_assets``) writes
    ``Figure.graphic_url`` as ``/issues/{N}/{review_id}/figures/{file}`` —
    root-absolute. When the site is deployed under a path prefix (e.g.
    ``/ride-static`` on GitHub Pages), templates must concatenate that
    prefix; otherwise the URL passes through. External URLs (``http(s)://``)
    or empty values are returned untouched so unparseable / unrewritten
    figures keep their legacy WordPress link rather than 404.
    """
    prefix = base_url.rstrip("/")

    def media_path(url: Optional[str]) -> str:
        if not url:
            return ""
        if url.startswith(("http://", "https://", "data:")):
            return url
        if url.startswith("/") and prefix:
            return f"{prefix}{url}"
        return url

    return media_path


# ── Citation export ──────────────────────────────────────────────────


_JOURNAL_TITLE = "RIDE — Reviews in Digital Editions"


def _author_name_pair(person) -> tuple[str, str]:
    """(family, given) — falls back to splitting full_name when fields are absent."""
    if person.surname or person.forename:
        return person.surname or "", person.forename or ""
    name = person.full_name or ""
    if "," in name:
        family, _, given = name.partition(",")
        return family.strip(), given.strip()
    parts = name.rsplit(" ", 1)
    if len(parts) == 2:
        return parts[1], parts[0]
    return name, ""


def _bibtex_escape(s: str) -> str:
    """Escape backslash and braces; keep ASCII, leave the rest verbatim.

    The closing-script defence (``</`` → ``<\\/``) protects the embedded
    <script class="ride-cite-data"> block from premature termination.
    """
    if not s:
        return ""
    # Sentinel pass: replace backslash with a placeholder so the brace-escape
    # step does not touch the braces inside ``\textbackslash{}``.
    sentinel = "\x00BIBSLASH\x00"
    out = s.replace("\\", sentinel)
    out = out.replace("{", r"\{").replace("}", r"\}")
    out = out.replace(sentinel, "\\textbackslash{}")
    return out.replace("</", "<\\/")


def to_bibtex(review) -> str:
    """Render one Review as a single-entry BibTeX string.

    Author names go to the BibTeX-canonical ``Family, Given`` form joined by
    ``and``. The title is wrapped in double braces to preserve case in
    BibTeX styles that lower-case titles. Year is sliced from
    ``publication_date`` when ISO-shaped; otherwise omitted.
    """
    authors = " and ".join(
        ", ".join(part for part in _author_name_pair(a.person) if part)
        for a in review.authors
    ) or "Anonymous"
    year = review.publication_date[:4] if review.publication_date and review.publication_date[:4].isdigit() else ""
    title = _bibtex_escape(review.title or "")
    fields = [
        f"  author    = {{{authors}}}",
        f"  title     = {{{{{title}}}}}",
        f"  journal   = {{{_JOURNAL_TITLE}}}",
    ]
    if review.issue:
        fields.append(f"  number    = {{{review.issue}}}")
    if year:
        fields.append(f"  year      = {{{year}}}")
    body = ",\n".join(fields)
    return f"@article{{{review.id or 'review'},\n{body},\n}}"


def to_csl_dict(review) -> dict:
    """Render one Review as a CSL-JSON object (dict — Jinja's tojson serialises).

    Outputs the schema.org-compatible subset most citation managers consume:
    id, type, title, author, container-title, issue, issued.
    """
    authors_csl: list[dict] = []
    for a in review.authors:
        family, given = _author_name_pair(a.person)
        if family or given:
            entry: dict = {}
            if family:
                entry["family"] = family
            if given:
                entry["given"] = given
            authors_csl.append(entry)
        elif a.person.full_name:
            authors_csl.append({"literal": a.person.full_name})

    obj: dict = {
        "id": review.id or "",
        "type": "article-journal",
        "title": review.title or "",
        "container-title": _JOURNAL_TITLE,
    }
    if authors_csl:
        obj["author"] = authors_csl
    if review.issue:
        obj["issue"] = review.issue
    if review.publication_date:
        date_parts = []
        for chunk in review.publication_date[:10].split("-"):
            if chunk.isdigit():
                date_parts.append(int(chunk))
            else:
                break
        if date_parts:
            obj["issued"] = {"date-parts": [date_parts]}
    return obj


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
    env.filters["slugify"] = slugify
    env.filters["obfuscate_mail"] = _obfuscate_mail
    env.filters["inlines_to_text"] = _inlines_to_text
    env.filters["to_bibtex"] = to_bibtex
    env.filters["to_csl_dict"] = to_csl_dict
    return env


# ── Public API ────────────────────────────────────────────────────────


def find_abstract(review: Review) -> Optional[Section]:
    """Return the review's abstract Section, or None.

    The corpus convention places the abstract under ``<front>``: 107 of 107
    reviews carry exactly one front section with ``type="abstract"`` and
    zero body abstracts. ``review.front`` is therefore the primary source;
    ``review.body`` is checked as a defensive fallback. Used by the HTML
    renderer (via :func:`split_abstract`), the JSON-LD serialiser, and
    the OAI-PMH serialiser — keep this single-source so the abstract
    resolution rule cannot drift across renderers.
    """
    for sec in review.front:
        if sec.type == "abstract":
            return sec
    for sec in review.body:
        if sec.type == "abstract":
            return sec
    return None


def split_abstract(review: Review) -> tuple[Optional[Section], tuple[Section, ...]]:
    """HTML-flavour wrapper around :func:`find_abstract` returning ``(abstract, body_rest)``.

    The body is returned unchanged when the abstract sits in front (the
    canonical case); when the abstract is in the body, it is filtered
    out so the renderer does not draw it twice.
    """
    abstract = find_abstract(review)
    if abstract is None or abstract not in review.body:
        return abstract, review.body
    return abstract, tuple(s for s in review.body if s is not abstract)


def abstract_first_paragraph_text(review: Review) -> Optional[str]:
    """Return the abstract's first Paragraph as plain text, or None.

    Convenience wrapper combining :func:`find_abstract` with the
    "first Paragraph block, flattened to text" rule the JSON-LD and
    OAI-PMH serialisers both need. Notes are dropped because the
    machine-consumer use case strips footnote bodies from abstracts.
    """
    section = find_abstract(review)
    if section is None:
        return None
    for block in section.blocks:
        if isinstance(block, Paragraph):
            text = inlines_to_plain_text(block.inlines, drop_notes=True)
            return text or None
    return None


def doi_url(doi: Optional[str]) -> Optional[str]:
    """Wrap a bare DOI ('10.18716/...') in the standard ``https://doi.org`` URL.

    Single source for DOI URL formatting — used by the HTML template
    sidebar/citation, the JSON-LD ``@id``, and the OAI-PMH
    ``dc:identifier``. Returns ``None`` for missing or empty DOIs so
    callers can guard with ``if doi_url(...): ...``.
    """
    if not doi:
        return None
    return f"https://doi.org/{doi}"


def render_review(
    review: Review,
    site: Optional[SiteConfig] = None,
    env: Optional[Environment] = None,
) -> str:
    """Render one Review to a complete HTML page string."""
    from src.render.jsonld import to_jsonld_string

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
        page_description=inlines_to_plain_text(_first_paragraph_inlines(review))[:200] or None,
        og=None,
        json_ld=to_jsonld_string(review, base_url=site.base_url),
        static_path=static_path_factory(site.base_url),
        media_path=media_path_factory(site.base_url),
    )


def _first_paragraph_inlines(review: Review):
    """First Paragraph in the body, used for meta description fallback."""
    for sec in review.body:
        for b in sec.blocks:
            if b.__class__.__name__ == "Paragraph":
                return b.inlines
    return ()
