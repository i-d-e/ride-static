# tests

Pytest suite for the ride-static pipeline. Run from the repo root.

## Test philosophy

The project's hard rule (see `CLAUDE.md`) governs where synthetic data is
allowed:

- **Integration tests drive the real corpus.** Anything that walks the
  domain model — parsers, page renderers, aggregations, the build — parses
  a real review from `issues/{N}/reviews/*-tei.xml` through `src.parser`
  and asserts the resulting shape, rather than constructing `Review` /
  `Section` / `Block` instances from synthetic dataclass values.
  Synthetic-from-dataclass construction hides parser regressions.
- **Pure functions and formatters may be synthetic.** A regex, classifier,
  validator, or a `Review → str/dict` formatter has a signature that is the
  only data form richer than its input, so a synthetic input is the crisp
  choice. Each such test names the exception in its docstring.
- **Genuine edge cases** the corpus does not carry (orphan reference,
  authorless review, unparseable date) keep a small synthetic fixture, or —
  preferably — start from a real parsed instance and adjust it with
  `dataclasses.replace()`. The docstring names the case.
- **Real-corpus tests skip cleanly** when the corpus is absent, so the unit
  suite still runs on a partial checkout.

## Shared fixtures (`conftest.py`)

Parsed once per session; each skips when the corpus is missing.

- `corpus_reviews` — every review, parsed via the real parser (tuple).
- `corpus_parsed` — every review as a `(path, Review)` pair, for consumers
  that need the source path (location / id-vs-DOI validators, redirect
  slugs).
- `corpus_review` — one stable, metadata-rich review (`makingandknowing` /
  `ride.21.4`: author with email, keywords, DOI, a questionnaire, figures,
  notes, bibliography, and the conventional `p1` / `ftn1` / `img1`
  anchors). Use it as the base for render tests; use `dataclasses.replace()`
  to pin the fields a test controls.
- `corpus_issue_reviews` — every review of one complete issue (issue 21),
  for aggregation-style tests that need a small but real set.

## Test groups

**Parser and model** (`test_parser_*.py`, `test_model.py`,
`test_validate.py`, `test_pages_schema.py`) — TEI → domain: header
metadata, section tree, blocks and inlines, bibliography, questionnaire,
reference resolution, editorial pages, plus RelaxNG validation and the
frozen dataclass model.

**Render** (`test_render_*.py`) — domain → output: per-review HTML,
factsheet, aggregation pages, JSON-LD, the corpus dump, sitemap, the three
syndication feeds (Atom in `test_render_feed.py`, RSS 2.0 in
`test_render_rss.py`, RSS 1.0/RDF in `test_render_rdf.py`, including the
legacy-path XML copies), OAI-PMH, redirects (including the legacy WP
listing-page stubs), navigation, questionnaire charts, and the explorer
data basis. Integration layers run on the shared corpus fixtures;
documented pure-formatter layers (e.g. the `_rfc3339` / `_rfc822` date
wideners) stay synthetic.

**Stage 0/1 scripts** (`test_inventory.py`, `test_structure.py`,
`test_sections.py`, `test_odd_extract.py`, `test_ids.py`, `test_refs.py`,
`test_taxonomy.py`, `test_cross_reference.py`, `test_p5_fetch.py`,
`test_render_data.py`, `test_render_schema.py`, `test_element_mapping.py`,
`test_tei_coverage.py`) — corpus inventory, audits, and the Markdown
knowledge renderers.

**Contracts** (`test_css_contract.py`, `test_js_modules.py`,
`test_render_explorer.py`) — interface pins: CSS token set, ES-module
structure of the static JS, and the `explorer.json` row schema
(field names, types, value ranges) that `static/js/explore.js` consumes.

**End to end** (`test_build_e2e.py`, `test_build.py`) — `test_build_e2e`
runs the full `src.build.build` once into a temp tree and asserts the exact
target paths of the core artefacts, that every corpus review gets a page,
and that the explorer row count tracks the corpus. `test_build` covers the
build helpers in isolation.

## Running

```
python -m pytest tests/                       # whole suite
python -m pytest tests/test_render_html.py    # one module
python -m pytest tests/ -k explorer           # by name
python -m pytest tests/ -k "not e2e"          # skip the full build
```

On a checkout without the TEI corpus the real-corpus tests skip and the
pure-function suite still runs.
