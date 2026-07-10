"""Tests for the UI-string override layer (``content/strings.yaml``).

The templates read localisable labels as ``site.strings.<key> |
default('English')`` or ``strings.get('<key>', 'English')``. The build
loads ``content/strings.yaml`` and threads the resulting dict into
``SiteConfig(strings=…)``. Editors override a label by uncommenting its
key; an unknown key is a typo and fails the build.

Two of these are pure-function / contract tests over the real template
files and the real ``STRING_KEYS`` constant (no synthetic Review needed);
the render-level test drives the real corpus through the parser and
``render_review`` per the CLAUDE.md real-corpus rule.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from src.build import STRING_KEYS, STRINGS_PATH, _load_strings
from src.render.html import REPO_ROOT, SiteConfig, render_review

TEMPLATES_DIR = REPO_ROOT / "templates" / "html"

# Matches strings.get('key', …) and strings.get("key", …).
_GET_RE = re.compile(r"strings\.get\(\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]")
# Matches attribute access strings.key (excluding the .get() method call).
_ATTR_RE = re.compile(r"strings\.([A-Za-z_][A-Za-z0-9_]*)")


def _keys_referenced_in_templates() -> set[str]:
    """Grep every template for the string keys it references, both the
    ``strings.get('k', …)`` and ``strings.k | default(…)`` forms."""
    keys: set[str] = set()
    for path in TEMPLATES_DIR.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        keys.update(_GET_RE.findall(text))
        for name in _ATTR_RE.findall(text):
            if name != "get":  # the dict method, not a vocabulary key
                keys.add(name)
    return keys


def test_vocabulary_constant_matches_templates() -> None:
    """Contract: the frozen STRING_KEYS vocabulary equals the set of
    ``strings.<key>`` references greppable from the real templates.

    Template drift (a new label added or a key renamed) fails here so the
    build-time typo guard and the editor-facing ``strings.yaml`` stay in
    lockstep with what the templates actually consume."""
    assert STRING_KEYS == _keys_referenced_in_templates()


def test_strings_yaml_parses_and_keys_are_known() -> None:
    """``content/strings.yaml`` parses as a mapping (or empty), and every
    active (non-comment) key it declares is in the vocabulary. The file
    ships all-commented, so this currently asserts the empty case too."""
    if not STRINGS_PATH.exists():
        pytest.skip("content/strings.yaml absent")
    data = yaml.safe_load(STRINGS_PATH.read_text(encoding="utf-8"))
    if data is None:
        data = {}
    assert isinstance(data, dict)
    for key in data:
        assert key in STRING_KEYS, f"unknown string key in strings.yaml: {key!r}"


def test_shipped_file_yields_no_active_overrides() -> None:
    """The deployed file carries every key as a comment and no active
    override, so the loaded dict is empty and site output is byte-stable."""
    if not STRINGS_PATH.exists():
        pytest.skip("content/strings.yaml absent")
    assert _load_strings(STRINGS_PATH) == {}


def test_load_strings_missing_file_is_empty(tmp_path: Path) -> None:
    """An absent file loads as ``{}`` — the override layer is optional."""
    assert _load_strings(tmp_path / "nope.yaml") == {}


def test_load_strings_unknown_key_raises(tmp_path: Path) -> None:
    """Synthetic exception case (no such file exists in the repo): an
    unknown key is a typo and fails the build with a message naming the
    bad key and pointing at the valid vocabulary."""
    bad = tmp_path / "strings.yaml"
    bad.write_text("not_a_real_key: Boom\n", encoding="utf-8")
    with pytest.raises(ValueError) as exc:
        _load_strings(bad)
    msg = str(exc.value)
    assert "not_a_real_key" in msg
    assert "STRING_KEYS" in msg  # points the editor at the vocabulary source


def test_load_strings_accepts_known_key(tmp_path: Path) -> None:
    """A known key loads through as an override (pure-function check on the
    loader; the key 'abstract' is a real vocabulary member)."""
    good = tmp_path / "strings.yaml"
    good.write_text("abstract: Zusammenfassung\n", encoding="utf-8")
    assert _load_strings(good) == {"abstract": "Zusammenfassung"}


def test_override_changes_rendered_label(corpus_review) -> None:
    """Build-level: an override dict actually reaches the rendered HTML,
    and ``strings={}`` leaves the English default in place. The TOC
    sidebar heading ('Contents') renders unconditionally for every
    review, so it is a stable probe."""
    default_html = render_review(corpus_review, site=SiteConfig(strings={}))
    assert ">Contents<" in default_html

    sentinel = "Inhaltsverzeichnis-XYZ"
    overridden = render_review(
        corpus_review, site=SiteConfig(strings={"toc": sentinel})
    )
    assert f">{sentinel}<" in overridden
    assert ">Contents<" not in overridden
