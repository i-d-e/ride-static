---
title: Parity with the live site
project:
  name: ride-static
status: active
created: 2026-11-10
updated: 2026-11-10
language: en
related:
  - "[[specification]]"
  - "[[redirects-feeds]]"
  - "[[oai-pmh-statisch]]"
  - "[[workflow]]"
---

# Parity with the live site

What the running ride.i-d-e.de offers readers and machines, how the static site answers each function, which data must be online for a server-free answer, and how `scripts/parity.py` measures the correspondence. The inventory was taken from the live site itself on 2026-11-10, read-only, through the cached fetcher of the parity check. Measured results live in the generated report (`inventory/parity/report.json` and `summary.md`) and in the dated journal entries, because they change with every corpus or code change.

## Function inventory of the live site

The live site is a WordPress installation (WordPress 6.8, theme Responsive with a child theme) on ride.i-d-e.de. A second host, exist.i-d-e.de, serves three listing pages and the charts as XQuery output that WordPress embeds through `<iframe>`. The OAI-PMH endpoint `/apis/oai` is the third live component. Downloads point at GitHub (`i-d-e/ride`) and Zenodo.

### Pages for readers

- Home page `/` with a rotating word-cloud carousel of the newest issue, news and an editorial teaser.
- Issue overview `/issues/` and one page per issue `/issues/issue-{N}/`.
- Review page `/issues/issue-{N}/{slug}/`. Header with the reviewed resource, reviewer, ORCID and e-mail, abstract, numbered paragraphs with anchors `#p{n}`, figures with a lightbox, notes `#ftn{n}`, bibliography, list of figures. The sidebar carries a table of contents, publication month and DOI, the factsheet link, a citation suggestion, the TEI download (GitHub blob URL), the PDF download (GitHub raw URL), the CC BY badge, the tags and share buttons for Facebook, X and WhatsApp.
- Factsheet page `/issues/issue-{N}/{slug}/factsheet/` with resource, reviewer and the questionnaire answers row by row, each row citing its criterion (`cf. Catalogue 1.2`).
- Tag archive `/tag/{slug}/` per WordPress tag, a tag cloud at `/data/by-tag/`, and an RSS feed per tag at `/tag/{slug}/feed/`.
- Data pages `/data/` (overview, download and API), `/data/questionnaires/`, two chart pages `/data/charts-scholarly-editions/` and `/data/charts-text-collections/` (Plotly charts from exist.i-d-e.de), `/data/reviewed-resources/` and `/reviewers/list-of-reviewers/` (both iframes onto exist.i-d-e.de).
- Editorial pages under `/about/` and `/reviewers/`, plus pages outside the menu: individual calls for reviews under `/reviewers/call-for-reviews/…`, `/archived-editorials/`, `/fair-criteria-editions/`, landing pages for single issues (`/latest-issue-…`, `/issue-15-tools-and-environments/`), `/copyright/` and an HTML sitemap `/sitemap.html`.
- Full-text search through the query string `/?s={term}`.

### Interfaces for machines

- XML sitemap index `/sitemap.xml` with `page-sitemap.xml` and `sitemap-misc.xml`, announced in `robots.txt`.
- Feeds `/feed/` (RSS 2.0), `/feed/atom/`, `/feed/rdf/`, a comment feed `/comments/feed/` and the per-tag feeds. The main feeds also list password-protected WordPress pages by title.
- OAI-PMH at `/apis/oai` with `oai_dc`, `oai_marcxml` and `oai_doajxml`, pages of twenty records with `resumptionToken`, no sets. Besides the reviews it lists the issue editorials as records (`ride.{N}.0`).
- WordPress REST API `/wp-json/`, oEmbed endpoints, XML-RPC discovery and shortlinks `/?p={id}`, which answer with a 301 to the page.
- Page head metadata: canonical link and feed autodiscovery. The live review pages carry no Highwire `citation_*` tags, no Open Graph tags, no JSON-LD and no Dublin Core tags.

### External dependencies

