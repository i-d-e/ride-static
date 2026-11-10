"""Polite, cached HTTP access for the parity check against the live RIDE site.

The parity check (`scripts/parity.py`) compares the running WordPress site
ride.i-d-e.de with the static rebuild. Every request to either site goes
through :class:`CachedFetcher`, which

- stores each response (status, selected headers, body) under a cache
  directory outside Git (default `inventory/_cache/parity/`, gitignored), so
  a repeated run compares the same bytes and does not touch the site again;
- waits at least ``min_interval`` seconds between two network requests
  (default one second, the courtesy limit agreed for the live site);
- never follows redirects itself: a 3xx response is cached with its
  ``Location`` header, and :meth:`CachedFetcher.resolve` walks the chain hop
  by hop, so redirects are evidence rather than hidden behaviour;
- sends a neutral User-Agent without personal identifiers.

Only GET is implemented; the parity check submits no forms and logs in
nowhere. Stdlib ``urllib`` is used deliberately (house rule: stdlib HTTP by
default), because the requests here are simple GETs.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote, urljoin

USER_AGENT = "ride-static-parity-check/1.0 (+https://github.com/i-d-e/ride-static)"
KEPT_HEADERS = ("content-type", "location", "last-modified", "content-length", "link")


@dataclass(frozen=True)
class Response:
    url: str
    status: int
    headers: dict[str, str]
    body: bytes
    from_cache: bool

    @property
    def content_type(self) -> str:
        return self.headers.get("content-type", "")

    @property
    def location(self) -> str | None:
        loc = self.headers.get("location")
        return urljoin(self.url, loc) if loc else None

    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")


def _ascii_url(url: str) -> str:
    """Percent-encode non-ASCII characters (tag slugs with accents) for the request line."""
    return quote(url, safe=":/?&=%#~+@,;!$*'()[]")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return None


class CachedFetcher:
    """GET with an on-disk cache and a minimum interval between network calls."""

    def __init__(self, cache_dir: Path, min_interval: float = 1.0, offline: bool = False) -> None:
        self.cache_dir = cache_dir
        self.min_interval = min_interval
        self.offline = offline
        self._last_request = 0.0
        self._opener = urllib.request.build_opener(_NoRedirect)
        self.network_requests = 0

    def _paths(self, url: str) -> tuple[Path, Path]:
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()
        sub = self.cache_dir / key[:2]
        return sub / f"{key}.json", sub / f"{key}.body"

    def get(self, url: str) -> Response:
        meta_path, body_path = self._paths(url)
        if meta_path.exists() and body_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            return Response(url, meta["status"], meta["headers"], body_path.read_bytes(), True)
        if self.offline:
            # Offline runs report an uncached URL as status 0 instead of fetching.
            return Response(url, 0, {}, b"", True)
        wait = self.min_interval - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(_ascii_url(url), headers={"User-Agent": USER_AGENT})
        try:
            with self._opener.open(req, timeout=60) as resp:
                status, raw_headers, body = resp.status, resp.headers, resp.read()
        except urllib.error.HTTPError as err:
            status, raw_headers, body = err.code, err.headers, err.read()
        except (urllib.error.URLError, TimeoutError) as err:
            # Network failure is cached nowhere: the next run retries.
            self._last_request = time.monotonic()
            return Response(url, -1, {"error": str(err)}, b"", False)
        self._last_request = time.monotonic()
        self.network_requests += 1
        headers = {k: raw_headers[k] for k in KEPT_HEADERS if raw_headers.get(k)}
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        body_path.write_bytes(body)
        meta = {
            "url": url,
            "status": status,
            "headers": headers,
            "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        return Response(url, status, headers, body, False)

    def head(self, url: str) -> int:
        """Status of a HEAD request, cached as metadata only (no body kept)."""
        meta_path, _ = self._paths(f"HEAD {url}")
        if meta_path.exists():
            return json.loads(meta_path.read_text(encoding="utf-8"))["status"]
        if self.offline:
            return 0
        wait = self.min_interval - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(
            _ascii_url(url), method="HEAD", headers={"User-Agent": USER_AGENT}
        )
        try:
            with self._opener.open(req, timeout=60) as resp:
                status = resp.status
        except urllib.error.HTTPError as err:
            status = err.code
        except (urllib.error.URLError, TimeoutError):
            self._last_request = time.monotonic()
            return -1
        self._last_request = time.monotonic()
        self.network_requests += 1
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta = {
            "url": url,
            "method": "HEAD",
            "status": status,
            "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return status

    def resolve(self, url: str, max_hops: int = 6) -> tuple[Response, list[tuple[int, str]]]:
        """Follow redirects hop by hop; return the final response and the chain."""
        chain: list[tuple[int, str]] = []
        resp = self.get(url)
        while 300 <= resp.status < 400 and resp.location and len(chain) < max_hops:
            chain.append((resp.status, resp.location))
            resp = self.get(resp.location)
        return resp, chain
