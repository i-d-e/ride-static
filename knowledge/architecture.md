# Architecture

> Design intent for the static-site generator. Hand-written;
> revisit when reality diverges from these assumptions.

## Inputs and outputs

**Inputs**
- `../ride/tei_all/*.xml` — review files (canonical source).
- `../ride/schema/ride.odd` — RIDE schema customisation.
- `inventory/*.json` — corpus knowledge (regenerated from the above).

**Outputs**
- `site/` — HTML pages, CSS, fonts, JS, images.
- `site/pdf/` — per-review PDFs.
- `site/search/index.json` — client-side search index.

## Layers

```
            ┌───────────────────────────────┐
            │  ride/tei_all/*.xml + ride.odd │   (read-only source)
            └──────────────┬─────────────────┘
                           │
          ┌────────────────▼────────────────┐
          │  scripts/                       │   Stage 0: Discovery (done)
          │  inventory, structure, sections,│
          │  odd_extract, p5_fetch,         │
          │  cross_reference, render_*      │
          └────────────────┬────────────────┘
                           │
                inventory/*.json + knowledge/*.md
                           │
          ┌────────────────▼────────────────┐
          │  src/parser/                    │   Stage 2: TEI → domain
          └────────────────┬────────────────┘
                           │
                       Domain objects
                  (Review, Section, Block …)
                           │
          ┌────────────────▼────────────────┐
          │  src/render/                    │   Stage 3+
          │  html · pdf · search_index      │
          └────────────────┬────────────────┘
                           │
                          site/
```

## Domain model

Templates and renderers never touch raw XML. They consume Python
objects that the parser produces from each TEI file.

- **`Review`** — one per file
  - `id`, `issue`, `language`, `publication_date`, `licence`
  - `editors: list[Editor]`, `authors: list[Author]`
  - `keywords: list[str]`
  - `questionnaire: Questionnaire` — the `<num>`-based classification payload (see `data.md`, `<num>` rule)
  - `front: list[Section]`, `body: list[Section]`, `back: list[Section]`
  - `bibliography: list[BibEntry]` (drawn from `<back>/<div type="bibliography">/<listBibl>/<bibl>`)
  - `relatedItems: list[RelatedItem]`

- **`Section`** — recursive
  - `xml_id` (synthesised from position when missing — see `data.md` "div without head" rule)
  - `type` — one of {`abstract`, `bibliography`, `appendix`, `None`}
  - `heading: str | None` (may be missing — fallback derived from `xml:id` or position)
  - `level` (1–3 max, per Schematron `ride.div-nesting`)
  - `blocks: list[Block]`
  - `subsections: list[Section]`

- **`Block`** types: `Paragraph`, `Heading`, `List`, `Table`, `Figure`, `Citation`, `CodeBlock`, `Note`.

- **`Inline`** types: `Text`, `Emphasis`, `Reference`, `Highlight`, `Note`.

The parser handles the known anomalies named in `data.md` and `schema.md` explicitly:

| Anomaly | Parser branch |
|---|---|
| 7 reviews without `<back>` | `Review.bibliography = []`, `Review.back = []` |
| `<num value="3">` | warn, treat as boolean unknown |
| `<list rend="numbered"`>, `"unordered">` | normalise to `ordered` / `bulleted` |
| `<ref type="crosssref">` | normalise to `crossref` |
| `<sourceDesc>` duplicated (1 review) | merge or pick first; warn |
| `<body>` starting with `<p>` or `<cit>` (7 reviews) | wrap in implicit single section |

Anything not yet listed but unknown should raise — silent coercion is forbidden.

## Renderers

Two output formats share the domain model:

- **`render/html.py`** — Jinja templates in `templates/html/`.
- **`render/pdf.py`** — PDF per review; engine choice deferred (WeasyPrint is the leading candidate).

Templates are dumb: they format `Review`/`Section`/`Block` instances and never reach into XML.

```
templates/html/
  base.html               page chrome
  index.html              corpus front page
  issue.html              issue TOC
  review.html             single review
  partials/
    section.html          recursive
    questionnaire.html    the <num> matrix
    bibliography.html
    blocks/
      paragraph.html, list.html, table.html, figure.html,
      citation.html, code.html, note.html
```

## Search and cross-references

- **Search index** — `render/search_index.py` builds a JSON index from the
  domain objects (heading text, paragraph text, keywords, author names,
  taxonomy terms). Loaded by client-side JS (Lunr or stork — decision deferred).
- **Internal `<ref @target="#xml-id">`** — resolved at build time so HTML
  contains real anchor links, not raw IDs. The parser maintains a per-review
  `xml_id → object` map.

## Build vs. runtime

The site is fully static. Everything is computed at build time. No server,
no database, no per-request work beyond serving files and running the
client-side search.

## Key design decisions

- **No XSLT.** Python only. RIDE has no XSLT expertise to maintain; Python keeps the team unblocked.
- **Domain model first.** Templates and renderers never see raw TEI.
- **Inventory-driven.** Anything the parser does is informed by `inventory/`. New elements or attributes that appear in the corpus must show up in the inventory before they are handled.
- **Anomalies are explicit.** Known data quirks become named branches in the parser. Unknown ones raise.
- **TDD throughout.** Every module ships with pytest using synthetic TEI fixtures.
- **Knowledge is committed; inventory is not.** `knowledge/*.md` is part of the repo (so a fresh clone can read the corpus knowledge); `inventory/*.json` is regeneratable and gitignored.

## Repository layout (target)

```
ride-static/
  scripts/                  Stage 0/1 — discovery + knowledge generation
  src/
    parser/                 TEI → domain
    model/                  domain types
    render/                 html, pdf, search_index
  templates/html/           Jinja templates
  inventory/                Generated, gitignored
  knowledge/                Obsidian vault, .md only
    data.md                 corpus structure reference
    schema.md               ride.odd reference
    architecture.md         this file
    pipeline.md             build & deploy
  tests/                    pytest
  site/                     Build output, gitignored
  CLAUDE.md
```

## Stages

| Stage | Status | Artifacts |
|---|---|---|
| 0 — Discovery | done | `inventory/*.json` |
| 1 — Knowledge | in progress | `knowledge/data.md`, `schema.md`, `architecture.md`, `pipeline.md` |
| 2 — Domain model | planned | `src/model/`, `src/parser/` |
| 3 — HTML render | planned | `src/render/html.py`, `templates/html/`, `site/` |
| 4 — Search index | planned | `src/render/search_index.py` |
| 5 — PDF render | planned | `src/render/pdf.py` |
| 6 — Deploy | planned | `.github/workflows/build.yml` |
