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

All sequence-typed fields use `tuple[...]` for immutability and hashability, per the convention in `CLAUDE.md`.

- **`Review`** — one per file
  - `id`, `issue`, `language`, `publication_date`, `licence`
  - `editors: tuple[Editor, ...]`, `authors: tuple[Author, ...]`
  - `keywords: tuple[str, ...]`
  - `questionnaires: tuple[Questionnaire, ...]` — the `<num>`-based classification payload (see [[data]], `<num>` rule). 105 reviews carry one taxonomy, 2 reviews carry two or three.
  - `front: tuple[Section, ...]` — **always carries the abstract** (107/107 reviews have exactly one Section with `type="abstract"` here, zero in body)
  - `body: tuple[Section, ...]`, `back: tuple[Section, ...]`
  - `figures: tuple[Figure, ...]`, `notes: tuple[Note, ...]` — corpus-order aggregates feeding the parallel apparate sub-blocks ([[interface#6]])
  - `bibliography: tuple[BibEntry, ...]` (drawn from `<back>/<div type="bibliography">/<listBibl>/<bibl>`)
  - `related_items: tuple[RelatedItem, ...]`

The TEI element `<bibl>` lives at three sites in the corpus and is parsed by three different paths into the same `BibEntry` shape (Phase 6.A unification): `<listBibl>/<bibl>` in `<back>` → `parse_bibliography` → `Review.bibliography`; `<cit>/<bibl>` inline in mixed content → `parse_bibl` from inside `parse_cit` → `Citation.bibl`; `<relatedItem>/<bibl>` in the header → `parse_related_items` → `Review.related_items` (this third path retains its own `RelatedItem` shape because the relatedItem wrapper carries `@type` semantics that BibEntry does not).

- **`Section`** — recursive
  - `xml_id` (synthesised from position when missing — see [[data]] "div without head" rule)
  - `type` — one of {`abstract`, `bibliography`, `appendix`, `None`}
  - `heading: tuple[Inline, ...] | None` (may be missing — fallback derived from `xml:id` or position)
  - `level` (1–3 max, per Schematron `ride.div-nesting`)
  - `blocks: tuple[Block, ...]`
  - `subsections: tuple[Section, ...]`

- **`Block`** types: `Paragraph`, `List`, `Table`, `Figure`, `Citation`. Empirically verified against the corpus: `<note>` is always inline (1900+ occurrences, all under `<p>`/`<head>`/`<quote>`/`<item>`), `<code>` is always inline (727 occurrences, no children), `<head>` is consumed by the section parser as section heading, `<eg>` lives only inside `<figure>` (modelled as `Figure(kind="code_example")`).

- **`Inline`** types: `Text`, `Emphasis`, `Highlight`, `Reference`, `Note`, `InlineCode`.

The parser handles the known anomalies named in [[data]] and [[schema]] explicitly. The acceptance criteria for the rendered output sit in [[requirements#R1 Rezension lesen]]:

| Anomaly | Parser branch |
|---|---|
| 7 reviews without `<back>` | `Review.bibliography = ()`, `Review.back = ()` |
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
  base.html               page chrome, OG metadata, lang propagation
  index.html              home page (current issue + selected reviews)
  issues.html             issues overview
  issue.html              single issue with TOC and contributor cards
  review.html             single review (header split, abstract, body, sidebar)
  tags.html, tag.html     tag overview and per-tag aggregation
  reviewers.html, reviewer.html
  resources.html          reviewed resources table
  data.html               questionnaire-derived charts
  editorial.html          about / imprint / criteria (content-only column)
  partials/
    apparate.html         parallel block: references | figures | notes
    questionnaire.html    the <num> matrix
    section.html          recursive
    blocks/
      paragraph.html, list.html, table.html, figure.html, citation.html
    inlines/
      reference.html, emphasis.html, highlight.html, note.html, code.html
```

The page-type set follows [[interface#4 Layout-Architektur]]; the parallel apparate block follows [[interface#6 Apparate als parallele Blöcke]].

## Search and cross-references

- **Search index** — Pagefind, per [[requirements#A4 Volltextsuche]]. Build-time generation against the rendered HTML in `site/`, client-side runtime via `static/js/search.js`. No bespoke `search_index.py` — Pagefind handles indexing and querying.
- **`<ref @target>` resolution** — four-bucket lookup at build time, fully specified in [[pipeline#Cross-cutting concerns]] and acceptance-tested against [[requirements#R1 Rezension lesen]]:
  1. Local anchor present in the per-review `xml_id → object` map → in-page HTML anchor.
  2. `#K…` prefix (5 209 cases — see `inventory/refs.json`) → external link to `{xml:base}#K…` on the criteria document. v1 does not resolve K-IDs to category titles; that is a possible later enhancement.
  3. External `http(s)://` → pass through.
  4. Anything else → build-time warning, rendered as plain text.

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

### Parser ↔ discovery-script boundary

`scripts/` and `src/parser/` both walk the TEI corpus, and a few patterns
appear in both. The split is intentional and worth knowing:

- `scripts/*.py` produces aggregated **discovery JSON** at build-time of the inventory only — `inventory/*.json` answers "what does the corpus actually contain?" and feeds the auto-rendered `knowledge/data.md` and `knowledge/schema.md`. Coarse aggregations are acceptable; over-attribution (e.g. `scripts/taxonomy.py` using `cat.iter()` to find any descendant `<num>`) is fine here because the consumer is a human reader of the JSON.
- `src/parser/*.py` produces **per-review domain objects** at site-build-time, consumed by templates and PDF renderer. Semantic precision matters; `parse_questionnaires` only collects from leaf categories so each `<num>` is attributed to exactly one answer.

Where the two layers parse the same TEI structure (taxonomy + num, reference classification, structure walks), they do it for different consumers with different precision requirements. Drift is mitigated by inventory-driven tests: every parser test that asserts a count against the corpus pins the inventory's number, so any divergence surfaces as a test failure.

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
    render/                 html, pdf, refs, assets, citation, corpus_dump
    build.py                Phase 8 build CLI: python -m src.build
  templates/html/           Jinja templates (Phase 8+)
  static/                   css/, js/, fonts/ (Phase 8+)
  config/
    element-mapping.yaml    domain class → template + CSS class (Phase 8+)
  content/                  editorial Markdown + per-issue YAML (Phase 9+)
    about.md, imprint.md, criteria.md
    issues/{n}.yaml
    reviewers/{slug}.md     optional
  inventory/                Generated, gitignored
  knowledge/                Obsidian-style vault, .md only
    data.md                 corpus structure reference (generated)
    schema.md               ride.odd reference (generated)
    architecture.md         this file
    pipeline.md             build & deploy plan with 15-phase plan
    requirements.md         product spec, R/N/A clauses
    interface.md            visual & interaction design
  docs/
    extending.md            how to add a new TEI element
    url-scheme.md           versioned URL contract
  tests/                    pytest
  site/                     Build output, gitignored
  README.md
  CONTRIBUTING.md
  Journal.md                session-by-session record
  CLAUDE.md                 project conventions
```

## Stages

A coarse orientation view. The fifteen-phase build plan lives in [[pipeline#Phasenplan]] and is the single source of truth for ordering, scope per phase, and requirement mapping. The four stages below group those phases.

| Stage | Phases | Status |
|---|---|---|
| Discovery + Knowledge | scripts/, knowledge/ | done |
| Domain model | 1–6 | 2.A done, 2.B–2.C pending |
| Site rendering | 7–10 | planned |
| Search, APIs, validation, PDF, deploy | 11–15 | planned |
