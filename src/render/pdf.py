"""PDF rendering via WeasyPrint — Phase 14.

Per [[specification#R3 Rezension herunterladen]] and
[[specification#A6 PDF-Pfad]] every review ships a PDF next to its HTML
page. We feed WeasyPrint the already-rendered ``index.html`` so the
print output reflects the same domain model and templates as the web
view; the ``@media print`` block in ``ride.css`` strips chrome
(nav, sidebar, WIP banner) and surfaces a DOI line on the first page.

WeasyPrint pulls Pango/Cairo at import time. The import lives inside
:func:`render_review_pdf` so missing system libraries surface as a
per-call ``ImportError`` rather than aborting :mod:`src.build` at
module load — callers can then decide between skip and hard-fail.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote, urlsplit
import warnings


def _build_root(html_path: Path) -> Path:
    """Return the output root containing ``issues/`` and ``static/``."""
    for parent in html_path.resolve().parents:
        if parent.name == "issues":
            return parent.parent
    return html_path.resolve().parent


def _local_build_asset(url: str, html_path: Path) -> Path | None:
    """Map a root-relative rendered-site URL to its local build file."""
    url_path = unquote(urlsplit(url).path).replace("\\", "/")
    root = _build_root(html_path)
    for marker in ("/static/", "/issues/", "/pagefind/"):
        if marker not in url_path:
            continue
        relative = url_path.split(marker, 1)[1]
        candidate = root / marker.strip("/") / relative
        if candidate.is_file():
            return candidate
    return None


def render_review_pdf(html_path: Path, pdf_path: Path) -> None:
    """Render an already-written review HTML file to PDF on disk.

    Relative asset URLs resolve from the HTML file. Root-relative site
    URLs such as ``/static/css/ride.css`` and ``/issues/.../figures``
    are mapped to the current build output before WeasyPrint fetches them.

    Raises ``ImportError`` when WeasyPrint or its system libraries
    cannot be loaded. The build records that exception as a requested
    PDF failure and exits unsuccessfully after writing its report.
    """
    from weasyprint import HTML, URLFetcher  # local import — see module docstring

    url_fetcher = URLFetcher()

    def fetch_url(url: str):
        local_path = _local_build_asset(url, html_path)
        if local_path is not None:
            return url_fetcher.fetch(local_path.resolve().as_uri())
        return url_fetcher.fetch(url)

    html = HTML(filename=str(html_path), url_fetcher=fetch_url)
    try:
        html.write_pdf(target=str(pdf_path), pdf_tags=True)
    except ValueError as exc:
        if str(exc) != "Table wrapper without a table":
            raise
        pdf_path.unlink(missing_ok=True)
        warnings.warn(
            f"Tagged PDF failed for {html_path.parent.name}; retrying without PDF tags",
            RuntimeWarning,
            stacklevel=2,
        )
        HTML(filename=str(html_path), url_fetcher=fetch_url).write_pdf(
            target=str(pdf_path),
            pdf_tags=False,
        )
