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
def test_default_renders_markdown_not_tei(tmp_path: Path) -> None:
    """Default path ships the Markdown editorials; TEI-only slugs are absent."""
    n = _render_editorials(make_env(), SiteConfig(), tmp_path, parsed=None)
    assert n > 0
    # Markdown-native and rename-origin slugs are present.
    assert _has(tmp_path, "submitting-a-review")
    assert _has(tmp_path, "projects-for-review")
    assert _has(tmp_path, "about")
    # TEI-only slugs do not exist in the default build.
    assert not _has(tmp_path, "writing-guidelines")
    assert not _has(tmp_path, "submission-guidelines")
    assert not _has(tmp_path, "dissemination-discussion")


@needs_sources
def test_tei_mode_renders_tei_with_markdown_fallback(tmp_path: Path) -> None:
    """TEI precedence: all 16 TEI slugs plus the generator-native fallback."""
    n = _render_editorials(make_env(), SiteConfig(), tmp_path, parsed=None, tei_editorials=True)
    # Every TEI page slug is produced.
    for slug in (
        "criteria", "publishing-policy", "writing-guidelines",
        "submission-guidelines", "projects-currently-under-review",
        "suggested-projects-for-review", "dissemination-discussion",
        "contact", "imprint", "team", "editorial", "ethical-code",
        "peer-reviewers", "ride-award", "call-for-reviews", "data",
    ):
        assert _has(tmp_path, slug), f"missing TEI slug: {slug}"
    # Generator-native Markdown pages survive as fallback.
    assert _has(tmp_path, "about")
    assert _has(tmp_path, "data/charts")
    assert _has(tmp_path, "data/questionnaires")
    # 16 TEI + 5 Markdown fallback (about, data/charts, data/questionnaires,
    # projects-for-review, submitting-a-review) = 21.
    assert n == 21


@needs_sources
def test_tei_page_wins_at_shared_slug(tmp_path: Path) -> None:
    """At a slug both sets define, the rendered page is the TEI one."""
    md_root = tmp_path / "md"
    tei_root = tmp_path / "tei"
    _render_editorials(make_env(), SiteConfig(), md_root, parsed=None)
    _render_editorials(make_env(), SiteConfig(), tei_root, parsed=None, tei_editorials=True)
    md_html = (md_root / "criteria" / "index.html").read_text(encoding="utf-8")
    tei_html = (tei_root / "criteria" / "index.html").read_text(encoding="utf-8")
    # The two source sets are different documents (parity audit dacde82);
    # at minimum the rendered bytes differ, proving TEI replaced Markdown.
    assert md_html != tei_html
