# ride-static

Static-site generator for [ride.i-d-e.de](https://ride.i-d-e.de) — *RIDE. A review journal for digital editions and resources*, published by the Institut für Dokumentologie und Editorik (IDE).

The pipeline reads 107 TEI XML reviews under `../ride/tei_all/`, a small editorial Markdown layer under `content/`, and one YAML configuration per issue. From those inputs, a single GitHub Actions workflow produces a complete `site/` tree — per-review HTML and PDF, aggregation pages, a Pagefind index, OAI-PMH and JSON-LD interfaces, sitemap. The output is fully static; no runtime server, no database, no per-request work beyond serving files and the client-side search.

The project replaces the previous eXist-based dynamic site. It is written in Python with Jinja templates; XSLT is not used. Every script and parser module ships with pytest fixtures, plus one optional smoke test against the real corpus that skips when the sibling repository is absent.

## Where to look

| Question | Source |
|---|---|
| Project conventions Claude operates under | `CLAUDE.md` |
| Setup, hard rules, contribution workflow | `CONTRIBUTING.md` |
| How to add a TEI element or render variant | `docs/extending.md` |
| URL contract, versioned | `docs/url-scheme.md` |
| Corpus structure, anomalies, K-refs | `knowledge/data.md` |
| Schema vs. corpus diff, Schematron rules | `knowledge/schema.md` |
| Architecture and domain model | `knowledge/architecture.md` |
| Build phases (15) and deploy plan | `knowledge/pipeline.md` |
| Functional and non-functional requirements | `knowledge/requirements.md` |
| Visual and interaction design | `knowledge/interface.md` |
| Session-by-session decisions and entry points | `Journal.md` |

The `knowledge/` directory is an Obsidian-style vault; cross-references use `[[wikilink]]` notation.

## Layout (short)

```
scripts/      Stage 0/1 — discovery and knowledge generation
src/          Stage 2+ — parser, domain model, render, build CLI
templates/    Jinja templates (Phase 8+)
config/       element-mapping.yaml and per-issue YAML (Phase 8+)
content/      editorial Markdown with frontmatter (Phase 9+)
inventory/    generated JSON artifacts, gitignored
knowledge/    six hand-written and generated docs
docs/         onboarding and extension references
tests/        pytest, run from repo root
```

The full layout, including the planned Phase-8-and-later directories, is documented in `CLAUDE.md`.

## Run it

```sh
python -m pytest tests/                # 88 tests, < 1 s on a current laptop
python scripts/inventory.py            # one of eleven discovery scripts
python -m src.build                    # build the static site (Phase 8+)
```

The corpus is expected at `../ride/`, configured via the path-resolution pattern documented in `CLAUDE.md`. The build is reproducible: each run records a `build-info.json` with corpus version, schema version, and commit hash.

## Status

Stages Discovery, Knowledge, and Domain-Model 2.A (header parser) are complete. The full plan covers fifteen sequential phases through deploy; current state and next entry point are recorded in `Journal.md`.

## Licence

Pipeline code, generated HTML output, and copied review images carry separate licences. Each is documented next to the artefact it covers; see `CONTRIBUTING.md` for the overview.
