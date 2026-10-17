"""Script-pipeline regressions for real editorial sources and deploy URLs.

Synthetic link strings cover pure HTML-formatting boundaries absent from the corpus.
"""

from pathlib import Path

import pytest
from lxml import html

from src.build import _render_editorials, _write_sitemap
from src.parser.page import PAGES_DIR, parse_page
from src.render.aggregations import render_index
from src.render.editorial import CONTENT_DIR, discover_editorials, discover_home_widgets
from src.render.html import SiteConfig, make_env, render_editorial_shell
from src.render.page import render_page
from src.render.sitemap import SITEMAP_XMLNS, collect_entries


needs_editorials = pytest.mark.skipif(
    not (PAGES_DIR / "about.xml").is_file() or not CONTENT_DIR.is_dir(),
    reason="real editorial source sets not present",
)


@needs_editorials
@pytest.mark.parametrize("base", ["", "/ride-static", "https://i-d-e.github.io/ride-static"])
def test_real_home_and_tei_links_follow_deployment(base: str) -> None:
    site = SiteConfig(base_url=base)
    homepage = html.fromstring(render_index((), site, make_env(), discover_home_widgets()))
    editorial = html.fromstring(render_page(parse_page(PAGES_DIR / "about.xml"), site))
    for document in (homepage, editorial):
        assert document.xpath('//a[text()="editorial"]/@href') == [f"{base}/about/editorial/"]
    for widget in discover_home_widgets():
        for anchor in html.fragment_fromstring(widget.body_html, create_parent="div").iter("a"):
            target = anchor.get("href", "")
            if target.startswith("/") and not target.startswith("//"):
                assert f"{base}{target}" in homepage.xpath("//a/@href")


@pytest.mark.parametrize("base", ["/ride-static", "https://i-d-e.github.io/ride-static"])
def test_body_url_boundaries(base: str) -> None:
    """Pure formatter cases preserve foreign origins, anchors, queries and escaping."""
    links = [
        "/about/?q=a&b=c#part",
        "/ride-static/about/",
        "//example.org/about/",
        "https://example.org/about/",
        "mailto:editor@example.org",
        "#section",
        "relative/",
    ]
    from html import escape

    body = "".join(f'<a href="{escape(link, quote=True)}">Link</a>' for link in links)
    rendered = render_editorial_shell(
        make_env(), SiteConfig(base_url=base), slug="sample", title="Sample", body_html=body
    )
    destinations = html.fromstring(rendered).xpath('//a[text()="Link"]/@href')
    assert destinations == [f"{base}/about/?q=a&b=c#part", f"{base}/about/", *links[2:]]


@needs_editorials
@pytest.mark.parametrize("tei", [True, False])
def test_sitemap_covers_exactly_rendered_editorials(tmp_path: Path, tei: bool) -> None:
    site = SiteConfig(base_url="https://i-d-e.github.io/ride-static")
    _render_editorials(make_env(), site, tmp_path, tei_editorials=tei)
    assert _write_sitemap((), site, tmp_path, tei_editorials=tei)
    from lxml import etree

    tree = etree.parse(str(tmp_path / "sitemap.xml"))
    locs = {node.text for node in tree.iter(f"{{{SITEMAP_XMLNS}}}loc")}
    actual = {
        f"{site.base_url}/{p.parent.relative_to(tmp_path).as_posix()}/"
        for p in tmp_path.rglob("index.html")
    }
    assert actual <= locs
    assert (f"{site.base_url}/about/editorial/" in locs) is tei
    for page in discover_editorials():
        assert f"{site.base_url}/{page.slug}/" in locs


@pytest.mark.parametrize(
    "base", ["/ride-static", "//example.org", "ftp://example.org", "https://example.org?q=x"]
)
def test_sitemap_rejects_nonabsolute_or_ambiguous_base(base: str) -> None:
    """Pure URL validation rejects unsupported sitemap deployment addresses."""
    with pytest.raises(ValueError, match="absolute"):
        collect_entries((), base_url=base)


def test_path_only_preview_omits_invalid_sitemap(tmp_path: Path) -> None:
    assert not _write_sitemap((), SiteConfig(base_url="/ride-static"), tmp_path)
    assert not (tmp_path / "sitemap.xml").exists()


@needs_editorials
def test_reused_markdown_preview_does_not_list_stale_tei_pages(tmp_path: Path) -> None:
    site = SiteConfig(base_url="https://i-d-e.github.io/ride-static")
    _render_editorials(make_env(), site, tmp_path, tei_editorials=True)
    _render_editorials(make_env(), site, tmp_path, tei_editorials=False)
    _write_sitemap((), site, tmp_path, tei_editorials=False)
    assert "/about/editorial/" not in (tmp_path / "sitemap.xml").read_text(encoding="utf-8")


def test_ci_uses_absolute_preview_address_and_one_pinned_search_version() -> None:
    import yaml
    from src.render.html import REPO_ROOT

    workflow = yaml.load(
        (REPO_ROOT / ".github/workflows/build.yml").read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )
    steps = next(iter(workflow["jobs"].values()))["steps"]
    build = next(step["run"] for step in steps if step.get("name") == "Build site")
    assert (
        "--base-url=https://${{ github.repository_owner }}.github.io/${{ github.event.repository.name }}"
        in build
    )
    commands = [
        step["run"]
        for step in steps
        if step.get("name") in {"Build Pagefind index", "Build draft Pagefind index"}
    ]
    assert len(commands) == 2
    assert all(command.startswith("npx -y pagefind@1.5.2 --site ") for command in commands)

    assert all("--force-language mul" in command for command in commands)
