"""End-to-end build smoke test.

Runs the full ``src.build.build`` once into a throwaway directory and
asserts the exact target paths of the core artefacts, that every review
in the corpus gets a page, and that the explorer sidecar row count
tracks the corpus. This is the one test that exercises parse → consistency
checks → render → aggregations → machine artefacts as a whole.

Real-corpus drive per the CLAUDE.md hard rule; skips cleanly when the
corpus is absent. Session-scoped so the (~4 s) build runs only once.
Validation and PDF are off: RelaxNG validation is covered by
``test_validate.py`` and WeasyPrint may be unavailable on the host.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

BASE_URL = "https://ride.i-d-e.de"


@pytest.fixture(scope="session")
def built_site(tmp_path_factory, corpus_reviews):
    """Build the public site once into a temp tree; yield its root."""
    from src.build import build

    out_root = tmp_path_factory.mktemp("site")
    published = tuple(r for r in corpus_reviews if not r.is_draft)
    written = build(
        out_root=out_root,
        base_url=BASE_URL,
        validate=False,
        pdf=False,
    )
    assert written == len(published)
    return out_root


@pytest.fixture(scope="session")
def draft_built_site(tmp_path_factory):
    """Build local draft previews while retaining public-output filtering."""
    from src.build import build

    out_root = tmp_path_factory.mktemp("site-with-drafts")
    build(
        out_root=out_root,
        validate=False,
        pdf=False,
        include_drafts=True,
    )
    return out_root


def test_core_artefact_paths_exist(built_site):
    """Every core artefact lands at its exact contracted path."""
    expected = [
        "index.html",
        "feed/atom.xml",
        "feed/rss.xml",
        "feed/rdf.xml",
        "feed/index.html",
        "feed/rss/index.html",
        "feed/atom/index.html",
        "feed/rdf/index.html",
        "sitemap.xml",
        "api/build-info.json",
        "api/corpus.json",
        "data/explore/index.html",
        "data/explorer.json",
        "issues/index.html",
    ]
    missing = [p for p in expected if not (built_site / p).is_file()]
    assert not missing, f"missing build artefacts: {missing}"


def test_a_concrete_review_page_exists(built_site, corpus_reviews):
    """A specific per-review page is written at issues/{N}/{id}/index.html,
    with its TEI download sibling, derived from the real corpus."""
    review = next(r for r in corpus_reviews if r.id and r.issue)
    page = built_site / "issues" / review.issue / review.id / "index.html"
    tei = built_site / "issues" / review.issue / review.id / f"{review.id}.xml"
    assert page.is_file(), f"no page for {review.id}"
    assert tei.is_file(), f"no TEI download for {review.id}"
    assert review.title in page.read_text(encoding="utf-8")


def test_every_published_corpus_review_has_a_page(built_site, corpus_reviews):
    missing = [
        r.id
        for r in corpus_reviews
        if not r.is_draft
        and r.id
        and r.issue
        and not (built_site / "issues" / r.issue / r.id / "index.html").is_file()
    ]
    assert not missing, f"reviews without a page: {missing}"


def test_build_info_reports_the_rendered_count(built_site, corpus_reviews):
    info = json.loads((built_site / "api" / "build-info.json").read_text(encoding="utf-8"))
    assert info["reviews"]["rendered"] == sum(not r.is_draft for r in corpus_reviews)
    assert info["reviews"]["drafts_discovered"] == sum(r.is_draft for r in corpus_reviews)
    assert info["site"]["base_url"] == BASE_URL


def test_explorer_json_row_count_equals_review_count(built_site, corpus_reviews):
    payload = json.loads((built_site / "data" / "explorer.json").read_text(encoding="utf-8"))
    published_count = sum(not r.is_draft for r in corpus_reviews)
    assert payload["review_count"] == published_count
    assert len(payload["reviews"]) == published_count


def test_public_build_excludes_every_draft_from_pages_and_machine_outputs(
    built_site,
    corpus_reviews,
):
    """Production outputs contain no route, asset, or metadata for any draft."""
    drafts = [review for review in corpus_reviews if review.is_draft]
    assert drafts

    for review in drafts:
        assert not (built_site / "issues" / review.issue / review.id).exists()
        assert not (built_site / "static" / "images" / "wordclouds" / f"{review.id}.png").exists()

    text_suffixes = {".bib", ".html", ".json", ".rdf", ".txt", ".xml"}
    for path in built_site.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in text_suffixes:
            continue
        text = path.read_text(encoding="utf-8")
        for review in drafts:
            assert review.id not in text, f"draft leaked into {path}"


def test_local_draft_build_renders_every_complete_bundle_preview(
    draft_built_site,
    corpus_reviews,
):
    """Every draft bundle produces review, factsheet, figures, XML, and wordcloud."""
    drafts = [review for review in corpus_reviews if review.is_draft]
    assert drafts
    draft_index = (draft_built_site / "drafts" / "index.html").read_text(encoding="utf-8")
    assert "Review workflow examples" in draft_index

    for review in drafts:
        root = draft_built_site / "issues" / review.issue / review.id
        assert (root / "index.html").is_file()
        assert (root / "factsheet" / "index.html").is_file()
        assert (root / f"{review.id}.xml").is_file()
        for figure in review.figures:
            if figure.graphic_url:
                assert (root / "figures" / Path(figure.graphic_url).name).is_file()
        wordcloud = draft_built_site / "static" / "images" / "wordclouds" / f"{review.id}.png"
        assert wordcloud.is_file()
        html = (root / "index.html").read_text(encoding="utf-8")
        assert "Draft preview" in html
        assert "review preview" in html
        assert "formal publication outputs" in html
        assert "local workflow testing" not in html
        assert 'name="robots" content="noindex, nofollow"' in html
        assert 'type="application/pdf"' not in html
        assert f"{review.id}.png" in draft_index


def test_sitemap_and_feeds_reference_the_base_url(built_site):
    sitemap = (built_site / "sitemap.xml").read_text(encoding="utf-8")
    feed = (built_site / "feed" / "atom.xml").read_text(encoding="utf-8")
    rss = (built_site / "feed" / "rss.xml").read_text(encoding="utf-8")
    assert BASE_URL in sitemap
    assert BASE_URL in feed
    assert BASE_URL in rss


def test_pages_advertise_both_feeds(built_site):
    """Feed autodiscovery: the page head links Atom and RSS."""
    head = (built_site / "index.html").read_text(encoding="utf-8")
    assert 'type="application/atom+xml"' in head
    assert 'type="application/rss+xml"' in head
    assert f"{BASE_URL}/feed/rss.xml" in head


def test_dynamic_wp_page_redirect_stub_exists(built_site):
    """The legacy dynamic WP listing pages get redirect stubs in a full
    build (unit coverage in test_render_redirects.py; this pins wiring)."""
    stub = built_site / "data" / "by-tag" / "index.html"
    assert stub.is_file()
    assert f"{BASE_URL}/tags/" in stub.read_text(encoding="utf-8")
