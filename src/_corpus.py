"""Corpus path helpers — central location for TEI/schema lookups.

Replaces the historic ``REPO_ROOT.parent / "ride" / "tei_all"`` pattern
that lived in every script and test. The corpus now ships inside this
repository under ``issues/{N}/reviews/*-tei.xml``, with the schema at
``schema/``.

Layout:

    issues/{N}/metadata.yaml       editorial metadata (DOI, editors, …)
    issues/{N}/reviews/*-tei.xml   the actual review files
    schema/ride.odd                RIDE TEI ODD customisation
    schema/ride.rng                compiled RelaxNG

``iter_tei_files()`` yields every review in document order (by issue
number, then by filename). ``find_tei(slug)`` resolves a slug like
``"anemoskala"`` to the file in whichever issue it sits.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_ROOT = REPO_ROOT / "issues"
SCHEMA_DIR = REPO_ROOT / "schema"
SCHEMA_ODD = SCHEMA_DIR / "ride.odd"
SCHEMA_RNG = SCHEMA_DIR / "ride.rng"


def _issue_sort_key(p: Path) -> tuple[int, str]:
    try:
        return (int(p.parent.parent.name), p.name)
    except ValueError:
        return (10**6, p.name)


def iter_tei_files(root: Path = CORPUS_ROOT) -> Iterator[Path]:
    """Yield every ``issues/*/reviews/*-tei.xml`` under ``root``,
    sorted by issue number then filename."""
    if not root.exists():
        return
    yield from sorted(root.glob("*/reviews/*.xml"), key=_issue_sort_key)


def list_tei_files(root: Path = CORPUS_ROOT) -> list[Path]:
    return list(iter_tei_files(root))


def find_tei(slug: str, root: Path = CORPUS_ROOT) -> Path:
    """Resolve a review slug (e.g. ``"anemoskala"`` or
    ``"anemoskala-tei.xml"``) to its TEI path. Raises FileNotFoundError."""
    name = slug if slug.endswith(".xml") else f"{slug}-tei.xml"
    for p in iter_tei_files(root):
        if p.name == name:
            return p
    raise FileNotFoundError(f"TEI file not found in corpus: {name}")


def corpus_available(root: Path = CORPUS_ROOT) -> bool:
    """True iff at least one TEI file exists under ``root``."""
    return any(iter_tei_files(root))
