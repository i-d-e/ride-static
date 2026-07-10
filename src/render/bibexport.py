"""Corpus-wide bibliography export — the Zotero mass-import channel.

Replaces the legacy corpus-wide RDF file with a corpus-wide BibTeX file
(``ride-corpus.bib``) and a corpus-wide CSL-JSON file
(``ride-corpus.csl.json``). Both are generated from the SAME per-review
formatters (:func:`src.render.html.to_bibtex` / :func:`~src.render.html.to_csl_dict`)
that back the per-review citation buttons, so the corpus export and the
single-review citations cannot drift.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from src.model.review import Review
from src.render.html import issue_numeric_prefix, to_bibtex, to_csl_dict


def _corpus_order(reviews: Iterable[Review]) -> list[Review]:
    """Deterministic corpus order: issue numeric prefix, then review id.

    Reuses :func:`src.render.html.issue_numeric_prefix` so a lettered
    special-edition issue ("11x") sorts by its numeric part, the same rule
    navigation and the other aggregations use.
    """
    return sorted(reviews, key=lambda r: (issue_numeric_prefix(r.issue or ""), r.id or ""))


def write_bibliography_exports(
    reviews: Iterable[Review], data_dir: Path
) -> tuple[Path, Path]:
    """Write ``ride-corpus.bib`` and ``ride-corpus.csl.json`` under ``data_dir``.

    Returns the two written paths. The BibTeX file concatenates the
    per-review entries blank-line separated; the CSL file is a JSON array
    of the per-review CSL dicts.
    """
    ordered = _corpus_order(reviews)
    data_dir.mkdir(parents=True, exist_ok=True)

    bib_path = data_dir / "ride-corpus.bib"
    csl_path = data_dir / "ride-corpus.csl.json"

    bib_path.write_text(
        "\n\n".join(to_bibtex(r) for r in ordered) + "\n", encoding="utf-8"
    )
    csl_path.write_text(
        json.dumps(
            [to_csl_dict(r) for r in ordered], indent=2, ensure_ascii=False
        ),
        encoding="utf-8",
    )
    return bib_path, csl_path
