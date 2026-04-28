# Architecture

> Design intent for the static-site generator. Hand-written;
> revisit when reality diverges from these assumptions.
>
> Anchored to [[requirements]] (product spec). Visual and interaction design is in [[interface]]. The phased build plan is in [[pipeline#Phasenplan]].

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

The model is designed for **two render targets** — HTML (Phase 8) and
PDF via WeasyPrint (Phase 13) — per [[requirements#A6 PDF-Pfad]]. No
HTML-specific assumption may leak into the dataclasses; presentation
concerns belong in the renderers.

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

The parser handles the known anomalies named in [[data]] and [[schema]] explicitly. The acceptance criteria for the rendered output sit in [[requirements#R1 Rezension lesen]]:

| Anomaly | Parser branch |
|---|---|
| 7 reviews without `<back>` | `Review.bibliography = []`, `Review.back = []` |
| `<num value="3">` | warn, treat as boolean unknown |
| `<list rend="numbered"`>, `"unordered">` | normalise to `ordered` / `bulleted` |
| `<ref type="crosssref">` | normalise to `crossref` |
| `<sourceDesc>` duplicated (1 review) | merge or pick first; warn |
| `<body>` starting with `<p>` or `<cit>` (7 reviews) | wrap in implicit single section |
| `<ref target="#K…">` — 5 209 refs (98.7 % of dangling internals) | resolve against the criteria document at the taxonomy's `@xml:base`, not as local anchors |
| `<ref target="#abb…">` and ~10 other prefixes (~70 refs) | unresolved — emit a warning and render as plain text |

Anything not yet listed but unknown should raise — silent coercion is forbidden.

## Renderers

Two output formats share the domain model:

- **`render/html.py`** — Jinja templates in `templates/html/`. Visual and interaction design is fixed in [[interface]]; templates implement that spec mechanically.
- **`render/pdf.py`** — PDF per review via WeasyPrint with own print stylesheet, per [[requirements#A6 PDF-Pfad]].

Templates are dumb: they format `Review`/`Section`/`Block` instances and never reach into XML. Apparate-Block layout (References, Figures, Notes as parallel sub-blocks) lives in the renderer, not the model — see [[interface#6 Apparate als parallele Blöcke]].

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
- **`<ref @target>` resolution** — three-step lookup at build time:
  1. If `target` starts with `#` and the anchor exists in the per-review
     `xml_id → object` map, render as a local HTML anchor.
  2. If `target` starts with `#K…` (5 209 cases — see `inventory/refs.json`),
     resolve against the criteria document at the matching taxonomy's
     `@xml:base`. The parser fetches the relevant criteria URL once per
     criteria set and maps each `K…` ID to the criterion description.
  3. External `http(s)://` targets pass through unchanged. Anything else
     emits a build-time warning and is rendered as plain text.

## Element-Mapping (declarative)

The bridge between the domain model and the rendered output is configured in `config/element-mapping.yaml`, not in Python. This makes the most common extension — wiring a new TEI element or variant to a template and CSS class — a YAML-only change. Implementing genuinely new behaviour still requires a Python dataclass and parser function, but ninety percent of presentation changes do not.

The mapping is a single YAML file with three top-level keys: `blocks`, `inlines`, `extensibility`. Each block or inline entry names the Jinja template, the CSS class, and optional variants for sub-kinds (e.g. list `bulleted` versus `ordered` versus `labeled`). The file is loaded once at the start of the build and consulted by every renderer.

```yaml
blocks:
  Paragraph:
    template: blocks/paragraph.html
    css_class: ride-paragraph
  List:
    template: blocks/list.html
    css_class: ride-list
    variants:
      bulleted: ride-list--bulleted
      ordered:  ride-list--ordered
      labeled:  ride-list--labeled
  Figure:
    template: blocks/figure.html
    css_class: ride-figure
    variants:
      graphic:      ride-figure--image
      code_example: ride-figure--code

inlines:
  Reference:
    template: inlines/reference.html
    css_class: ride-ref
    by_bucket:
      local:    ride-ref--local
      criteria: ride-ref--criteria
      external: ride-ref--external
      orphan:   ride-ref--orphan
  Emphasis:
    template: inlines/emphasis.html
    css_class: ride-emph

extensibility:
  unknown_element_strategy: warn-and-render-text   # or: raise
  warn_unknown_attributes: true
```

**What this covers and what it does not.** The mapping resolves the binding `domain class → template + CSS`. It does not encode parsing rules, anomaly handling, or business logic. Adding a new block kind that has new structural semantics still requires a dataclass in `src/model/` and a parser function in `src/parser/`. Adding a new visual variant of an existing kind, or rewiring a template path, is YAML-only.

This separation is the formal answer to [[requirements#N2 Erweiterbarkeit auf vier Ebenen]]. The four extension levels in N2 — new TEI elements, new attribute values, changed text-node behaviour, downstream build effects — map onto two action paths: the YAML for presentation, Python for semantics. The mechanics of each path live in `docs/extending.md`.

The mapping file is loaded in Phase 8 ([[pipeline#Phasenplan]]) and is the single source for all template-class associations from then on. CI fails if the mapping references a template path that does not exist or a domain class that the parser does not produce.

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

The high-level stage view kept for orientation. The detailed phase-by-phase
build plan lives in [[pipeline#Phasenplan]] and is anchored to the seventeen
R- and ten N-clauses in [[requirements]].

| Stage | Status | Artifacts |
|---|---|---|
| 0 — Discovery | done | `inventory/*.json` (incl. `ids.json`, `refs.json`, `taxonomy.json`) |
| 1 — Knowledge | done | `knowledge/data.md`, `schema.md`, `architecture.md`, `pipeline.md`, `requirements.md`, `interface.md` |
| 2 — Domain model | in progress | 2.A done (`src/model/review.py`, header parser); 2.B/2.C pending |
| 3 — Inhaltsbereich (HTML) | planned | `src/render/html.py`, `templates/html/`, rezensionsbezogene Seiten |
| 4 — Aggregations- und Editorialschicht | planned | Hefte, Tags, Reviewer, Resources, redaktionelle Markdown-Inhalte |
| 5 — Funktions- und Infrastrukturschicht | planned | Pagefind, OAI-PMH, JSON-LD, Validierung, Build-Bericht |
| 6 — PDF aus Domänenmodell | planned | WeasyPrint, gemäß [[requirements#A6 PDF-Pfad]] |
| 7 — Deploy und Ops | planned | GitHub-Actions-Workflow, Tracking, Accessibility-Audit |
