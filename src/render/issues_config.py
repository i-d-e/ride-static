"""Per-issue configuration loader — Phase 10/11 R11.

Issue metadata that is editorially curated (DOI, editors, status,
display title, free-text description, optional contribution order)
lives as YAML files under ``issues/{n}/metadata.yaml`` — next to the
TEI reviews for that issue. The loader returns one :class:`IssueConfig`
per file.

Consistency with the TEI corpus (R11 acceptance criterion: "Inkonsistenzen
brechen den Build") is checked by :func:`validate_issue_configs`. The
build calls it with the parsed reviews and raises if anything is
missing or extra.

YAML schema (all fields optional except ``issue``):

```yaml
issue: 13
title: "Issue 13 — Music editions"
doi: "10.18716/ride.13"
status: regular              # or "rolling"
publication_date: "2024-06-01"
description: |
  Free-text intro shown on the Issue-Ansicht above the contribution list.
editors:
  - name: "Editor Person"
    affiliation: "Some University"
    orcid: "https://orcid.org/0000-0000-0000-0000"
contribution_order:           # optional — overrides default sort
  - ride.13.1
  - ride.13.7
```

Anything not listed here is rejected with a build-time warning so
typos do not silently disappear.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from src.model.review import Review
from src.render.html import REPO_ROOT

ISSUES_DIR = REPO_ROOT / "issues"

_VALID_STATUS = {"regular", "rolling"}
_KNOWN_FIELDS = {
    "issue", "title", "doi", "status", "publication_date",
    "description", "editors", "contribution_order",
}
_KNOWN_EDITOR_FIELDS = {"name", "affiliation", "orcid", "email", "role"}


@dataclass(frozen=True)
class IssueEditor:
    """One editor on an issue's masthead. Distinct from ``Review.editors``;
    issue-level editing is curatorial, not authorial."""

    name: str
    affiliation: Optional[str] = None
    orcid: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None


@dataclass(frozen=True)
class IssueConfig:
    """Editorially curated metadata for one issue."""

    issue: str
    title: Optional[str] = None
    doi: Optional[str] = None
    status: str = "regular"
    publication_date: Optional[str] = None
    description: Optional[str] = None
    editors: tuple[IssueEditor, ...] = field(default_factory=tuple)
    contribution_order: Optional[tuple[str, ...]] = None

    @property
    def is_rolling(self) -> bool:
        return self.status == "rolling"


# ── Loader ─────────────────────────────────────────────────────────────


def parse_issue_config(path: Path) -> IssueConfig:
    """Read one YAML file; raise on shape errors."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path.name}: expected a YAML mapping at top level")

    unknown = set(raw) - _KNOWN_FIELDS
    if unknown:
        raise ValueError(
            f"{path.name}: unknown field(s) {sorted(unknown)} — "
            f"valid fields: {sorted(_KNOWN_FIELDS)}"
        )

    status = str(raw.get("status", "regular"))
    if status not in _VALID_STATUS:
        raise ValueError(
            f"{path.name}: status must be 'regular' or 'rolling', got {status!r}"
        )

    editors = tuple(_parse_editor(e, path.name) for e in raw.get("editors") or [])

    raw_order = raw.get("contribution_order")
    if raw_order is not None and not isinstance(raw_order, list):
        raise ValueError(f"{path.name}: contribution_order must be a list of review IDs")
    order = tuple(str(rid) for rid in raw_order) if raw_order else None

    # Issue number defaults to the YAML's parent directory (issues/{N}/metadata.yaml).
    # Falls back to ``path.stem`` for backward compatibility with flat YAMLs.
    issue_no = str(raw.get("issue") or path.parent.name or path.stem)
    pub_date = raw.get("publication_date")
    if pub_date is not None:
        pub_date = str(pub_date)

    return IssueConfig(
        issue=issue_no,
        title=raw.get("title"),
        doi=raw.get("doi"),
        status=status,
        publication_date=pub_date,
        description=raw.get("description"),
        editors=editors,
        contribution_order=order,
    )


def _parse_editor(entry, file_label: str) -> IssueEditor:
    if not isinstance(entry, dict) or "name" not in entry:
        raise ValueError(f"{file_label}: each editor must be a mapping with at least 'name'")
    unknown = set(entry) - _KNOWN_EDITOR_FIELDS
    if unknown:
        raise ValueError(
            f"{file_label}: unknown editor field(s) {sorted(unknown)} — "
            f"valid: {sorted(_KNOWN_EDITOR_FIELDS)}"
        )
    return IssueEditor(
        name=str(entry["name"]),
        affiliation=entry.get("affiliation"),
        orcid=entry.get("orcid"),
        email=entry.get("email"),
        role=entry.get("role"),
    )


