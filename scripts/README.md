# scripts/ — Stage 0/1 discovery and knowledge rendering

One-off introspection over the TEI corpus. Stage 0 discovers the corpus into
JSON under `inventory/`; Stage 1 renders two of the knowledge-vault documents
from that JSON. None of this is required for the site build in `src/`; it
produces the reference material the build code and its authors rely on.

Each script exposes `run(...)` for testing plus a thin `main()` that writes its
output. Shared TEI helpers (namespace constants, `localname`, `normalize`) live
in `_tei.py`; do not redefine them per script.

## Scripts and outputs

| Script | Writes | Purpose |
|---|---|---|
| `inventory.py` | `inventory/elements.json`, `inventory/attributes.json` | element and attribute usage: counts, parents, distinct values, presence |
| `structure.py` | `inventory/structure.json` | per-element children, common ordered child sequences, ancestor paths, depth |
| `sections.py` | `inventory/sections.json` | nested `<div type>` tree with `@subtype`, `xml:id`, and `<head>` text per review |
| `odd_extract.py` | `inventory/odd-summary.json` | ODD summary: imported P5 modules, elementSpec customisations, Schematron rules |
| `ids.py` | `inventory/ids.json` | per-file `xml:id` audit: parse errors and format conformance against the Schematron patterns |
| `refs.py` | `inventory/refs.json` | classifies `<ref @target>` as internal / external_url / other; flags dangling internal anchors |
| `taxonomy.py` | `inventory/taxonomy.json` | RIDE questionnaire taxonomies plus each review's per-category answers (`@value` 0/1) |
| `p5_fetch.py` | `inventory/tei-spec.json` | TEI P5 normative spec slice for the elements the corpus uses (downloads `p5subset.xml`, cached at `inventory/_cache/`) |
| `cross_reference.py` | `inventory/cross-reference.json` | joins empirical inventory × P5 spec × ODD; diffs corpus usage against both |
| `render_data.py` | `knowledge/data.md` | corpus structure-and-knowledge reference (Stage 1 render) |
| `render_schema.py` | `knowledge/schema.md` | RIDE schema reference including ODD-vs-corpus value diffs (Stage 1 render) |
| `compile_schema.py` | `schema/ride.rng` | deterministic ODD-to-Relax-NG compilation with pinned TEI Stylesheets; `--check` verifies drift without writing |
| `_tei.py` | — | shared helpers for the above; not runnable on its own |

## Workflow

```
Stage 0  Discovery                          Stage 1  Render
inventory.py ─┐
structure.py  │
sections.py   ├─→ inventory/*.json ─→ render_data.py   ─→ knowledge/data.md
odd_extract.py│                        render_schema.py ─→ knowledge/schema.md
ids.py        │
refs.py       │   (cross_reference.py consumes
taxonomy.py   │    elements/tei-spec/odd-summary;
p5_fetch.py   │    render_* consume the inventory set)
cross_reference.py ─┘
```

`render_data.py` reads most of the inventory set; `render_schema.py` reads
`elements.json`, `odd-summary.json`, and `cross-reference.json`. Run the Stage-0
scripts before the renderers.

## Running

From the repo root:

```sh
uv run python scripts/<name>.py        # writes its output
uv run python scripts/inventory.py     # e.g. elements.json + attributes.json
```

`compile_schema.py` is separate from the inventory DAG. Run it after editing
`schema/ride.odd`; it requires Java and TEI Stylesheets 7.60.0. The exact
checkout and commands are documented in `CONTRIBUTING.md`.

`inventory/` is gitignored (visible, no leading dot) and regeneratable at any
time from these scripts. The generated `knowledge/data.md` and
`knowledge/schema.md` must not be hand-edited; change the renderer instead.
