# Pipeline

> Build and deploy plan. Hand-written; revise as the build reaches each stage.

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

### Build the site (planned, Stage 3+)

```sh
python -m src.build         # parses ride/tei_all/, renders site/
python -m src.build --pdf   # also runs pdf renderer
python -m src.build --serve # local preview server on :8000
```

## GitHub Actions workflow (planned)

`.github/workflows/build.yml` — triggered on push to `main` and via `workflow_dispatch`.

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

## Output structure (planned)

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

- **Asset handling.** Images referenced via `<graphic @url>` live next to the TEI in `../ride/issues/{n}/`. The build copies them into `site/issues/{n}/{review-id}/figures/` and rewrites URLs.
- **Reference resolution.** `<ref @target>` follows three paths at build time:
  - local anchor present in this review → render as in-page anchor link;
  - looks like `#K…` (5 209 cases) → resolve against the criteria document
    at the taxonomy's `@xml:base` (see `architecture.md`);
  - external URL → pass through;
  - anything else → log a build warning and render as plain text.
- **Cross-review references.** Reviews citing one another (via `<relatedItem>`) become hyperlinks if the target is in the corpus; otherwise they stay as bibliographic citations.
- **Schematron warnings.** Build prints (but does not fail on) Schematron violations from `inventory/cross-reference.json`. Hard failures are reserved for parsing errors.

## Deployment target (open)

| Option | Pros | Cons |
|---|---|---|
| GitHub Pages | Built into CI, no extra infra | URL would be `<owner>.github.io/...`; less control |
| i-d-e.de via SSH/rsync | IDE-controlled, expected long-term home | Requires deploy key + SSH action |

**Default plan:** GitHub Pages for early stages, switch to i-d-e.de before public launch. Decide before Stage 6.

## Re-deployment flow

```
git push main
  → GitHub Actions
      → pytest
      → regenerate inventory/ (gitignored, in CI workspace only)
      → render knowledge/*.md
      → src.build → site/
      → deploy site/
```

`knowledge/*.md` regenerated in CI may diverge from the committed copy
when the corpus changed but the docs were not refreshed locally. Two
acceptable options:

- **Strict.** CI fails if regenerated docs differ from committed ones (forces local re-render before push).
- **Auto-commit.** CI commits the refreshed docs back. Risk of merge churn.

Pick one before Stage 6 — strict is cleaner.

## Open decisions

- PDF engine — WeasyPrint vs. Prince vs. headless Chromium.
- Search engine — Lunr vs. Stork vs. Pagefind.
- Knowledge-doc CI behaviour — strict vs. auto-commit (above).
- Deployment target — GitHub Pages vs. i-d-e.de (above).
- Whether to track `site/` builds as artifacts beyond CI retention.
