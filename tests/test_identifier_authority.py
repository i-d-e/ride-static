"""Tests for mixed-authority identifier handling on author/editor @ref.

Two layers per the CLAUDE.md hard rule:

1. ``classify_identifier`` is a pure function whose signature (a single
   ``@ref`` string) is the only data form richer than a synthetic literal,
   so its cases are constructed inline — the documented pure-function
   exception. The junk branches ("/" , "none", doubled, leading space)
   are real corpus values quoted verbatim.
2. Real-corpus drive — one review each carrying a VIAF, GND, bare-ORCID
   and junk ``@ref`` is parsed and (for the label cases) rendered, so the
   parser classification and the byline label are pinned against real data.
   These skip cleanly when the in-repo corpus is absent.
"""
from __future__ import annotations

from src.parser.metadata import classify_identifier
from src.parser.review import parse_review
from src.render.html import render_review
from src._corpus import find_tei
from tests._shared import needs_corpus


# ── Pure-function unit tests (synthetic inputs, see module docstring) ──


def test_classify_orcid_url():
    url = "https://orcid.org/0000-0002-2071-6407"
    assert classify_identifier(url) == (url, "orcid")


def test_classify_bare_orcid_normalises_to_canonical_url():
    """Named branch: a bare ORCID id gains the canonical https://orcid.org/ prefix."""
    assert classify_identifier("0000-0002-4618-9481") == (
        "https://orcid.org/0000-0002-4618-9481",
        "orcid",
    )


def test_classify_bare_orcid_with_check_digit_x():
    assert classify_identifier("0000-0003-2852-065X") == (
        "https://orcid.org/0000-0003-2852-065X",
        "orcid",
    )


def test_classify_viaf_url():
    url = "http://viaf.org/viaf/107106790"
    assert classify_identifier(url) == (url, "viaf")


def test_classify_gnd_url():
    url = "https://d-nb.info/gnd/1161423672"
    assert classify_identifier(url) == (url, "gnd")


def test_classify_leading_space_is_trimmed():
    """Corpus editor refs carry a stray leading space before the ORCID URL."""
    assert classify_identifier(" https://orcid.org/0000-0001-8820-5112") == (
        "https://orcid.org/0000-0001-8820-5112",
        "orcid",
    )


def test_classify_doubled_value_takes_first_token():
    """One corpus editor ref repeats the id twice; the first token wins."""
    assert classify_identifier(
        "https://orcid.org/0000-0003-2852-065X 0000-0003-2852-065X"
    ) == ("https://orcid.org/0000-0003-2852-065X", "orcid")


def test_classify_junk_slash_degrades_to_none():
    assert classify_identifier("/") == (None, None)


def test_classify_literal_none_degrades_to_none():
    assert classify_identifier("none") == (None, None)


def test_classify_empty_and_missing_degrade_to_none():
    assert classify_identifier("") == (None, None)
    assert classify_identifier(None) == (None, None)


def test_classify_unrecognised_url_degrades_without_raising():
    """A URL from an unknown authority is not classified; it degrades to no
    identifier rather than raising, per the task's junk-tolerance policy."""
    assert classify_identifier("https://example.org/person/42") == (None, None)


# ── Real-corpus drive ────────────────────────────────────────────────


@needs_corpus
def test_viaf_author_authority_and_rendered_label():
    r = parse_review(find_tei("varitext"))
    author = r.authors[0]
    assert author.person.identifier_authority == "viaf"
    assert author.person.identifier_url == "http://viaf.org/viaf/107106790"
    assert author.person.orcid is None  # backwards-compat view is ORCID-only
    html = render_review(r)
    assert 'aria-label="VIAF"' in html
    assert ">VIAF</a>" in html


@needs_corpus
def test_gnd_author_authority_and_rendered_label():
    r = parse_review(find_tei("mei-friend"))
    author = r.authors[0]
    assert author.person.identifier_authority == "gnd"
    assert author.person.identifier_url == "https://d-nb.info/gnd/1161423672"
    html = render_review(r)
    assert 'aria-label="GND"' in html
    assert ">GND</a>" in html


@needs_corpus
def test_bare_orcid_author_is_normalised_to_url():
    r = parse_review(find_tei("lakomp"))
    author = r.authors[0]
    assert author.person.identifier_authority == "orcid"
    assert author.person.identifier_url == "https://orcid.org/0000-0003-1492-7766"
    assert author.person.orcid == "https://orcid.org/0000-0003-1492-7766"


@needs_corpus
def test_junk_slash_ref_renders_no_identifier_link_and_does_not_crash():
    r = parse_review(find_tei("stylo"))
    author = r.authors[0]
    assert author.person.identifier_url is None
    assert author.person.identifier_authority is None
    html = render_review(r)  # must not raise
    assert "ride-review__orcid" not in html
