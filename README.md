# ride-static

Static-site generator for [ride.i-d-e.de](https://ride.i-d-e.de) — *RIDE. A review journal for digital editions and resources*, published by the Institut für Dokumentologie und Editorik (IDE).

The pipeline reads 111 TEI XML reviews under `issues/{N}/reviews/`, a small editorial Markdown layer under `content/`, and one `metadata.yaml` per issue. A single GitHub Actions workflow produces a complete `site/` tree — per-review HTML and PDF, aggregation pages, a Pagefind index, OAI-PMH and JSON-LD interfaces, sitemap. The output is fully static; no runtime server, no database, no per-request work beyond serving files and the client-side search.

It replaces the previous eXist-based dynamic site. Written in Python with Jinja templates. Every script and parser module ships with pytest coverage; integration tests drive off the in-repo TEI files (Real-Corpus-Drive).

## Workflow overview

```
                ┌────────────────────────────────────┐
   inputs       │  issues/{N}/reviews/*-tei.xml      │   (canonical content)
                │  issues/{N}/metadata.yaml          │   (editorial metadata per issue)
                │  schema/{ride.odd, ride.rng}       │   (validation contract)
                │  content/*.md, content/home/*.md   │   (editorial pages, home widgets)
                │  config/{element-mapping,nav}.yaml │   (presentation + navigation)
                │  ../ride/issues/.../pictures/      │   (figure assets — still external)
                └─────────────────┬──────────────────┘
                                  │
                ┌─────────────────▼──────────────────┐
   scripts/     │  Discovery (inventory, structure,  │   one-off introspection
                │  sections, ids, refs, taxonomy,    │   → inventory/*.json
                │  odd_extract, p5_fetch,            │   → knowledge/data.md
                │  cross_reference, render_*)        │     knowledge/schema.md
                └─────────────────┬──────────────────┘
                                  │
                ┌─────────────────▼──────────────────┐
   src/         │  parser/    TEI → Review domain    │   immutable dataclasses
                │  render/    Review → HTML/PDF/JSON │
                │  build.py   end-to-end CLI         │
                │  validate.py  RelaxNG pre-build    │
                └─────────────────┬──────────────────┘
                                  │
                ┌─────────────────▼──────────────────┐
   outputs      │  site/                             │   uploaded to GitHub Pages
                │   ├─ issues/{N}/{id}/{index.html,  │     by .github/workflows/build.yml
                │   │            review.pdf, *.xml}  │
                │   ├─ tags/, reviewers/, resources/ │
                │   ├─ api/{corpus,build-info}.json  │
                │   ├─ oai/, sitemap.xml             │
                │   ├─ pagefind/                     │   Pagefind client-side search
                │   └─ static/{css, js, fonts}       │
                └────────────────────────────────────┘
```

## Editorial workflow

### Add a review to an existing issue

1. Write the review as TEI per `schema/ride.odd`, including in `<fileDesc>`:
   ```xml
   <seriesStmt>
     <biblScope unit="issue" n="22"/>   <!-- ← matches issues/22/ -->
   </seriesStmt>
   ```
2. Drop the file at `issues/{N}/reviews/{slug}-tei.xml`.
3. Run `python -m pytest tests/test_validate.py` and `python -m src.build` locally; the validator pins drift against `schema/ride.rng`, the build raises if `biblScope @n` and the directory disagree.
4. Commit, push, CI deploys.

### Add a new issue

1. Create `issues/{N}/metadata.yaml`:
   ```yaml
   issue: '23'
   title: 'Issue 23: Scholarly Editions'
   doi: 10.18716/ride.a.23
   status: regular              # or "rolling" for open volumes
   publication_date: 2026-09
   description: |
     Free-text intro shown above the contribution list.
   editors:
     - name: Ulrike Henny-Krahmer
       affiliation: Universität Rostock
       orcid: https://orcid.org/0000-0003-2852-065X
     - name: Finnja Borchardt
       role: assistant
   contribution_order:           # optional — fixes ordering on the issue page
     - ride.a.23.1
     - ride.a.23.7
   ```
   Only `issue:` is required. Schema (`src/render/issues_config.py`): `title`, `doi`, `status` (`regular`/`rolling`), `publication_date`, `description`, `editors[]`, `contribution_order[]`. Typos in field names break the build (no silent fail).
2. Add the first reviews under `issues/{N}/reviews/` as above.
3. The home page and issue-overview pages pick the new issue up on the next build; no further wiring needed.

### Edit an editorial page (About, Imprint, Criteria, …)

1. Open the Markdown file in `content/{slug}.md` (e.g. `content/about.md`). It uses frontmatter for `title`, `subtitle`, optional `order`.
2. Home-page widgets live in `content/home/*.md` and use the same frontmatter pattern.
3. Global navigation is in `config/navigation.yaml`; the loader validates every entry against discovered editorial pages, so a typo breaks the build.

### Adjust TEI-to-HTML rendering

For most changes, edit `config/element-mapping.yaml` — it binds TEI elements to template paths and CSS classes without touching Python. Schema and contract are in `docs/extending.md`.

For new TEI elements or new domain shapes, see `docs/extending.md` (six files to touch: parser, dataclass, mapping, template, CSS, test).

## Build workflow

### Locally

```sh
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m pytest tests/                             # 475 tests, ~20 s
python -m src.build                                 # full build → site/
python -m src.build --pdf                           # also produces per-review PDFs (WeasyPrint)
python -m src.build --linkcheck                     # probes external bibliography URLs (slow)
python -m src.build --base-url=/ride-static         # path prefix for GitHub Pages project page

python -m http.server -d site                       # local preview at http://localhost:8000
```

The build runs in two passes:

1. **Parse**: walks `issues/*/reviews/*-tei.xml`, parses every TEI into an immutable `Review` dataclass, classifies references (`local`/`criteria`/`external`/`orphan`), copies referenced figures from `../ride/issues/.../pictures/` (sibling repo, optional).
2. **Render**: writes per-review HTML, per-review PDF (`--pdf`), aggregation pages, OAI-PMH snapshot, JSON-LD, sitemap, corpus dump, redirects, build report.

Each run records `site/api/build-info.json` with commit hash, corpus version, validation findings, asset report, and licence — the build is reproducible.

### Discovery scripts (one-off)

Run any from the repo root; they read TEI from `issues/*/reviews/` and write JSON to `inventory/` (gitignored) or Markdown to `knowledge/`:

```sh
python scripts/inventory.py        # element/attribute usage → elements.json, attributes.json
python scripts/structure.py        # parent/child shapes → structure.json
python scripts/sections.py         # <div type> hierarchy per review → sections.json
python scripts/ids.py              # xml:id audit → ids.json
python scripts/refs.py             # <ref @target> classification → refs.json
python scripts/taxonomy.py         # criteria taxonomies → taxonomy.json
python scripts/odd_extract.py      # ride.odd modules + Schematron → odd-summary.json
python scripts/p5_fetch.py         # TEI P5 spec subset (cached) → tei-spec.json
python scripts/cross_reference.py  # empirical × P5 × ODD diff → cross-reference.json
python scripts/render_data.py      # → knowledge/data.md
python scripts/render_schema.py    # → knowledge/schema.md
```

## Deploy workflow

A single workflow at `.github/workflows/build.yml`. Triggers: push to `main` on TEI/content/code paths, or manual `workflow_dispatch`.

```
1. Checkout ride-static (TEI corpus + schema ship in-repo)
2. Checkout i-d-e/ride sibling — picture assets only
3. Setup Python 3.11, install requirements.txt
4. Install WeasyPrint system libs (Pango, HarfBuzz)
5. Run pytest
6. Run discovery scripts (Tier 1–4)
7. Run python -m src.build --pdf
8. Build Pagefind index (npx pagefind --site site)
9. Upload site/ as Pages artifact
10. Deploy to GitHub Pages
```

The second checkout is the only remaining external dependency; it can drop once the ~437 MB of picture assets migrate into this repo (Git-LFS likely needed).

## Development workflow

### Setup

Requirements: Python 3.11, git. Optional: clone `i-d-e/ride` as `../ride/` for live figure rendering.

```sh
git clone <this-repo>
cd ride-static
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest tests/                # confirm 475 pass
```

### Add a test

Place it at `tests/test_<name>.py`. Real-corpus integration tests look up files via the central helper:

```python
from src._corpus import find_tei, iter_tei_files

review = parse_review(find_tei("anemoskala"))     # by slug
for path in iter_tei_files():                     # all 111 reviews
    ...
```

Pure-function unit tests may use synthetic TEI fixtures — see CLAUDE.md "Hard rules" for the test-data philosophy. Synthetic-from-dataclass construction of `Review`/`Section`/`Block` is technical debt.

### Commit and branch conventions

Short imperative titles. See `CONTRIBUTING.md` for the rest.

## Repository layout

```
issues/{N}/
   metadata.yaml          editorially curated issue metadata (DOI, editors, …)
   reviews/*-tei.xml      the TEI reviews for this issue
schema/
   ride.odd, ride.rng     RIDE TEI ODD + compiled RelaxNG
scripts/                  Stage 0/1 — discovery, inventory, knowledge generation
src/
   _corpus.py             central corpus helper (iter_tei_files, find_tei, …)
   model/                 immutable domain dataclasses (Review, Section, Block, …)
   parser/                TEI → domain
   render/                domain → HTML/PDF/JSON
   build.py               end-to-end build CLI
   validate.py            RelaxNG pre-build validation
templates/html/           Jinja templates
static/                   css/, js/, fonts/, images/
config/                   element-mapping.yaml, navigation.yaml
content/                  editorial Markdown (about, imprint, team, …) + home/
inventory/                generated JSON artifacts — gitignored
knowledge/                Obsidian-style vault, .md only, wikilinks for cross-refs
docs/                     extending.md, url-scheme.md
tests/                    pytest, run from repo root
site/                     build output — gitignored
.github/workflows/        single build+deploy workflow
README.md / CLAUDE.md / CONTRIBUTING.md / Journal.md
```

## Where to look for more detail

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

## Status

Phases 0–14 and 15.A are complete (parser, render, aggregations, Pagefind, OAI-PMH/JSON-LD/sitemap, RelaxNG validation, WeasyPrint PDF, contact + licence + Matomo + WCAG polish). Phase 15.B (WCAG 2.2-AA audit on live site, Matomo CI secrets, custom-domain decision) is open. Current state and next entry point are in `Journal.md`.

## Licence

Pipeline code, generated HTML output, and copied review images carry separate licences. Each is documented next to the artefact it covers; see `CONTRIBUTING.md` for the overview.
