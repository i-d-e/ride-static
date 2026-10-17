"""Render layer — domain objects to output formats.

Per knowledge/architecture.md, renderers consume immutable domain objects
from src.model and never touch raw XML. The two output paths share this
module:

* ``html.render_review(review, site)`` for Phase 8 HTML.
* ``pdf.render_review(review, site)`` for Phase 14 (planned).

The dispatcher in ``templates/html/partials/render.html`` implements
the element-to-markup binding. ``config/element-mapping.yaml`` records
the tested template and BEM-class reference; the build does not load it.
Presentation changes update the dispatcher, CSS and mapping reference.
"""
