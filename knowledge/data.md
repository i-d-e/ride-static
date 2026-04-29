---
generated: 2026-04-28
source: scripts/render_data.py
inputs:
  - inventory/elements.json
  - inventory/structure.json
  - inventory/sections.json
  - inventory/cross-reference.json
  - inventory/odd-summary.json
  - inventory/tei-spec.json
  - inventory/ids.json
  - inventory/refs.json
  - inventory/taxonomy.json
---

# RIDE TEI Structure Reference

> Structural knowledge for code that walks the RIDE corpus. Lists what each element contains, what attributes it carries, and the rules a script can rely on. Re-run `python scripts/render_data.py` after the inventory changes.

## Document patterns

Rules that hold for every RIDE TEI document, derived from the inventory:

- Document root is `<TEI>` with children `[teiHeader, text]` (always).
- `<text>` children appear in two shapes: `[front, body, back]`, `[front, body]`. The shorter shape is reviews without back-matter. Code must accept both.
- 7 reviews omit `<back>` entirely (no bibliography, no appendix): `berliner-intellektuelle-tei.xml`, `busoni-nachlass-tei.xml`, `tustep-tei.xml`, `twain-tei.xml`, `victorians-tei.xml`, `wba_upgrade-tei.xml`, `wega-tei.xml`.
- `<fileDesc>` children are `[titleStmt, publicationStmt, seriesStmt, notesStmt, sourceDesc]` in fixed order. Anomaly: one review duplicates `<sourceDesc>`.
- `<publicationStmt>` children are `[publisher, date, idno, idno, idno, availability]` in every review.
- `<num>` carries the RIDE questionnaire payload (the dominant element by occurrence). It always sits inside `<catDesc>` and always has `@type` ∈ {`boolean`} with `@value` ∈ {`0`, `1`, `3`}. `@value` outside `0` / `1` should be treated as a data anomaly.
- `<row>` and `<cell>` always carry `@rows="1"` and `@cols="1"`. No merged cells exist in this corpus; the attributes are redundant noise.
- A non-trivial fraction of `<div>` elements lacks a `<head>` child. Code must derive a section title from `@xml:id` or position.
- `<body>` usually starts with `<div>`, but in some reviews it starts with `<p>` or `<cit>` — these are flat-content reviews (no top-level `<div>` wrapping).
- Classification chain: `<encodingDesc>` → `<classDecl>` → `<taxonomy>` → `<category>` (recursive) → `<catDesc>` → `<num>` | `<ref>` | `<gloss>`. This chain encodes the structured part of every RIDE review.
- `<ref target="#K…">` is **not** a local anchor — it points to a RIDE criterion ID defined in the criteria document at the matching taxonomy's `@xml:base`. Code must resolve K-prefixed refs externally, not against the per-review file. See `inventory/refs.json`.
- Reviews use one of 4 criteria sets identified by `<taxonomy/@xml:base>`. Per-review answers live as `<num type="boolean" value="0"|"1">` inside each `<catDesc>`. See "Questionnaire criteria sets" below.
- `xml:id` format constraints (Schematron) hold for the whole corpus. Code can trust the patterns listed under "ID format conformance" below; libxml2 also enforces within-file uniqueness at parse time.

## Reference resolution

`<ref @target>` falls into four buckets the build phase must distinguish:

- **Local anchors.** `target` starts with `#` and the anchor exists in the same file. Resolve to an in-page HTML link.
- **Criteria references.** `target` starts with `#K` (e.g. `#K1.2`, `#K4.16`). These are *not* local anchors — they reference RIDE criterion IDs defined in the criteria document at the matching taxonomy's `@xml:base`. They show up as the dominant family of "dangling" internal refs because the IDs only exist externally. Resolve them against the criteria URL, not against the file.
- **External URLs.** `http://` or `https://`. Pass through. Most external targets archive reviewed resources at `web.archive.org`, `doi.org`, `www.i-d-e.de`.
- **Other.** A small number of `mailto:`, relative paths, and typos (e.g. `#http…`). Render as plain text and warn at build time.

Beyond `K`, dangling-prefix families to expect are: `#abb…`, `#appendix…`, `#bbaw…`, `#bollmanndipper…`, `#giacomelli_settesoldi…`, `#haines…`. Most are individual edge cases; review case-by-case.

## Questionnaire criteria sets

