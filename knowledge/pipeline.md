---
title: Pipeline
project:
  name: ride-static
  repository: https://github.com/i-d-e/ride-static
method:
  name: Promptotyping
  url: https://dhcraft.org/excellence/blog/Promptotyping
status: active
created: 2026-04-28
updated: 2026-06-12
version: 0.2
topics:
  - "[[Static Site Generation]]"
related:
  - "[[specification]]"
  - "[[architecture]]"
  - "[[interface]]"
  - "[[staging]]"
  - "[[data]]"
---

# Pipeline

> Build and deploy plan. Hand-written; revise as the build reaches each stage.
>
> The phase table at the bottom is anchored to [[specification]]. Each phase
> names the R- and N-clauses it satisfies; conversely, every R- or N-clause
> in [[specification]] is covered by at least one phase. Architectural
> commitments are in [[architecture]].

## Local development

### Discovery scripts (run when the corpus changes)

The eleven Stage 0/1 scripts form a small DAG. Independent ones can run in
parallel; the dependent ones must wait. Locally, running them in this order
is safe and explicit:

```sh
# Tier 1 — independent extractors (parallel-safe)
python scripts/inventory.py        # elements.json, attributes.json, corpus-stats.json
python scripts/odd_extract.py      # odd-summary.json
python scripts/structure.py        # structure.json
python scripts/sections.py         # sections.json
python scripts/ids.py              # ids.json (xml:id audit)
python scripts/refs.py             # refs.json (link classification + dangling detection)
python scripts/taxonomy.py         # taxonomy.json (criteria sets + per-review answers)

# Tier 2 — needs Tier 1's elements.json + attributes.json
python scripts/p5_fetch.py         # tei-spec.json (caches p5subset.xml in inventory/_cache/)

# Tier 3 — needs elements.json, tei-spec.json, odd-summary.json
python scripts/cross_reference.py  # cross-reference.json

# Tier 4 — Markdown render, needs every JSON above
python scripts/render_data.py      # knowledge/data.md
python scripts/render_schema.py    # knowledge/schema.md
```

Output is `inventory/*.json` (gitignored) plus refreshed knowledge notes
(committed).

### Tests

```sh
python -m pytest tests/
```

### Build the site

```sh
python -m src.build                                # parses issues/*/reviews/, renders site/
python -m src.build --pdf                          # also produces a per-review PDF via WeasyPrint
python -m src.build --linkcheck                    # probe external bibliography URLs (slow)
python -m src.build --matomo-url URL --matomo-site-id ID   # emit cookieless tracker snippet
```

WeasyPrint (Phase 14) braucht GTK/Pango zur Laufzeit. Auf Linux genügt `apt install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0`; auf Windows fehlt der GTK3-Runtime und PDFs werden lokal übersprungen — die Tests skippen sauber statt zu crashen.

For local preview after a build: `python -m http.server -d site/` is sufficient. No `--serve` flag is in scope.

## GitHub Actions workflow (Phase 15)

