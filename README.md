# ride-static

Static-site generator for [ride.i-d-e.de](https://ride.i-d-e.de) — RIDE, *Reviews in Digital Editions*, published by IDE.

The site is built from 107 TEI XML reviews, a small set of editorial Markdown texts, and one YAML config per issue. A single GitHub Actions workflow turns these inputs into a fully static `site/` deployable to GitHub Pages — HTML reviews, PDF downloads, Pagefind search, OAI-PMH and JSON-LD machine interfaces. No backend, no database, no per-request server.

## Where to start

| If you want to … | Read |
|---|---|
| Contribute code or docs | `CONTRIBUTING.md` |
| Add a new TEI element or render variant | `docs/extending.md` |
| Understand the URL scheme | `docs/url-scheme.md` |
| Understand the corpus and its anomalies | `knowledge/data.md`, `knowledge/schema.md` |
| Understand the architecture | `knowledge/architecture.md` |
| Understand the build phases | `knowledge/pipeline.md` |
| Understand the product scope | `knowledge/requirements.md` |
| Understand the visual and interaction design | `knowledge/interface.md` |
| Track session-by-session work | `Journal.md` |
| Know the conventions Claude operates under | `CLAUDE.md` |

## Layout (short form)

```
scripts/      Stage 0/1 — discovery and knowledge generation
src/          Stage 2+ — parser, model, render, build CLI
inventory/    Generated JSON artifacts (gitignored)
knowledge/    Hand-written and generated docs (.md only)
templates/    Jinja templates for HTML and PDF rendering
config/       element-mapping.yaml and per-issue YAML configs
content/      Editorial Markdown (about, imprint, criteria, reviewers)
tests/        pytest suite
docs/         Onboarding and extension docs
```

The full layout is in `CLAUDE.md`.

## Run it

```sh
python -m pytest tests/                # run tests
python scripts/inventory.py            # one of the discovery scripts
python -m src.build                    # build the static site (Phase 8+)
```

Source corpus lives in the sibling directory `../ride/` — see `CLAUDE.md` for the path-resolution convention.

## Licence

See `CONTRIBUTING.md` for separate licences covering pipeline code, generated HTML output, and copied images.
