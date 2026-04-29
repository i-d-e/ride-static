"""External-link probe with Wayback-Machine fallback (Welle 10.C).

Walks every Review's bibliography and reviewed-edition references,
HEAD-checks each external URL with a short timeout, and records dead
links. For each dead link the module looks up the most recent snapshot
on the Internet Archive's Wayback Machine and stores both the original
and the archive URL in the per-build report — Phase 13 follow-up will
surface the archive URL in the rendered review when the original 404s.

Defensive choices:

* Network failures (DNS, TLS, timeout) count as "dead" — same outcome
  for the reader.
* The Wayback lookup is best-effort; if the Archive itself is slow we
  cap waits to 4 s and fall through with no replacement URL.
* The probe is opt-in via ``--linkcheck`` because a 1500-URL HEAD pass
  takes ~5 minutes and CI shouldn't pay that on every push.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Iterable, Iterator, Optional

from src.model.review import Review

WAYBACK_AVAILABILITY = "https://archive.org/wayback/available?url={url}"
PROBE_TIMEOUT = 8.0
WAYBACK_TIMEOUT = 4.0
WORKERS = 16


@dataclass(frozen=True)
class LinkProbe:
    """One link's check result."""

    url: str
    status: str  # "alive" | "dead" | "skipped"
    code: Optional[int] = None
    wayback_url: Optional[str] = None
    review_id: Optional[str] = None


@dataclass
class LinkReport:
    """Aggregated link-probe outcome for the build report."""

    probed: int = 0
    alive: int = 0
    dead: int = 0
    skipped: int = 0
    findings: list[LinkProbe] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "probed": self.probed,
            "alive": self.alive,
            "dead": self.dead,
            "skipped": self.skipped,
            "dead_links": [
                {
                    "url": p.url,
                    "code": p.code,
                    "review_id": p.review_id,
                    "wayback_url": p.wayback_url,
                }
                for p in self.findings
                if p.status == "dead"
            ],
        }


def _is_external(url: str) -> bool:
    return url.startswith("http://") or url.startswith("https://")


def collect_external_urls(reviews: Iterable[Review]) -> Iterator[tuple[str, str]]:
    """Yield ``(url, review_id)`` pairs for every external bibliography
    or reviewed-edition reference in the corpus.

    Deduplication is the caller's concern — the same URL legitimately
    surfaces across reviews and the report can show that.
    """
    for review in reviews:
        for ri in review.related_items:
            for target in ri.bibl_targets:
                if _is_external(target):
                    yield target, review.id
        for entry in review.bibliography:
            if entry.ref_target and _is_external(entry.ref_target):
                yield entry.ref_target, review.id


def _probe_one(url: str, review_id: str) -> LinkProbe:
    """Single HEAD with GET fallback, capped at PROBE_TIMEOUT seconds."""
    req = urllib.request.Request(url, method="HEAD")
    req.add_header("User-Agent", "ride-static linkcheck/1.0")
    try:
        with urllib.request.urlopen(req, timeout=PROBE_TIMEOUT) as resp:
            return LinkProbe(url=url, status="alive", code=resp.status, review_id=review_id)
    except urllib.error.HTTPError as exc:
        # Some servers refuse HEAD. Fall back to a tiny GET.
        if exc.code in (405, 501):
            try:
                req2 = urllib.request.Request(url)
                req2.add_header("User-Agent", "ride-static linkcheck/1.0")
                with urllib.request.urlopen(req2, timeout=PROBE_TIMEOUT) as resp2:
                    return LinkProbe(url=url, status="alive", code=resp2.status, review_id=review_id)
            except Exception:
                pass
        return LinkProbe(url=url, status="dead", code=exc.code, review_id=review_id)
    except Exception:
        return LinkProbe(url=url, status="dead", code=None, review_id=review_id)


def _wayback_lookup(url: str) -> Optional[str]:
    """Most-recent Internet-Archive snapshot URL, or None."""
    api = WAYBACK_AVAILABILITY.format(url=urllib.parse.quote(url, safe=""))
    try:
        with urllib.request.urlopen(api, timeout=WAYBACK_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        snap = data.get("archived_snapshots", {}).get("closest", {})
        if snap.get("available") and snap.get("url"):
            return snap["url"]
    except Exception:
        return None
    return None


def probe_links(
    reviews: Iterable[Review],
    *,
    workers: int = WORKERS,
    limit: Optional[int] = None,
) -> LinkReport:
    """Probe every external URL referenced by ``reviews``; return the report."""
    pairs = list(collect_external_urls(reviews))
    seen: dict[str, str] = {}
    for url, review_id in pairs:
        seen.setdefault(url, review_id)
    items = list(seen.items())
    if limit:
        items = items[:limit]

    report = LinkReport()
    if not items:
        return report

    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_to_pair = {
            pool.submit(_probe_one, url, review_id): (url, review_id)
            for url, review_id in items
        }
        for future in as_completed(future_to_pair):
            probe = future.result()
            report.probed += 1
            if probe.status == "alive":
                report.alive += 1
            else:
                # Lookup the wayback snapshot for dead links only.
                snap = _wayback_lookup(probe.url)
                report.findings.append(
                    LinkProbe(
                        url=probe.url,
                        status=probe.status,
                        code=probe.code,
                        wayback_url=snap,
                        review_id=probe.review_id,
                    )
                )
                report.dead += 1
    return report
