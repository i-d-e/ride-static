# Contributing

Goal of this document: any new contributor reaches a productive state within half a day, without follow-up questions. If something here is unclear or wrong, fix it in the same PR as your other change.

## Setup

Requirements: Python 3.11, [uv](https://docs.astral.sh/uv/), git.

```sh
git clone <this-repo>
cd ride-static
uv sync --locked
uv run ruff check .
uv run python -m pytest tests/
uvx pre-commit install
```

The TEI corpus ships in this repo under `issues/{N}/reviews/`, no separate clone is needed. Per-issue **picture assets** still live in `i-d-e/ride`; clone it as a sibling (`git clone <ride-corpus-repo> ../ride`) only if you need figures to render in the local build — the pipeline degrades cleanly without it.

## Repository layout

See `CLAUDE.md` for the layout reference. In short:

- `scripts/` — Stage 0/1 discovery and knowledge generation. Each script exposes `run(...)` for testing and a `main()` that writes to `inventory/` or `knowledge/`.
- `src/parser/` and `src/model/` — Stage 2 TEI-to-domain parsing, immutable dataclasses.
- `src/render/` — Stage 3 onwards, HTML and PDF.
- `templates/html/` — Jinja templates, dumb (consume domain objects, never XML).
- `config/element-mapping.yaml` — declarative binding of domain classes to templates and CSS classes (introduced in Phase 8; see `docs/extending.md` for the schema).
- `pages/` — editorial pages as TEI, validated against `schema/ride-pages.rng`. This is the build default for the non-review pages.
- `content/` — editorial Markdown fallback (home widgets plus the `--no-tei-editorials` legacy path); per-issue YAML configs (introduced in Phase 9).
- `tests/` — pytest, run from repo root with `uv run python -m pytest tests/`.
- `knowledge/` — Obsidian-style vault, `.md` only, internal links use `[[wikilink]]`.
- `inventory/` — generated JSON artifacts, gitignored, regeneratable from `scripts/`.

## Hard rules

These are the project's non-negotiables. Codified for clarity, not for ceremony.

- **TDD.** Every script and parser module ships with pytest. Integration tests drive off the real corpus shipped under `issues/{N}/reviews/`; pure-function unit tests may use synthetic inputs.
- **`knowledge/` stays clean.** Hand-written and generated `.md` only. No JSON, no scripts, no notebooks. Cross-references between knowledge docs use `[[wikilink]]` notation.
- **`inventory/` is gitignored.** Always regeneratable from scripts. Never edit by hand.
- **Anomalies are explicit.** Known data quirks become named branches in the parser. Unknown ones must raise.
- **Domain model first.** Renderers consume domain objects, never raw XML.
- **Read-only pipeline.** The pipeline never writes back to TEI. TEI is the single source of truth for structured content.

## Where decisions live

| Question | Source of truth |
|---|---|
| What does the product do? | `knowledge/specification.md` |
| How does it look and behave? | `knowledge/interface.md` |
| How is it architected? | `knowledge/architecture.md` |
| In what order is it built? | `knowledge/pipeline.md` Phasenplan |
| What's in the corpus? | `knowledge/data.md` |
| What's in the schema? | `knowledge/schema.md` |
| What was decided when? | `knowledge/journal.md` |

If a documented decision conflicts with the code, fix the code. If the code is right and the doc is stale, fix the doc in the same PR.

## Conventions

**Commits.** Short title in the form `Area: what changed`, e.g. `Parser: integrate body into parse_review`. Body is optional — use it when the *why* needs explaining. Sign with the standard `Co-Authored-By` trailer if pair-coding with an agent.

**Tests.** Synthetic fixtures live inline in test files. Real-corpus tests find files via `src._corpus.find_tei("slug")` or iterate via `iter_tei_files()`. Each new script or parser module gets its own `tests/test_<name>.py`. Assert exact output paths when scripts write files (see `tests/test_odd_extract.py` for the canonical example).

**Type hints.** Domain types are immutable: `@dataclass(frozen=True)` with `tuple[...]` for sequences (hashability). Optional fields default to `None`, never to mutable defaults.

**Whitespace and quotes.** Black-compatible formatting, double quotes by default. JSON output uses `indent=2, ensure_ascii=False`.

**Wikilinks.** Inside `knowledge/`, link to other docs as `[[filename]]` or `[[filename#anchor]]`. Filenames are lowercase for hand-written docs.

## Adding things

- **A new TEI element or variant** — see `docs/extending.md`. Most variants are YAML-only via `config/element-mapping.yaml`; structural additions need a dataclass and parser.
- **A new editorial page** — add a TEI file under `pages/` that validates against `schema/ride-pages.rng`; its location decides the URL section. See `docs/extending.md` (Editorial pages) and `docs/url-scheme.md`. The Markdown under `content/` is only the `--no-tei-editorials` fallback.
- **A new test** — name it `tests/test_<thing>.py` and run `uv run python -m pytest tests/test_<thing>.py -v`.

## Review schema

`schema/ride.odd` is the editable contract. Do not edit `schema/ride.rng` by hand. The compiler requires Java and TEI Stylesheets 7.60.0:

```sh
git clone --branch v7.60.0 --depth 1 https://github.com/TEIC/Stylesheets.git ../tei-stylesheets
uv run python scripts/compile_schema.py --stylesheets ../tei-stylesheets
uv run python scripts/compile_schema.py --stylesheets ../tei-stylesheets --check
```

New review bundles are validated strictly against this schema. Drafts use `<revisionDesc status="draft">` and a unique provisional `xml:id` in the form `draft.{lowercase-slug}`. Content-bearing graphics should carry a concise `<figDesc>` after `<graphic>` so HTML and PDF receive meaningful alternative text. Historical flat reviews retain a warning-only compatibility path for pre-existing schema drift. Missing or unsafe `pictures/` references fail a bundle build with the review ID and source path.

## Wordclouds

The build generates wordclouds for review bundles into `site/static/images/wordclouds/{review_id}.png`. Bundle wordclouds are derived output and are not committed. Legacy flat reviews continue to use committed thumbnails under `static/images/wordclouds/`; regenerate one when its text changes:

```sh
uv run python scripts/wordclouds.py --review <slug>
# or by path:
uv run python scripts/wordclouds.py issues/<N>/reviews/<slug>-tei.xml
```

The generator extracts `//tei:body//text()`, applies a language-specific stopword list (`scripts/wordcloud-assets/stopwords_{de,en,fr}.txt`, ported from `i-d-e/ride-scripts`; other languages fall back to the library's built-in list), renders through a silhouette mask (`scripts/wordcloud-assets/cloud_mask.png`) with a fixed `random_state`, and writes `{review_id}.png`. The fixed seed makes repeated output byte-identical.

## Running a session with Claude Code

Claude reads `CLAUDE.md` automatically and the journal entries in `knowledge/journal.md` when a session starts. Append a new dated entry to `knowledge/journal.md` at the end of each working session — five fields, two to four lines each. The format is documented at the top of `knowledge/journal.md`.

## Licence

See the project root `LICENSE` for code. Generated HTML output and copied review images carry their own licences from the source corpus and editorial choices; see `knowledge/interface.md` and the per-review licence display.
