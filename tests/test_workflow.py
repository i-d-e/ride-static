"""Check build-trigger coverage against real repository paths.

This script-pipeline contract uses positive literal and directory/** filters.
fnmatchcase covers these cases; this is not a general GitHub glob evaluator.
"""

from __future__ import annotations

from fnmatch import fnmatchcase
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
EDITORIAL_PAGES = tuple(sorted((REPO_ROOT / "pages").rglob("*.xml")))


def _push_paths() -> tuple[str, ...]:
    # BaseLoader preserves the YAML key "on" instead of treating it as a boolean.
    workflow = yaml.load(
        (REPO_ROOT / ".github/workflows/build.yml").read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )
    return tuple(workflow["on"]["push"]["paths"])


@pytest.mark.parametrize("source", ["README.md", "knowledge/pipeline.md", "docs/url-scheme.md"])
def test_documentation_only_change_does_not_trigger_build(source: str) -> None:
    """Existing documentation is outside the site's build-input filters."""
    assert (REPO_ROOT / source).is_file()
    assert not any(fnmatchcase(source, pattern) for pattern in _push_paths())


@pytest.mark.parametrize(
    "page", EDITORIAL_PAGES, ids=[p.relative_to(REPO_ROOT).as_posix() for p in EDITORIAL_PAGES]
)
def test_editorial_tei_change_triggers_build(page: Path) -> None:
    """Every real editorial TEI source, including nested pages, triggers a build."""
    source = page.relative_to(REPO_ROOT).as_posix()
    assert any(fnmatchcase(source, pattern) for pattern in _push_paths()), source