- DOIs (prefix 10.18716, registered through DataCite) resolve to landing pages on ride.i-d-e.de. The landing URL registered per DOI was not checked against DataCite, because the publication boundary of this survey allowed requests to the two sites only. The TEI `publicationStmt/idno[@type='URI']` and the OAI `dc:identifier` print the WordPress address, so the registered URL is presumably one of the addresses the redirects below preserve.
- Harvesters of the OAI endpoint are unknown (see [[redirects-feeds#OAI harvester research (2026-07-10)]] and issue #6).
- Feed subscribers use `/feed/`, `/feed/atom/` or `/feed/rdf/`.
- Links in publications and on other sites point at review, factsheet, issue and tag URLs and at paragraph anchors `#p{n}`.
- The listings and charts depend on exist.i-d-e.de, the downloads on GitHub raw URLs of `i-d-e/ride`.

The earlier statement in [[workflow#Gesamtbefund zum Alt-Stack]] that eXist serves only the OAI endpoint publicly is corrected by this survey: the reviewed-resources list, the reviewer list and both chart pages are live iframes onto exist.i-d-e.de.

## Correspondence on the static site

Each function falls into one of four classes. The parity report measures the classes "present" and "solved differently" per review and per URL.

### Present

Review pages with numbered paragraphs, notes, figures, bibliography, list of figures, citation suggestion, TEI and PDF download and licence; factsheet pages; issue pages and overview; tag pages; data pages including charts, reviewed resources and reviewer list (built from TEI at build time, no eXist host); editorial pages under `/about/` and `/reviewers/`; the three feeds as `.xml` endpoints and as copies at the WordPress feed paths; XML sitemap; OAI-PMH `oai_dc` snapshot files; canonical link and feed autodiscovery in every page head.

### Solved differently

- Search runs client-side through Pagefind instead of `/?s=`.
- Old addresses resolve through meta-refresh stubs (see [[redirects-feeds]]). Review addresses come from the WordPress sitemap recorded in `config/legacy-urls.json`, from the TEI address of record and from the file stem. Tag archives `/tag/{slug}/` lead to `/tags/{slug}/`, and a WordPress tag that no TEI keyword carries yet leads to the tag overview.
- The citation suggestion follows [[specification#R2 Rezension zitieren]] (title without "Review of", full editor list), so its wording differs from the live box by decision.
- Downloads are served from the static site itself instead of GitHub raw URLs.
- Share buttons are replaced by Open Graph metadata and copy links ([[specification#8 Migrationsvertrag (heute → künftig)]], row Social-Buttons).
- The static pages add a description, Open Graph tags and JSON-LD (`schema.org/ScholarlyArticle`), and the corpus offers `/api/corpus.json`, `/data/explorer.json` and corpus-wide BibTeX and CSL-JSON.

### Not yet present

- OAI-PMH `oai_marcxml` and `oai_doajxml` records, the editorial records `ride.{N}.0`, and the bare identifier form of the live endpoint (`ride.1.1`, the static snapshot writes `oai:ride.i-d-e.de:ride.1.1`).
- Answer labels of the select questions in the text-collection and tools questionnaires. The TEI carries only category identifiers such as `tokens_gt10mio`. The live factsheets show labels from the extended questionnaire files in ride-tech, and the static factsheet falls back to the identifier.
- Editorial pages outside the menu (individual calls for reviews, archived editorials, FAIR criteria, issue landing pages, copyright). Whether they move is part of the TEI conversion scope in issue #3.
- Highwire `citation_*` tags for reference managers. The live site has none either, so this is an addition rather than a parity gap.

### Deliberately not reproduced, or not reproducible statically

- Comment feed, WordPress REST API, oEmbed and XML-RPC: WordPress machinery without journal content. `/api/corpus.json` is the static data interface.
- Query-string addresses (`/?s=`, `/?p=`, `/apis/oai?verb=…`). GitHub Pages ignores the query string, so no file can answer them ([[oai-pmh-statisch#The protocol constraint]]). A queryable OAI endpoint needs a request-handling component, which remains the institutional decision of issue #6.
- Per-tag feeds and the HTML sitemap. No consumer is known; the XML sitemap and the main feeds cover the use.
- Tags that exist only in WordPress. TEI is the only tag source ([[specification#A2 Datenquellen]]), and the one-off consolidation of WordPress tags into TEI is an editorial task. The parity report lists the WordPress tags missing per review, which is the worklist for that task.

## Data that must be online for a server-free answer

- Every page as pre-rendered HTML, including factsheets, tag pages and aggregations.
- Per review the TEI file, the PDF and the figures beside the page.
- Redirect stubs at every recorded WordPress address, generated from `config/legacy-urls.json`, from the TEI address of record and from tag labels.
- Feed XML at the `.xml` endpoints and at the legacy feed paths.
- The OAI snapshot (`/oai/identify.xml`, `list-metadata-formats.xml`, `list-identifiers.xml`, `list-records.xml`, `records/{id}.xml`).
- `sitemap.xml`, `api/corpus.json`, `api/build-info.json`, `data/explorer.json`, `data/ride-corpus.bib`, `data/ride-corpus.csl.json` and the Pagefind index.

Not replaceable by files are the query-string protocols named above.

## Parity check

`scripts/parity.py` compares the two sites and writes `inventory/parity/report.json` (every finding) and `inventory/parity/summary.md` (coverage and deviations per category). `scripts/parity_fetch.py` sends every request with a neutral User-Agent, waits one second between requests to the live site, follows no redirect on its own and keeps each response under `inventory/_cache/parity/`, which Git ignores. A repeated run therefore compares the same bytes without loading the live site again, and `--offline` runs from the cache alone.

```sh
uv run python scripts/parity.py --sample                       # fixed sample, deployed static site
uv run python scripts/parity.py --full                         # every live review
uv run python scripts/parity.py --full --static-root site/     # against a local build
uv run python scripts/parity.py --full --static-root site/ --write-legacy-urls config/legacy-urls.json
```

The check joins live and static reviews by DOI, the identifier both sides print and external services resolve. Per joined review it compares title, DOI, issue, publication month, authors (from the citation suggestion), the set of numbered paragraphs, the text of each paragraph, figure files, notes, bibliography, tags, licence, the reachability of TEI and PDF download, and the factsheet answers per criterion. Text equality means equal word sequences after Unicode compatibility folding and case folding. Quotes, dashes and whitespace runs therefore do not count, while a lost space between two words does. Every URL of the live sitemap, every tag URL seen on a live review and every address printed in the live OAI records is resolved on the static site through its stubs. Contract tests cover OAI-PMH (live endpoint harvested over all resumption tokens against the snapshot), the feeds, the sitemap and the entry counts of the eXist listings.

The fixed sample (`SAMPLE` in the script) holds one review per feature the comparison has to see: figures in running text, footnotes, an amendment, `.PNG` figure files, a text-collection questionnaire, a compound review, a tools questionnaire in a rolling issue, a picture directory alias and the newest review. The full run then covers every review the live sitemap lists. `tests/test_parity.py` pins the comparison logic on trimmed copies of real pages.

### Contributions taken over from i-d-e/ride (2026-11-10)

The corpus was copied in May 2026 from `i-d-e/ride/tei_all/`, which holds the reviews but neither the issue editorials nor the OpenRefine review. The live site publishes all six with DOI and OAI record. Their TEI files were taken over unchanged from the issue folders of `i-d-e/ride` at revision 6e592d0 as `issues/{N}/reviews/editorial-tei.xml` and `issues/19/reviews/openrefine-tei.xml`; their pictures resolve from the sibling checkout like every historical review. One exception: the current revision of the issue 21 editorial is not well-formed XML (a typographic quotation mark closes two `placeName/@ref` attributes, commits of 2026-06-21). The corpus holds the last well-formed revision, 667fdb0, which differs only in the affiliation identifiers of three authors. The upstream file needs the correction.

Editorials are recognised by RIDE's numbering `ride.{N}.0` (`Review.is_editorial`). They render like a review with "By" instead of "Reviewed by", without factsheet, and their authors stay out of the reviewer list. Their WordPress factsheet address redirects to the editorial. Whether editorials should get a page type of their own is an editorial question.

The parity check finds these differences between TEI and WordPress for the six: the issue 21 editorial title lacks the prefix "EDITORIAL:" in TEI, the issue 16 editorial carries the keyword "digital scholarly editions" where WordPress tags "digital scholarly edition", and the paragraph numbering of the editorials of issues 8 and 9 differs by one paragraph. The OpenRefine factsheet has no live counterpart in the WordPress sitemap.

### Defects the check found in the static build

The first full run on 2026-11-10 found three parser defects, each now fixed with a real-corpus test.

- A `<body>` opening with an epigraph `<cit>` or a `<p>` before its `<div>` sections took the body-wrap branch, which kept the leading blocks and dropped every following section. Five reviews (commedia, whistler, bdmp, wba, ps) were published nearly without text and figures.
- Whitespace at the inner edges of `<emph>`, `<hi>` and `<ref>` was stripped, so `of the<emph> Nietzsche Estate</emph>` rendered as "theNietzsche Estate". The space now moves outside the inline element.
- A `<p>` holding only a list or a code figure lost its `xml:id`, so the cited paragraph number `#pN` had no anchor. An empty numbered paragraph now carries it.

The redirect gaps it found (WordPress slugs differing from file stems, the tag archives) are described in [[redirects-feeds#Which old addresses get a stub (2026-11-10)]].

### What the check cannot establish

- Live markup that is itself defective counts as a difference. The WordPress page for melville fuses its bibliography into one paragraph and renders amendment notes as footnotes, and the static side follows the TEI there.
- Where the WordPress text was edited after the TEI conversion (for example "Fig." against "Abb." in larepubblica), the static site follows TEI, and the report shows the divergence without deciding which version is authoritative.
- Visual layout, interaction, accessibility and the rendered PDF content stay outside the measurement. The check tests reachability of the PDF only.
