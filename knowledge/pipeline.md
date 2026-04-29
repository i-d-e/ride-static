# Pipeline

> Build and deploy plan. Hand-written; revise as the build reaches each stage.
>
> The phase table at the bottom is anchored to [[requirements]]. Each phase
> names the R- and N-clauses it satisfies; conversely, every R- or N-clause
> in [[requirements]] is covered by at least one phase. Architectural
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
python -m src.build                                # parses ride/tei_all/, renders site/
python -m src.build --pdf                          # also produces a per-review PDF via WeasyPrint
python -m src.build --linkcheck                    # probe external bibliography URLs (slow)
python -m src.build --matomo-url URL --matomo-site-id ID   # emit cookieless tracker snippet
```

WeasyPrint (Phase 14) braucht GTK/Pango zur Laufzeit. Auf Linux genügt `apt install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0`; auf Windows fehlt der GTK3-Runtime und PDFs werden lokal übersprungen — die Tests skippen sauber statt zu crashen.

For local preview after a build: `python -m http.server -d site/` is sufficient. No `--serve` flag is in scope.

## GitHub Actions workflow (Phase 15)

A single workflow file `.github/workflows/build.yml` per [[requirements#N10 Single-Workflow-Build]] — triggered on push to `main` (TEI sources, Markdown texts, pipeline code) and via `workflow_dispatch`.

```
1. Checkout ride-static (this repo)
2. Checkout ride at sibling path ../ride
3. Setup Python 3.11
4. Install dependencies (lxml, jinja2, pytest, weasyprint, requests)
5. Run pytest
6. Run all scripts/*.py in dependency order
7. Run python -m src.build → site/
8. Upload site/ as artifact
9. Deploy to target (see "Deployment target" below)
```

The `ride` repo is checked out as a sibling so the path-resolution
pattern in `scripts/*.py` (`REPO_ROOT.parent / "ride" / ...`) works
unchanged in CI.

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
- **Schematron warnings.** Build prints (but does not fail on) Schematron violations from `inventory/cross-reference.json`. Hard failures are reserved for parsing errors. The full pre-build validation layer ([[requirements#N3 Validierung als eigene Schicht]]) is implemented in Phase 13.
- **Lizenzhinweise pro Artefakt (N6).** Jedes maschinenlesbare Artefakt nennt seine Lizenz explizit, damit Konsumenten die Nutzungsbedingungen ohne Inferenz aus dem Footer kennen. Eine Quelle der Wahrheit: `LICENCE_NAME = "CC-BY-4.0"` und `LICENCE_URL = "https://creativecommons.org/licenses/by/4.0/"` in `src/render/corpus_dump.py`. Setzungs-Punkte: `site/api/corpus.json` (`licence: {name, url}` als Top-Level-Feld neben `version` und `review_count`); `site/api/build-info.json` (selbes Lizenzfeld); OAI-PMH `<dc:rights>` pro Record (aus `Review.licence` aus dem TEI-Quelltext); HTML-Footer als Mensch-lesbare Zeile mit ISSN, Brand und Imprint-Link. Die TEI-Dateien tragen ihre Lizenz im `<publicationStmt>/<licence>` selbst — kein Inject, keine zweite Wahrheit. PDFs (Phase 14) erben die Lizenzanzeige über das Print-Stylesheet aus dem HTML.
- **Cookieless Matomo (R16).** Tracker-Konfiguration ist deploy-time-bound, nicht code-bound. Build-Flags `--matomo-url` + `--matomo-site-id` werden gemeinsam gesetzt — `parser.error` wenn nur eines kommt, weil ein halbkonfigurierter Deploy still mit `setSiteId('')` Hits sendet. Lokal und im Default-CI-Lauf bleibt der Snippet weg, kein Tracker, kein Cookie-Banner, nichts zum Opt-out. Sobald die produktive Matomo-URL in CI als Secret hinterlegt ist, steigt das Snippet ein.
- **Console-Banner (N4-Manifestation).** Build-Commit + Datum erscheinen an drei Stellen: HTML-Footer (`<code>{commit_short}</code>` plus `data-commit`/`data-build-date`), `site/api/build-info.json` (`build.commit` und `build.commit_short`), und in der Devtools-Konsole als kleines `console.info`-Banner mit Brand-Pille. Das Banner ist gated auf `site.build_info.commit_short` — Dev-Builds ohne Git bleiben silent. Drei Manifestationen einer einzigen Quelle (`BuildInfo`-Dataclass aus `src/render/html.py`) — wer eine debuggt, hat sie alle.

## Deployment

GitHub Pages, per [[requirements#2 Plattform und Architekturgrundsätze]]. Custom domain versus `<owner>.github.io/<repo>` is still open per [[requirements#8 Offene Fragen]]; this affects the URL scheme stability promised in [[requirements#R17 Stabile URLs]] and is to be decided before Phase 15.

For large artifacts (older PDF versions, OAI-PMH dumps): the choice between GitHub Pages and GitHub Releases is deferred per [[requirements#8 Offene Fragen]].

## Re-deployment flow

```
git push main
  → GitHub Actions (single workflow, see [[requirements#N10]])
      → pre-build validation (Phase 13, [[requirements#N3]])
      → pytest
      → regenerate inventory/ (gitignored, in CI workspace only)
      → render knowledge/data.md and schema.md
      → src.build → site/  (HTML + PDF + Pagefind index + JSON-LD + OAI-PMH dump + sitemap)
      → upload build-info.json ([[requirements#N4]])
      → deploy site/
```

`knowledge/*.md` regenerated in CI may diverge from the committed copy
when the corpus changed but the docs were not refreshed locally. Two
acceptable options:

- **Strict.** CI fails if regenerated docs differ from committed ones (forces local re-render before push).
- **Auto-commit.** CI commits the refreshed docs back. Risk of merge churn.

Strict is cleaner; pick before Phase 15.

## Resolved design decisions (locked by [[requirements]])

| Decision | Resolution | Anchor |
|---|---|---|
| PDF engine | WeasyPrint, with own print stylesheet | [[requirements#A6 PDF-Pfad]] |
| Search engine | Pagefind, build-time index, client-side runtime | [[requirements#A4 Volltextsuche]] |
| Hosting platform | GitHub Pages | [[requirements#2 Plattform und Architekturgrundsätze]] |
| Editorial format | Markdown with frontmatter, in-repo | [[requirements#A3 Redaktionelle Texte]] |
| Tag source of truth | TEI only; WordPress retired post-consolidation | [[requirements#A2 Datenquellen]] |
| Machine APIs | OAI-PMH + JSON-LD + JSON dump + sitemap with `schema.org/ScholarlyArticle` | [[requirements#A5 Maschinenschnittstellen]] |

## Still open

- Knowledge-doc CI behaviour — strict vs. auto-commit (above).
- Custom domain vs. `<owner>.github.io/<repo>` ([[requirements#8 Offene Fragen]]).
- Distribution path for large artifacts ([[requirements#8 Offene Fragen]]).
- Reach of the WordPress-to-TEI consolidation ([[requirements#8 Offene Fragen]]).

## Phasenplan

The build is split into fifteen sequential phases. Each phase produces one commit, has synthetic test fixtures plus a real-corpus smoke test, and respects the TDD rule from `CLAUDE.md`. Each row maps to the [[requirements]] clauses it satisfies.

| # | Phase | Output | Requirements |
|---|---|---|---|
| 1 | Domain model — Section / Block / Inline | Frozen dataclasses; doc patch for `labeled` list and `figure/eg` | [[requirements#A6 PDF-Pfad]] (zwei Renderings) |
| 2 | Section parser | Recursive sections, body-wrap anomaly, fallback `xml_id` | [[requirements#R1 Rezension lesen]] (TOC, anchors) |
| 3 | Block parser | Paragraph, List (3 kinds), Table, Figure (graphic / code_example), Citation | [[requirements#R1 Rezension lesen]] |
| 4 | Inline parser | Mixed-content walker; Text, Emphasis, Highlight, Reference, Note, InlineCode | [[requirements#R1 Rezension lesen]] (lang, footnotes) |
| 5 | Integration in `parse_review` | `Review.body` fully populated for all 107 reviews. **Stage 2.B done.** | [[requirements#R1 Rezension lesen]] |
| 6 | Bibliography + Questionnaire | `BibEntry`, `Questionnaire` dataclasses + parsers; aggregates for tags, reviewers, reviewed resources. **Stage 2.C done.** | R1 (Bibliographie, Factsheet, Tags), R6, R7, R8, [[requirements#A2 Datenquellen]] |
| 7 | Ref-Resolver + Asset-Pipeline | `Reference.bucket` ∈ {local, criteria, external, orphan} via `src/parser/refs_resolver.py`; image copy + URL rewrite via `src/parser/assets.py`. Wayback-Hint deferred → Phase 13. **done** | R1 (cross-refs, K-refs), [[requirements#R17 Stabile URLs]] |
| 8 | HTML — Rezensionsseiten | Per-review HTML via Jinja; citation export (BibTeX, CSL-JSON); TEI + PDF download links; Open-Graph metadata; Copy-Link auf Absätze; Tooltip-Vorschau für Cross-Refs; vier kleine JS-Module; **done bis Welle 6** inklusive: visual refresh am Mockup (Welle 4: Tagline-Header, Sans-Serif-Body, IDE/RIDE-Logo, mockup-aligned Farben #333/#0d6efd, R2-Citation mit Mikrokopie, ISSN-Footer); CSS-Konsolidierung (Welle 5: Spacing-Tokens, Panel-Komponente, ride-prose-Rhythmik, font-feature-settings, Soft-Cap auf 1000 Zeilen angehoben); Issue-Page als Rich-Entry-Liste mit Wordcloud-Thumbnails (Welle 6) | R1, [[requirements#R2 Rezension zitieren]], [[requirements#R3 Rezension herunterladen]], [[requirements#R13 Sharing]], [[interface]] |
| 9 | Editorialschicht | Editorial · Publishing Policy · Ethical Code · Team · Peer Reviewers (About-Untermenü) · Call for Reviews · Submitting a Review · Projects for Review · RIDE Award (Reviewers-Untermenü) · Imprint · Reviewing Criteria — alles als Markdown mit Frontmatter unter `content/`; Home-Widgets unter `content/home/*.md`; per-issue YAML config unter `content/issues/{N}.yaml`; consistency check against TEI headers; globale Navigation aus `config/navigation.yaml`. **done bis Welle 6**: alle 12 Editorial-Stubs mit echten Texten von ride.i-d-e.de befüllt (About, Editorial, Team, Peer-Reviewers, Imprint), 5 Home-Widgets (Welcome, News, Call for Reviews, Open Data, Follow us), 22 Issue-YAML-Configs gescrapt | [[requirements#R10 Statische Inhalte pflegen]], [[requirements#R11 Issue-Metadaten pflegen]], [[requirements#R11.5 Globale Navigation pflegen]], [[requirements#A3 Redaktionelle Texte]] |
| 10 | Aggregations- und Übersichtsseiten | Issue-Übersicht, Issue-Ansicht (Welle 6: Rich-Entry-Liste mit Wordcloud-Thumbnails, Citation, Abstract-Excerpt; Lead-Satz statt dl-Tabelle), Tag-Übersicht, Reviewer-Liste + Detailseiten, Reviewed-Resources-Tabelle, Data-Charts (R9: drei inline-SVG Bar-Charts, eine pro Kriterienset, aggregiert nach Top-Level-Section über das echte Korpus; `value="3"`-Anomalie wird ausgewiesen). **done.** | [[requirements#R4 Issue-Ansicht]], [[requirements#R5 Issue-Übersicht]], [[requirements#R6 Tag-Aggregation]], [[requirements#R7 Reviewed Resources]], [[requirements#R8 Reviewer-Liste]], [[requirements#R9 Data-Charts]] |
| 11 | Pagefind-Suche | Build-time index; client-side runtime with context highlighting; im Navbar verankert (interface.md §4). **done** (Welle 9) — `data-pagefind-body` auf Review-Wrapper, Facetten-Filter (Issue, Tag, Reviewer) als hidden spans, lazy-mount via IntersectionObserver. CI baut den Index nach `python -m src.build` mit `npx pagefind --site site`. | [[requirements#R12 Volltextsuche]], [[requirements#A4 Volltextsuche]] |
| 12 | Maschinenschnittstellen | OAI-PMH static snapshot; JSON-LD per page (DOI als kanonischer @id); full corpus JSON dump; sitemap with `schema.org/ScholarlyArticle`. **done** | [[requirements#R15 Maschinenschnittstellen]], [[requirements#A5 Maschinenschnittstellen]] |
| 13 | Validierung + Build-Bericht | RelaxNG pre-build check (`src/validate.py`) mit per-file Findings; corpus-drift findings als warnings, XML-parse-errors als hard errors; optional Linkcheck (`--linkcheck`, ~5min); aggregierter Bericht in `site/api/build-info.json` (Schema-Version, Lizenz, Reviews-Counts, Asset-Summary, Validation, optional Linkcheck). **done** (Welle 10). Schematron deferred — die Korpus-Drift gegen `ride.rng` ist umfangreich genug, dass ein zusätzlicher Schematron-Layer keinen neuen Signal-Wert bringt; eine spätere Iteration kann ihn nachziehen, sobald die Korpus-Drift behoben ist. | [[requirements#N3 Validierung als eigene Schicht]], [[requirements#N4 Reproduzierbarkeit]], [[requirements#N7 Build-Bericht]] |
| 14 | PDF aus Domänenmodell | WeasyPrint mit eigenem Print-Stylesheet (`@page A4`, Chrome aus, `page-break-after` auf Headings). Print-only DOI-Zeile im Review-Header (A6: DOI auf Seite 1, da Sidebar im Print verschwindet). PDF wird per `--pdf`-Flag neben dem `index.html` eines jeden Reviews abgelegt; CI installiert `libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0` und ruft das Flag auf. **done.** | [[requirements#R3 Rezension herunterladen]], [[requirements#A6 PDF-Pfad]] |
| 15 | Deploy + Ops | Single GitHub-Actions workflow; cookieless Matomo tracking; WCAG 2.2 AA audit; licence statements; Kontakt; meta-refresh redirects on rename. **partial.** Erledigt: GH-Actions-Workflow läuft (Welle 9/10), R14 Contact-Seite + Footer-Link, R16 Matomo-Snippet (config-bereit, `disableCookies` + `--matomo-url`/`--matomo-site-id` deploy-time-konfigurierbar), N5 generic `:focus-visible` über alle interaktiven Element-Familien + Tag-Pills mit `min-height: 24px` (WCAG 2.5.8), N6 Lizenzfeld in `corpus.json` + `build-info.json` + `<dc:rights>` in OAI-PMH, R17 Legacy-URL-Redirects via `src/render/redirects.py`. **Offen:** WCAG-Vollaudit (axe-Pass über Live-Site), Matomo-URL in CI-ENV setzen, Knowledge-Doc-CI-Verhalten (strict vs. auto-commit), Custom-Domain-Entscheidung. | [[requirements#R14 Kontakt]], [[requirements#R16 Tracking]], [[requirements#R17 Stabile URLs]], [[requirements#N5 Barrierefreiheit]], [[requirements#N6 Lizenzklarheit pro Artefakt]], [[requirements#N10 Single-Workflow-Build]] |

Phases 1–8 form the inhaltliche Basislinie; the site is renderable end-to-end after Phase 8. Phases 9–15 add the surrounding apparatus (editorial, aggregation, search, machine APIs, validation, PDF, deploy). Estimated total effort ~55 hours, distributed across roughly twelve sessions.
