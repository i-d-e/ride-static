"""JS-Module-Smoketest (Welle 8.C).

Verifies that the four `static/js/*.js` modules referenced from
``base.html`` exist, are non-empty, and that the DOM hooks they
target are actually rendered by the templates. This is a static
contract check — no headless browser, no JS execution. Real end-
to-end behaviour testing belongs in a separate manual UA pass.

The pairs we pin:

* ``copy-link.js`` ↔ ``.ride-paragraph__anchor`` (rendered on every
  numbered paragraph in a Review).
* ``cite-copy.js`` ↔ ``.ride-cite__btn`` plus ``.ride-cite-data``
  (rendered in the Review sidebar Citation box).
* ``clipboard.js`` is the shared copy helper both of the above import;
  it is not referenced from base.html directly.
* ``pagefind.js`` is a Phase 11 stub; existence-only.
* ``explore.js`` is the /data/explore/ view, loaded as an ES module
  with the vendored d3 as a classic script before it.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.parser.review import parse_review
from src.render.html import SiteConfig, make_env, render_review

REPO_ROOT = Path(__file__).resolve().parent.parent
JS_DIR = REPO_ROOT / "static" / "js"
TEMPLATES_DIR = REPO_ROOT / "templates" / "html"
RIDE_TEI_DIR = REPO_ROOT / "issues"

needs_corpus = pytest.mark.skipif(
    not RIDE_TEI_DIR.is_dir(), reason="corpus not present"
)


# -- existence + non-empty ------------------------------------------------


def test_js_modules_exist() -> None:
    """Every JS file referenced in base.html must ship under static/js/."""
    base = (TEMPLATES_DIR / "base.html").read_text(encoding="utf-8")
    for name in ("copy-link.js", "cite-copy.js", "pagefind.js", "nav.js"):
        assert name in base, f"{name} not referenced from base.html"
        assert (JS_DIR / name).exists(), f"{name} missing from static/js/"


def test_tooltip_stub_is_gone() -> None:
    """The tooltip.js no-op stub was removed; base.html no longer loads it."""
    base = (TEMPLATES_DIR / "base.html").read_text(encoding="utf-8")
    assert "tooltip.js" not in base, "base.html still references the removed tooltip.js"
    assert not (JS_DIR / "tooltip.js").exists(), "tooltip.js stub should be deleted"


def test_js_modules_non_empty() -> None:
    for name in ("copy-link.js", "cite-copy.js", "clipboard.js", "pagefind.js", "nav.js"):
        text = (JS_DIR / name).read_text(encoding="utf-8")
        assert text.strip(), f"{name} is empty"


def test_nav_module_targets_dropdown_details() -> None:
    """nav.js is the progressive enhancement over the <details>-based
    dropdowns: opening one closes the others, outside click and Escape
    close all. It must target the details element base.html renders and
    must not replace the native mechanism (no preventDefault on summary)."""
    js = (JS_DIR / "nav.js").read_text(encoding="utf-8")
    assert ".ride-nav__dropdown" in js
    assert "toggle" in js, "nav.js no longer listens to the details toggle event"
    assert "Escape" in js
    assert "preventDefault" not in js, (
        "nav.js must stay additive — native <details> is the no-JS fallback"
    )


def test_clipboard_helper_is_shared() -> None:
    """copy-link.js and cite-copy.js import the shared clipboard helper
    rather than each defining their own ``copyToClipboard`` — the byte-
    identical duplicate was extracted into clipboard.js."""
    clip = (JS_DIR / "clipboard.js").read_text(encoding="utf-8")
    assert "export async function copyToClipboard" in clip
    assert "export const FEEDBACK_MS" in clip
    for name in ("copy-link.js", "cite-copy.js"):
        js = (JS_DIR / name).read_text(encoding="utf-8")
        assert "from './clipboard.js'" in js, f"{name} does not import clipboard.js"
        assert "async function copyToClipboard" not in js, (
            f"{name} still defines its own copyToClipboard"
        )


def test_explore_js_is_es_module() -> None:
    """explore.js is loaded as an ES module with the vendored d3 as a
    classic script before it (window.d3 global), and no longer wraps its
    body in an ES5 IIFE."""
    tmpl = (TEMPLATES_DIR / "explore.html").read_text(encoding="utf-8")
    assert 'type="module" src="{{ static_path(\'js/explore.js\') }}"' in tmpl
    # d3 stays a classic (non-module) script tag.
    assert 'src="{{ static_path(\'js/vendor/d3.v7.min.js\') }}" defer' in tmpl
    js = (JS_DIR / "explore.js").read_text(encoding="utf-8")
    assert "(function ()" not in js and 'var d3 = window.d3' not in js, (
        "explore.js still looks like the ES5 IIFE"
    )
    assert "const d3 = window.d3" in js


# -- module ↔ DOM-hook contract -------------------------------------------


def test_copy_link_module_targets_paragraph_anchor() -> None:
    js = (JS_DIR / "copy-link.js").read_text(encoding="utf-8")
    assert ".ride-paragraph__anchor" in js, (
        "copy-link.js no longer references the paragraph anchor selector — "
        "either the template hook moved or the module became stale"
    )


def test_cite_copy_module_targets_cite_btn_and_data() -> None:
    js = (JS_DIR / "cite-copy.js").read_text(encoding="utf-8")
    assert ".ride-cite__btn" in js
    assert "ride-cite-data" in js


# -- real-corpus integration: the hooks render in actual review HTML ------


@needs_corpus
def test_review_html_carries_cite_hooks() -> None:
    """Walk a slice of the corpus and confirm the citation-related JS
    hooks appear on every rendered review page — the citation sidebar
    is unconditional and a regression here means cite-copy.js would
    silently no-op."""
    env = make_env()
    site = SiteConfig()
    candidates = sorted(RIDE_TEI_DIR.glob("**/*-tei.xml"))[:10]
    assert candidates, "no TEI files to test against"
    for f in candidates:
        review = parse_review(f)
        html = render_review(review, site=site, env=env)
        assert 'class="ride-cite__btn"' in html, (
            f"{f.name}: cite-copy.js has no hook"
        )
        assert 'class="ride-cite-data"' in html, (
            f"{f.name}: cite-copy.js missing citation payload"
        )


@needs_corpus
def test_paragraph_anchor_hook_is_corpus_gap() -> None:
    """Document a real corpus finding (Welle 8.C): no review in the
    current corpus carries ``<p @n="…">`` paragraph numbers, so the
    ``ride-paragraph__anchor`` element never renders. The copy-link.js
    module is correctly wired in template + CSS, but its hook only
    surfaces if and when the redaktionelle Pflege ``@n`` einführt.

    This test pins the *current* state so a future change (adding @n
    to even one review) becomes a deliberate, observable transition
    rather than a silent regression."""
    env = make_env()
    site = SiteConfig()
    seen = False
    for f in sorted(RIDE_TEI_DIR.glob("**/*-tei.xml")):
        review = parse_review(f)
        html = render_review(review, site=site, env=env)
        if 'class="ride-paragraph__anchor"' in html:
            seen = True
            break
    assert not seen, (
        "A review now carries ride-paragraph__anchor — wonderful! Update "
        "this test (and the JS module is no longer effectively unused)."
    )
