"""PDF rendering via WeasyPrint — Phase 14.

Per [[requirements#R3 Rezension herunterladen]] and
[[requirements#A6 PDF-Pfad]] every review ships a PDF next to its HTML
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


def render_review_pdf(html_path: Path, pdf_path: Path) -> None:
    """Render an already-written review HTML file to PDF on disk.

    Relative asset URLs (figures, stylesheet, fonts) resolve relative
    to ``html_path``'s directory — the build writes everything next
    to ``index.html`` so this matches the deployed layout.

    Raises ``ImportError`` when WeasyPrint or its system libraries
    cannot be loaded. The caller is expected to print a helpful
    install hint and continue without PDFs rather than crash.
    """
    from weasyprint import HTML  # local import — see module docstring

    HTML(filename=str(html_path)).write_pdf(target=str(pdf_path))
