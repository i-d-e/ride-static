"""CSS contract tests — WCAG 2.2 AA hygiene checks.

Static-stylesheet checks: we don't run a browser, so we can't measure
computed layout. Instead we pin the *rules* that produce the WCAG
behaviour — focus-visible on every interactive element family, target
size on tag pills, reduced-motion respect. Style edits that drop one
of these requirements break the test.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RIDE_CSS = REPO_ROOT / "static" / "css" / "ride.css"


def _css() -> str:
    return RIDE_CSS.read_text(encoding="utf-8")


def test_focus_visible_covers_every_interactive_element_family():
    """WCAG 2.4.7 / 2.4.11: keyboard focus is always perceivable.

    The single combined rule covers links, buttons, form inputs and
    native disclosure widgets so we don't accidentally rely on UA
    defaults — those vary across browsers and don't always meet AA
    contrast.
    """
    css = _css()
    for selector in (
        "a:focus-visible",
        "button:focus-visible",
        "input:focus-visible",
        "select:focus-visible",
        "textarea:focus-visible",
        "summary:focus-visible",
    ):
        assert selector in css, f"missing focus-visible rule for {selector}"


def test_skip_link_appears_on_focus():
    """WCAG 2.4.1: a skip link must exist and become visible on focus.

    The implementation hides it off-screen at ``left: -10000px`` and
    pulls it back to ``left: 0`` on focus.
    """
    css = _css()
    assert ".ride-skip" in css
    assert ".ride-skip:focus" in css


def test_tag_pills_meet_target_size_minimum():
    """WCAG 2.5.8 (Target Size, Minimum, AA): pointer targets are
    at least 24×24 CSS-px. Tag pills carry a ``min-height: 24px``
    so the small font size doesn't shrink them under the threshold.
    """
    css = _css()
    # The min-height token sits inside the .ride-tag-pills li a rule.
    # Find that rule and assert min-height is in it.
    start = css.find(".ride-tag-pills li a")
    assert start != -1
    end = css.find("}", start)
    rule = css[start:end]
    assert "min-height: 24px" in rule


def test_reduced_motion_preference_is_honoured():
    """WCAG 2.3.3 (AAA, but project policy): users who set
    ``prefers-reduced-motion: reduce`` get no animations, no
    transitions. The blanket override at the bottom of the
    accessibility section covers every element."""
    css = _css()
    assert "@media (prefers-reduced-motion: reduce)" in css
    # The block kills both animation and transition globally.
    block_start = css.find("@media (prefers-reduced-motion: reduce)")
    block_end = css.find("}", block_start + 50)
    block = css[block_start:block_end]
    assert "animation: none" in block
    assert "transition: none" in block
