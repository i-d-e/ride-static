# ride-static

Static-site generator for [ride.i-d-e.de](https://ride.i-d-e.de) — *RIDE. A review journal for digital editions and resources*, published by the Institut für Dokumentologie und Editorik (IDE).

The pipeline reads the TEI XML reviews under `../ride/tei_all/`, a small editorial Markdown layer under `content/`, and one YAML configuration per issue. From those inputs, a single GitHub Actions workflow produces a complete `site/` tree — per-review HTML and PDF, aggregation pages, a Pagefind index, OAI-PMH and JSON-LD interfaces, sitemap. The output is fully static; no runtime server, no database, no per-request work beyond serving files and the client-side search.

The project replaces the previous eXist-based dynamic site. It is written in Python with Jinja templates. Every script and parser module ships with pytest coverage; integration tests run against the real corpus and skip cleanly when the sibling repository is absent.

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
| Functional and non-functional requirements | `knowledge/specification.md` |
| Visual and interaction design | `knowledge/interface.md` |
| Pre-publication preview — problem, options, proposal | `knowledge/staging.md` |
| Session-by-session decisions and entry points | `Journal.md` |

The `knowledge/` directory is an Obsidian-style vault with its own index (`knowledge/INDEX.md`); cross-references use `[[wikilink]]` notation.

## Layout (short)

```
scripts/      Stage 0/1 — discovery and knowledge generation
src/          Stage 2+ — parser, domain model, render, build CLI
templates/    Jinja templates
config/       element-mapping.yaml and navigation.yaml
content/      editorial Markdown with frontmatter, per-issue YAML
inventory/    generated JSON artifacts, gitignored
knowledge/    Promptotyping vault — hand-written and generated docs
docs/         onboarding, extension references, upstream workflow templates
tests/        pytest, run from repo root
```

The full layout is documented in `CLAUDE.md`.

## Run it

```sh
python -m pytest tests/                # 473 tests, ~15 s on a current laptop
python scripts/inventory.py            # one of eleven discovery scripts
python -m src.build                    # build the static site into site/
python -m src.build --pdf              # …including per-review PDFs (WeasyPrint)
```

The corpus is expected at `../ride/`, configured via the path-resolution pattern documented in `CLAUDE.md`. The build is reproducible: each run records a `site/api/build-info.json` with build commit, validation findings, and asset summary.

## Editorial workflow — from `ride-editors` to the live site

Three repositories share the work. **`i-d-e/ride-editors`** (private) is the editors' workspace: one folder per issue (`issue-{name}/`), one folder per review (`{slug}/`) holding `{slug}-tei.xml`, `pictures/`, and `{slug}-wordcloud.png`. **`i-d-e/ride`** (public) is the published corpus: `tei_all/{slug}-tei.xml` plus the image tree `issues/issue{NN}/{slug}/pictures/`. **`ride-static`** (this repository) holds the generator, the editorial Markdown layer, and one YAML per issue.

### Publishing a review

1. **Finish the TEI in `ride-editors`** under the folder convention above. Figure references keep the canonical URL form `https://ride.i-d-e.de/wp-content/uploads/issue_{N}/{slug}/pictures/{file}` — the asset pipeline rewrites them to the static tree at build time.
2. **Move the review into `ride`**: the TEI file to `tei_all/{slug}-tei.xml`, the images to `issues/issue{NN}/{slug}/pictures/` (two-digit issue number on disk, e.g. `issue05`, `issue22`).
3. **Add the wordcloud** to this repository as `static/images/wordclouds/{slug}.png` (or `.jpg`) — a copy of `{slug}-wordcloud.png` from `ride-editors`, renamed to the bare slug. A missing wordcloud is not an error; the issue-page entry simply renders without a thumbnail.
4. **First review of a new issue?** Create `content/issues/{N}.yaml` in this repository:

   ```yaml
   issue: '23'
   title: 'Issue 23: …'
   doi: 10.18716/ride.a.23
   publication_date: 2026-09
   editors:
   - name: …
   - name: …
     role: assistant
   ```

   The issue page and its overview entry are generated from the corpus either way; the YAML supplies title, DOI, and editors. The build fails with a clear error when YAML and TEI headers disagree.
5. **Push.** A push to `ride` notifies this repository via `repository_dispatch` and the site rebuilds and deploys — review pages, issue pages, search index, PDFs, sitemap, OAI-PMH, and the JSON dump all regenerate from scratch; there is no per-page cache to invalidate. The sender workflow is a one-time install per content repository; templates and instructions live in `docs/upstream-workflows/`.

Rolling release is the normal mode: an issue grows review by review, and every push republishes the complete site.

### Previewing before publication

The pre-publication preview environment (password-protected vs. unlisted draft pages) is an open editorial decision; the options and the implementation proposal are documented in `knowledge/staging.md`. Until it is decided, previews are generated locally: copy the draft TEI into a local working copy of `../ride/tei_all/` (without committing) and its images into the `issues/` tree, then

```sh
python -m src.build --pdf
python -m http.server -d site/
```

renders the complete site, draft included, at `http://localhost:8000/`.

## Status

Phases 1–14 of the fifteen-phase plan are complete; Phase 15 (deploy and ops) is partially done — the GitHub Actions workflow builds and deploys to GitHub Pages, while the WCAG full audit, the production Matomo configuration, and the custom-domain decision remain open. Current state and the next entry point are recorded in `Journal.md`.

## Licence

Pipeline code, generated HTML output, and copied review images carry separate licences. Each is documented next to the artefact it covers; see `CONTRIBUTING.md` for the overview.
