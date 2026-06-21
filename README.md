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

Reviews are prepared in the private companion repository `i-d-e/ride-editors`. Its convention: one folder per issue (`issue-{name}/`), inside it one folder per review (`{slug}/`) holding the TEI file `{slug}-tei.xml`, the figure images in `pictures/`, and the article image `{slug}-wordcloud.png`, next to working material (submissions, versions, peer review). Publishing a review means carrying these three pieces over, as described below.

### Publish a review (from ride-editors)

1. Finish the TEI in `ride-editors`. Figure references keep the canonical URL form `https://ride.i-d-e.de/wp-content/uploads/issue_{N}/{slug}/pictures/{file}`; the build rewrites them to the static site at build time. The `<fileDesc>` carries the issue number:
   ```xml
   <seriesStmt>
     <biblScope unit="issue" n="22"/>   <!-- ← matches issues/22/ -->
   </seriesStmt>
   ```
2. Copy the TEI file into this repository at `issues/{N}/reviews/{slug}-tei.xml`. The directory number and `biblScope @n` must match — the build stops with a clear error if they disagree.
3. Copy the images into the picture repository `i-d-e/ride` at `issues/issue{NN}/{slug}/pictures/` (two-digit issue number on disk, e.g. `issue05`, `issue22`). The pictures are the only part that still lives outside this repository, because of their size.
4. Copy the wordcloud into this repository as `static/images/wordclouds/{slug}.png` (or `.jpg`) — same file as in `ride-editors`, renamed to the bare slug. A missing wordcloud is not an error; the issue page simply shows no thumbnail for that entry.
5. Optionally check locally: `python -m pytest tests/test_validate.py` and `python -m src.build`. Then commit and push — CI rebuilds and deploys the whole site. An issue grows review by review (rolling release); every push republishes everything, so nothing can go stale.

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

### Preview before publication

How unpublished reviews are shown to authors and the IDE for final checking is an open editorial decision — the options (password-protected hosting vs. publicly built but unlisted pages) and a concrete proposal are written up in `knowledge/staging.md`. Until that is decided, a preview is generated locally: copy the draft TEI into `issues/{N}/reviews/` in a local working copy (without committing), then

```sh
python -m src.build --pdf
python -m http.server -d site
```

shows the complete site, draft included, at `http://localhost:8000/`.

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

python -m pytest tests/                             # full suite, run from repo root
python -m src.build                                 # full build → site/
python -m src.build --pdf                           # also produces per-review PDFs (WeasyPrint)
python -m src.build --linkcheck                     # probes external bibliography URLs (slow)
python -m src.build --base-url=/ride-static         # path prefix for GitHub Pages project page

python -m http.server -d site                       # local preview at http://localhost:8000
```

`python -m src.build` runs three stages in order: **validate** (`src/validate.py`, RelaxNG against `schema/ride.rng`), **parse** (`src/parser/`, TEI into immutable `Review` dataclasses; classifies references, copies figures from `../ride/issues/.../pictures/` if the sibling repo is present), **render** (`src/render/`, HTML + optional PDF + aggregations + OAI-PMH + JSON-LD + sitemap + corpus dump + redirects).

Each run records `site/api/build-info.json` with commit hash, corpus version, validation findings, asset report, and licence — the build is reproducible.

### Discovery scripts

Stage-0/1 introspection lives in `scripts/`. Each script exposes `run(...)` for testing plus a `main()` that writes JSON to `inventory/` (gitignored) or Markdown to `knowledge/`. Full list and outputs: see `CLAUDE.md`. They run as part of CI but are not required for the build itself.

## Deploy workflow

Single workflow at `.github/workflows/build.yml`. Triggers on push to `main` (TEI / content / code paths), on manual `workflow_dispatch`, and on a notification from a companion repository (GitHub `repository_dispatch`): a push to `i-d-e/ride` (picture updates) or `i-d-e/ride-editors` (work in progress) can rebuild this site, because those pushes do not reach this repository on their own. The notification needs a small one-time setup per companion repository — one workflow file plus one access token; copy-ready templates and instructions are in `docs/upstream-workflows/`.

The workflow checks out this repo plus `i-d-e/ride` for picture assets, installs Python + WeasyPrint system libs, runs pytest and the discovery scripts, runs `python -m src.build --pdf`, builds the Pagefind index, and deploys `site/` to GitHub Pages.

The second checkout is the only remaining external dependency; it can drop once the ~437 MB of picture assets migrate into this repo (Git-LFS likely needed).

## Further reading

- `CONTRIBUTING.md` — setup, hard rules, conventions, and the pointer table to internal docs.
- `CLAUDE.md` — repository layout, script outputs, project conventions.
- `docs/extending.md` — adding a TEI element or render variant.
- `docs/url-scheme.md` — versioned URL contract.
- `knowledge/` — Obsidian-style vault with its own index (`knowledge/INDEX.md`): corpus reference (`data.md`, `schema.md`), design intent (`architecture.md`, `pipeline.md`), product specification (`specification.md`, `interface.md`, `staging.md`). Cross-references use `[[wikilink]]` notation.
- `knowledge/journal.md` — session-by-session decisions and current entry point.

## Status

Live: per-review HTML and PDF, aggregation pages (tags, reviewers, resources), client-side search (Pagefind), OAI-PMH and JSON-LD interfaces, sitemap, RelaxNG validation, contact + licence + Matomo + WCAG polish. Open: WCAG 2.2-AA audit on the live site, Matomo CI secrets, custom-domain decision, pre-publication preview decision (`knowledge/staging.md`). Current state and next entry point are in `knowledge/journal.md`.

## Licence

Pipeline code, generated HTML output, and copied review images carry separate licences. Each is documented next to the artefact it covers; see `CONTRIBUTING.md` for the overview.
