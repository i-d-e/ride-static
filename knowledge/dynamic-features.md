---
title: Dynamic features
project:
  name: ride-static
  repository: https://github.com/i-d-e/ride-static
method:
  name: Promptotyping
  url: https://dhcraft.org/excellence/blog/Promptotyping
status: active
created: 2026-06-22
updated: 2026-06-22
version: 0.1
language: en
related:
  - "[[architecture]]"
  - "[[pipeline]]"
  - "[[specification]]"
issue: https://github.com/i-d-e/ride-static/issues/4
---

# Dynamic features — coverage, gaps, and data interfaces

## Why this document

GitHub issue #4 lists the pages and functions the legacy WordPress site generates dynamically and asks three questions: which of them the static rebuild already replaces, which cannot be replaced, and which we may no longer need. This document answers the first question with a coverage map, names the open problems where solutions are still needed, and explains the data-interface landscape (feeds, harvesting, crawling, embedded semantics) so the remaining decisions rest on understanding rather than habit. The technical findings are checked against the code as of 2026-06-22; the interface background is from the web research listed under *Sources*.

## Coverage map

"Replaced" here means an equivalent, live page exists at a static URL, not that field-by-field content parity has been verified. Charts in particular were confirmed at the level of the criteria sets the renderer handles, not by comparing rendered diagrams against the WordPress charts.

| WordPress dynamic page | Static-site equivalent | Status |
|---|---|---|
| All Issues: Overview (`/issues/`) | `/issues/` (`render_issues_overview`) | replaced |
| Charts, Scholarly Editions | `/data/charts/` (editions catalogue) | replaced, **consolidated** — one page for both catalogues |
| Charts, Text Collections | `/data/charts/` (text-collections catalogue) | replaced, same page |
| Tags (`/data/by-tag/`) | `/tags/` plus a page per tag | replaced, **URL changed** |
| Reviewed Resources | `/resources/` (`render_resources`) | replaced |
| List of Reviewers | `/reviewers/` (reviewers overview) | replaced |
| OAI interface (`/apis/oai`) | `/oai/` (`write_oai_pmh`, needs `base_url`) | replaced |
| RSS feed (`/feed/rss`) | — | **gap** |
| RDF feed (`/feed/rdf`) | — | **gap** |
| ATOM feed (`/feed/atom/`) | — | **gap** |

Seven of ten functions are replaced. The three syndication feeds are the substantive gap; charts and tags are replaced but with a changed structure or URL.

## Open problems — where solutions are still needed

### 1. Syndication feeds, and a live dead-link defect

No feed is generated. There is no feed renderer in `src/render/`, and the build writes `sitemap.xml`, the OAI snapshot, and `api/corpus.json` but no feed. Independently of issue #4 this is also a **defect**: the home-page widget `content/home/05-follow-us.md` advertises the three feeds —

> There are also feeds: [RSS](/feed/rss/), [RDF](/feed/rdf/) and [ATOM](/feed/atom/).

— so the live static site links to three URLs that do not exist. These links must be fixed regardless of the wider feed decision, by generating the feeds or by removing the promise.

### 2. Charts — consolidation and URL

The WordPress site had two chart pages (scholarly editions, text collections); the static site renders one `/data/charts/` that covers both criteria catalogues (`src/render/charts.py` carries both the digital-editions and text-collections taxonomies). Open: keep one consolidated page or restore two, and whether to mirror the old URLs by redirect.

### 3. Tags and other URL changes

`/data/by-tag/` became `/tags/`. This is one instance of the still-open URL-scheme question (see [[pipeline]] and `docs/url-scheme.md`): mirror legacy paths with redirects, or commit to clean new URLs.

### 4. Page-level content parity (optional, deeper)

The coverage map asserts existence, not parity. If the team wants certainty that `/resources/`, `/reviewers/`, and the charts show the same content as the WordPress originals, that is a separate field-by-field verification, probably not needed for an exploratory discussion but named here so the limit of the claim is explicit.

## Background: the four data interfaces and what each is for

A site can expose its content to non-browser consumers through four distinct interfaces. They are easy to conflate because all four emit XML or JSON, but they serve different audiences and are not substitutes for one another.

### Syndication feeds — RSS 2.0, RSS 1.0 (= RDF), Atom

A feed is a machine-readable list of recent items (title, link, date, summary) that a person subscribes to in a feed reader to be notified of new content. Three formats coexist:

- **RSS 2.0** ("Really Simple Syndication") — the most widespread feed format, simple, but never put through a formal standards process.
- **RSS 1.0** ("RDF Site Summary") — RDF-based and modular. Outside scholarly publishing it is effectively abandoned. **This is what the WordPress `/feed/rdf` is.**
- **Atom** — IETF standard RFC 4287, stricter and cleaner than RSS, with better date and internationalisation handling. The modern default when starting fresh.

