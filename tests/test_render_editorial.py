"""Tests for src.render.editorial — Markdown editorial pages.

Frontmatter parsing, Markdown rendering, integration with the editorial
template. Real content/ files exist as stubs; tests use synthetic ones
in tmp_path so the assertions stay independent of editorial copy.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.render.editorial import (
    EditorialPage,
    discover_editorials,
    parse_editorial,
    render_editorial,
)


# ── Frontmatter parsing ─────────────────────────────────────────────


def test_parse_editorial_extracts_frontmatter_and_body(tmp_path: Path):
    p = tmp_path / "about.md"
    p.write_text(
        "---\n"
        "title: About Us\n"
        "slug: about\n"
        "language: de\n"
        "last_updated: 2026-04-29\n"
        "---\n"
        "# Heading\n\nBody **markdown**.\n",
        encoding="utf-8",
    )
    page = parse_editorial(p)
    assert page.title == "About Us"
    assert page.slug == "about"
    assert page.language == "de"
    assert page.last_updated == "2026-04-29"
    assert "Body **markdown**" in page.body_md


def test_parse_editorial_raises_when_frontmatter_missing(tmp_path: Path):
    p = tmp_path / "no-fm.md"
    p.write_text("# Just a heading\nNo frontmatter.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="frontmatter"):
        parse_editorial(p)


def test_parse_editorial_defaults_slug_to_filename(tmp_path: Path):
    p = tmp_path / "imprint.md"
    p.write_text("---\ntitle: Imprint\n---\nbody\n", encoding="utf-8")
    page = parse_editorial(p)
    assert page.slug == "imprint"


# ── Render ───────────────────────────────────────────────────────────


def _page(**overrides) -> EditorialPage:
    base = dict(
        slug="about",
        title="About",
        language="en",
        last_updated="2026-04-29",
        body_md="# Heading\n\nA paragraph with *emphasis*.\n",
    )
    base.update(overrides)
    return EditorialPage(**base)


def test_render_editorial_emits_full_page():
    html = render_editorial(_page())
    assert "<!doctype html>" in html
    assert "ride-editorial" in html
    assert "<h1>Heading</h1>" in html
    assert "<em>emphasis</em>" in html
    assert "ride-page--solo" in html
    assert "2026-04-29" in html  # last_updated is shown


def test_render_editorial_omits_last_updated_when_absent():
    html = render_editorial(_page(last_updated=None))
    # The frontmatter date appears nowhere if not provided
    assert "Last updated" not in html


def test_render_editorial_propagates_language():
    html = render_editorial(_page(language="de"))
    assert 'lang="de"' in html


# ── Discovery against the actual content/ tree ──────────────────────


def test_discover_editorials_finds_repo_content_files():
    pages = discover_editorials()
    slugs = {p.slug for p in pages}
    # Stubs added in this commit
    assert "about" in slugs
    assert "imprint" in slugs
    assert "criteria" in slugs
