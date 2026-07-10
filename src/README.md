# src/ — parser, domain model, render, build

Stage 2+. The pipeline turns validated TEI into a static site:

```
TEI XML ─→ parser/ ─→ model/ ─→ render/ ─→ site/
           (lxml       (frozen    (Jinja,
            find)       dataclasses) one module
                                    per output family)
                        build.py orchestrates end to end
```

The parser uses lxml's namespace-prefixed `find()`/`findall()` with helpers in
`parser/common.py` (a different paradigm from the iter-based `scripts/`). Domain
types are immutable `@dataclass(frozen=True)` with `tuple[...]` sequences.
Renderers consume domain objects only; they never re-read TEI.

## model/ — domain types

| File | Responsibility |
|---|---|
| `review.py` | `Review` plus the header-layer metadata types |
| `section.py` | recursive `Section` between `Review.{front,body,back}` and blocks |
| `block.py` | block-level types (Paragraph, List, Table, Citation, Figure, …) |
| `inline.py` | inline-level types living inside paragraphs, headings, cells, quotes |
| `bibliography.py` | `BibEntry` for each `<bibl>` in the back-bibliography |
| `questionnaire.py` | per-review questionnaire (factsheet) types from `<taxonomy>` |
| `page.py` | `Page` for the non-review editorial TEI pages |

## parser/ — TEI to domain

| File | Responsibility |
|---|---|
| `review.py` | top-level entry (`parse_review`): one TEI file → `Review` |
| `metadata.py` | `<teiHeader>` metadata slices into immutable types |
| `sections.py` | recursive `<front>`/`<body>`/`<back>` → `Section` sequences |
| `blocks.py` | block-level parsing, one function per kind plus dispatcher |
| `inlines.py` | inline mixed-content walker (`parse_inlines`) |
| `bibliography.py` | back-bibliography (`<back>/<div type="bibliography">/<listBibl>`) |
| `questionnaire.py` | `<encodingDesc>/<classDecl>/<taxonomy>` → questionnaire |
| `refs_resolver.py` | classifies every `<ref>` target into a `Reference.bucket` |
| `aggregate.py` | walks a parsed `Review` for document-order figures and notes |
| `datasets.py` | cross-corpus aggregations (tags, reviewers, reviewed resources) |
| `assets.py` | copies figure images to the site tree, rewrites `graphic_url` |
| `page.py` | parses a `pages/*.xml` editorial page into the `Page` model |
| `common.py` | shared TEI parsing helpers (namespaces, `xml:`-prefixed attrs) |

## render/ — domain to output

| File | Responsibility |
|---|---|
| `html.py` | per-review HTML entry point; holds the shared context helpers |
| `factsheet.py` | Factsheet full-page HTML, parallel to `html.render_review` |
| `page.py` | renders a `Page` (TEI editorial page) to HTML |
| `editorial.py` | renders the Markdown editorial pages under `content/` |
| `aggregations.py` | tag / reviewer / resource aggregation and overview pages |
| `charts.py` | aggregated questionnaire charts for the Data-Charts page |
| `explorer.py` | flat denormalised data dump for the `/data/explore/` view |
| `corpus_dump.py` | full-corpus JSON dump |
| `jsonld.py` | JSON-LD `schema.org/ScholarlyArticle` per review |
| `oai_pmh.py` | static OAI-PMH snapshot |
| `feed.py` | Atom 1.0 syndication feed |
| `rss.py` | RSS 2.0 syndication feed, same entries and identifiers as Atom |
| `sitemap.py` | `sitemap.xml` |
| `redirects.py` | `<meta refresh>` stub pages at legacy WordPress URLs |
| `pdf.py` | per-review PDF via WeasyPrint |
| `navigation.py` | global navigation loaded from `config/navigation.yaml` |
| `issues_config.py` | per-issue `metadata.yaml` loader (DOI, editors, status, …) |

## Top-level

| File | Responsibility |
|---|---|
| `build.py` | build CLI (`python -m src.build`): validate → parse → render → `site/` |
| `validate.py` | RelaxNG validation against `schema/ride.rng`, run as a pre-build step |
| `linkcheck.py` | HEAD-probes external bibliography URLs with a Wayback-Machine fallback |
| `_corpus.py` | corpus path helpers (`iter_tei_files`, `find_tei`, `CORPUS_ROOT`, `SCHEMA_ODD`, …) |

## Single-source helpers (convention)

URL and context construction is centralised in `render/html.py`. Do not
recompute these inline in other renderers or templates:

- `review_url(review, base_url="")` — the canonical path for a review
- `doi_url(doi)` — the resolvable DOI URL, or `None`
- `base_ctx(...)` — the shared Jinja render context every page starts from

## Building

Run from the repo root:

```sh
python -m src.build                    # full build → site/
python -m src.build --pdf              # also per-review PDFs (WeasyPrint)
python -m src.build --linkcheck        # probe external bibliography URLs (slow)
python -m src.build --no-validate      # skip the RelaxNG pre-check
python -m src.build --reviews=N        # limit to the first N reviews (iteration)
python -m src.build --base-url=/ride-static   # path prefix for a Pages project page
python -m src.build --no-tei-editorials       # fall back to content/*.md editorials
```

Matomo tracking is wired via `--matomo-url` and `--matomo-site-id`. Each build
records `site/api/build-info.json` (commit hash, corpus version, validation
findings, asset report, licence). Corpus structure and named anomalies are
documented in `knowledge/data.md`; design intent in `knowledge/architecture.md`.
