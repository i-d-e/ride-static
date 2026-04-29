---
title: Data
slug: data
language: en
last_updated: 2026-04-29
---

# Data

RIDE provides every review and questionnaire as machine-readable data
under a Creative Commons licence. The collected dataset can be cited,
mirrored, and reused without barrier.

## Downloads and APIs

- **Full corpus dump** — every parsed review as JSON: [/api/corpus.json](/api/corpus.json).
- **Per-review TEI/XML** — every review page exposes a `Download XML`
  link; the source TEI is the canonical archival form.
- **Per-review PDF** — coming with the WeasyPrint pipeline (Phase 14).
- **GitHub** — TEI source for every review:
  [github.com/i-d-e/ride](https://github.com/i-d-e/ride).
- **Zenodo** — tagged snapshots of the corpus with their own DOI:
  [zenodo.org/record/4562966](https://zenodo.org/record/4562966).

## Standards-Endpoints

- **OAI-PMH** — Dublin Core metadata for every review:
  [/oai/](/oai/). Use `?verb=ListRecords&metadataPrefix=oai_dc` to
  retrieve the full set.
- **JSON-LD** — every review page embeds a
  [`schema.org/ScholarlyArticle`](https://schema.org/ScholarlyArticle)
  block with the DOI as the canonical `@id`.
- **Sitemap** — [/sitemap.xml](/sitemap.xml) for crawlers.

## Aggregations

- [Questionnaires](/data/questionnaires/) — answered criteria per review
- [Charts](/data/charts/) — score distributions and tag clusters
- [Tags](/tags/) — all keywords used across the corpus
- [Reviewed Resources](/resources/) — every reviewed edition with its
  reviewers and issue
