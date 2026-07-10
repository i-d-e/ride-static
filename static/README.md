# static/ — client assets copied verbatim to site/

No build step, no bundler. The build copies this tree into `site/static/`.

## css/

One stylesheet, `ride.css`. Design is driven by a `--ride-*` custom-property
token system (layout widths, colour, type scale) declared at `:root`; component
hooks follow the BEM convention that also names the classes the templates emit.
No preprocessor. The visual and interaction spec is `knowledge/interface.md`.

## js/

Plain ES modules loaded directly by the templates; no transpilation. Each module
is small and self-contained.

| Module | Responsibility |
|---|---|
| `cite-copy.js` | copies BibTeX or CSL-JSON for the current review from embedded `<script>` data blocks |
| `copy-link.js` | paragraph-permalink affordance: copies the absolute paragraph URL on click |
| `clipboard.js` | shared clipboard helper used by `cite-copy` and `copy-link`; async Clipboard API with a `<textarea>`/`execCommand` fallback for non-secure contexts |
| `explore.js` | interactive corpus exploration for `/data/explore/`; renders the facet browser and issue timeline with D3 from an inline JSON island |
| `nav.js` | exclusive-open for the `<details>` nav dropdowns (open one closes the rest, outside click / Escape close all); additive over the native no-JS behaviour |
| `pagefind.js` | defers loading of the Pagefind UI bundle into the navbar search container |

`vendor/d3.v7.min.js` is vendored (no CDN); `explore.js` consumes D3 as the
global that the classic `<script>` exposes.

## fonts/

Self-hosted web fonts, copied as-is. No external font CDN.

## images/

Site chrome (`logo-ide.png`, `logo-ide-grey.png`) plus `wordclouds/`, the
per-review thumbnail images named `ride.{issue}.{n}.png` (one `.jpg`). The
wordclouds are vendored source assets carried in from `ride-editors`; there is no
in-repo generator for them. A missing wordcloud is not an error; the renderer
falls back cleanly and the issue entry simply shows no thumbnail.
