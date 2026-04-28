# ride-static

Static site for [ride.i-d-e.de](https://ride.i-d-e.de) (RIDE — Reviews in Digital Editions, published by IDE) built from the TEI corpus.

## Pipeline

TEI XML → Python/Jinja → HTML/PDF, deployed via GitHub Actions.

## Hard rules

- **No XSLT.** Python only.
- **TDD.** Every script gets a pytest with synthetic TEI fixtures (see `tests/`).
- **`knowledge/` is a clean Obsidian vault — `.md` only.** Generated JSON belongs in `inventory/`.
- **`inventory/` is gitignored** (visible, no leading dot). Always regeneratable from scripts.

## Layout

```
ride-static/
  scripts/        Python extractors (read sibling ../ride/, write inventory/)
  inventory/      Generated JSON artifacts — gitignored, source of truth for knowledge/*.md
  inventory/_cache/  Cached upstream downloads (e.g. p5subset.xml) — also gitignored
  knowledge/      Obsidian vault, .md only (data.md, schema.md, architecture.md, pipeline.md)
  tests/          pytest, run from repo root
  CLAUDE.md       this file
```

Source corpus lives in the **sibling** directory `../ride/`:

- `../ride/tei_all/*.xml` — 107 reviews
- `../ride/schema/ride.odd` — RIDE-specific TEI ODD
- `../ride/issues/` — per-issue dirs with images

Scripts dereference this via `REPO_ROOT.parent / "ride" / ...`.

## Stage 0 (Discovery) outputs

Each script in `scripts/` exposes `run(tei_dir, out_dir)` for testing plus a thin `main()` that writes to `inventory/`:

| Script | Output | Purpose |
|---|---|---|
| `inventory.py` | `elements.json`, `attributes.json`, `corpus-stats.json` | element/attribute usage, value distributions, presence ratios |
| `odd_extract.py` | `odd-summary.json` | modules, elementSpec customizations, Schematron rules |
| `structure.py` | `structure.json` | per-element children, child sequences, ancestor paths |
| `sections.py` | `sections.json` | `<div type>` + `<head>`-tree per review |
| `p5_fetch.py` *(planned)* | `tei-spec.json` | TEI P5 spec slice for elements actually used |
| `cross_reference.py` *(planned)* | `cross-reference.json` | empirical × P5 × ODD diff |

Run any: `python scripts/<name>.py`. Run tests: `python -m pytest tests/`.

## Conventions

- Structuring attributes (`@type`, `@subtype`, `@role`, `@cert`, `@n`) get **complete** value lists in `elements.json` (no top-N truncation), flagged via `values_complete: true`.
- All extractor scripts use the same path-resolution pattern: `REPO_ROOT = Path(__file__).resolve().parent.parent`.
- Output JSON: `indent=2`, `ensure_ascii=False`.
