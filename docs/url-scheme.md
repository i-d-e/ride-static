# URL scheme

Versioned definition of the URL scheme. Anchored to `specification.md` clauses R17 (stable URLs) and A1 (rolling issue URL reservation).

## Scheme version

**v2 — 2026-06-24.** Editorial pages move from flat slugs to section-mirroring hierarchical paths (`/about/team/` instead of `/team/`), aligning the URL with the navigation sections and the legacy WordPress structure. See *Editorial pages* and *History*.

**v1 — 2026-04-28.** Initial definition. Any future incompatible change increments the version and is recorded in the History section below.

## Base

The site is hosted on GitHub Pages. The base is one of:

- `https://<owner>.github.io/<repo>/` — default while the custom domain decision is pending (see `specification.md` §8).
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
/data/                                  Data overview (section root)
```

Slugs (`{tag_slug}`, `{reviewer_slug}`) are derived from the source identifier with whitespace collapsed and non-word characters dropped. Slug derivation is deterministic and lossless given the inputs.

## Editorial pages

Editorial pages mirror the navigation sections in their URL (v2). The slug
is the source path relative to its root, so a page in the `about` section
lives under `/about/…`:

```
/about/                          About overview (section root)
/about/editorial/
/about/publishing-policy/
/about/ethical-code/
/about/team/
/about/peer-reviewers/
/about/contact/
/reviewers/call-for-reviews/
/reviewers/submitting-a-review/
/reviewers/projects-for-review/
/reviewers/ride-award/
/data/                           Data overview (section root)
/data/questionnaires/
/data/charts/
/data/explore/                   interactive explore view (navigation.yaml entry)
/imprint/                        standalone (footer)
/criteria/                       Reviewing Criteria (top-level nav entry)
```

The hierarchy is carried by the source location: a TEI page at
`pages/<section>/<name>.xml` renders to `/<section>/<name>/`, a top-level
`pages/<name>.xml` keeps the flat `/<name>/`. The Markdown fallback under
`content/` carries it in the frontmatter `slug:` (e.g. `slug: about/team`).
Adding a new editorial page is still one source file; its directory (TEI)
or its `slug` (Markdown) decides the section. TEI pages with no section
assignment (e.g. `writing-guidelines`, `submission-guidelines`) stay flat
at `/<name>/` until they are placed.

## Machine interfaces

```
/api/corpus.json                        full corpus dump
/data/explorer.json                     flat per-review data table backing /data/explore/
/oai/                                   OAI-PMH static snapshot, see verb routing below
/feed/atom.xml                          Atom 1.0 feed (RFC 4287), newest reviews
/feed/rss.xml                           RSS 2.0 feed, same entries and identifiers as Atom
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

When a path moves, a meta-refresh redirect is emitted at the old path. This satisfies R17 without requiring server-side configuration that GitHub Pages does not provide. Redirects live in `src/render/redirects.py` (`EDITORIAL_REDIRECTS` for the legacy menu paths, plus the per-review and per-issue redirect logic) and are written during the build (Phase 15).

The dynamically generated WordPress listing pages redirect to their static replacements:

```
/data/charts-scholarly-editions/   ->  /data/charts/#chart-digital-editions-1.1
/data/charts-text-collections/    ->  /data/charts/#chart-text-collections-1.0
/data/by-tag/                     ->  /tags/
/data/reviewed-resources/         ->  /resources/
/reviewers/list-of-reviewers/     ->  /reviewers/
```

The legacy feed URLs (`/feed/rss`, `/feed/atom/`, `/feed/rdf`) are not covered by meta-refresh stubs, feed readers fetch XML and ignore HTML redirect pages; continuity for existing subscriptions is an infrastructure decision at the domain switch (see the redirects-and-feeds knowledge document).

## What this scheme does not cover

- Author profile pages independent of reviewer profiles. Out of scope per current requirements.
- Per-language URL variants. Reviews are mono-language at the source; no language-switched URL needed.
- Pretty URLs for specific Pagefind queries. The search runtime is client-side; query parameters are not part of the URL contract.

## History

**v2, 2026-06-24** — editorial pages hierarchised under their navigation section (`/about/…`, `/reviewers/…`, `/data/…`). The flat editorial slugs (`/team/`, `/editorial/`, …) are retired; this re-matches the legacy WordPress section paths, so most WP editorial redirects collapse to identity and are dropped. Standalone `/imprint/` and the top-level `/criteria/` stay flat. Per-review, aggregation, and machine-interface URLs are unchanged.

**v1, 2026-04-28** — initial definition, locked together with `Phase 8` of the build.
