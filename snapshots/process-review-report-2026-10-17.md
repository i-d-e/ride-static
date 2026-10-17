---
title: Publication process review
project:
  name: ride-static
  repository: https://github.com/i-d-e/ride-static
method:
  name: Promptotyping
  url: https://dhcraft.org/excellence/blog/Promptotyping
status: snapshot
created: 2026-10-17
updated: 2026-10-17
language: en
related:
  - "[[workflow]]"
  - "[[pipeline]]"
  - "[[redirects-feeds]]"
  - "[[teicrafter-pilot]]"
---

# Publication process review

The existing generator supports prepared TEI, editorial pages and multiple publication outputs. Its public migration preview still has reproducible search and URL defects. Confidential editorial review, human release responsibility and metadata handover remain incomplete. These findings support bounded repair and an explicit editorial operating agreement. They provide no technical reason for replacing the static architecture.

## Source boundary and verification

This dated analysis covers RIDE-PROCESS-REVIEW-2026-10-17. It changes documentation only. Product code, editorial content, dependencies, deployment and external services remain untouched.

| Evidence | Observed state on 17 October 2026 |
|---|---|
| Local source | main at 1bdc9ab2f10bf795b08e3cade5d508b2d44deb68, including the completed editorial-page build-filter correction |
| Remote source after fetch | main at cb141fbd6ac21f4e32f0acb913f677581c97bad2 |
| Public build | api/build-info.json identifies cb141fb and its 23 August commit date |
| Latest public CI | [Successful run 32631887506](https://github.com/i-d-e/ride-static/actions/runs/32631887506), executed on 23 August, inspected again today |
| Fresh local suite | 752 passed, 2 native-PDF tests skipped because WeasyPrint or its system libraries were unavailable |
| Fresh builds | Production and draft-inclusive builds both completed with validation enabled and PDF disabled |
| Fresh lint and lock checks | Ruff passed. Offline lock consistency passed. The locked environment was not installed or rerun |
| Public browser checks | Search failed to mount. A homepage editorial link opened a GitHub 404. Draft review and factsheet displayed their draft status and artifact navigation |

The local suite used existing host Python 3.11.9 packages, including pytest 8.4.2, rather than a newly synchronized uv environment. The repository has no configured typechecker. The earlier baseline found existing whole-repository formatting differences. This review did not reformat files or repeat that formatting audit.

Both fresh builds reported 114 input files without hard validation errors and 62 warning findings. Production rendered 111 published reviews. The preview rendered those reviews and three drafts. A focused output audit found no draft identifiers in the production corpus, explorer data, sitemap, feeds, static OAI records or bibliography exports. Preview draft pages had noindex/nofollow, no canonical URL and no JSON-LD.

Fresh local PDF generation, Pagefind indexing, Java ODD compilation, responsive visual inspection and accessibility testing were not performed. Their successful steps in the August CI are historical evidence. A public draft PDF was downloaded and its PDF signature checked, without a fresh visual examination. Temporary logs and build outputs were kept outside the repository. The observations needed for decisions are recorded here so they survive scratch cleanup.

## Current publication path

1. Editorial preparation starts before this generator. The documented LimeSurvey-to-TEI conversion belongs upstream. The supported technical entrance here is a prepared review.xml with its questionnaire information and review assets. Whether conversion itself belongs in the future editorial service remains an editorial scope decision.
2. The generator discovers historical flat files and newer review bundles. New bundles keep their pictures alongside the TEI. The TEI revision status controls draft inclusion. Published identifiers and DOI-to-output mappings are checked, including duplicate output paths. The previous DOI conflict has already been corrected and must not become a new implementation task.
3. Parsing and rendering produce the review, an independent factsheet page, source TEI and optional PDF. Aggregations then produce issue listings, indexes, corpus and explorer data, feeds, bibliographic exports, static OAI XML and redirects. Editorial prose normally comes from pages/**/*.xml. Some generated data views and homepage content retain Markdown sources for their distinct functions.
4. Validation distinguishes strict new bundles from inherited corpus drift. Existing Relax NG warnings can coexist with a successful build. Validation runs late enough to write diagnostic output, and hard failures still produce a nonzero exit that prevents successful CI publication. Embedded Schematron assertions are not executed.
5. Draft previews support technical and editorial inspection. The public examples are explicitly authorized self-audits and visibly identify their status. They demonstrate the four-artifact workflow. Their existence establishes neither independent review nor human editorial acceptance.
6. Human release decisions remain outside the generator. The build consumes publication status but cannot infer that the responsible editor has approved the content, identifier assignment or publication. The code defaults absent legacy status to published, so the new-bundle authoring contract needs explicit status discipline.
7. GitHub Actions installs locked Python dependencies, checks schema generation, runs lint and tests, builds PDF outputs, invokes Pagefind and deploys GitHub Pages. The workflow also creates a draft artifact with limited retention. The currently public build includes the authorized example drafts. A future confidential draft must stay outside the public repository and public build inputs.
8. Maintenance retains amendments and legacy URLs, with an unresolved dependence on some images on the old host. DataCite, DOAJ and OAI handover still require actual operational information and responsible institutions.

The workflow listens for repository_dispatch notifications but does not check out the private editorial repository. A notification does not carry a completed private review into the publication source. Copy-ready sender workflow templates establish a proposed integration, not evidence that another repository has installed and exercised it.

## Findings and bounded improvements

### Confidential preview and release responsibility

The public examples are inspectable, while [issue 5](https://github.com/i-d-e/ride-static/issues/5) still requires protected preview and a defined approval process. The current public build includes every discovered draft when include-drafts is enabled. There is no individual public-draft allowlist. A noindex instruction controls indexing and provides no access protection. A confidential source committed to the public repository would already cross the confidentiality boundary.

Agree the review audience, the access owner and the person or role authorizing release. Prefer an existing protected institutional hosting route if it meets these requirements. Keep confidential inputs and preview deployment separate from the public examples. A successful rehearsal should update one approved test bundle, expose all four artifacts to authorized readers, deny anonymous access and demonstrate that the confidential identifier is absent from public inputs and outputs. Preserve prepared TEI as the technical entrance unless the editorial process actually requires conversion support here.

### Search fails in the deployed preview

The public homepage produced the browser error `PagefindUI is not a constructor` from static/js/pagefind.js, and no search input mounted. That module dynamically imports the generated UI script and expects a constructor export. The deployed bundle does not satisfy this expectation. Existing JavaScript tests inspect source hooks and module structure without running this browser path. Successful index creation therefore does not prove usable search. The workflow also invokes an unpinned `npx -y pagefind`.

Use the supported UI entry point for a tested Pagefind version and pin that version in the existing build command. Add a small browser check that enters an actual published review title, receives a result and follows its correct URL. Check draft exclusion in the same indexed output. This repairs a reader-facing function without introducing another search system.

### Deployment prefixes and sitemap coverage

The homepage Editorial link points to https://i-d-e.github.io/about/editorial/ and returns 404 because the project prefix is missing. The local output audit found seven root-relative editorial destinations with the same problem. The regular navigation retains the correct prefix. Markdown editorial rendering and TEI reference rendering both preserve raw root-relative references, which explains why some link paths work while body links fail.

The public sitemap contains locations such as `/ride-static/` without a scheme or host. All 618 audited local sitemap locations have this form. The sitemap also omits all 17 rendered editorial TEI pages because its source enumeration uses Markdown editorial discovery rather than the rendered TEI page set.

Resolve internal body links through a shared deployment-aware URL function, supply the absolute public origin where metadata requires it, and derive sitemap page coverage from actual rendered pages. Verify internal destinations both at the project prefix and at a domain root. Require absolute sitemap URLs and coverage of the actual editorial pages. Inspect feed, canonical and structured-data URLs in the same bounded change rather than assuming they inherit a fix automatically. Relevant implementation is in src/render/editorial.py, src/render/page.py, src/render/sitemap.py and src/build.py::_write_sitemap.

### Legacy diagnostics still need an operating rule

Both fresh builds copied 756 assets and reported 63 missing files, with no bundle errors or unparseable files. The published August build reports different asset counts, consistent with a separate image checkout. These figures are build snapshots rather than stable corpus properties. A selected legacy image still returned HTTP 200 from the old WordPress host. A missing local copy therefore establishes a migration dependency, not proof that every corresponding live illustration is currently broken.

Turn the existing warning and missing-asset reports into a reviewed baseline. Distinguish accepted historical exceptions from newly introduced failures, and establish where the affected images will be served before switching off the old host. Successful verification should show the selected review illustrations served from their intended preserved source and detect new unexplained missing assets. A wholesale corpus rewrite has no demonstrated benefit for this particular gap.

### Validation and editorial acceptance have different reach

New-bundle schema and asset failures already stop the build. Legacy warnings remain deliberately nonblocking. The summary field files_valid means no hard error under this policy and must not be read as proof that every file strictly conforms to the current schema. Executable Schematron remains a documented gap, while DOI collision and publication-path safeguards already exist in runtime code.

Select concrete editorial assertions that catch a known invalid input and pilot their execution with explicit legacy exceptions. Use a small failing example derived from actual data, then confirm the corrected input passes. Human judgments about review quality, independence and release remain a separately recorded editorial act. Enabling all inherited assertions at once would obscure which rules the editorial team actually accepts.

### External metadata handover remains evidence-dependent

The legacy endpoint https://ride.i-d-e.de/apis/oai?verb=Identify returned an OAI-PMH 2.0 XML response during this review. The static generator exports XML documents but does not implement the query protocol of a live OAI-PMH service. Repository inspection cannot establish whether external consumers use the old endpoint.

A July design record recommends retiring it on the premise that no harvester was found. Later corrected public comments explicitly state that usage is unknown. [Issue 6](https://github.com/i-d-e/ride-static/issues/6) requires the actual DataCite and DOAJ procedure, responsible owner and role of the static exports. The corrected statements in [issue 2](https://github.com/i-d-e/ride-static/issues/2#issuecomment-5385112766) and [issue 4](https://github.com/i-d-e/ride-static/issues/4#issuecomment-5385112867) qualify the older recommendation.

Obtain the current submission procedure and evidence of endpoint use from the responsible service owners or available logs. Keep the existing endpoint available while that use is unresolved. Then record whether continuity, replacement or retirement is required and reconcile the older design recommendation with the corrected premise. A new API or proxy would be premature before a consumer requirement is established.

### Maintenance instructions and build provenance need small corrections

The current documentation contains several outdated operational claims. The pilot still lists a DOI conflict already fixed in August. Historical entries saying commit or push are pending must be read with the subsequent successful deployment. README, the index glossary and extension guidance describe YAML-only rendering changes, while config/README.md identifies the mapping files as specifications that runtime does not consume. Activating an unused configuration abstraction would add work. Correcting the contributor instructions to describe the actual template and CSS path would remove the immediate confusion.

The build report records the site-code commit and its commit timestamp. The image checkout and unpinned Pagefind invocation add inputs that this identifier alone cannot reproduce. Extend the existing build report with actual build time and the relevant external source revision and tool version. This would make future differences in assets and search attributable without introducing another orchestration layer.

## Decision objects

- Authorize a bounded technical stabilization of search, internal URLs and sitemap output, with real browser and output checks as acceptance evidence. Include the directly related version and provenance corrections if desired. Existing architecture and editorial content can stay intact.
- Establish the protected editorial preview and release agreement. The institution must supply the permitted audience, access responsibility and release role. An existing protected host is the preferred candidate if available. Keeping the public examples alone leaves confidential review unsupported.
- Request the actual DataCite, DOAJ and OAI handover information from the responsible institutions. Preserve the current service while use is unknown. Implementation can then follow the real submission and consumer requirements.

Legacy diagnostics, selected Schematron rules and instruction corrections can be specified as follow-up maintenance within that agreed operating process. They are recommendations in this review and have not been implemented.

## Sources and limits

The assessment combines current README and project rules, the relevant knowledge documents, workflow and source code, actual TEI and bundle inputs, fresh local tests and isolated builds, public GitHub issues and their comments, public Actions metadata, build-info, sitemap, browser interactions and selected public artifact requests. [Issue 3](https://github.com/i-d-e/ride-static/issues/3#issuecomment-5385112816) distinguishes completed TEI migration from outstanding scholarly proofreading. Public threads read here do not establish a subsequent human editorial acceptance. Private correspondence and decisions elsewhere were not searched.

The private editorial repository, service accounts, server logs and upstream sender installation were not inspected. Current DataCite or DOAJ account procedures were not independently verified. This report completes the commissioned analysis. Editorial acceptance of the report and authorization of its proposals remain with the operator.
