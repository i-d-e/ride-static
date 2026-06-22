# ride-static

Static site for [ride.i-d-e.de](https://ride.i-d-e.de) (RIDE — Reviews in Digital Editions, published by IDE) built from the TEI corpus.

## Pipeline

TEI XML → Python/Jinja → HTML/PDF, deployed via GitHub Actions.

## Hard rules

- **TDD with real-corpus drive.** Every script and parser module ships with pytest coverage. **Integration tests use the real corpus** (`issues/{N}/reviews/*-tei.xml`) — parse a real review and assert the resulting domain shape, rather than constructing `Review`/`Section`/`Block` instances directly from synthetic dataclass values. Synthetic-from-dataclass construction is technical debt: it locks tests to the model contract while bypassing the parser, hiding parser regressions. **Pure-function unit tests** (regex, classifier, formatter) may use synthetic inputs because the function signature is the only data form richer than that — document this in the test docstring. **Edge cases that genuinely do not exist in the corpus** (truly unparseable URLs, future-proofing branches) keep a synthetic fixture but the docstring names the case as an explicit exception. Real-corpus tests skip cleanly when the corpus is absent so the unit suite runs on a partial checkout.
- **`knowledge/` is a clean Obsidian-style vault — Markdown plus referenced image attachments.** Generated JSON belongs in `inventory/`. Cross-references inside the vault use `[[wikilink]]` notation. Hand-written filenames are lowercase. Image attachments (e.g. `image-workflow.png`) live next to the Markdown that references them, the conventional Obsidian-vault layout.
- **`inventory/` is gitignored** (visible, no leading dot). Always regeneratable from scripts.
- **Anomalies are explicit.** Known data quirks (no `<back>`, `<num value="3">`, `<list rend="numbered">`, etc. — see `knowledge/data.md`) become named branches in the parser. Unknown ones must raise.
- **Journal at the end of every session.** Append a new dated entry to `knowledge/journal.md` (top of the entries section, five fixed fields) before closing a working session. Format documented at the top of `knowledge/journal.md`. The journal complements memory and git: it captures *why* and *next-step*, not just *what changed*.

## Layout

```
ride-static/
  scripts/                Stage 0 / Stage 1 — discovery and knowledge generation
    _tei.py               shared TEI helpers (namespace constants, localname, normalize)
    inventory.py, structure.py, sections.py, odd_extract.py    (corpus inventory)
    ids.py, refs.py, taxonomy.py                                (content audits)
    p5_fetch.py, cross_reference.py                             (spec join)
    render_data.py, render_schema.py                            (Markdown render)
  src/                    Stage 2+ — parser, model, render
    model/                domain types (Review, Person, Editor, …)
    parser/               TEI → domain
    render/, build.py     html, pdf, refs, assets, build CLI
  templates/html/         Jinja templates
  static/                 css/, js/, fonts/
  config/                 element-mapping.yaml, navigation.yaml
  pages/                  editorial pages as TEI (editorial, team, imprint, …); profile schema/ride-pages.rng
  content/                editorial Markdown: home widgets + Markdown fallback (about, data charts/questionnaires)
  issues/{N}/             TEI corpus, grouped per issue
    metadata.yaml         editorially curated issue metadata (DOI, editors, …)
    reviews/*-tei.xml     the TEI review files for this issue
  schema/                 ride.odd + ride.rng (reviews) + ride-pages.rng (editorial pages)
  inventory/              Generated JSON artifacts — gitignored
    _cache/               Cached upstream downloads (e.g. p5subset.xml)
  knowledge/              Obsidian-style vault, .md only, wikilinks for cross-refs
    INDEX.md              vault index — document matrix, reading paths, glossary
    data.md               corpus structure reference (generated)
    schema.md             ride.odd reference (generated)
    architecture.md       design intent — data flow, domain model (hand-written)
    pipeline.md           build & deploy plan with 15-phase plan (hand-written)
    specification.md      product requirements, user stories, fixed design decisions
    interface.md          visual & interaction design, layout, typography, a11y
    staging.md            pre-publication preview — options and proposal, decision open
    journal.md            session-by-session narrative
  docs/
    extending.md          how to add a new TEI element or render variant
    url-scheme.md         versioned URL contract
    upstream-workflows/   copy-ready dispatch senders for ride and ride-editors
  tests/                  pytest, run from repo root
  site/                   build output, gitignored
  README.md               short orientation for new visitors
  CONTRIBUTING.md         setup, conventions, hard rules
  CLAUDE.md               this file
```

The knowledge vault groups by purpose:

| Group | Files | Source |
|---|---|---|
| Corpus reference | `data.md`, `schema.md` | generated by `scripts/render_*.py` from `inventory/*.json` |
| Design intent | `architecture.md`, `pipeline.md` | hand-written |
| Product specification | `specification.md`, `interface.md`, `staging.md` | hand-written |

Cross-references inside `knowledge/` use **Obsidian wikilinks** (`[[filename]]` or `[[filename#anchor]]`). The vault is not opened in Obsidian as the daily editor, but the link syntax keeps it portable and lets the docs form a navigable web rather than isolated files.

Generated docs (`data.md`, `schema.md`) must not be edited by hand — changes go into `scripts/render_data.py` / `render_schema.py`. Hand-written docs are the only place where wikilinks may be added directly.

The TEI corpus and schema live **inside this repo**:

- `issues/{N}/reviews/*-tei.xml` — 111 reviews, grouped by issue number (`biblScope @n`)
- `issues/{N}/metadata.yaml` — per-issue editorial metadata (DOI, editors, contribution order, …)
- `schema/ride.odd` — RIDE-specific TEI ODD
- `schema/ride.rng` — compiled RelaxNG used by `src/validate.py`
- `pages/*.xml` — editorial pages as TEI (the non-review RIDE pages), profile `schema/ride-pages.rng`

Path lookups go through `src/_corpus.py` (`iter_tei_files`, `find_tei`, `CORPUS_ROOT`, `SCHEMA_ODD`, …). Per-issue **pictures** still live in the sibling repo `i-d-e/ride` under `../ride/issues/issue{NN}/{slug}/pictures/`; the asset pipeline reads them via `REPO_ROOT.parent / "ride"` and degrades cleanly when the sibling is absent. When pictures move into this repo too, that fallback drops.

## Stage 0/1 outputs

Each script in `scripts/` exposes `run(...)` for testing plus a thin `main()` that writes to `inventory/` (or `knowledge/` for renderers):

| Script | Output | Purpose |
|---|---|---|
| `inventory.py` | `elements.json`, `attributes.json`, `corpus-stats.json` | element/attribute usage, value distributions, presence ratios |
| `odd_extract.py` | `odd-summary.json` | modules, elementSpec customisations, Schematron rules |
| `structure.py` | `structure.json` | per-element children, child sequences, ancestor paths |
| `sections.py` | `sections.json` | `<div type>` + `<head>`-tree per review |
| `p5_fetch.py` | `tei-spec.json` | TEI P5 spec slice for elements actually used (cached at `inventory/_cache/p5subset.xml`) |
| `cross_reference.py` | `cross-reference.json` | empirical × P5 × ODD diff |
| `ids.py` | `ids.json` | per-file `xml:id` audit (parse errors, format violations against Schematron patterns) |
| `refs.py` | `refs.json` | classifies `<ref @target>` as internal / external_url / other; flags dangling internal anchors and bucket them by prefix |
| `taxonomy.py` | `taxonomy.json` | RIDE criteria taxonomies grouped by `@xml:base`, plus per-review category answers (`@value` 0/1) |
| `render_data.py` | `knowledge/data.md` | structure-and-knowledge reference for code that walks the corpus |
| `render_schema.py` | `knowledge/schema.md` | RIDE-specific schema reference, including ODD-vs-corpus diffs |

Run any: `python scripts/<name>.py`. Run tests: `python -m pytest tests/`.

## Conventions

- Structuring attributes (`@type`, `@subtype`, `@role`, `@cert`, `@n`) get **complete** value lists in `elements.json` (no top-N truncation), flagged via `values_complete: true`.
- All extractor scripts use the same path-resolution pattern: `REPO_ROOT = Path(__file__).resolve().parent.parent`.
- Shared TEI helpers (namespace constants, `localname`, `normalize`) live in `scripts/_tei.py` — do not redefine them per script.
- Stage 2 parser uses lxml's namespace-prefixed `find()` and has its own helpers in `src/parser/common.py` (different paradigm from the iter-based scripts).
- Output JSON: `indent=2`, `ensure_ascii=False`.
- Domain types are immutable (`@dataclass(frozen=True)`), sequences typed as `tuple[...]` for hashability.
