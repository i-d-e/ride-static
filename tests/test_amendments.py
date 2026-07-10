"""Real-corpus tests for the post-publication amendments apparatus.

Per the CLAUDE.md hard rule these integration tests drive the *real* TEI
through ``src.parser.review.parse_review`` and assert the resulting domain
shape, rather than constructing ``Amendment`` instances synthetically. Only
two reviews carry post-publication corrections:

* ``melville`` (issue 3) — 6 ``<mod>`` amendments, each a ``<del>``/``<add>``
  replacement (5 wrapped in ``<subst>``, 1 a bare ``<del>``) plus a reviewer
  ``<note>``, with matching ``<revisionDesc>`` changes.
* ``sandrart`` (issue 1) — 1 ``<mod>`` carrying only a correction ``<note>``
  (no del/add), nested inside a regular footnote.

Every other review carries no amendments; the mass case asserts zero output.

The tests skip cleanly when the in-repo corpus is absent.
"""
from __future__ import annotations

import pytest

from src.model.inline import Amendment
from src.render.html import inlines_to_plain_text, render_review
from tests._shared import needs_corpus


# ── Corpus fixtures ──────────────────────────────────────────────────


def _review(slug: str):
    from src._corpus import find_tei
    from src.parser.review import parse_review

    try:
        path = find_tei(slug)
    except Exception:  # pragma: no cover - skip path
        pytest.skip(f"{slug} not present in corpus")
    if path is None:
        pytest.skip(f"{slug} not present in corpus")
    return parse_review(path)


@pytest.fixture(scope="module")
def melville():
    return _review("melville")


@pytest.fixture(scope="module")
def sandrart():
    return _review("sandrart")


def _body_plain_text(review) -> str:
    """Flatten every body/front/back section's inline text the way the
    renderer's meta/alt path does — Amendment contributes only its inline
    replacement, never the deleted original or the note."""
    from src.model.walk import iter_inline_groups

    parts: list[str] = []

    def walk(sections):
        for s in sections:
            if s.heading:
                parts.append(inlines_to_plain_text(s.heading))
            for group in iter_inline_groups(s.blocks):
                parts.append(inlines_to_plain_text(group))
            walk(s.subsections)

    walk(review.front + review.body + review.back)
    return " ".join(parts)


# ── melville: six replacement amendments ─────────────────────────────


@needs_corpus
def test_melville_has_six_amendments(melville):
    assert len(melville.amendments) == 6
    assert all(isinstance(a, Amendment) for a in melville.amendments)


@needs_corpus
def test_melville_markers_and_ids(melville):
    markers = [a.marker for a in melville.amendments]
    assert markers == ["i", "ii", "iii", "iv", "v", "vi"]
    ids = [a.xml_id for a in melville.amendments]
    assert ids == ["ftn-i", "ftn-ii", "ftn-iii", "ftn-iv", "ftn-v", "ftn-vi"]


@needs_corpus
def test_melville_revision_metadata_joined(melville):
    """@when / @resp come from the matching <revisionDesc> change."""
    for a in melville.amendments:
        assert a.date == "2016-01-01"
        assert a.resp == "author"
        assert a.change and a.change.startswith("#revision")


@needs_corpus
def test_melville_del_text_absent_from_running_text(melville):
    """The deleted original must no longer appear in the body flow — it is
    carried only in Amendment.deleted for the apparate."""
    first = melville.amendments[0]
    # A distinctive phrase from revision1's <del>.
    phrase = "reproductions of imitated marginalia"
    deleted_text = inlines_to_plain_text(first.deleted)
    assert phrase in deleted_text
    assert phrase not in _body_plain_text(melville)


@needs_corpus
def test_melville_added_text_present_in_running_text(melville):
    """The replacement <add> renders inline in the running text."""
    # revision2's <add> opens with this distinctive clause.
    phrase = "collaborates closely with the Houghton library"
    assert phrase in _body_plain_text(melville)


@needs_corpus
def test_melville_render_has_amendments_panel_and_marker_links(melville):
    html = render_review(melville)
    assert "ride-apparate__panel--amendments" in html
    assert 'id="apparate-amendments"' in html
    assert ">Amendments<" in html
    # Bidirectional link: inline marker -> entry, entry -> marker.
    assert 'href="#ftn-i"' in html
    assert 'id="ftn-i-mark"' in html
    assert 'id="ftn-i"' in html
    assert 'href="#ftn-i-mark"' in html
    # The apparate lists the original text under an "Original" label.
    assert "Original" in html
    assert "reproductions of imitated marginalia" in html


# ── sandrart: one note-only amendment, nested in a footnote ──────────


@needs_corpus
def test_sandrart_has_one_amendment(sandrart):
    assert len(sandrart.amendments) == 1
    a = sandrart.amendments[0]
    assert isinstance(a, Amendment)
    assert a.marker == "i"
    assert a.xml_id == "ftn-i"
    assert a.children == ()  # no replacement text
    assert a.deleted == ()


@needs_corpus
def test_sandrart_note_carried_on_amendment(sandrart):
    note_text = inlines_to_plain_text(sandrart.amendments[0].note)
    assert "Christian Thomas" in note_text
    assert sandrart.amendments[0].date == "2014-11-22"
    assert sandrart.amendments[0].resp == "author"


@needs_corpus
def test_sandrart_amendment_note_excluded_from_footnotes(sandrart):
    """The <note> child of a <mod> must not leak into the regular footnotes
    apparate, even though the <mod> is nested inside footnote ftn4."""
    notes_text = " ".join(inlines_to_plain_text(n.children) for n in sandrart.notes)
    assert "Christian Thomas" not in notes_text
    # And the amendment note is not part of the running body text either.
    assert "Christian Thomas" not in _body_plain_text(sandrart)


@needs_corpus
def test_sandrart_render_shows_amendment_note(sandrart):
    html = render_review(sandrart)
    assert "ride-apparate__panel--amendments" in html
    assert "Christian Thomas" in html


# ── mass case: reviews without amendments render nothing ─────────────


@needs_corpus
def test_unaffected_review_has_no_amendments():
    review = _review("makingandknowing")
    assert review.amendments == ()
    html = render_review(review)
    assert "ride-apparate__panel--amendments" not in html
    assert 'id="apparate-amendments"' not in html
