---
title: OAI-PMH as static files
project:
  name: ride-static
status: decided
created: 2026-07-14
updated: 2026-07-17
language: en
related:
  - "[[redirects-feeds]]"
  - "[[workflow]]"
  - "[[pipeline]]"
---

# OAI-PMH as static files

Concept study, not an implementation, for the open OAI-PMH question in [[workflow#Offene Redaktionsentscheidungen]] and [[redirects-feeds#Open (editorial decisions)]]. Question: can RIDE's OAI-PMH endpoint be answered by files generated in the build and served from GitHub Pages, in a form that BASE, OpenAIRE and comparable harvesters actually harvest. The RIDE-specific evidence that no harvester currently consumes the live endpoint and that metadata reaches aggregators over DataCite lives in [[redirects-feeds#OAI harvester research (2026-07-10)]]; this document adds the protocol analysis and a feasibility verdict, and does not repeat those findings.

## The protocol constraint

OAI-PMH is a request-response protocol over HTTP GET. A harvester sends `?verb=…` with parameters (`metadataPrefix`, `from`, `until`, `set`, `resumptionToken`) and the repository computes the answer. Three of the six verbs return a possibly large, paginated record stream: `ListRecords`, `ListIdentifiers`, `ListSets`. Pagination runs over a `resumptionToken` the server issues and the harvester echoes on the next GET. The three remaining verbs (`Identify`, `ListMetadataFormats`, `GetRecord`) are small and parameter-light.

Two properties of GitHub Pages collide with this. First, it has no request logic: it maps a path to a file and ignores the query string entirely, so `…/oai?verb=ListRecords&metadataPrefix=oai_dc` and `…/oai?verb=Identify` resolve to the same file (or none). Second, it sets the Content-Type from the file extension and cannot be configured per route. Both are the same limits already documented for the feed copies in [[redirects-feeds#RSS 2.0 feed (decided)]].

## Two routes, and why only one is spec-defined

### Route A — pre-render verb responses at query-shaped paths

Generate one file per expected request and rely on the harvester hitting exactly that URL. This fails at the protocol level, not the effort level. GitHub Pages discards the query string, so no `?verb=…` request can be routed to a distinct file; a harvester requesting `Identify` and one requesting `ListRecords` receive the same bytes. Rewriting verbs into the path (`/oai/ListRecords/oai_dc.xml`) is not OAI-PMH, no harvester constructs such URLs. `resumptionToken` values are server-issued opaque strings; a static site cannot mint them in a way a harvester will follow, and `from`/`until` selection is a server-side filter with no static equivalent short of pre-rendering every date-range combination. Route A needs a request-handling layer, an edge worker or a thin proxy mapping verbs and tokens to snapshot files. That is the proxy option already named in [[redirects-feeds#Open (editorial decisions)]] and is by definition no longer static.

### Route B — the OAI Static Repository (spec-defined)

OAI-PMH has a dedicated answer to exactly this problem: the *Static Repository*, specified alongside the protocol. A data provider publishes a single XML file at a persistent HTTP URL; a third-party *Static Repository Gateway* reads that file and answers all six verbs on its behalf, so harvesters interact with the gateway's base URL as with any live repository. The provider hosts a static file, the gateway supplies the request logic Route A lacks.

The file is one XML document containing exactly one `Identify` block, one `ListMetadataFormats` block, and one or more `ListRecords` blocks (one per `metadataPrefix`). RIDE's corpus fits the intended scale: the spec targets collections between 1 and 5000 records, and the build already emits the record set as Dublin Core.

Hard constraints the spec places on a Static Repository, verbatim from the specification:

- "The MIME type of a Static Repository must be `text/xml`."
- "The HTTP URL must not contain a fragment or a query string."
- The repository "must not use sets", "must not include headers for deleted records", "must not include any resumptionToken elements", and "must express all datestamps using YYYY-MM-DD granularity".

The gateway synthesises `from`/`until` selection and pagination over the flat file, so the loss of `resumptionToken` and sets on the provider side is not a loss of harvestability, it is delegated to the gateway. Selective harvesting is limited to YYYY-MM-DD granularity, which matches the corpus date precision anyway.

## Where Route B strains against GitHub Pages

- **MIME type.** The spec requires `text/xml`; GitHub Pages serves an `.xml` file as `application/xml` and offers no way to override the header (same ceiling as the feed copies). Whether a given gateway rejects `application/xml` or content-sniffs past it is gateway-implementation-dependent and not guaranteed. This is the sharpest conformance risk of Route B.
- **The gateway is the hard dependency.** The static file is inert without a running Static Repository Gateway pointed at it. The only public gateway named in the literature is the experimental Los Alamos instance at `http://purl.lanl.gov/NET/srepod`, with no evidence it still runs. Open-source gateway code exists in three forms (the original Los Alamos C implementation on SourceForge, an Omeka gateway plugin, and a PHP implementation `wendig-ou/oai-srg` that states it passes data-provider validation), but each is self-hosted software requiring a server, in the PHP case an Apache-plus-MySQL stack, and none shows recent release activity. Self-hosting any of them reintroduces the server RIDE is trying to shed. No major aggregator is documented as operating a public gateway a provider can simply register against, and OpenArchives discontinued repository registration on 2025-07-18 (validation only remains).
- **Aggregator ingestion still expects a base URL.** OpenAIRE registration takes the base OAI-PMH URL of the data source and validates it against its guidelines; BASE harvests provider OAI endpoints. A Static Repository is reachable to them only through a gateway base URL, so the gateway dependency is unavoidable for the very harvesters this is meant to serve.

## Documented practice

Static Repositories are a real, specified mechanism with implementations (Omeka plugins for both the static-repository side and the gateway side, a SourceForge gateway). The pattern is documented and was demonstrated (Los Alamos, the originating IEEE/D-Lib work). What is not demonstrable is a currently running, publicly usable gateway that a small journal could register a GitHub-Pages-hosted file against and thereby appear in BASE or OpenAIRE. The mechanism exists on paper and in code; the live third-party infrastructure it depends on is not visibly maintained.

## Feasibility verdict

Producing the OAI payload as static files in the build is straightforward and already largely done (the Dublin Core record set exists as a snapshot). Making those files *harvestable as OAI-PMH* is where static hosting alone falls short: a directly queryable endpoint (Route A) is impossible on GitHub Pages because query strings are ignored, and the spec-conformant static route (Route B) hands the request logic to a Static Repository Gateway that must be operated by someone and whose public instances are not demonstrably available, with an added `text/xml`-vs-`application/xml` conformance risk. Static generation solves the data half of the problem and not the protocol half; the protocol half needs a running component, whether a gateway or a thin proxy, that is not static.

## Recommendation options

1. **Retire the OAI endpoint, keep the static snapshot as a documented export.** Justified by the RIDE-specific finding that no harvester demonstrably consumes it and metadata flows over DataCite ([[redirects-feeds#OAI harvester research (2026-07-10)]]). The `/oai/` snapshot files stay as a convenience export (the `oai_doajxml` format is already used to produce the DOAJ upload file per [[workflow#Schritt 3 — Postpublishing]]); no gateway, no proxy, no live protocol endpoint advertised.
2. **Static file plus thin proxy (Route A infrastructure).** Keep the snapshot files and put a stateless edge worker (e.g. a serverless function or CDN worker) in front that maps `?verb=…`, `from`/`until` and pagination onto the files. Protocol-conformant and queryable, but adds one hosted component; contradicts "in jedem Fall ohne eXist" only in spirit, since it is a new server, however thin.
3. **OAI Static Repository plus gateway (Route B).** Publish the single spec-conformant XML file and register it with a Static Repository Gateway. Lowest build effort, but blocked on locating or self-hosting a live gateway and on the `text/xml` MIME requirement GitHub Pages cannot meet. Recommended only if a maintained public gateway is found or the editors accept self-hosting one, which reintroduces the server this is meant to remove.
4. **Standards-based static harvesting over ResourceSync.** Sidestep OAI-PMH: expose the corpus for harvesting via ResourceSync built on the existing sitemap (already noted as an option in [[redirects-feeds#Open (editorial decisions)]]). Fully static and requires no gateway, but ResourceSync is not OAI-PMH and reaches a different, smaller set of consumers; it does not substitute for OAI where a harvester specifically expects OAI.

The `from`/`until` and `resumptionToken` machinery cannot be reproduced by static files under any route without a request-handling component; that is the load-bearing conclusion for the operator decision.

## Decision (2026-07-17)

Option 1 is decided: retire the OAI-PMH endpoint and keep the static snapshot as a documented, archivable export. The rationale is the RIDE-specific finding that no harvester demonstrably consumes the live endpoint and that metadata reaches aggregators over DataCite, so a live protocol endpoint carries cost without a demonstrable consumer. The snapshot already emitted by the build (`src/render/oai_pmh.py`, `write_oai_pmh`) is the archivable form of the decision. It writes one Dublin Core document holding every record (`/oai/list-records.xml`) plus the header listing (`/oai/list-identifiers.xml`), the repository description (`/oai/identify.xml`), the format declaration (`/oai/list-metadata-formats.xml`), and one `<GetRecord>` file per review under `/oai/records/`. The record set is regenerated from the corpus on every build, so the deployed `/oai/` tree is the current snapshot; no gateway, no proxy, and no live queryable endpoint is advertised.

The steps that reach outside the repository stay with the operator: the comment on the corresponding issue, the actual shutdown of the former eXist-served endpoint at `ride.i-d-e.de/apis/oai`, and the DOAJ path (the `oai_doajxml` format on the old endpoint was a convenience export for the manual dashboard upload, not a harvested feed, per [[redirects-feeds#OAI harvester research (2026-07-10)]]).

## Sources

All accessed 2026-07-14.

- Specification for an OAI Static Repository and an OAI Static Repository Gateway. <https://www.openarchives.org/OAI/2.0/guidelines-static-repository.htm> (MIME `text/xml` requirement, no query-string/fragment in URL, no sets/deleted-records/resumptionToken, YYYY-MM-DD granularity, single-file structure of one Identify + one ListMetadataFormats + one-or-more ListRecords blocks, 1–5000 record target, gateway intermediation, experimental Los Alamos gateway `http://purl.lanl.gov/NET/srepod`).
- The Open Archives Initiative Protocol for Metadata Harvesting, v2.0. <https://www.openarchives.org/OAI/openarchivesprotocol.html> (the six verbs, GET request-response, resumptionToken pagination, selective harvesting).
- OpenAIRE, How to validate and register a data source. <https://www.openaire.eu/validator-and-registration/> (registration takes a base OAI-PMH URL and validates against the OpenAIRE Guidelines; Dublin Core basis for literature repositories).
- MIME types on GitHub Pages / serving XML feeds on GitHub Pages. <https://mfhepp.github.io/test_mime_types/> and <https://taylor.fausak.me/2012/04/26/serving-atom-feeds-with-github-pages/> (Content-Type derived from file extension, `.xml` served as `application/xml`, no per-route header configuration).
- OAI-PMH Static Repository Gateway (SourceForge srepod), the Omeka gateway/static-repository plugins, and the PHP gateway `wendig-ou/oai-srg` as available self-hosted implementations. <https://srepod.sourceforge.net/>, <https://github.com/Daniel-KM/Omeka-plugin-OaiPmhGateway> and <https://github.com/wendig-ou/oai-srg> (PHP, requires Apache and MySQL; states it passes data-provider validation; no published releases).
- OAI-PMH data-provider registration discontinued 2025-07-18, validation retained. <https://www.openarchives.org/pmh/register_data_provider>.
