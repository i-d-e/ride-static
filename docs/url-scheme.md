# URL scheme

Versioned definition of the URL scheme. Anchored to `requirements.md` clauses R17 (stable URLs) and A1 (rolling issue URL reservation).

## Scheme version

**v1 — 2026-04-28.** Initial definition. Any future incompatible change increments the version and is recorded in the History section below.

## Base

The site is hosted on GitHub Pages. The base is one of:

- `https://<owner>.github.io/<repo>/` — default while the custom domain decision is pending (see `requirements.md` §8).
- `https://ride.i-d-e.de/` — once the custom domain is configured.

Internal links are always relative to the site root (`/`); the base prefix is added at deploy time.

## Per-review pages

```
/issues/{issue_no}/{review_id}/
/issues/{issue_no}/{review_id}/index.html
/issues/{issue_no}/{review_id}/{review_id}.pdf
/issues/{issue_no}/{review_id}/{review_id}.xml
/issues/{issue_no}/{review_id}/figures/{filename}
```

`{review_id}` is the TEI file basename without the `-tei.xml` suffix. Example: `1641-tei.xml` becomes `1641`. This matches the existing eXist-based scheme so external citations remain stable.

`{issue_no}` is the integer issue number from `<seriesStmt>/<biblScope/@n>` in the TEI header.

## In-review anchors

Anchors inside a review use the `xml:id` of the corresponding TEI element verbatim:

```
/issues/{issue_no}/{review_id}/#{xml_id}
```

The corpus is verified clean on `xml:id` uniqueness within each file (see `knowledge/data.md` ID format conformance section). Paragraph anchors are particularly important: each numbered paragraph carries its own `xml:id`, and the rendered page exposes a copy-link affordance on hover (see `knowledge/interface.md` §11).

## Aggregation pages

```
/                                       home
/issues/                                issues overview
/issues/{issue_no}/                     single issue with TOC
/tags/                                  tags overview
/tags/{tag_slug}/                       reviews carrying this tag
/reviewers/                             reviewer list
/reviewers/{reviewer_slug}/             reviewer detail
/resources/                             reviewed resources table
/data/                                  questionnaire-derived charts
```

Slugs (`{tag_slug}`, `{reviewer_slug}`) are derived from the source identifier with whitespace collapsed and non-word characters dropped. Slug derivation is deterministic and lossless given the inputs.

## Editorial pages

```
/about/
/imprint/
/criteria/
```

These are rendered from `content/*.md` files with frontmatter. Adding a new editorial page is a matter of adding a Markdown file — the URL is the filename slug.

## Machine interfaces

```
/api/corpus.json                        full corpus dump
/oai/                                   OAI-PMH static snapshot, see verb routing below
/sitemap.xml                            sitemap with last-modified dates
/pagefind/                              client-side search index, served as static assets
```

Each per-review page also embeds JSON-LD with `schema.org/ScholarlyArticle` markup; no separate URL.

OAI-PMH verbs are dispatched via static query-string responses; the snapshot is regenerated at every build. The verb endpoints are:

```
/oai/?verb=Identify
/oai/?verb=ListIdentifiers
/oai/?verb=ListRecords
/oai/?verb=GetRecord&identifier={oai_id}
```

## Reserved version segment (A1)

The scheme reserves `/v/{version}/` as an optional first path segment for snapshot versioning of rolling issues, e.g.

```
/v/2026-Q2/issues/3/{review_id}/
```

Currently unused. When introduced, the unversioned URL will continue to serve the latest snapshot, and `/v/{version}/...` will serve the named snapshot. Existing URLs do not break.

## Redirects

When a path moves, a meta-refresh redirect is emitted at the old path. This satisfies R17 without requiring server-side configuration that GitHub Pages does not provide. Redirects are pinned in `redirects.yaml` at repo root and applied during the build (Phase 15).

## What this scheme does not cover

- Author profile pages independent of reviewer profiles. Out of scope per current requirements.
- Per-language URL variants. Reviews are mono-language at the source; no language-switched URL needed.
- Pretty URLs for specific Pagefind queries. The search runtime is client-side; query parameters are not part of the URL contract.

## History

**v1, 2026-04-28** — initial definition, locked together with `Phase 8` of the build.
