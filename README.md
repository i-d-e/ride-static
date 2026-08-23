# ride-static

Static-site generator for [ride.i-d-e.de](https://ride.i-d-e.de) — *RIDE. A review journal for digital editions and resources*, published by the Institut für Dokumentologie und Editorik (IDE).

The pipeline reads the TEI XML review corpus under `issues/{N}/reviews/`, including both legacy flat files and self-contained review bundles, the editorial pages as TEI under `pages/` (with a Markdown fallback under `content/`), and one `metadata.yaml` per issue. A single GitHub Actions workflow produces a complete `site/` tree with per-review HTML and PDF, aggregation pages, a Pagefind index, OAI-PMH and JSON-LD interfaces, a sitemap, three syndication feeds (Atom, RSS 2.0, RSS 1.0/RDF), and a redirect layer that keeps the old WordPress URLs and feed paths working. The output is fully static; no runtime server, no database, no per-request work beyond serving files and the client-side search.

It replaces the previous eXist-based dynamic site. Written in Python with Jinja templates. Every script and parser module ships with pytest coverage; integration tests drive off the in-repo TEI files (Real-Corpus-Drive).

## Workflow overview

```
                ┌────────────────────────────────────┐
   inputs       │  issues/{N}/reviews/*-tei.xml      │   (legacy review layout)
                │  issues/{N}/reviews/{slug}/        │   (review.xml + pictures/ bundle)
                │  issues/{N}/metadata.yaml          │   (editorial metadata per issue)
                │  schema/{ride.odd, ride.rng}       │   (validation contract)
                │  pages/*.xml  (ride-pages.rng)     │   (editorial pages as TEI)
                │  content/*.md, content/home/*.md   │   (Markdown fallback, home widgets)
                │  config/{element-mapping,nav}.yaml │   (presentation + navigation)
                │  ../ride/issues/.../pictures/      │   (legacy figure fallback)
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
                │   │       factsheet/, *.pdf, *.xml}│
                │   ├─ tags/, reviewers/, resources/ │
                │   ├─ api/{corpus,build-info}.json  │
                │   ├─ oai/, sitemap.xml             │
                │   ├─ pagefind/                     │   Pagefind client-side search
                │   └─ static/{css, js, fonts}       │
                └────────────────────────────────────┘
```

## Editorial workflow

New reviews may enter the repository as self-contained review folders. Each folder contains the TEI source as `review.xml` and its associated pictures. The code calls this folder a review bundle. The legacy flat-file and sibling-picture layout remains supported for the existing corpus.

### Add a self-contained review folder

1. Add one folder under the target issue:

   ```text
   issues/19/reviews/teicrafter/
   ├── review.xml
   └── pictures/
       └── picture-1.svg
   ```

2. Use relative figure URLs in the TEI, for example `<graphic url="pictures/picture-1.svg"/>`. Add a concise `<figDesc>` after each content-bearing graphic. The build copies each file to the review's stable `figures/` output path and uses `figDesc` as its alternative text.
3. Keep a working review in draft state with `<revisionDesc status="draft">`. A draft may omit its DOI and must use a unique provisional `xml:id` in the form `draft.{lowercase-slug}`. Render it locally with `uv run python -m src.build --include-drafts`. The resulting page and factsheet carry a draft notice and `noindex`; the review remains absent from issue pages, feeds, sitemap, OAI-PMH, corpus data, bibliography exports, navigation, redirects, and the Pagefind index. After explicit approval and a commit, GitHub Pages exposes the same marked preview at its stable review URL.
4. Before publication, assign the registered review DOI, align `TEI/@xml:id` with that DOI, and remove the draft status or set it to `published`. The directory number and `<biblScope unit="issue" @n>` must agree.
5. Run `uv run python -m pytest tests/test_validate.py` and `uv run python -m src.build --include-drafts` for the complete local preview. On Linux with WeasyPrint system libraries, add `--pdf --pdf-drafts-only` to generate only the draft PDFs. The build discovers the TEI, validates new review folders strictly, copies the pictures, generates the deterministic wordcloud, and writes the review page, factsheet, XML download, and derived outputs. Commit and push only after explicit approval. The Pages build renders committed drafts as marked previews while every formal publication output continues to use published reviews exclusively.

A committed draft is public in both the Git repository and the GitHub Pages preview. Use the private companion repository for confidential review material; the draft flag controls formal publication outputs and does not provide access control.

### Try the complete review workflow

The repository includes three self-contained draft review folders under `issues/19/reviews/`. They provide public, explicitly marked workflow examples without changing a published review. The `teicrafter-pilot` folder is the primary walkthrough; the two other self-audits exercise the same path with different source material:

- [teiCrafter self-audit](https://i-d-e.github.io/ride-static/issues/19/draft.teicrafter-pilot/)
- [SZD OCR/HTR self-audit](https://i-d-e.github.io/ride-static/issues/19/draft.szd-htr-self-audit/)
- [ZBZ-OCR-TEI self-audit](https://i-d-e.github.io/ride-static/issues/19/draft.zbz-ocr-tei-self-audit/)

1. Prepare the locked environment and run the review validation.

   ```sh
   uv sync --locked
   uv run python -m pytest tests/test_validate.py
   ```

2. Build a preview that includes drafts, add the Pagefind search index, and serve the generated directory from its root. The Pagefind command requires Node.js.

   ```sh
   uv run python -m src.build --output review-preview --include-drafts
   npx -y pagefind --site review-preview
   uv run python -m http.server 8000 -d review-preview
   ```

3. Open `http://localhost:8000/drafts/`. Each draft entry exposes the same output set as its review page through one navigation row. The row contains Review, Factsheet, TEI XML and the PDF status.

4. Compare the generated output with the published issue 19 reference.

   [Review](https://i-d-e.github.io/ride-static/issues/19/ride.19.1/) |
   [Factsheet](https://i-d-e.github.io/ride-static/issues/19/ride.19.1/factsheet/) |
   [TEI XML](https://i-d-e.github.io/ride-static/issues/19/ride.19.1/ride.19.1.xml) |
   [PDF](https://i-d-e.github.io/ride-static/issues/19/ride.19.1/ride.19.1.pdf)

5. On Linux, generate the draft PDFs with the native WeasyPrint libraries installed.

   ```sh
   uv run python -m src.build \
     --output review-preview \
     --include-drafts \
     --pdf \
     --pdf-drafts-only
   ```

The GitHub Actions run publishes committed, approved examples as `noindex` GitHub Pages previews and also uploads the complete `draft-review-preview` artifact. After downloading and extracting that artifact, serve its extracted root with `python -m http.server`; opening nested HTML files directly from the filesystem does not provide the site-root URL semantics used by the generated pages. The artifact is retained for seven days and remains useful for a bounded review round.

### Legacy review layout

Existing reviews remain at `issues/{N}/reviews/{slug}-tei.xml`. Their figure URLs resolve through the sibling `i-d-e/ride` repository, and their wordclouds remain committed under `static/images/wordclouds/{review_id}.png`. The CLI `uv run python scripts/wordclouds.py --review <slug>` continues to regenerate those legacy thumbnails. Relax NG drift and missing sibling pictures remain warnings for this historical layout; the same findings are hard build failures in new bundles.

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

The workflow distinguishes public examples from confidential editorial drafts. Explicitly approved examples committed to this public repository appear on GitHub Pages with a draft notice and `noindex`; they remain excluded from all formal publication outputs. Confidential reviews stay in the private companion repository until a password-protected staging service has been selected. For local review, run

```sh
uv run python -m src.build --include-drafts
uv run python -m http.server -d site
```

and open `http://localhost:8000/drafts/` or `http://localhost:8000/issues/{N}/{draft-id}/`. Add `--pdf` only on a system with the native WeasyPrint dependencies installed; the deployment CI installs them, while a default Windows Python environment usually does not.

### Edit an editorial page (Editorial, Imprint, Criteria, …)

Editorial pages, everything outside the reviews and factsheets, are TEI. Each lives at `pages/{slug}.xml`, or at `pages/{section}/{slug}.xml` to carry a navigation section in its URL. They validate against the page profile `schema/ride-pages.rng`, a deliberately small grammar with a reduced `teiHeader` and a body of `div`/`head`/`p`/`list`/`table`/`eg` blocks plus `ref`/`persName`/`email`/`hi`/`code`/`lb` inline. The build parses each file into the `Page` model (`src/parser/page.py` → `src/model/page.py`) and renders it through `src/render/page.py` into the shared single-column `editorial.html` template. The deployed build renders these with precedence over the legacy Markdown.

The URL mirrors the file location (URL scheme v2). A file directly under `pages/` keeps a flat URL (`pages/criteria.xml` → `/criteria/`); a file in a section folder takes that prefix (`pages/about/team.xml` → `/about/team/`), matching its navigation section. See `docs/url-scheme.md`.

1. Edit the body of `pages/{slug}.xml` (or `pages/{section}/{slug}.xml`). Stay within the elements `ride-pages.rng` allows, or `tests/test_pages_schema.py` fails.
2. **Add a new page:** drop a new file under `pages/` that validates against the profile. Put it in a section folder (`pages/about/{newslug}.xml` → `/about/{newslug}/`) or at the top level for a flat `/{newslug}/`; `discover_pages()` finds it automatically. Add an entry to `config/navigation.yaml`, and `tests/test_render_navigation.py` checks that every menu URL resolves to a built page.
3. A few generator-native pages stay Markdown under `content/`: the About overview and the data charts/questionnaire pages (these are data-driven, not prose). For any slug no TEI page covers, `content/{slug}.md` renders as fallback. Pass `--no-tei-editorials` to build the Markdown set instead.
4. Home-page widgets live in `content/home/*.md` (frontmatter pattern). Global navigation is `config/navigation.yaml`; the loader validates every entry, so a typo breaks the build.

### Adjust TEI-to-HTML rendering

For most changes, edit `config/element-mapping.yaml` — it binds TEI elements to template paths and CSS classes without touching Python. Schema and contract are in `docs/extending.md`.

For new TEI elements or new domain shapes, see `docs/extending.md` (six files to touch: parser, dataclass, mapping, template, CSS, test).

## Build workflow

### Locally

```sh
uv sync --locked
uv run ruff check .
uv run python -m pytest tests/                       # full suite, run from repo root
uv run python -m src.build                           # full build → site/
uv run python -m http.server -d site                 # local preview at http://localhost:8000
```

`--pdf`, `--linkcheck`, `--base-url` and the remaining build flags are documented in full in `knowledge/pipeline.md`.

`uv run python -m src.build` runs three stages in order: **validate** (`src/validate.py`, Relax NG against `schema/ride.rng`), **parse** (`src/parser/`, TEI into immutable `Review` dataclasses; classifies references, copies figures from `../ride/issues/.../pictures/` if the sibling repo is present), **render** (`src/render/`, HTML + optional PDF + aggregations + OAI-PMH + JSON-LD + sitemap + corpus dump + redirects). Parse, strict bundle validation, bundle-asset, render, and requested PDF failures produce a non-zero exit code after `build-info.json` has recorded the diagnostics.

`schema/ride.odd` is the editable review schema source. `schema/ride.rng` is deterministic generated output. The pinned TEI Stylesheets and the compilation commands are documented in `CONTRIBUTING.md`; CI rejects any ODD/RNG drift.

Each run records `site/api/build-info.json` with commit hash, corpus version, validation findings, asset report, and licence — the build is reproducible.

### Discovery scripts

Stage-0/1 introspection lives in `scripts/`. Each script exposes `run(...)` for testing plus a `main()` that writes JSON to `inventory/` (gitignored) or Markdown to `knowledge/`. Full list and outputs: see `CLAUDE.md`. They run as part of CI but are not required for the build itself.

## Deploy workflow

Single workflow at `.github/workflows/build.yml`. Triggers on push to `main` (TEI / content / code paths), on manual `workflow_dispatch`, and on a notification from a companion repository (GitHub `repository_dispatch`): a push to `i-d-e/ride` (picture updates) or `i-d-e/ride-editors` (work in progress) can rebuild this site, because those pushes do not reach this repository on their own. The notification needs a small one-time setup per companion repository — one workflow file plus one access token; copy-ready templates and instructions are in `docs/upstream-workflows/`.

The workflow checks out this repo plus `i-d-e/ride` for picture assets and the pinned TEI Stylesheets for schema verification. It installs the locked uv environment and WeasyPrint system libraries, checks ODD/RNG synchronization, runs Ruff, pytest and the discovery scripts, builds the public site with PDFs and approved draft previews, and creates a separate downloadable draft-preview artifact before deploying `site/` to GitHub Pages. Draft previews remain outside issue listings, feeds, sitemap, OAI-PMH, corpus data, redirects, navigation, and Pagefind search.

The second checkout is the only remaining external dependency; it can drop once the ~437 MB of picture assets migrate into this repo (Git-LFS likely needed).

## Further reading

- `CONTRIBUTING.md` — setup, hard rules, conventions, and the pointer table to internal docs.
- `CLAUDE.md` — repository layout, script outputs, project conventions.
- `docs/extending.md` — adding a TEI element or render variant.
- `docs/url-scheme.md` — versioned URL contract.
- `knowledge/` — Obsidian-style vault with its own index (`knowledge/INDEX.md`): corpus reference (`data.md`, `schema.md`), design intent (`architecture.md`, `pipeline.md`), product specification (`specification.md`, `interface.md`). Cross-references use `[[wikilink]]` notation.
- `knowledge/journal.md` — session-by-session decisions and current entry point.

Per-directory READMEs describe their own folder:

- `scripts/README.md` — Stage 0/1 discovery scripts and their JSON/Markdown outputs.
- `src/README.md` — parser, model, render, and build modules with the data flow.
- `config/README.md` — `navigation.yaml` and the spec-only `element-mapping.yaml`.
- `static/README.md` — css, js modules, fonts, and vendored image assets.

## Status

The generator builds and deploys the current RIDE corpus. The latest verified state, outstanding work, and next working entry point are recorded in the [project journal](knowledge/journal.md).

The [knowledge index](knowledge/INDEX.md) provides access to the architecture, specification, interface design, and data documentation. Build, publication, draft preview, and staging behaviour are documented in the [pipeline](knowledge/pipeline.md).

## Licence

Pipeline code, generated HTML output, and copied review images carry separate licences. Each is documented next to the artefact it covers; see `CONTRIBUTING.md` for the overview.