A single workflow file `.github/workflows/build.yml` per [[specification#N10 Single-Workflow-Build]] — triggered on push to `main` (TEI corpus, Markdown texts, pipeline code), via `workflow_dispatch`, and via `repository_dispatch`, a cross-repository notification, from the two companion repositories whose pushes do not reach this repo on their own: a push to `i-d-e/ride` (picture assets) fires `corpus-updated`, a push to `i-d-e/ride-editors` (work in progress) fires `editors-updated`. The sender side is one copy-ready workflow file per companion repository plus a shared token secret; templates and install steps live in `docs/upstream-workflows/`. The `editors-updated` event stays dormant until the staging decision lands — see [[staging]].

```
1. Checkout ride-static (this repo) — TEI corpus ships under issues/{N}/reviews/
2. Checkout i-d-e/ride at sibling path ../ride — picture assets only
3. Setup Python 3.11
4. Install dependencies (lxml, jinja2, pytest, weasyprint, requests)
5. Run pytest
6. Run all scripts/*.py in dependency order
7. Run python -m src.build → site/
8. Upload site/ as artifact
9. Deploy to target (see "Deployment target" below)
```

The picture assets still live in the sibling `i-d-e/ride` repo;
`src/parser/assets.py` reads them via `REPO_ROOT.parent / "ride"` and
degrades cleanly when the sibling is absent. When pictures move into
this repo too, step 2 drops.

Cache `inventory/_cache/p5subset.xml` between runs to avoid re-downloading the 4 MB TEI P5 source on every build.

## Output structure

```
site/
  index.html                              corpus front page
  issues/
    1/                                    issue 1 TOC + reviews
      index.html
      <review-id>/
        index.html
        <review-id>.pdf
        figures/...
    2/...
    ...
  authors/
    <author-id>/index.html                author profile
  taxonomy/
    <category-id>/index.html              taxonomy node
  search/
    index.json
  static/
    css/, js/, fonts/
```

URL pattern: `https://ride-static.example/issues/{issue_no}/{review_id}/`

`{review_id}` matches the file basename without `-tei.xml`, e.g. `1641-tei.xml` → `1641`.

## Cross-cutting concerns

- **Asset handling (Phase 7).** Images referenced via `<graphic @url>` live in `../ride/issues/issue{NN:02d}/{slug}/pictures/`. `src/parser/assets.py::rewrite_figure_assets(review, ride_root, site_root)` copies them into `site/issues/{N}/{review_id}/figures/` and rewrites `Figure.graphic_url` to the site-root-relative form `/issues/{N}/{review_id}/figures/{file}`. Missing source files become entries in `AssetReport.missing` — no crash; Phase 13 aggregates the per-review reports.
- **Reference resolution (Phase 7).** `src/parser/refs_resolver.py::resolve_references(review)` runs as a post-pass in `parse_review` and writes `Reference.bucket ∈ {local, criteria, external, orphan, None}` on every `<ref>`:
  - `local` — `#xml-id` and the anchor exists in this review's `xml:id` index (sections, paragraphs, figures, notes, bibliography entries);
  - `criteria` — `#K…` (5 209 corpus cases, all in `<teiHeader>/<catDesc>`, none in body — see [[data#Reference resolution]]). Renderer dispatches to the external criteria document at the taxonomy's `@xml:base`;
  - `external` — `http(s)://`, passed through;
  - `orphan` — anything else (mailto:, bare bibkeys, `#abb…`-style dangling internals). Build-time warning, renderer falls back to plain text.
  Bucket is `None` when the source `<ref>` has no `@target` at all.
- **Cross-review references.** Reviews citing one another (via `<relatedItem>`) become hyperlinks if the target is in the corpus; otherwise they stay as bibliographic citations.
- **Schematron warnings.** Build prints (but does not fail on) Schematron violations from `inventory/cross-reference.json`. Hard failures are reserved for parsing errors. The full pre-build validation layer ([[specification#N3 Validierung als eigene Schicht]]) is implemented in Phase 13.
- **Lizenzhinweise pro Artefakt (N6).** Jedes maschinenlesbare Artefakt nennt seine Lizenz explizit, damit Konsumenten die Nutzungsbedingungen ohne Inferenz aus dem Footer kennen. Eine Quelle der Wahrheit: `LICENCE_NAME = "CC-BY-4.0"` und `LICENCE_URL = "https://creativecommons.org/licenses/by/4.0/"` in `src/render/corpus_dump.py`. Setzungs-Punkte: `site/api/corpus.json` (`licence: {name, url}` als Top-Level-Feld neben `version` und `review_count`); `site/api/build-info.json` (selbes Lizenzfeld); OAI-PMH `<dc:rights>` pro Record (aus `Review.licence` aus dem TEI-Quelltext); HTML-Footer als Mensch-lesbare Zeile mit ISSN, Brand und Imprint-Link. Die TEI-Dateien tragen ihre Lizenz im `<publicationStmt>/<licence>` selbst — kein Inject, keine zweite Wahrheit. PDFs (Phase 14) erben die Lizenzanzeige über das Print-Stylesheet aus dem HTML.
- **Cookieless Matomo (R16).** Tracker-Konfiguration ist deploy-time-bound, nicht code-bound. Build-Flags `--matomo-url` + `--matomo-site-id` werden gemeinsam gesetzt — `parser.error` wenn nur eines kommt, weil ein halbkonfigurierter Deploy still mit `setSiteId('')` Hits sendet. Lokal und im Default-CI-Lauf bleibt der Snippet weg, kein Tracker, kein Cookie-Banner, nichts zum Opt-out. Sobald die produktive Matomo-URL in CI als Secret hinterlegt ist, steigt das Snippet ein.
- **Console-Banner (N4-Manifestation).** Build-Commit + Datum erscheinen an drei Stellen: HTML-Footer (`<code>{commit_short}</code>` plus `data-commit`/`data-build-date`), `site/api/build-info.json` (`build.commit` und `build.commit_short`), und in der Devtools-Konsole als kleines `console.info`-Banner mit Brand-Pille. Das Banner ist gated auf `site.build_info.commit_short` — Dev-Builds ohne Git bleiben silent. Drei Manifestationen einer einzigen Quelle (`BuildInfo`-Dataclass aus `src/render/html.py`) — wer eine debuggt, hat sie alle.

## Deployment

GitHub Pages, per [[specification#2 Plattform und Architekturgrundsätze]]. Custom domain versus `<owner>.github.io/<repo>` is still open per [[specification#8 Offene Fragen]]; this affects the URL scheme stability promised in [[specification#R17 Stabile URLs]] and is to be decided before Phase 15.

For large artifacts (older PDF versions, OAI-PMH dumps): the choice between GitHub Pages and GitHub Releases is deferred per [[specification#8 Offene Fragen]].

## Re-deployment flow

```
git push main
  → GitHub Actions (single workflow, see [[specification#N10]])
      → pre-build validation (Phase 13, [[specification#N3]])
      → pytest
      → regenerate inventory/ (gitignored, in CI workspace only)
      → render knowledge/data.md and schema.md
      → src.build → site/  (HTML + PDF + Pagefind index + JSON-LD + OAI-PMH dump + sitemap)
      → upload build-info.json ([[specification#N4]])
      → deploy site/
```

`knowledge/*.md` regenerated in CI may diverge from the committed copy
when the corpus changed but the docs were not refreshed locally. Two
acceptable options:

- **Strict.** CI fails if regenerated docs differ from committed ones (forces local re-render before push).
- **Auto-commit.** CI commits the refreshed docs back. Risk of merge churn.

Strict is cleaner; pick before Phase 15.

## Resolved design decisions (locked by [[specification]])

| Decision | Resolution | Anchor |
|---|---|---|
| PDF engine | WeasyPrint, with own print stylesheet | [[specification#A6 PDF-Pfad]] |
| Search engine | Pagefind, build-time index, client-side runtime | [[specification#A4 Volltextsuche]] |
| Hosting platform | GitHub Pages | [[specification#2 Plattform und Architekturgrundsätze]] |
| Editorial format | TEI under `pages/` (A3); `content/*.md` legacy-active until the build cutover | [[specification#A3 Redaktionelle Texte]] |
| Tag source of truth | TEI only; WordPress retired post-consolidation | [[specification#A2 Datenquellen]] |
| Machine APIs | OAI-PMH + JSON-LD + JSON dump + sitemap with `schema.org/ScholarlyArticle` | [[specification#A5 Maschinenschnittstellen]] |

## Still open

- Knowledge-doc CI behaviour — strict vs. auto-commit (above).
- Custom domain vs. `<owner>.github.io/<repo>` ([[specification#8 Offene Fragen]]).
- Distribution path for large artifacts ([[specification#8 Offene Fragen]]).
- Reach of the WordPress-to-TEI consolidation ([[specification#8 Offene Fragen]]).
- Pre-publication preview environment — options and proposal in [[staging]], decision with the editorial team.

## Phasenplan

The build is split into fifteen sequential phases. Each phase produces one commit, has synthetic test fixtures plus a real-corpus smoke test, and respects the TDD rule from `CLAUDE.md`. Each row maps to the [[specification]] clauses it satisfies.

This table is the static plan, not a tracker. What is currently live and what is open lives in `Journal.md` (running ledger) and `README.md` (feature stand).

| # | Phase | Output | Requirements |
|---|---|---|---|
| 1 | Domain model — Section / Block / Inline | Frozen dataclasses; doc patch for `labeled` list and `figure/eg` | [[specification#A6 PDF-Pfad]] (zwei Renderings) |
| 2 | Section parser | Recursive sections, body-wrap anomaly, fallback `xml_id` | [[specification#R1 Rezension lesen]] (TOC, anchors) |
| 3 | Block parser | Paragraph, List (3 kinds), Table, Figure (graphic / code_example), Citation | [[specification#R1 Rezension lesen]] |
| 4 | Inline parser | Mixed-content walker; Text, Emphasis, Highlight, Reference, Note, InlineCode | [[specification#R1 Rezension lesen]] (lang, footnotes) |
| 5 | Integration in `parse_review` | `Review.body` populated for every TEI under `issues/{N}/reviews/` | [[specification#R1 Rezension lesen]] |
| 6 | Bibliography + Questionnaire | `BibEntry`, `Questionnaire` dataclasses + parsers; aggregates for tags, reviewers, reviewed resources | R1 (Bibliographie, Factsheet, Tags), R6, R7, R8, [[specification#A2 Datenquellen]] |
| 7 | Ref-Resolver + Asset-Pipeline | `Reference.bucket` ∈ {local, criteria, external, orphan} via `src/parser/refs_resolver.py`; image copy + URL rewrite via `src/parser/assets.py` | R1 (cross-refs, K-refs), [[specification#R17 Stabile URLs]] |
| 8 | HTML — Rezensionsseiten | Per-review HTML via Jinja; citation export (BibTeX, CSL-JSON); TEI + PDF download links; Open-Graph metadata; Copy-Link auf Absätze; Tooltip-Vorschau für Cross-Refs; vier kleine JS-Module | R1, [[specification#R2 Rezension zitieren]], [[specification#R3 Rezension herunterladen]], [[specification#R13 Sharing]], [[interface]] |
| 9 | Editorialschicht | Elf Editorial-Markdowns unter `content/` (Editorial, Publishing Policy, Ethical Code, Team, Peer Reviewers, Call for Reviews, Submitting a Review, Projects for Review, RIDE Award, Imprint, Reviewing Criteria); Home-Widgets unter `content/home/*.md`; per-issue YAML config unter `issues/{N}/metadata.yaml` mit Consistency-Check gegen TEI-Header; globale Navigation aus `config/navigation.yaml`. Die Editorialseiten-Quelle wird von Markdown auf TEI umgestellt (`pages/<slug>.xml`, validiert gegen `schema/ride-pages.rng`); der Build-Cutover (`pages/` in den Build rendern) steht noch aus. | [[specification#R10 Statische Inhalte pflegen]], [[specification#R11 Issue-Metadaten pflegen]], [[specification#R11.5 Globale Navigation pflegen]], [[specification#A3 Redaktionelle Texte]] |
| 10 | Aggregations- und Übersichtsseiten | Issue-Übersicht; Issue-Ansicht als redaktionelle Liste mit Wordcloud-Thumbnails, Citation und Abstract-Excerpt; Tag-Übersicht; Reviewer-Liste + Detailseiten; Reviewed-Resources-Tabelle; Data-Charts (R9: drei inline-SVG Bar-Charts, eine pro Kriterienset, aggregiert nach Top-Level-Section; `value="3"`-Anomalie wird ausgewiesen) | [[specification#R4 Issue-Ansicht]], [[specification#R5 Issue-Übersicht]], [[specification#R6 Tag-Aggregation]], [[specification#R7 Reviewed Resources]], [[specification#R8 Reviewer-Liste]], [[specification#R9 Data-Charts]] |
| 11 | Pagefind-Suche | Build-time index; client-side runtime mit Context-Highlighting; im Navbar verankert ([[interface]] §4); `data-pagefind-body` auf Review-Wrapper, Facetten-Filter (Issue, Tag, Reviewer) als hidden spans, lazy-mount via IntersectionObserver; CI baut den Index nach `python -m src.build` mit `npx pagefind --site site` | [[specification#R12 Volltextsuche]], [[specification#A4 Volltextsuche]] |
| 12 | Maschinenschnittstellen | OAI-PMH static snapshot; JSON-LD per page (DOI als kanonischer @id); full corpus JSON dump; sitemap mit `schema.org/ScholarlyArticle` | [[specification#R15 Maschinenschnittstellen]], [[specification#A5 Maschinenschnittstellen]] |
| 13 | Validierung + Build-Bericht | RelaxNG pre-build check (`src/validate.py`) mit per-file Findings; Corpus-Drift als Warnings, XML-parse-errors als Hard-Errors; optionaler Linkcheck (`--linkcheck`); aggregierter Bericht in `site/api/build-info.json` (Schema-Version, Lizenz, Reviews-Counts, Asset-Summary, Validation, optional Linkcheck). Schematron-Layer deferred bis die Korpus-Drift gegen `ride.rng` behoben ist | [[specification#N3 Validierung als eigene Schicht]], [[specification#N4 Reproduzierbarkeit]], [[specification#N7 Build-Bericht]] |
| 14 | PDF aus Domänenmodell | WeasyPrint mit eigenem Print-Stylesheet (`@page A4`, Chrome aus, `page-break-after` auf Headings); Print-only DOI-Zeile im Review-Header (A6: DOI auf Seite 1, da Sidebar im Print verschwindet); PDF wird per `--pdf`-Flag neben dem `index.html` eines jeden Reviews abgelegt; CI installiert `libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0` und ruft das Flag auf | [[specification#R3 Rezension herunterladen]], [[specification#A6 PDF-Pfad]] |
| 15 | Deploy + Ops | Single GitHub-Actions workflow; cookieless Matomo tracking (deploy-time-konfigurierbar via `--matomo-url`/`--matomo-site-id`); WCAG 2.2-AA-Konformität; Lizenzhinweise pro Artefakt; Kontakt-Seite; Meta-Refresh-Redirects für Legacy-WordPress-URLs | [[specification#R14 Kontakt]], [[specification#R16 Tracking]], [[specification#R17 Stabile URLs]], [[specification#N5 Barrierefreiheit]], [[specification#N6 Lizenzklarheit pro Artefakt]], [[specification#N10 Single-Workflow-Build]] |

Phases 1–8 form die inhaltliche Basislinie; the site is renderable end-to-end after Phase 8. Phases 9–15 add the surrounding apparatus (editorial, aggregation, search, machine APIs, validation, PDF, deploy).
