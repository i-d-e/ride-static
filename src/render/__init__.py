"""Render layer — domain objects to output formats.

Per knowledge/architecture.md, renderers consume immutable domain objects
from src.model and never touch raw XML. The two output paths share this
module:

* ``html.render_review(review, site)`` for Phase 8 HTML.
* ``pdf.render_review(review, site)`` for Phase 14 (planned).

The element-to-template binding is configured in
``config/element-mapping.yaml``; CSS classes follow the BEM convention
pinned there. Templates live under ``templates/html/``.
"""
