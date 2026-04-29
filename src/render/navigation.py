"""Globale Navigation, geladen aus ``config/navigation.yaml``.

Public API:

* :func:`load_navigation` parses the YAML into immutable
  :class:`NavItem` objects. Pure function — no corpus, no I/O beyond
  reading the file.
* :func:`resolve_navigation` resolves data-driven children. Today the
  only kind is ``issues``: the entry's submenu is built from the
  corpus, listing the last N issue numbers plus an "All Issues" link.
  Pure function over (items, reviews).

The build hands the resolved tuple to every template via the render
context. Templates iterate without knowing where the entries came from.

Spec anchors:
    - knowledge/requirements.md R11.5 (config-driven Navigation)
    - knowledge/interface.md §4 (five top-level entries, <details> Dropdowns)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

import yaml

from src.model.review import Review
from src.render.html import REPO_ROOT

CONFIG_PATH = REPO_ROOT / "config" / "navigation.yaml"


@dataclass(frozen=True)
class NavLink:
    label: str
    url: str


@dataclass(frozen=True)
class NavItem:
    """One top-level navigation entry.

    ``url`` is the click target on the top-level label. For dropdown
    items it serves as a fallback (e.g. clicking "Issues" goes to the
    issues overview). Items with neither ``children`` nor a
    ``children_kind`` are leaf-only links (Reviewing Criteria).
    """

    label: str
    url: Optional[str] = None
    children: tuple[NavLink, ...] = ()
    children_kind: Optional[str] = None
    children_count: Optional[int] = None
    fallback_url: Optional[str] = None

    @property
    def has_dropdown(self) -> bool:
        return bool(self.children) or self.children_kind is not None


def load_navigation(path: Path = CONFIG_PATH) -> tuple[NavItem, ...]:
    """Parse the navigation YAML; raises FileNotFoundError if missing."""
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    items_raw = data.get("items") or []
    out: list[NavItem] = []
    for raw in items_raw:
        children_raw = raw.get("children") or []
        children = tuple(
            NavLink(label=str(c["label"]), url=str(c["url"]))
            for c in children_raw
        )
        out.append(
            NavItem(
                label=str(raw["label"]),
                url=raw.get("url"),
                children=children,
                children_kind=raw.get("children_kind"),
                children_count=raw.get("children_count"),
                fallback_url=raw.get("fallback_url"),
            )
        )
    return tuple(out)


def _issue_children(reviews: Sequence[Review], count: int) -> tuple[NavLink, ...]:
    """Build the Issues submenu — last N issues + "All Issues" link.

    Issues are sorted descending by their numeric prefix so the most
    recent issue is first. Reviews without an issue value are silently
    dropped — they cannot belong to any issue.
    """
    seen: list[str] = sorted({r.issue for r in reviews if r.issue}, key=_issue_sort_key, reverse=True)
    most_recent = seen[:count]
    out: list[NavLink] = [NavLink(label="All Issues", url="/issues/")]
    for issue in most_recent:
        out.append(NavLink(label=f"Issue {issue}", url=f"/issues/{issue}/"))
    return tuple(out)


def _issue_sort_key(issue: str) -> tuple[int, str]:
    """Sort key — numeric where possible, alpha fallback.

    Issue numbers are usually integers ("1", "2", ..., "20"), but the
    spec allows letter suffixes ("11x") for special editions. The tuple
    keeps numeric ordering for the common case and falls back to
    lexicographic for the rest.
    """
    digits = ""
    for ch in issue:
        if ch.isdigit():
            digits += ch
        else:
            break
    n = int(digits) if digits else -1
    return (n, issue)


def resolve_navigation(
    items: Sequence[NavItem],
    reviews: Sequence[Review] = (),
) -> tuple[NavItem, ...]:
    """Replace data-driven children with concrete links.

    Today only ``children_kind == "issues"`` is recognised. Unknown
    kinds raise ValueError so a typo in the YAML is loud, not silent.
    """
    out: list[NavItem] = []
    for item in items:
        if item.children_kind == "issues":
            count = item.children_count or 4
            resolved = _issue_children(reviews, count)
            out.append(
                NavItem(
                    label=item.label,
                    url=item.url or item.fallback_url,
                    children=resolved,
                    fallback_url=item.fallback_url,
                )
            )
        elif item.children_kind is not None:
            raise ValueError(
                f"navigation.yaml: unknown children_kind {item.children_kind!r} for {item.label!r}"
            )
        else:
            out.append(
                NavItem(
                    label=item.label,
                    url=item.url or item.fallback_url,
                    children=item.children,
                    fallback_url=item.fallback_url,
                )
            )
    return tuple(out)
