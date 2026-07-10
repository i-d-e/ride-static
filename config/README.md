# config/ — build configuration

## navigation.yaml

The global site navigation: five top-level entries with explicit or
data-driven submenus. Loaded by `src/render/navigation.py`
(`load_navigation` parses it into immutable `NavItem` objects,
`resolve_navigation` fills data-driven children such as the issues submenu).
The loader validates every entry, so a typo breaks the build.
`tests/test_render_navigation.py` (the nav guard) checks that every menu URL
resolves to a page the build actually produces. Adding an editorial page means
editing this YAML, not the templates.

## element-mapping.yaml

Documentation of the intended declarative bridge from `src/model/` block and
inline types to their Jinja template paths and BEM CSS classes.

Status: **spec-only / presentation reference.** This file is *not* loaded by
`src.build`. The templates in `templates/html/partials/render.html` dispatch
directly on dataclass class names and emit hard-coded BEM classes; the YAML is a
living contract kept in sync with that convention, pinned by
`tests/test_element_mapping.py` and `tests/test_tei_coverage.py`. A future phase
may activate it as a CI check. See `docs/extending.md` and
`knowledge/architecture.md` for the full rationale.
