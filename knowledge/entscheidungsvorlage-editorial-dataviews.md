---
title: Decision brief — editorial boundary and data views
project:
  name: ride-static
status: decided
created: 2026-07-15
updated: 2026-07-17
language: en
related:
  - "[[workflow]]"
  - "[[redirects-feeds]]"
  - "[[architecture]]"
  - "[[specification]]"
  - "[[oai-pmh-statisch]]"
---

# Decision brief — editorial boundary and data views

Two open questions from the WP-page migration ([[workflow#Offene Redaktionsentscheidungen]]) need an editorial call, not a mechanical one. Both concern where the line runs between hand-written editorial prose and generator-native output. This brief lays out the facts and the options for each; it does not pick one. The operator context is fixed: ride-static always receives TEI-XML as its source data, so any move toward TEI here is a move of a page's source form, not a new data pipeline.

## Part A — the editorial boundary

### What runs as editorial today

An editorial page is a non-review RIDE page. Two source forms coexist, resolved in the build (`_render_editorials` in `src/build.py`):

1. **TEI pages** under `pages/**/*.xml`, validated against `schema/ride-pages.rng`, parsed by `src/parser/page.py`, rendered by `src/render/page.py`.
2. **Markdown fallback** under `content/*.md`, parsed by `src/render/editorial.py`.

A TEI page takes precedence at its slug; a Markdown page is rendered only for a slug no TEI page covers. All of the WP editorial prose pages of the migration list now have a `pages/**/*.xml` source, including `about` as of the current session. What remains Markdown-only, with no TEI page at the same slug, is four pages: the two data views `data/charts` and `data/questionnaires`, and the two twin halves `reviewers/submitting-a-review` and `reviewers/projects-for-review` whose TEI counterparts exist under different slugs (`submission-guidelines`, `suggested-projects-for-review`). Every other `content/*.md` file now sits at a slug a TEI page covers, so it is inert fallback the build never reaches.

### The grey zone: content/ against pages/

The migration produced a Markdown file and, later, a TEI file for most editorial slugs. After the TEI cutover the Markdown file at a covered slug is dead fallback the build never reaches, yet it still carries a slug and invites double maintenance. Two frontier cases sit unresolved:

- **`about`.** Genuine editorial prose. Was held as Markdown (`content/about.md`) while the build documentation deliberately treated it as generator-native. A TEI source `pages/about.xml` now exists (content-faithful to `content/about.md`, validated against the page profile) and wins at the `about` slug, so `about` is now the same kind of page as `editorial`, `team`, `imprint`: editorial prose living as TEI. This resolves `about` on the prose side; the residual item is whether the now-inert `content/about.md` fallback is retired or kept.
- **`data/charts` and `data/questionnaires`.** These are the Data views (Part B). They carry editorial prose framing a generated view. They have no TEI source and are marker-driven Markdown.

Beyond these, two pairs carry overlapping content under diverging slugs, an artefact of the migration where the flat TEI slug and the hierarchical Markdown slug never converged: `pages/submission-guidelines.xml` (slug `submission-guidelines`) against `content/submitting-a-review.md` (slug `reviewers/submitting-a-review`), and `pages/suggested-projects-for-review.xml` (slug `suggested-projects-for-review`) against `content/projects-for-review.md` (slug `reviewers/projects-for-review`). These are not the same-slug precedence case, both pages build and both are reachable; they are genuine content duplication across two URLs (flagged in the journal, 2026-06-24).

### What the criteria are

The live WP site does not resolve the boundary by itself: on WordPress every page was a WP page regardless of whether its body was prose or an embedded generated table, so the live site offers no signal about which pages "should" be TEI. The signal that does exist is internal:

- A page whose body is editorial prose (About, Editorial, Team, Imprint, Publishing Policy, Ethical Code, Contact, the Reviewers pages, the Criteria pages) fits the TEI page profile and is uniform with its siblings as TEI.
- A page whose body is a generated data view with a thin prose frame (Charts, Questionnaires) is prose around a build artefact; its substance is not authored, it is derived from the corpus at build time.

### Options for the editorial boundary

For each Markdown-only or double-sourced slug the choice is one of:

1. **Promote to TEI, retire the Markdown.** The page becomes a `pages/**/*.xml` source, validated against the profile, and its `content/*.md` twin is deleted. Consequence: one source of truth, uniform with the other editorial pages, editors edit TEI. Cost: TEI is a higher editing bar than Markdown for a page that is pure prose; the page profile must cover every construct the page uses.
2. **Keep as Markdown, accept it as generator-native.** The page stays `content/*.md` with no TEI source. Consequence: lower editing bar, and for the data views the marker-substitution mechanism (`<!-- ride:charts -->`) stays where it already works. Cost: two editorial source regimes remain side by side; a reader has to know which slug is which.
3. **Retire the inert twin only.** For slugs already covered by a TEI page, delete the dead `content/*.md` fallback and keep the TEI page as sole source. Consequence: removes silent double-maintenance without changing the editing model. Cost: loses the Markdown fallback for those slugs, so a broken TEI page no longer degrades to Markdown.

The three options are not mutually exclusive across slugs; the editorial call can differ per page (prose pages toward option 1 or 3, data views toward option 2).

## Part B — the data views

### What they are technically

`data/charts` and `data/questionnaires` are the two remaining pages where the body is a view onto the parsed corpus, not authored text.

- **`data/charts`.** `content/data-charts.md` carries editorial framing prose plus a single marker `<!-- ride:charts -->`. At build time `src/render/charts.py` (`render_charts_block`) walks every parsed review, aggregates the questionnaire answers per criteria set and per top-level section, and emits one inline-SVG bar chart per set. The build substitutes the SVG block into the marker (`_render_editorials` in `src/build.py`), so the prose stays hand-editable while the view is always re-derived from the corpus. The `value="3"` anomaly is counted separately and reported under each chart. No runtime backend, everything is materialised at build time (specification R9).
- **`data/questionnaires`.** `content/data-questionnaires.md` is currently framing prose plus a placeholder pointing at the full corpus dump (`/api/corpus.json`) and the TEI mirror; the interactive per-answer table is not built. So this page is today a prose stub over a promised view, whereas `data/charts` is a prose frame over a live view.

Both draw from the same source, the questionnaire taxonomy in each review's TEI header, which the parser already reads in full (`src/model/questionnaire.py`, `src/render/factsheet.py` for the per-review view, `src/render/explorer.py` for the interactive `/data/explore/` view).

### What a TEI framing would mean

A TEI framing here would move the prose frame of these pages into a `pages/**/*.xml` source, the same as the other editorial pages. It would not, and could not, move the generated view itself into TEI: the chart SVG and any answer table are build products aggregated across the whole corpus, they are not authored content and have no place in a hand-written TEI page body. So a TEI framing of a data view means splitting the page into an authored TEI frame and a build-injected view, keeping a substitution mechanism analogous to the current chart marker but now targeting a TEI element instead of a Markdown comment.

The page profile (`schema/ride-pages.rng`) would need a defined carrier for the injection point. The current marker is an HTML comment in Markdown; in TEI it would be a designated empty element or a `<div>` with a known attribute that the renderer fills. That is a profile extension, small but real, and it commits the data views to the same validated-source discipline as the prose pages.

### For and against a TEI framing of the data views

For:

- Uniformity. Every editorial page becomes a validated TEI source; no page sits outside the profile discipline.
- Single editing model. Editors touch TEI everywhere, not TEI for prose pages and Markdown for two data pages.
- The prose frame of a data view is genuine editorial text and benefits from the same schema guarantees as the other pages.

Against:

- The generated view stays outside TEI regardless, so a TEI framing does not make the page "a TEI page" in the way About or Editorial are; it makes the frame TEI and leaves the substance a build artefact. The hybrid is arguably less honest than an openly generator-native Markdown page.
- It needs a page-profile extension for the injection carrier, and a renderer path that fills a TEI element rather than a Markdown marker, for a gain that is uniformity rather than capability.
- The marker-substitution mechanism already works in Markdown and is simpler to reason about for a page whose point is the generated view.
- `data/questionnaires` has no built view yet, so framing it in TEI now frames an empty promise; the framing question for it is better joined to building the view.

## What is decided and what is open

Decided in the current session: `about` has a content-faithful TEI source (`pages/about.xml`) validated against the profile, so it is available as a TEI editorial page uniform with its siblings.

Open for the operator:

- Editorial boundary: per slug, promote to TEI (option 1), keep as Markdown (option 2), or retire the inert Markdown twin only (option 3). In particular whether the `content/*.md` fallbacks at TEI-covered slugs are retired, and whether the double-sourced twins (`submission-guidelines` / `submitting-a-review`, `suggested-projects-for-review` / `projects-for-review`) are consolidated.
- Data views: whether `data/charts` and `data/questionnaires` get a TEI frame (with the profile extension that requires) or stay generator-native Markdown, and whether the questionnaires view is built before its framing is decided.

## Decision (2026-07-17)

**Editorial boundary — option 3.** The inert `content/*.md` fallbacks at TEI-covered slugs are retired, and the two double-sourced twins are consolidated onto their TEI source. The twelve Markdown files whose slug a TEI page already covered (`about`, `about/contact`, `about/editorial`, `about/ethical-code`, `about/peer-reviewers`, `about/publishing-policy`, `about/team`, `criteria`, `data`, `imprint`, `reviewers/call-for-reviews`, `reviewers/ride-award`) are deleted, so each prose page has one source of truth in TEI. The two twins are consolidated by moving their TEI source into the `reviewers/` section so it renders at the `/reviewers/…/` URL the navigation and internal links already use, `pages/submission-guidelines.xml` to `pages/reviewers/submitting-a-review.xml` and `pages/suggested-projects-for-review.xml` to `pages/reviewers/projects-for-review.xml`, and the Markdown twins are deleted. The flat slugs the moved TEI pages formerly rendered at (`/submission-guidelines/`, `/suggested-projects-for-review/`) get redirect stubs onto the new URLs, so no existing URL breaks. Option 3 over option 1 because the prose is already authored in TEI and option 3 removes the silent double-maintenance without changing the editing model; the twin move keeps the TEI-sole-source discipline while preserving the live URL.

**Data views — option 2, plus building the questionnaires view.** `data/charts` and `data/questionnaires` stay generator-native Markdown with the marker-substitution mechanism, no TEI-profile extension. The `data/questionnaires` view is now built generator-native, orientated at the existing charts view but one level finer, one HTML table per criteria set with one row per question carrying the corpus-wide yes-rate. The renderer (`src/render/questionnaires.py`) substitutes into a `<!-- ride:questionnaires -->` marker the same way the charts block does. Option 2 because the generated view stays a build artefact outside TEI regardless, so a TEI frame would buy uniformity at the cost of a profile extension for no capability gain.