The scholarly nuance explains RIDE's RDF feed: Crossref's recommendation for scholarly publishers favoured **RSS 1.0** precisely because its RDF modularity carries rich bibliographic metadata — Dublin Core (creators, dates, identifiers), PRISM (DOI, volume, issue, pages), and a Content module for HTML summaries. That richness is the reason a journal would once choose RDF over plain RSS. Feeds remain in real use in academia: public collections list thousands of journal feeds, and researchers track new articles through feed readers. So the feed function is not obsolete — it is the one interface aimed at a **human** who wants to follow new reviews.

### Metadata harvesting — OAI-PMH

OAI-PMH is a harvesting protocol for the digital-library world. A repository or aggregator (a library, a discovery index) pulls metadata in bulk, selectively by datestamp, to build and incrementally update its own copy. Its audience is **machines in the repository ecosystem**, and its strength is date-based selective harvesting of the whole corpus, not a rolling list of the newest items. RIDE has this at `/oai/`.

### Crawler interface — sitemap.xml

A sitemap is a flat list of all canonical URLs with last-modified dates, consumed by **search-engine crawlers** to discover and prioritise pages. It is neither a subscription nor a metadata record. RIDE has this (`sitemap.xml`, needs `base_url`).

### Embedded semantics — JSON-LD and the corpus dump

Per-review JSON-LD (`schema.org`) embeds structured data in each page for **search engines and knowledge graphs**; the full-corpus `api/corpus.json` dump gives a consumer the entire dataset in one file. Both describe content semantically rather than syndicating or harvesting it.

### How they relate

| Interface | Audience | Purpose | RIDE status |
|---|---|---|---|
| RSS / Atom feed | human, via feed reader | subscribe to newest reviews | **missing** |
| OAI-PMH | repositories, aggregators | bulk, datestamp-based metadata harvesting | present (`/oai/`) |
| sitemap.xml | search-engine crawlers | URL discovery | present |
| JSON-LD + corpus.json | search engines, data consumers | embedded semantics, full dataset | present |

The key insight for issue #4: the rich-bibliographic-metadata role that RSS 1.0 / PRISM once played for scholarly feeds is **already covered** by RIDE's OAI-PMH, per-review JSON-LD, and `corpus.json`. What none of those provide is the plain human subscription to "a new review was published" — that is the feed's remaining, distinct job.

## Recommendation

- **Feeds.** Generate **one Atom feed** (RFC 4287) of the most recent reviews at build time, from the already-parsed `Review` list — every needed field exists (`title`, the review URL, `publication_date`, the abstract). Optionally add an RSS 2.0 feed for the broadest reader compatibility. **Drop the RDF (RSS 1.0) feed**: its only advantage was rich bibliographic metadata, which OAI-PMH and JSON-LD already serve, and the format is otherwise legacy. The effort is small — a feed is a templated XML file plus a build step, validated with the W3C feed validator.
- **Dead links.** Fix `content/home/05-follow-us.md` regardless of the above: point it at the feed(s) that will exist, or remove the promise until they do.
- **Charts / Tags URLs.** Decide as part of the URL-scheme question: mirror the legacy paths with redirects, or adopt the new URLs cleanly. This is a presentation/compatibility choice, not a missing function.
- **Page parity.** Optional. Run a field-by-field comparison only if the team wants certainty beyond "an equivalent live page exists."

## Sources

- [RSS — Wikipedia](https://en.wikipedia.org/wiki/RSS) — format history; RSS 1.0 = RDF, RSS 2.0 most used, Atom = RFC 4287.
- [Crossref — Recommendations on RSS Feeds for Scholarly Publishers](https://www.crossref.org/wp/labs/whitepapers/rss-best-practice/) — the scholarly RSS 1.0 / Dublin Core / PRISM rationale.
- [Jakob Voß — Syndication and Harvesting with RSS, ATOM, OAI-PMH and Sitemaps](http://jakoblog.de/2007/09/28/syndication-and-harvesting-with-rss-atom-oai-pmh-and-sitemaps/) — the feeds-vs-OAI-vs-sitemap distinction.
- [science-journal-feeds (sg-s)](https://github.com/sg-s/science-journal-feeds) — large public list of academic journal feeds, evidence of continued use.
- [Simple RSS, Atom and JSON feed for your blog (Paweł Grzybek)](https://pawelgrzybek.com/simple-rss-atom-and-json-feed-for-your-blog/) — build-time feed generation for static sites.
