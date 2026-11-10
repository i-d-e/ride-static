"""Tests for the parity check against the live RIDE site (scripts/parity.py).

Test-data philosophy per CLAUDE.md: the fixtures under
``tests/fixtures/parity/`` are trimmed copies of real pages (the live
WordPress review of Nietzschesource and its static counterpart), with markup
kept verbatim. The short inline snippets below are verbatim excerpts of real
live pages (larepubblica and carolingian-scholarship notes, the Nietzschesource
factsheet, a static factsheet question) and are named where they are used. The
normalisation helpers are pure functions and take synthetic strings.
No test touches the network.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from lxml import html

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import parity  # noqa: E402
from parity_fetch import CachedFetcher  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures" / "parity"


@pytest.fixture(scope="module")
def live() -> parity.ReviewRecord:
    body = (FIXTURES / "live-nietzschesource.html").read_bytes()
    return parity.extract_live_review("https://ride.i-d-e.de/issues/issue-1/nietzschesource/", body)


@pytest.fixture(scope="module")
def static() -> parity.ReviewRecord:
    body = (FIXTURES / "static-ride.1.4.html").read_bytes()
    return parity.extract_static_review(
        "https://i-d-e.github.io/ride-static/issues/1/ride.1.4/", body
    )


def test_tokens_ignore_typography_but_keep_word_boundaries() -> None:
    """Pure function: synthetic input."""
    assert parity.same_text("Nietzsche’s ‘work’ – 1994", "Nietzsche's 'work' - 1994")
    assert not parity.same_text("of the Nietzsche Estate", "of theNietzsche Estate")


def test_norm_date_reads_both_site_formats() -> None:
    """Pure function: the two date spellings of the live and the static page."""
    assert parity.norm_date("Jun 2014") == "2014-06"
    assert parity.norm_date("2014-06") == "2014-06"


def test_live_extraction(live: parity.ReviewRecord) -> None:
    assert live.title == "Nietzschesource"
    assert live.doi == "10.18716/ride.a.1.4"
    assert live.published == "2014-06"
    assert set(live.paragraphs) == {"p1", "p4"}
    # The figure nested inside paragraph 4 is apparatus, not paragraph text.
    assert "eKGWB main view" not in live.paragraphs["p4"]
    assert live.figures == ["picture-1.png"]
    assert len(live.bibliography) == 2
    assert live.tags == ["collected works", "work critical edition"]
    assert live.downloads["pdf"].endswith("nietzschesource.pdf")
    assert live.head["canonical"] and not live.head["json_ld"]


def test_static_extraction(static: parity.ReviewRecord) -> None:
    assert static.doi == "10.18716/ride.a.1.4"
    assert static.published == "2014-06"
    assert set(static.paragraphs) == {"p1", "p4"}
    assert static.figures == ["picture-1.png"]
    assert static.tags == ["collected works"]
    assert static.head["json_ld"] and static.head["open_graph"]


def test_comparison_finds_the_lost_space_and_the_missing_tag(
    live: parity.ReviewRecord, static: parity.ReviewRecord
) -> None:
    findings = {f.category: f for f in parity.compare_reviews(live, static, "1", "1")}
    for category in ("title", "doi", "issue", "published", "authors", "figures", "licence"):
        assert findings[category].status == "equal", findings[category]
    assert findings["paragraph_count"].status == "equal"
    text = findings["paragraph_text"]
    assert text.status == "differs"
    assert "p1" in text.detail and "thenietzsche" in text.detail
    assert findings["bibliography_text"].status == "equal"
    assert findings["tags"].status == "differs"
    assert "work critical edition" in findings["tags"].detail


def test_live_notes_split_both_wordpress_shapes() -> None:
    """Verbatim excerpts: carolingian-scholarship (one <p> per note) and
    la-repubblica-corpus (all notes in one <p>, separated by <br>)."""
    per_paragraph = html.fromstring(
        '<div class="notes"><h2 id="footnotes">Anmerkungen</h2>'
        '<p>[<a class="internalref" href="#fnid-ftn1" id="ftn1">1</a>]&nbsp;&nbsp;Lutz weist '
        "den Kommentar der Autorschaft des irischen Bischofs Dunchad zu.</p>"
        '<p>[<a class="internalref" href="#fnid-ftn2" id="ftn2">2</a>]&nbsp;&nbsp;Siehe vor '
        "allem Teeuwen 2011.</p></div>"
    )
    one_paragraph = html.fromstring(
        '<div class="notes"><h2 id="h3">Anmerkungen</h2>'
        '<p><a href="#fnid-ftn1" class="internalref"><b id="ftn1">1.</b></a>&nbsp;Neben dem '
        "Korpus CORIS/CODIS.<br />\n"
        '<a href="#fnid-ftn2" class="internalref"><b id="ftn2">2.</b></a>&nbsp;Wie zum '
        "Zeitpunkt der Korpuserstellung.</p></div>"
    )
    a = parity.live_notes(per_paragraph)
    b = parity.live_notes(one_paragraph)
    assert len(a) == 2 and len(b) == 2
    assert parity.same_note(a[1], "Siehe vor allem Teeuwen 2011.")
    assert parity.same_note(b[0], "Neben dem Korpus CORIS/CODIS.")


def test_factsheet_answers_compare_across_markup() -> None:
    """Verbatim rows: Nietzschesource factsheet (live) and a static question."""
    live_rows = parity.extract_live_factsheet(
        b'<table class="factsheet"><tr><th>Bibliographic description</th><td><div>Is it '
        b'easily possible?</div><div>(<a href="http://www.i-d-e.de/publikationen/weitereschriften/'
        b'criteria-version-1-1#K1.2">cf. Catalogue 1.2</a>)</div></td><td><img decoding="async" '
        b'src="http://ride.i-d-e.de//wp-content/themes/responsive-child/icons/button_ok.png" '
        b'alt="yes" title="yes"></td></tr></table>'
    )
    static_rows = parity.extract_static_factsheet(
        b'<div class="ride-question"><p class="ride-question__label">Bibliographic description '
        b'<a class="ride-question__criteria-ref" href="http://www.i-d-e.de/publikationen/'
        b'weitereschriften/criteria-version-1-1#K1.2">cf. Catalogue 1.2</a></p>'
        b'<p class="ride-question__answer"><span class="ride-question__answer-label">Answer'
        b'</span> <span class="ride-question__answer-value">Yes</span></p></div>'
    )
    assert [(k, parity.answer_key(v)) for k, v in live_rows] == [("K1.2", "yes")]
    assert [(k, parity.answer_key(v)) for k, v in static_rows] == [("K1.2", "yes")]


def test_static_site_follows_meta_refresh_stubs(tmp_path: Path) -> None:
    """A local build with one real redirect stub as src.render.redirects writes it."""
    from src.render.redirects import _redirect_html

    stub = tmp_path / "issues" / "issue-1" / "nietzschesource" / "index.html"
    stub.parent.mkdir(parents=True)
    stub.write_text(_redirect_html("/ride-static/issues/1/ride.1.4/"), encoding="utf-8")
    target = tmp_path / "issues" / "1" / "ride.1.4" / "index.html"
    target.parent.mkdir(parents=True)
    target.write_bytes((FIXTURES / "static-ride.1.4.html").read_bytes())
    site = parity.StaticSite(parity.STATIC_BASE, CachedFetcher(tmp_path / "cache"), tmp_path)
    ok = parity.check_url(site, "/issues/issue-1/nietzschesource/", "/issues/1/ride.1.4/")
    assert ok.status == "equal" and "redirect" in ok.detail
    wrong = parity.check_url(site, "/issues/issue-1/nietzschesource/", "/issues/1/ride.1.5/")
    assert wrong.status == "differs"
    missing = parity.check_url(site, "/issues/issue-1/codex-sinaiticus/", "")
    assert missing.status == "missing_static"


def test_offline_fetcher_never_touches_the_network(tmp_path: Path) -> None:
    fetcher = CachedFetcher(tmp_path, offline=True)
    resp = fetcher.get("https://ride.i-d-e.de/")
    assert resp.status == 0 and fetcher.network_requests == 0