RIDE reviews fill a structured questionnaire driven by a shared `<taxonomy>` embedded in `<encodingDesc>/<classDecl>`. Each taxonomy is identified by its `@xml:base` (the canonical criteria URL on i-d-e.de). The corpus uses the following criteria sets:

- `http://www.i-d-e.de/criteria-text-collections-version-1-0` — 282 categories, depth 5, used by 10 taxonomy embedding(s).
- `http://www.i-d-e.de/publikationen/weitereschriften/criteria-version-1-1` — 224 categories, depth 3, used by 73 taxonomy embedding(s).
- `https://www.i-d-e.de/publikationen/weitereschriften/criteria-text-collections…` — 282 categories, depth 5, used by 10 taxonomy embedding(s).
- `https://www.i-d-e.de/publikationen/weitereschriften/criteria-tools-version-1/` — 245 categories, depth 3, used by 17 taxonomy embedding(s).

Inside each `<category>`, a `<num type="boolean" value="0"|"1">` records the review's yes/no answer. Some reviews embed multiple `<taxonomy>` blocks. The full structure plus per-review answers is in `inventory/taxonomy.json` — Stage 2.C will hydrate a `Questionnaire` model directly from there.

## ID format conformance

`ride.odd`'s Schematron mandates strict ID formats. The current corpus respects each:

- `<TEI/@xml:id>` must match `^ride\.\d{1,2}\.\d{1,2}$`
- `<div/@xml:id>` must match `^div\d{1,2}(\.\d{1,2}){0,2}$`

Zero format violations across the corpus — code can rely on these patterns.

Within-file uniqueness of `xml:id` is enforced by libxml2 at parse time (duplicate IDs raise `XMLSyntaxError`), so any file we successfully parse is guaranteed unique on that axis.

## Schema vs. corpus mismatches

Cases where the empirical corpus does not match `ride.odd`. Each item is either a stale schema rule or a real data anomaly:

- `<taxonomy>/@m` is not documented in TEI P5 — likely a custom or stale attribute. Code should not rely on it.
- `<num>/@type`: corpus uses `boolean` which are not in the `ride.odd` closed list [`cardinal`, `ordinal`, `fraction`, `percentage`]. Either the schema is stale or the data has typos.
- `<ref>/@type`: corpus uses `crosssref` which are not in the `ride.odd` closed list [`crossref`, `bibl`]. Either the schema is stale or the data has typos.
- `<list>/@rend`: corpus uses `numbered`, `unordered` which are not in the `ride.odd` closed list [`bulleted`, `ordered`, `labeled`]. Either the schema is stale or the data has typos.

## Functional element reference

### Document skeleton

#### `<TEI>`
- Appears at document root.
- Children: `[teiHeader, text]` (always).
- Attributes:
  - `@xml:id` — always; open (free identifier or URL)

#### `<teiHeader>`
- Appears under `TEI`.
- Children: `[fileDesc, encodingDesc, profileDesc]` (always).

#### `<text>`
- Appears under `TEI`.
- Children: typically `[front, body, back]`; sometimes `[front, body]`.


### Header — file description

#### `<fileDesc>`
- Appears under `TEI/teiHeader`.
- Children: `[titleStmt, publicationStmt, seriesStmt, notesStmt, sourceDesc]` (always).

#### `<titleStmt>`
- Appears under `TEI/teiHeader/fileDesc`.
- Children: typically `[title, author]`; sometimes `[title, author, author]`.