def discover_issue_configs(content_dir: Path = ISSUES_DIR) -> dict[str, IssueConfig]:
    """Load every ``issues/*/metadata.yaml``. Returns a mapping issue → config."""
    if not content_dir.exists():
        return {}
    return {
        cfg.issue: cfg
        for cfg in (
            parse_issue_config(p) for p in sorted(content_dir.glob("*/metadata.yaml"))
        )
    }


# ── Validation ────────────────────────────────────────────────────────


class IssueConfigError(ValueError):
    """Raised when issue YAML and TEI corpus disagree."""


def validate_issue_configs(
    configs: dict[str, IssueConfig],
    reviews: tuple[Review, ...],
) -> list[str]:
    """Return a list of inconsistency messages. Empty list means clean.

    R11 says inconsistencies must break the build with a clear error.
    The build CLI raises :class:`IssueConfigError` when this returns
    a non-empty list.
    """
    by_issue: dict[str, set[str]] = defaultdict(set)
    for r in reviews:
        if r.issue:
            by_issue[r.issue].add(r.id)

    errors: list[str] = []
    for issue_no, cfg in configs.items():
        tei_ids = by_issue.get(issue_no, set())
        if not tei_ids:
            errors.append(
                f"issue YAML {issue_no!r} has no matching reviews in the corpus"
            )
            continue
        if cfg.contribution_order is None:
            continue
        order_ids = set(cfg.contribution_order)
        missing_in_yaml = tei_ids - order_ids
        missing_in_tei = order_ids - tei_ids
        if missing_in_yaml:
            errors.append(
                f"issue {issue_no}: contribution_order is missing {sorted(missing_in_yaml)}"
            )
        if missing_in_tei:
            errors.append(
                f"issue {issue_no}: contribution_order lists {sorted(missing_in_tei)} "
                f"not present in the TEI corpus"
            )
    return errors


def validate_review_locations(
    parsed: list[tuple[Path, Review]],
    corpus_root: Optional[Path] = None,
) -> list[str]:
    """Return mismatches between a TEI file's enclosing folder and its
    ``biblScope @n`` value.

    The canonical layout is ``issues/{N}/reviews/{slug}-tei.xml`` and
    the parser reads the issue number from the TEI header (``Review.issue``
    = ``biblScope @n``). When the two disagree the build still completes
    but the review silently renders in the wrong issue. This check makes
    that mismatch explicit so the build raises with a clear message.

    Only files under ``corpus_root`` are checked; synthetic paths from
    unit tests fall through unchanged. When ``corpus_root`` is ``None``
    the loader resolves it from :mod:`src._corpus`.
    """
    if corpus_root is None:
        from src._corpus import CORPUS_ROOT
        corpus_root = CORPUS_ROOT
    corpus_root = corpus_root.resolve()

    errors: list[str] = []
    for path, review in parsed:
        try:
            rel = path.resolve().relative_to(corpus_root)
        except ValueError:
            continue  # not in the canonical corpus tree (test fixture, etc.)
        # rel == "{N}/reviews/{slug}-tei.xml" — three parts, middle is "reviews"
        parts = rel.parts
        if len(parts) != 3 or parts[1] != "reviews":
            errors.append(
                f"{path.name}: unexpected path {rel} — "
                f"expected issues/{{N}}/reviews/{{slug}}-tei.xml"
            )
            continue
        folder_issue = parts[0]
        if folder_issue != review.issue:
            errors.append(
                f"{path.name}: located in issues/{folder_issue}/reviews/ "
                f"but biblScope @n is {review.issue!r} — "
                f"move the file or fix the TEI header so they agree"
            )
    return errors


def order_reviews(
    issue_no: str,
    issue_reviews: list[Review],
    config: Optional[IssueConfig],
) -> list[Review]:
    """Return reviews for one issue in the order set by the config, or
    the natural id-order fallback when no order is configured."""
    if config and config.contribution_order:
        idx = {rid: i for i, rid in enumerate(config.contribution_order)}
        return sorted(issue_reviews, key=lambda r: idx.get(r.id, len(idx)))
    return sorted(issue_reviews, key=lambda r: r.id)
