# ride-static

Static site for [ride.i-d-e.de](https://ride.i-d-e.de) (RIDE — Reviews in Digital Editions, published by IDE) built from the TEI corpus.

## Pipeline

TEI XML → Python/Jinja → HTML/PDF, deployed via GitHub Actions.

## Hard rules

- **No XSLT.** Python only.
- **TDD.** Every script and parser module ships with a pytest using synthetic TEI fixtures (`tests/`). The parser also has one real-corpus smoke test that skips when `../ride/` is not present.
- **`knowledge/` is a clean Obsidian vault — `.md` only.** Generated JSON belongs in `inventory/`.
- **`inventory/` is gitignored** (visible, no leading dot). Always regeneratable from scripts.
- **Anomalies are explicit.** Known data quirks (no `<back>`, `<num value="3">`, `<list rend="numbered">`, etc. — see `knowledge/data.md`) become named branches in the parser. Unknown ones must raise.

## Layout

```
ride-static/
  scripts/                Stage 0 / Stage 1 — discovery and knowledge generation
    _tei.py               shared TEI helpers (namespace constants, attribute names, localname, normalize)
    inventory.py, structure.py, sections.py, odd_extract.py    (corpus inventory)
    ids.py, refs.py, taxonomy.py                                (content audits)
    p5_fetch.py, cross_reference.py                             (spec join)
    render_data.py, render_schema.py                            (Markdown render)
  src/                    Stage 2+ — parser, model, render
    model/                domain types (Review, Person, Editor, …)
    parser/               TEI → domain
  inventory/              Generated JSON artifacts — gitignored
    _cache/               Cached upstream downloads (e.g. p5subset.xml)
  knowledge/              Obsidian vault, .md only
    data.md               corpus structure reference (generated)
    schema.md             ride.odd reference (generated)
    architecture.md       design intent (hand-written)
    pipeline.md           build & deploy plan (hand-written)
  tests/                  pytest, run from repo root
  CLAUDE.md               this file
```

Source corpus lives in the **sibling** directory `../ride/`:

- `../ride/tei_all/*.xml` — 107 reviews
- `../ride/schema/ride.odd` — RIDE-specific TEI ODD
- `../ride/issues/` — per-issue dirs with images

Scripts dereference this via `REPO_ROOT.parent / "ride" / ...`.

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