#### `<publicationStmt>`
- Appears under `TEI/teiHeader/fileDesc`.
- Children: `[publisher, date, idno, idno, idno, availability]` (always).
- The three `<idno>` children carry distinct `@type` values: `URI` (the live page on `ride.i-d-e.de`), `DOI` (the article DOI, e.g. `10.18716/ride.a.5.4`), and `archive` (the PDF archive URL on the GitHub `i-d-e/ride` repository). The DOI is the canonical persistent identifier per [[requirements#R2 Rezension zitieren]] and feeds `Review.doi`.

#### `<seriesStmt>`
- Appears under `TEI/teiHeader/fileDesc`.
- Common children: `editor`, `idno`, `title`, `biblScope`.

#### `<notesStmt>`
- Appears under `TEI/teiHeader/fileDesc`.
- Children: `[relatedItem, relatedItem]` (always).

#### `<sourceDesc>`
- Appears under `TEI/teiHeader/fileDesc`.
- Children: `[p]` (always).


### Header — encoding & classification

#### `<encodingDesc>`
- Appears under `TEI/teiHeader`.
- Children: `[classDecl]` (always).

#### `<classDecl>`
- Appears under `TEI/teiHeader/encodingDesc`.
- Children: `[taxonomy]` (always).

#### `<taxonomy>`
- Appears under `TEI/teiHeader/encodingDesc/classDecl`.
- Common children: `category`, `desc`.
- Attributes:
  - `@xml:base` — always; values: `http://www.i-d-e.de/publikationen/weitereschriften/criteria-version-1-1`, `https://www.i-d-e.de/publikationen/weitereschriften/criteria-tools-version-1/`, `https://www.i-d-e.de/publikationen/weitereschriften/criteria-text-collections-version-1-0/`, `http://www.i-d-e.de/criteria-text-collections-version-1-0`
  - `@n` — rare; values seen: `rev2` | `rev1` | `rev3`
  - `@m` — rare; always `rev1`

#### `<category>`
- Appears under `TEI/teiHeader/encodingDesc/classDecl/taxonomy/category/category`, `TEI/teiHeader/encodingDesc/classDecl/taxonomy/category`, `TEI/teiHeader/encodingDesc/classDecl/taxonomy/category/category/category`.
- Common children: `catDesc`, `category`, `desc`.
- Attributes:
  - `@xml:id` — usually; open (free identifier or URL)
  - `@corresp` — rare; values: `#free`, `#other`, `#none`, `#unknown`, `#not_applicable`

#### `<catDesc>`
- Appears under `TEI/teiHeader/encodingDesc/classDecl/taxonomy/category/category/category`, `TEI/teiHeader/encodingDesc/classDecl/taxonomy/category/category`, `TEI/teiHeader/encodingDesc/classDecl/taxonomy/category/category/category/category`.
- Common children: `num`, `ref`, `gloss`.

#### `<num>`
- Appears under `TEI/teiHeader/encodingDesc/classDecl/taxonomy/category/category/category/catDesc`, `TEI/teiHeader/encodingDesc/classDecl/taxonomy/category/category/category/category/catDesc`, `TEI/teiHeader/encodingDesc/classDecl/taxonomy/category/category/catDesc`.
- Leaf — text content only.
- Attributes:
  - `@type` — always; always `boolean`
  - `@value` — always; values: `0`, `1`, `3`


### Header — profile

#### `<profileDesc>`
- Appears under `TEI/teiHeader`.
- Children: `[langUsage, textClass]` (always).

#### `<langUsage>`
- Appears under `TEI/teiHeader/profileDesc`.
- Children: `[language]` (always).

#### `<language>`
- Appears under `TEI/teiHeader/profileDesc/langUsage`.
- Leaf — text content only.
- Attributes:
  - `@ident` — always; values: `en`, `de`, `fr`, `it`

#### `<textClass>`
- Appears under `TEI/teiHeader/profileDesc`.
- Children: `[keywords]` (always).

#### `<keywords>`
- Appears under `TEI/teiHeader/profileDesc/textClass`.
- Common children: `term`.
- Attributes:
  - `@xml:lang` — always; always `en`

#### `<term>`
- Appears under `TEI/teiHeader/profileDesc/textClass/keywords`.
- Leaf — text content only.

#### `<gloss>`
- Appears under `TEI/teiHeader/encodingDesc/classDecl/taxonomy/category/category/category/catDesc`.
- Leaf — text content only.


### Header — revision

#### `<revisionDesc>`
- Appears under `TEI/teiHeader`.
- Children: `[listChange]` (always).

#### `<listChange>`
- Appears under `TEI/teiHeader/revisionDesc`.
- Common children: `change`.
- Attributes:
  - `@type` — always; always `post-publication`

#### `<change>`
- Appears under `TEI/teiHeader/revisionDesc/listChange`.
- Leaf — text content only.
- Attributes:
  - `@resp` — always; always `author`
  - `@when` — always; values: `2016-01-01`, `2014-11-22`
  - `@xml:id` — always; values: `revision1`, `revision2`, `revision3`, `revision4`, `revision5` (and others)


### Sections

#### `<front>`
- Appears under `TEI/text`.
- Children: `[div]` (always).

#### `<body>`
- Appears under `TEI/text`.
- Common children: `div`, `p`, `cit`.

#### `<back>`
- Appears under `TEI/text`.
- Children: `[div]` (always).

#### `<div>`
- Appears under `TEI/text/body`, `TEI/text/body/div`, `TEI/text/front`.
- Common children: `p`, `head`, `div`, `listBibl`, `table`, `figure`.
- Attributes:
  - `@xml:id` — usually; open (free identifier or URL)
  - `@type` — occasionally; values seen: `abstract` | `bibliography` | `appendix`

#### `<head>`
- Appears under `TEI/text/body/div`, `TEI/text/body/div/p/figure`, `TEI/text/body/div/div`.
- Common children: `emph`, `ref`, `note`, `code`, `hi`, `mod`.
- Attributes:
  - `@type` — often; always `legend`


### Block content

#### `<p>`
- Appears under `TEI/text/body/div`, `TEI/text/body/div/div`, `TEI/teiHeader/fileDesc/sourceDesc`.
- Common children: `emph`, `note`, `ref`, `figure`, `code`, `list`.
- Attributes:
  - `@xml:id` — usually; open (free identifier or URL)
  - `@rend` — rare; always `Metadata-Categories`
  - `@style` — rare; always `text-align: justify;`

#### `<list>`
- Appears under `TEI/text/body/div/p`, `TEI/text/body/div/div/p`, `TEI/text/body/div/div/div/p`.
- Common children: `item`, `figure`.
- Attributes:
  - `@rend` — always; values: `bulleted`, `ordered`, `numbered`, `unordered`, `labeled`

#### `<item>`
- Appears under `TEI/text/body/div/p/list`, `TEI/text/body/div/div/p/list`, `TEI/text/body/div/div/p/table/row/cell/list`.
- Common children: `emph`, `code`, `ref`, `note`, `label`, `hi`.
- Attributes:
  - `@n` — rare; values seen: `1` | `2` | `3` | `4`

#### `<table>`
- Appears under `TEI/text/body/div/div/div`, `TEI/text/body/div/p`, `TEI/text/body/div/div/p`.
- Common children: `row`, `head`.
- Attributes:
  - `@xml:id` — occasionally; always `table1`

#### `<row>`
- Appears under `TEI/text/body/div/p/table`, `TEI/text/body/div/div/p/table`, `TEI/text/body/div/div/div/table`.
- Common children: `cell`.
- Attributes:
  - `@role` — usually; values seen: `data` | `label`
  - `@cols` — often; always `1`
  - `@rows` — often; always `1`

#### `<cell>`
- Appears under `TEI/text/body/div/p/table/row`, `TEI/text/body/div/div/div/table/row`, `TEI/text/body/div/div/p/table/row`.
- Common children: `ref`, `figure`, `hi`, `note`, `emph`, `lb`.
- Attributes:
  - `@role` — often; always `data`
  - `@cols` — often; always `1`
  - `@rows` — often; always `1`

#### `<figure>`
- Appears under `TEI/text/body/div/p`, `TEI/text/body/div/div/p`, `TEI/text/body/div/div/div/p`.
- Children: `[graphic, head]` (always).
- Attributes:
  - `@xml:id` — always; values: `img1`, `img2`, `img3`, `img4`, `img5` (and others)

#### `<graphic>`
- Appears under `TEI/text/body/div/p/figure`, `TEI/text/body/div/div/p/figure`, `TEI/text/body/div/div/div/p/figure`.
- Leaf — text content only.
- Attributes:
  - `@url` — always; open (free identifier or URL)

#### `<cit>`
- Appears under `TEI/text/body/div/p`, `TEI/text/body/div/div/p`, `TEI/text/body`.
- Children: typically `[quote, bibl]`; sometimes `[quote]`.

#### `<quote>`
- Appears under `TEI/text/body/div/p/cit`, `TEI/text/body/div/div/p/cit`, `TEI/text/body/cit`.
- Common children: `lb`, `emph`, `note`, `code`, `ref`.

#### `<code>`
- Appears under `TEI/text/body/div/p`, `TEI/text/body/div/div/p`, `TEI/text/body/div/div/p/list/item`.
- Leaf — text content only.

#### `<lb>`
- Appears under `TEI/text/body/div/div/p/figure/eg`, `TEI/text/body/div/p/figure/eg`, `TEI/text/body/div/div/p/cit/quote`.
- Leaf — text content only.

#### `<space>`
- Appears under `TEI/text/body/div/div/p/figure/eg`, `TEI/text/body/div/p/figure/eg`.
- Leaf — text content only.
- Attributes:
  - `@quantity` — always; values: `2`, `4`, `6`
  - `@unit` — always; always `chars`

#### `<eg>`
- Appears under `TEI/text/body/div/p/figure`, `TEI/text/body/div/div/p/figure`.
- Common children: `lb`, `space`.
- Attributes:
  - `@xml:space` — often; always `preserve`


### Inline content

#### `<emph>`
- Appears under `TEI/text/body/div/p`, `TEI/text/back/div/listBibl/bibl`, `TEI/text/body/div/div/p`.
- Common children: `ref`, `emph`.

#### `<ref>`
- Appears under `TEI/teiHeader/encodingDesc/classDecl/taxonomy/category/category/catDesc`, `TEI/text/body/div/p`, `TEI/text/body/div/p/note`.
- Common children: `emph`.
- Attributes:
  - `@target` — always; open (free identifier or URL)
  - `@type` — occasionally; values seen: `crossref` | `crosssref`

#### `<hi>`
- Appears under `TEI/text/body/div/p`, `TEI/text/body/div/div/p`, `TEI/text/body/div/div/div/table/row/cell`.
- Leaf — text content only.
- Attributes:
  - `@rend` — always; values: `sup`, `bold`, `subscript`, `underline superscript`, `underline subscript` (and others)
  - `@style` — rare; always `font-family:EB Garamond;font-size:9pt`
  - `@xml:space` — rare; always `preserve`

#### `<note>`
- Appears under `TEI/text/body/div/p`, `TEI/text/body/div/div/p`, `TEI/text/body/div/div/div/p`.
- Common children: `ref`, `emph`, `code`, `hi`, `p`, `lb`.
- Attributes:
  - `@xml:id` — always; open (free identifier or URL)

#### `<label>`
- Appears under `TEI/text/body/p/list/item`.
- Leaf — text content only.


### Bibliography apparatus

#### `<listBibl>`
- Appears under `TEI/text/back/div`.
- Common children: `bibl`, `head`.

#### `<bibl>`
- Appears under `TEI/text/back/div/listBibl`, `TEI/teiHeader/fileDesc/notesStmt/relatedItem`, `TEI/text/body/div/p/cit`.
- Common children: `emph`, `respStmt`, `ref`, `date`, `title`, `editor`.
- Attributes:
  - `@xml:id` — often; open (free identifier or URL)

#### `<title>`
- Appears under `TEI/teiHeader/fileDesc/notesStmt/relatedItem/bibl`, `TEI/teiHeader/fileDesc/titleStmt`, `TEI/teiHeader/fileDesc/seriesStmt`.
- Common children: `emph`.
- Attributes:
  - `@level` — often; always `j`

#### `<biblScope>`
- Appears under `TEI/teiHeader/fileDesc/seriesStmt`.
- Leaf — text content only.
- Attributes:
  - `@n` — always; values seen: `6` | `15` | `5` | `8` | `20` | `17` | `14` | `2` | `16` | `12` | `18` | `1` | `7` | `11` | `3` | `9` | `4` | `13` | `10` | `19` | `22` | `21`
  - `@unit` — always; always `issue`

#### `<idno>`
- Appears under `TEI/teiHeader/fileDesc/publicationStmt`, `TEI/teiHeader/fileDesc/seriesStmt`, `TEI/teiHeader/fileDesc/notesStmt/relatedItem/bibl`.
- Leaf — text content only.
- Attributes:
  - `@type` — always; values seen: `URI` | `DOI` | `archive`

#### `<date>`
- Appears under `TEI/teiHeader/fileDesc/notesStmt/relatedItem/bibl`, `TEI/teiHeader/fileDesc/publicationStmt`.
- Leaf — text content only.
- Attributes:
  - `@type` — often; values seen: `publication` | `accessed`
  - `@when` — often; values: `2017-09`, `2022-12`, `2017-02`, `2018-02`, `2014-12` (and others)

#### `<publisher>`
- Appears under `TEI/teiHeader/fileDesc/publicationStmt`.
- Leaf — text content only.

#### `<availability>`
- Appears under `TEI/teiHeader/fileDesc/publicationStmt`.
- Children: `[licence]` (always).

#### `<licence>`
- Appears under `TEI/teiHeader/fileDesc/publicationStmt/availability`.
- Leaf — text content only.
- Attributes:
  - `@target` — always; always `http://creativecommons.org/licenses/by/4.0/`

#### `<editor>`
- Appears under `TEI/teiHeader/fileDesc/seriesStmt`, `TEI/teiHeader/fileDesc/notesStmt/relatedItem/bibl`.
- Leaf — text content only.
- Attributes:
  - `@ref` — usually; values: `https://orcid.org/0000-0003-2852-065X`, `https://orcid.org/0000-0001-8279-9298`, `https://orcid.org/0000-0002-6457-0913`, `http://viaf.org/viaf/80243768`, `https://orcid.org/0000-0003-1438-3236` (and others)
  - `@role` — often; values seen: `managing` | `technical` | `assistant` | `chief`

#### `<author>`
- Appears under `TEI/teiHeader/fileDesc/titleStmt`.
- Children: `[name, affiliation, email]` (always).
- Attributes:
  - `@ref` — usually; open (free identifier or URL)

#### `<respStmt>`
- Appears under `TEI/teiHeader/fileDesc/notesStmt/relatedItem/bibl`.
- Children: `[resp, persName]` (always).

#### `<resp>`
- Appears under `TEI/teiHeader/fileDesc/notesStmt/relatedItem/bibl/respStmt`.
- Leaf — text content only.

#### `<relatedItem>`
- Appears under `TEI/teiHeader/fileDesc/notesStmt`.
- Children: `[bibl]` (always).
- Attributes:
  - `@type` — always; values seen: `reviewed_resource` | `reviewing_criteria`
  - `@xml:id` — rare; values: `rev1`, `rev2`, `rev3`


### People & affiliation

#### `<persName>`
- Appears under `TEI/teiHeader/fileDesc/notesStmt/relatedItem/bibl/respStmt`.
- Common children: `name`.

#### `<forename>`
- Appears under `TEI/teiHeader/fileDesc/titleStmt/author/name`.
- Leaf — text content only.

#### `<surname>`
- Appears under `TEI/teiHeader/fileDesc/titleStmt/author/name`.
- Leaf — text content only.

#### `<name>`
- Appears under `TEI/teiHeader/fileDesc/notesStmt/relatedItem/bibl/respStmt/persName`, `TEI/teiHeader/fileDesc/titleStmt/author`.
- Common children: `forename`, `surname`.

#### `<orgName>`
- Appears under `TEI/teiHeader/fileDesc/titleStmt/author/affiliation`.
- Leaf — text content only.

#### `<placeName>`
- Appears under `TEI/teiHeader/fileDesc/titleStmt/author/affiliation`.
- Leaf — text content only.
- Attributes:
  - `@ref` — usually; open (free identifier or URL)

#### `<affiliation>`
- Appears under `TEI/teiHeader/fileDesc/titleStmt/author`, `TEI/text/body/div/head`.
- Children: `[orgName, placeName]` (always).

#### `<email>`
- Appears under `TEI/teiHeader/fileDesc/titleStmt/author`.
- Leaf — text content only.


### Editorial markup

#### `<mod>`
- Appears under `TEI/text/body/div/div/p`, `TEI/text/body/div/div/p/figure/head`, `TEI/text/body/div/p`.
- Children: typically `[subst, note]`; sometimes `[del, note]`.
- Attributes:
  - `@change` — always; values: `#revision1`, `#revision2`, `#revision3`, `#revision4`, `#revision5` (and others)
  - `@n` — always; values seen: `i` | `ii` | `iii` | `iv` | `v` | `vi`
  - `@xml:id` — always; values: `ftn-i`, `ftn-ii`, `ftn-iii`, `ftn-iv`, `ftn-v` (and others)

#### `<subst>`
- Appears under `TEI/text/body/div/div/p/mod`, `TEI/text/body/div/div/p/figure/head/mod`, `TEI/text/body/div/p/mod`.
- Children: `[del, add]` (always).

#### `<add>`
- Appears under `TEI/text/body/div/div/p/mod/subst`, `TEI/text/body/div/div/p/figure/head/mod/subst`, `TEI/text/body/div/p/mod/subst`.
- Common children: `ref`.

#### `<del>`
- Appears under `TEI/text/body/div/div/p/mod/subst`, `TEI/text/body/div/p`, `TEI/text/body/div/p/list/item`.
- Common children: `ref`, `emph`.

#### `<seg>`
- Appears under `TEI/text/body/div/div/p/note`.
- Leaf — text content only.
- Attributes:
  - `@xml:space` — always; always `preserve`

#### `<desc>`
- Appears under `TEI/teiHeader/encodingDesc/classDecl/taxonomy/category/category/category/category`, `TEI/teiHeader/encodingDesc/classDecl/taxonomy/category/category/category/category/category`, `TEI/teiHeader/encodingDesc/classDecl/taxonomy/category/category/category`.
- Leaf — text content only.
