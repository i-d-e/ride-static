"""M3 build-cutover: TEI editorial precedence in _render_editorials.

The build can render editorial pages from two source sets. Default is the
legacy ``content/*.md`` path (what deploys). With ``tei_editorials=True``
the TEI set under ``pages/*.xml`` takes precedence at each slug, and any
Markdown editorial whose slug no TEI page covers stays as a fallback so no
page disappears. This test pins both modes so the cutover cannot regress
and the default cannot start shipping TEI by accident.

Fast: exercises ``_render_editorials`` directly into a tmp dir with no
review corpus (``parsed=None``), so the data/charts marker is left intact
rather than chart-injected.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.build import _render_editorials
from src.render.html import REPO_ROOT, make_env
from src.render.html import SiteConfig

PAGES_DIR = REPO_ROOT / "pages"
CONTENT_DIR = REPO_ROOT / "content"

needs_sources = pytest.mark.skipif(
    not PAGES_DIR.is_dir() or not CONTENT_DIR.is_dir(),
    reason="editorial source sets not present",
)


def _has(out_root: Path, slug: str) -> bool:
    return (out_root / slug / "index.html").is_file()


@needs_sources
def test_default_renders_only_the_generator_native_markdown(tmp_path: Path) -> None:
    """Default (Markdown-only) path ships just the two generator-native data
    views after the editorial-boundary consolidation (2026-07-17); every
    prose page moved to TEI, so no prose slug renders in this mode."""
    n = _render_editorials(make_env(), SiteConfig(), tmp_path, parsed=None)
    assert n == 2
    assert _has(tmp_path, "data/charts")
    assert _has(tmp_path, "data/questionnaires")
    # Prose slugs are TEI-only now and absent from the Markdown-only build.
    assert not _has(tmp_path, "about")
    assert not _has(tmp_path, "reviewers/submitting-a-review")
    assert not _has(tmp_path, "writing-guidelines")


@needs_sources
def test_tei_mode_renders_tei_with_markdown_fallback(tmp_path: Path) -> None:
    """TEI precedence: every TEI slug plus the two generator-native fallbacks.

    The two consolidated twins now live as TEI under reviewers/, so their
    old flat slugs (submission-guidelines, suggested-projects-for-review)
    are gone; the only Markdown fallback left is the two data views."""
    n = _render_editorials(make_env(), SiteConfig(), tmp_path, parsed=None, tei_editorials=True)
    # Every TEI page slug is produced.
    for slug in (
        "criteria", "about", "about/publishing-policy", "writing-guidelines",
        "reviewers/submitting-a-review", "projects-currently-under-review",
        "reviewers/projects-for-review", "dissemination-discussion",
        "about/contact", "imprint", "about/team", "about/editorial",
        "about/ethical-code", "about/peer-reviewers", "reviewers/ride-award",
        "reviewers/call-for-reviews", "data",
    ):
        assert _has(tmp_path, slug), f"missing TEI slug: {slug}"
    # The consolidated twins no longer render at their old flat slugs.
    assert not _has(tmp_path, "submission-guidelines")
    assert not _has(tmp_path, "suggested-projects-for-review")
    # Generator-native Markdown data views survive as fallback.
    assert _has(tmp_path, "data/charts")
    assert _has(tmp_path, "data/questionnaires")
    # 17 TEI + 2 Markdown fallback (data/charts, data/questionnaires) = 19.
    assert n == 19


@needs_sources
def test_tei_twin_wins_at_consolidated_slug(tmp_path: Path) -> None:
    """The consolidated twins render from TEI at the /reviewers/ URL the
    navigation uses, and no Markdown fallback exists at that slug anymore
    (the content/*.md twin was retired, 2026-07-17)."""
    _render_editorials(make_env(), SiteConfig(), tmp_path, parsed=None, tei_editorials=True)
    tei_html = (
        tmp_path / "reviewers" / "submitting-a-review" / "index.html"
    ).read_text(encoding="utf-8")
    # The rich TEI body wins: it carries the Review Submission Checklist head
    # that only the TEI page has.
    assert "Review Submission Checklist" in tei_html
    # Markdown-only mode produces nothing at this slug now.
    md_root = tmp_path / "md"
    _render_editorials(make_env(), SiteConfig(), md_root, parsed=None)
    assert not (md_root / "reviewers" / "submitting-a-review" / "index.html").is_file()
