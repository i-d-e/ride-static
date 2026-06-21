"""RelaxNG validation of the editorial pages against ``schema/ride-pages.rng``.

The page parser and renderer have unit tests, but nothing asserted that the
``pages/*.xml`` sources actually satisfy the page profile they claim to.
This closes that gap: every page must validate against the hand-written
profile, so a malformed page or a construct outside the profile fails the
build's test gate rather than surfacing only at render time.

Pure schema proof, deterministic, independent of network or render output.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree

REPO_ROOT = Path(__file__).resolve().parent.parent
PAGES_DIR = REPO_ROOT / "pages"
PAGES_RNG = REPO_ROOT / "schema" / "ride-pages.rng"

needs_corpus = pytest.mark.skipif(
    not PAGES_DIR.is_dir() or not any(PAGES_DIR.glob("*.xml")),
    reason="page corpus not present",
)
needs_schema = pytest.mark.skipif(
    not PAGES_RNG.exists(), reason="ride-pages.rng not available"
)


def _pages() -> list[Path]:
    return sorted(PAGES_DIR.glob("*.xml"))


@needs_schema
def test_schema_compiles() -> None:
    """The page profile itself is a well-formed, loadable RelaxNG grammar."""
    etree.RelaxNG(etree.parse(str(PAGES_RNG)))


@needs_corpus
@needs_schema
@pytest.mark.parametrize("page", _pages(), ids=lambda p: p.stem)
def test_page_validates_against_profile(page: Path) -> None:
    """Each editorial page satisfies ``schema/ride-pages.rng`` exactly."""
    rng = etree.RelaxNG(etree.parse(str(PAGES_RNG)))
    doc = etree.parse(str(page))
    rng.assertValid(doc)
