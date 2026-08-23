"""Corpus path helpers — central location for TEI/schema lookups.

Replaces the historic ``REPO_ROOT.parent / "ride" / "tei_all"`` pattern
that lived in every script and test. The corpus now ships inside this
repository, with the schema at ``schema/``. Published legacy files use
``issues/{N}/reviews/*-tei.xml``. Review bundles use
``issues/{N}/reviews/{slug}/review.xml`` and may carry ``pictures/``.

Layout:

    issues/{N}/metadata.yaml       editorial metadata (DOI, editors, …)
    issues/{N}/reviews/*-tei.xml   legacy review files
    issues/{N}/reviews/*/review.xml bundled review files
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


def _issue_sort_key(p: Path, root: Path) -> tuple[int, str]:
    try:
        relative = p.relative_to(root)
        return (int(relative.parts[0]), review_slug(p))
    except (ValueError, IndexError):
        return (10**6, p.as_posix())


def is_review_bundle(path: Path) -> bool:
    """Return whether ``path`` is ``reviews/{slug}/review.xml``."""
    return path.name == "review.xml" and path.parent.parent.name == "reviews"


def review_slug(path: Path) -> str:
    """Return the editorial slug represented by a legacy file or bundle."""
    if is_review_bundle(path):
        return path.parent.name
    return path.stem.removesuffix("-tei")


def iter_tei_files(root: Path = CORPUS_ROOT) -> Iterator[Path]:
    """Yield every legacy review and bundle TEI in editorial order."""
    if not root.exists():
        return
    files = [
        *root.glob("*/reviews/*-tei.xml"),
        *root.glob("*/reviews/*/review.xml"),
    ]
    yield from sorted(files, key=lambda path: _issue_sort_key(path, root))


def list_tei_files(root: Path = CORPUS_ROOT) -> list[Path]:
    return list(iter_tei_files(root))


def find_tei(slug: str, root: Path = CORPUS_ROOT) -> Path:
    """Resolve a review slug or legacy filename to its TEI source."""
    matches = [
        path for path in iter_tei_files(root) if review_slug(path) == slug or path.name == slug
    ]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(f"Review slug is ambiguous in corpus: {slug}")
    raise FileNotFoundError(f"TEI review not found in corpus: {slug}")


def corpus_available(root: Path = CORPUS_ROOT) -> bool:
    """True iff at least one TEI file exists under ``root``."""
    return any(iter_tei_files(root))
