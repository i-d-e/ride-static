# Contributing

Goal of this document: any new contributor reaches a productive state within half a day, without follow-up questions. If something here is unclear or wrong, fix it in the same PR as your other change.

## Setup

Requirements: Python 3.11, git, a checkout of the sibling corpus repo at `../ride/`.

```sh
git clone <this-repo>
git clone <ride-corpus-repo> ../ride        # the TEI source corpus

cd ride-static
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest tests/
```

If `../ride/` is not present, the parser still runs and 87 of 88 tests pass — only the real-corpus smoke test skips. Discovery scripts in `scripts/` need `../ride/` to do anything useful.

## Repository layout

See `CLAUDE.md` for the layout reference. In short:

- `scripts/` — Stage 0/1 discovery and knowledge generation. Each script exposes `run(...)` for testing and a `main()` that writes to `inventory/` or `knowledge/`.
- `src/parser/` and `src/model/` — Stage 2 TEI-to-domain parsing, immutable dataclasses.
- `src/render/` — Stage 3 onwards, HTML and PDF.
- `templates/html/` — Jinja templates, dumb (consume domain objects, never XML).
- `config/element-mapping.yaml` — declarative binding of domain classes to templates and CSS classes (introduced in Phase 8; see `docs/extending.md` for the schema).
- `content/` — editorial Markdown with frontmatter; per-issue YAML configs (introduced in Phase 9).
- `tests/` — pytest, run from repo root with `python -m pytest tests/`.
- `knowledge/` — Obsidian-style vault, `.md` only, internal links use `[[wikilink]]`.
- `inventory/` — generated JSON artifacts, gitignored, regeneratable from `scripts/`.

## Hard rules

These are the project's non-negotiables. Codified for clarity, not for ceremony.

- **No XSLT.** Python only. RIDE has no XSLT expertise to maintain.
- **TDD.** Every script and parser module ships with pytest using synthetic TEI fixtures. The parser also has one real-corpus smoke test that skips when `../ride/` is absent.
- **`knowledge/` stays clean.** Hand-written and generated `.md` only. No JSON, no scripts, no notebooks. Cross-references between knowledge docs use `[[wikilink]]` notation.
- **`inventory/` is gitignored.** Always regeneratable from scripts. Never edit by hand.
- **Anomalies are explicit.** Known data quirks become named branches in the parser. Unknown ones must raise.
- **Domain model first.** Renderers consume domain objects, never raw XML.
- **Read-only pipeline.** The pipeline never writes back to TEI. TEI is the single source of truth for structured content.

## Where decisions live

| Question | Source of truth |
|---|---|
| What does the product do? | `knowledge/requirements.md` |
| How does it look and behave? | `knowledge/interface.md` |
| How is it architected? | `knowledge/architecture.md` |
| In what order is it built? | `knowledge/pipeline.md` Phasenplan |
| What's in the corpus? | `knowledge/data.md` |
| What's in the schema? | `knowledge/schema.md` |
| What was decided when? | `Journal.md` |

If a documented decision conflicts with the code, fix the code. If the code is right and the doc is stale, fix the doc in the same PR.

## Conventions

**Commits.** Short title in the form `Area: what changed`, e.g. `Parser: integrate body into parse_review`. Body is optional — use it when the *why* needs explaining. Sign with the standard `Co-Authored-By` trailer if pair-coding with an agent.

**Tests.** Synthetic fixtures live inline in test files. Real-corpus smoke tests skip via `pytest.skip` when `../ride/` is absent. Each new script or parser module gets its own `tests/test_<name>.py`. Assert exact output paths when scripts write files (see `tests/test_odd_extract.py` for the canonical example).

**Type hints.** Domain types are immutable: `@dataclass(frozen=True)` with `tuple[...]` for sequences (hashability). Optional fields default to `None`, never to mutable defaults.

**Whitespace and quotes.** Black-compatible formatting, double quotes by default. JSON output uses `indent=2, ensure_ascii=False`.

**Wikilinks.** Inside `knowledge/`, link to other docs as `[[filename]]` or `[[filename#anchor]]`. Filenames are lowercase for hand-written docs.

## Adding things

- **A new TEI element or variant** — see `docs/extending.md`. Most variants are YAML-only via `config/element-mapping.yaml`; structural additions need a dataclass and parser.
- **A new editorial page** — drop a Markdown file with frontmatter in `content/`. The build picks it up.
- **A new test** — name it `tests/test_<thing>.py` and run `python -m pytest tests/test_<thing>.py -v`.

## Running a session with Claude Code

Claude reads `CLAUDE.md` automatically and the journal entries in `Journal.md` when a session starts. Append a new dated entry to `Journal.md` at the end of each working session — five fields, two to four lines each. The format is documented at the top of `Journal.md`.

## Licence

See the project root `LICENSE` for code. Generated HTML output and copied review images carry their own licences from the source corpus and editorial choices; see `knowledge/interface.md` and the per-review licence display.
