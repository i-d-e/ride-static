---
generated: 2026-04-28
source: scripts/render_schema.py
inputs:
  - inventory/odd-summary.json
  - inventory/elements.json
  - inventory/cross-reference.json
---

# RIDE Schema Reference

> What `ride.odd` imports, customises, constrains, and where the corpus diverges from those constraints. Re-run `python scripts/render_schema.py` after `ride.odd` or the corpus changes.

## TEI modules used

`ride.odd` imports these P5 modules (a `(full)` marker means every element of the module is available; an explicit list means only those elements were pulled in):

- **tei** (full)
- **core** — only: `abbr`, `add`, `author`, `bibl`, `biblScope`, `cit`, `date`, `del` (and 32 more)
- **corpus** — only: `particDesc`
- **figures** — only: `cell`, `figure`, `row`, `table`
- **header** — only: `appInfo`, `availability`, `category`, `catDesc`, `catRef`, `change`, `classCode`, `classDecl` (and 22 more)
- **namesdates** — only: `affiliation`, `forename`, `listPerson`, `person`, `placeName`, `persName`, `orgName`, `roleName` (and 1 more)
- **tagdocs** — only: `att`, `code`, `eg`, `egXML`, `gi`, `ident`, `tag`, `val`
- **textstructure** — only: `TEI`, `back`, `body`, `div`, `front`, `text`
- **transcr** — only: `subst`, `add`, `del`, `mod`, `space`

## RIDE customisations

Out of 66 elementSpec entries in `ride.odd`, 56 actually change something (deleted attributes, changed usage, or constrained value lists). Only those are listed:

#### `<TEI>`
- Removed attributes: `@n`, `@rend`, `@resp`, `@type`, `@version`, `@xml:base`, `@xml:lang`, `@xml:space`
- `@xml:id` — mode `change`, usage `req`

#### `<add>`
- Removed attributes: `@xml:base`, `@xml:lang`, `@xml:space`, `@n`, `@rend`, `@resp`, `@type`

#### `<affiliation>`
- Removed attributes: `@from`, `@n`, `@notBefore`, `@notAfter`, `@rend`, `@resp`, `@role`, `@to`, `@type`, `@scheme`, `@xml:base`, `@xml:lang`, `@xml:space`, `@xml:id`, `@when`

#### `<att>`
- Removed attributes: `@scheme`

#### `<author>`
- Removed attributes: `@n`, `@rend`, `@resp`, `@role`, `@xml:base`, `@xml:id`, `@xml:lang`, `@xml:space`
- `@ref` — mode `change`, usage `opt`

#### `<availability>`
- Removed attributes: `@n`, `@rend`, `@resp`, `@status`, `@xml:base`, `@xml:id`, `@xml:lang`, `@xml:space`

#### `<bibl>`
- Removed attributes: `@n`, `@rend`, `@resp`, `@type`, `@xml:base`, `@xml:lang`, `@xml:space`

#### `<biblScope>`
- Removed attributes: `@rend`, `@resp`, `@type`, `@xml:base`, `@xml:id`, `@xml:lang`, `@xml:space`
- `@unit` — mode `change`, usage `req`
- `@n` — mode `change`, usage `req`
- `@unit` — value list (closed): `issue`

#### `<catDesc>`
- Removed attributes: `@xml:lang`, `@xml:space`, `@n`, `@xml:id`, `@resp`

#### `<category>`
- Removed attributes: `@xml:lang`, `@xml:space`, `@n`, `@rend`, `@cert`, `@resp`
- `@corresp` — mode `add`, usage `opt`

#### `<change>`
- Removed attributes: `@target`, `@who`, `@notBefore`, `@notAfter`, `@type`
- `@when` — mode `change`, usage `req`
- `@resp` — mode `change`, usage `req`
- `@xml:id` — mode `change`, usage `req`
- `@resp` — value list (closed): `author`, `editor`

#### `<change>`
- Removed attributes: `@who`, `@calendar`, `@period`, `@notBefore`, `@notAfter`, `@from`, `@to`, `@when-iso`, `@notBefore-iso`, `@notAfter-iso`, `@from-iso`, `@to-iso`, `@when-custom`, `@notBefore-custom`, `@notAfter-custom`, `@from-custom`, `@to-custom`, `@datingPoint`, `@datingMethod`, `@status`, `@xml:base`, `@xml:lang`, `@xml:space`, `@n`, `@xml:id`, `@rend`, `@subtype`
- `@corresp` — mode `add`, usage `opt`

#### `<cit>`
- Removed attributes: `@n`, `@rend`, `@resp`, `@type`, `@xml:base`, `@xml:id`, `@xml:lang`, `@xml:space`

#### `<classDecl>`
- Removed attributes: `@cert`, `@n`, `@rend`, `@resp`, `@xml:base`, `@xml:id`, `@xml:lang`, `@xml:space`

#### `<date>`
- Removed attributes: `@n`, `@from`, `@to`, `@notAfter`, `@notBefore`, `@rend`, `@resp`, `@xml:base`, `@xml:lang`, `@xml:space`, `@xml:id`
- `@type` — mode `change`, usage `unspecified`
- `@when` — mode `change`, usage `unspecified`
- `@type` — value list (closed): `publication`, `accessed`

#### `<del>`
- Removed attributes: `@xml:base`, `@xml:lang`, `@xml:space`, `@n`, `@rend`, `@resp`, `@type`

#### `<desc>`
- Removed attributes: `@n`, `@rend`, `@resp`, `@type`, `@xml:base`, `@xml:lang`, `@xml:space`, `@xml:id`

#### `<div>`
- Removed attributes: `@n`, `@resp`, `@rend`, `@subtype`, `@xml:base`, `@xml:lang`, `@xml:space`
- `@type` — mode `change`, usage `unspecified`
- `@xml:id` — mode `change`, usage `unspecified`
- `@type` — value list (closed): `abstract`, `acknowledgements`, `authorNotes`, `dedication`, `appendix`, `bibliography`, `editorialIntroduction`, `editorNotes`, `corrections`, `text`

#### `<editor>`
- `@ref` — mode `change`, usage `opt`
- `@role` — mode `change`, usage `unspecified`
- `@role` — value list (closed): `translator`, `guest`, `chief`, `managing`, `technical`, `assistant`

#### `<emph>`
- Removed attributes: `@n`, `@rend`, `@rendition`, `@resp`, `@subtype`, `@xml:base`, `@xml:id`, `@xml:lang`, `@xml:space`

#### `<encodingDesc>`
- Removed attributes: `@cert`, `@n`, `@rend`, `@resp`, `@xml:base`, `@xml:id`, `@xml:lang`, `@xml:space`

#### `<figure>`
- Removed attributes: `@xml:base`, `@xml:lang`, `@xml:space`, `@n`, `@place`, `@rend`, `@resp`, `@type`

#### `<forename>`
- Removed attributes: `@role`, `@type`

#### `<front>`
- Removed attributes: `@xml:base`, `@xml:lang`, `@xml:space`, `@n`, `@rend`, `@resp`, `@type`

#### `<gap>`
- Removed attributes: `@xml:base`, `@xml:lang`, `@xml:space`, `@n`, `@xml:id`, `@rend`, `@resp`

#### `<graphic>`
- Removed attributes: `@xml:base`, `@xml:lang`, `@xml:space`, `@n`, `@rend`, `@resp`, `@type`, `@height`, `@width`

#### `<head>`
- Removed attributes: `@xml:base`, `@xml:lang`, `@xml:space`, `@n`, `@xml:id`, `@rend`, `@resp`

#### `<head>`
- `@type` — mode `change`, usage `opt`
- `@type` — value list (closed): `legend`, `license`

#### `<ident>`
- Removed attributes: `@type`

#### `<idno>`
- `@type` — mode `replace`, usage `req`
- `@type` — value list (closed): `ORCID`, `GND`, `VIAF`, `DOI`, `URI`, `archive`

#### `<keywords>`
- Removed attributes: `@n`, `@rend`, `@resp`, `@scheme`, `@xml:base`, `@xml:space`, `@xml:id`
- `@xml:lang` — mode `change`, usage `req`
- `@xml:lang` — value list (closed): `en`

#### `<label>`
- Removed attributes: `@type`, `@place`

#### `<language>`
- Removed attributes: `@usage`

#### `<lb>`
- Removed attributes: `@type`

#### `<list>`
- Removed attributes: `@n`, `@resp`, `@type`, `@xml:base`, `@xml:lang`, `@xml:space`, `@xml:id`
- `@type` — mode `change`, usage `opt`
- `@rend` — mode `change`, usage `opt`
- `@type` — value list (closed): `gloss`, `simple`
- `@rend` — value list (closed): `bulleted`, `ordered`, `labeled`

#### `<listBibl>`
- Removed attributes: `@type`

#### `<listChange>`
- Removed attributes: `@n`, `@ordered`, `@rend`, `@resp`, `@xml:base`, `@xml:lang`, `@xml:space`, `@xml:id`
- `@type` — mode `change`, usage `req`
- `@type` — value list (closed): `post-publication`

#### `<name>`
- Removed attributes: `@role`, `@notAfter`, `@type`

#### `<note>`
- Removed attributes: `@rend`, `@resp`, `@xml:base`, `@xml:lang`, `@xml:space`, `@anchored`, `@targetEnd`, `@place`, `@target`, `@type`, `@n`

#### `<num>`
- `@type` — mode `change`, usage `opt`
- `@type` — value list (closed): `cardinal`, `ordinal`, `fraction`, `percentage`

#### `<orgName>`
- Removed attributes: `@notAfter`, `@role`, `@type`

#### `<p>`
- Removed attributes: `@xml:base`, `@xml:lang`, `@xml:space`, `@n`, `@rend`, `@cert`, `@resp`

#### `<ptr>`
- `@target` — mode `change`, usage `req`
- `@type` — mode `change`, usage `unspecified`
- `@type` — value list (closed): `crossref`

#### `<pubPlace>`
- Removed attributes: `@role`

#### `<q>`
- Removed attributes: `@type`

#### `<quote>`
- Removed attributes: `@n`, `@rend`, `@resp`, `@type`, `@notation`, `@xml:base`, `@xml:id`, `@xml:lang`, `@xml:space`

#### `<ref>`
- Removed attributes: `@n`, `@rend`, `@resp`, `@xml:base`, `@xml:id`, `@xml:lang`, `@xml:space`
- `@target` — mode `change`, usage `req`
- `@type` — mode `change`, usage `unspecified`
- `@type` — value list (closed): `crossref`, `bibl`

#### `<rendition>`
- Removed attributes: `@scope`
- `@scheme` — mode `change`, usage `unspecified`
- `@scheme` — value list (closed): `css`

#### `<roleName>`
- Removed attributes: `@role`, `@type`

#### `<surname>`
- Removed attributes: `@role`, `@type`

#### `<table>`
- Removed attributes: `@xml:base`, `@xml:lang`, `@xml:space`, `@n`, `@xml:id`, `@rend`, `@resp`, `@type`, `@subtype`

#### `<taxonomy>`
- Removed attributes: `@rend`, `@resp`, `@xml:id`, `@xml:lang`, `@xml:space`
- `@change` — mode `change`, usage `opt`
- `@xml:base` — mode `change`, usage `req`

#### `<teiHeader>`
- Removed attributes: `@type`

#### `<term>`
- Removed attributes: `@target`, `@type`

#### `<text>`
- Removed attributes: `@type`

#### `<title>`
- `@type` — mode `change`, usage `unspecified`
- `@type` — value list (closed): `main`


## Closed value lists (vs. the corpus)

Where `ride.odd` defines a closed list of values for an attribute, the two lines below show what the schema allows and what the corpus actually contains. **Bold** values appear in the corpus but are not in the schema list — they are either typos or signs of stale schema rules.

#### `<biblScope>/@unit`
- ODD allows: `issue`
- Corpus uses: `issue`

#### `<change>/@resp`
- ODD allows: `author`, `editor`
- Corpus uses: `author`

#### `<date>/@type`
- ODD allows: `publication`, `accessed`
- Corpus uses: `publication`, `accessed`

#### `<div>/@type`
- ODD allows: `abstract`, `acknowledgements`, `authorNotes`, `dedication`, `appendix`, `bibliography`, `editorialIntroduction`, `editorNotes`, `corrections`, `text`
- Corpus uses: `abstract`, `bibliography`, `appendix`

#### `<editor>/@role`
- ODD allows: `translator`, `guest`, `chief`, `managing`, `technical`, `assistant`
- Corpus uses: `managing`, `technical`, `assistant`, `chief`

#### `<head>/@type`
- ODD allows: `legend`, `license`
- Corpus uses: `legend`

#### `<idno>/@type`
- ODD allows: `ORCID`, `GND`, `VIAF`, `DOI`, `URI`, `archive`
- Corpus uses: `URI`, `DOI`, `archive`

#### `<keywords>/@xml:lang`
- ODD allows: `en`
- Corpus uses: `en`

#### `<list>/@type`
- ODD allows: `gloss`, `simple`
- Corpus uses: _(attribute not used)_

#### `<list>/@rend` — corpus diverges (see Schema vs. corpus mismatches in `data.md`)
- ODD allows: `bulleted`, `ordered`, `labeled`
- Corpus uses: `bulleted`, `ordered`, **`numbered`**, **`unordered`**, `labeled`

#### `<listChange>/@type`
- ODD allows: `post-publication`
- Corpus uses: `post-publication`

#### `<num>/@type` — corpus diverges (see Schema vs. corpus mismatches in `data.md`)
- ODD allows: `cardinal`, `ordinal`, `fraction`, `percentage`
- Corpus uses: **`boolean`**

#### `<ptr>/@type`
- ODD allows: `crossref`
- Corpus uses: _(attribute not used)_

#### `<ref>/@type` — corpus diverges (see Schema vs. corpus mismatches in `data.md`)
- ODD allows: `crossref`, `bibl`
- Corpus uses: `crossref`, **`crosssref`**

#### `<rendition>/@scheme`
- ODD allows: `css`
- Corpus uses: _(attribute not used)_

#### `<title>/@type`
- ODD allows: `main`
- Corpus uses: _(attribute not used)_

## Schematron rules

`ride.odd` carries 46 Schematron constraints, grouped here by the element they target. The `test:` is the XPath the assertion runs; the `message:` is the human-readable explanation as written in the ODD.

#### `<(unscoped)>`
- `jtei.sch-localLinkTarget` (report) on `None` — test: `exists($orphan.pointers)` — message: "There's no local target for : . Please make sure you're referring to an existing @xml:id value."
- `jtei.sch-renditionTarget` (report) on `None` — test: `exists($orphan.pointers)` — message: "point to a <rendition> target: ."
- `jtei.sch-quoteDelim` (assert) on `None` — test: `not(matches(., concat('^', $double.quotes, '|', $double.quotes, '$')))` — message: "Quotation mark delimiters are not allowed for : they are completed at processing time."
- `jtei.sch-crossref-id` (assert) on `None` — test: `@xml:id` — message: "You're strongly advised to add an @xml:id attribute to to ease formal cross-referencing with (ptr|ref)[@type='crossref']"
- `jtei.sch-formalCrossref` (assert) on `None` — test: `not(matches(., '(table|figure|example|section) \d+([.,]\d+)* ((above)|(below))', 'i'))` — message: "Please replace literal references to tables, figures, examples, and sections with a formal crosslink: (ptr|ref)[@type="crossref"]"
- `jtei.sch-crossrefTargetType` (report) on `None` — test: `exists($orphan.pointers)` — message: "Cross-links ( [@type="crossref"]) should be targeted at div, figure, table, or note elements. The target of doesn't satisfy this condition: ."
- `jtei.sch-crossrefType` (report) on `None` — test: `id(substring-after(@target, '#'))/(self::tei:div|self::tei:figure|self::tei:table)` — message: "Please type internal cross-references as 'crossref' ( [@type="crossref"])."

#### `<TEI>`
- `ride.sch-tei` (assert) on `TEI/@xml:id` — test: `matches(., 'ride.\d{1,2}.\d{1,2}$')` — message: "The xml:id is required and must have the format [ride].[issue-number].[review-number]"

#### `<add>`
- `ride.sch-add-context` (assert) on `add` — test: `ancestor::tei:mod` — message: "may only occur inside modifications."

#### `<att>`
- `jtei.sch-att` (assert) on `att` — test: `not(matches(., '^@'))` — message: "Attribute delimiters are not allowed for : they are completed at processing time."

#### `<author>`
- `jtei.sch-author` (assert) on `author` — test: `tei:name and tei:affiliation and tei:email` — message: "Author information in the <titleStmt> must include <name>, <affiliation> and <email>."

#### `<back>`
- `jtei.sch-back` (assert) on `back` — test: `tei:div[@type='bibliography']/tei:listBibl` — message: "must have a bibliography (div[@type="bibliography"]), which must be organized inside a listBibl element."

#### `<bibl>`
- `jtei.sch-bibl-endpunctuation` (assert) on `bibl` — test: `ends-with(normalize-space(), '.')` — message: "A bibliographic entry should end with a period."

#### `<del>`
- `ride.sch-del-context` (assert) on `del` — test: `ancestor::tei:mod` — message: "may only occur inside modifications."

#### `<div>`
- `jtei.sch-divtypes-front` (assert) on `div` — test: `parent::tei:front` — message: "A text division of type may only occur inside front."
- `jtei.sch-divtypes-front2` (assert) on `div` — test: `@type = $div.types.front` — message: "Only text divisions of type may appear in the <front>."
- `jtei.sch-divtypes-back` (assert) on `div` — test: `parent::tei:back` — message: "Bibliography ( [@type="bibliography"]) and appendices ( [@type="appendix"]) may only occur inside back."
- `jtei.sch-divtypes-body` (assert) on `div` — test: `parent::tei:body` — message: "An editorial introduction ( [@type="editorialIntroduction"]) may only occur inside body."
- `jtei.sch-div-head` (assert) on `div` — test: `tei:head` — message: "A must contain a head."
- `ride.div-nesting` (report) on `div` — test: `count(ancestor::tei:div) gt 2` — message: "maximum three levels of nested elements are allowed"
- `ride.sch-tei` (assert) on `div/@xml:id` — test: `matches(., 'div(\d{1,2})(.\d{1,2}){0,2}$')` — message: "The xml:id must have the format div[chapter].[subchapter].[subsubchapter]"

#### `<front>`
- `jtei.sch-front-abstract` (assert) on `front` — test: `tei:div[@type='abstract']` — message: "must have an abstract (div[@type='abstract'])."

#### `<gap>`
- `jtei.sch-gap` (report) on `gap` — test: `following-sibling::node()[1][self::text()] and starts-with(following-sibling::node()[1], '.')` — message: "A element should follow a period rather than precede it when an ellipsis follows the end of a sentence."
- `jtei.sch-gap-ws` (report) on `gap` — test: `preceding-sibling::node()[1][self::text()][matches(., '\.\s+$')]` — message: "A should follow a period directly, without preceding whitespace."

#### `<graphic>`
- `jtei.sch-graphic-context` (assert) on `graphic` — test: `parent::tei:figure` — message: "may only occur inside figure."

#### `<head>`
- `jtei.sch-head-number` (report) on `head` — test: `matches(., '^\s*((Fig|Code|Abb)\.\s?)\d', 'i')` — message: "Headings are numbered and labeled automatically, please remove the hard-coded label from the text."
- `jtei.sch-figure-head` (assert) on `head` — test: `@type = ('legend', 'license')` — message: "Figure titles must have a type 'legend' or 'license'."
- `jtei.sch-legend-punctuation` (assert) on `head` — test: `. = '' or matches(normalize-space(), '[.?!]$')` — message: "A head with the type attribute legend should end with closing punctuation."

#### `<idno>`
- `jtei.sch-doi-order` (report) on `idno` — test: `following-sibling::tei:ref` — message: "If a bibliographic entry has a formal DOI code, it should be placed at the very end of the bibliographic description."
- `ride.sch-idno-author` (assert) on `idno` — test: `@type='ORCID' or @type='GND' or @type='VIAF'` — message: "Only the type ORCID, GND, or VIAF is allowed."
- `ride.sch-idno-author` (assert) on `idno` — test: `@type='ORCID' or @type='GND' or @type='VIAF'` — message: "Only the type ORCID, GND, or VIAF is allowed."
- `ride.sch-idno-publicationStmt` (assert) on `idno` — test: `@type='URI' or @type='DOI' or @type='archive'` — message: "Only the type URI, DOI, or archive is allowed."

#### `<note>`
- `jtei.sch-note-punctuation` (assert) on `note` — test: `matches(normalize-space(), '[.?!]$')` — message: "A footnote should end with closing punctuation."
- `jtei.sch-note-blocks` (report) on `note` — test: `.//(tei:cit|tei:table|tei:list[not(tokenize(@rend, '\s+')[. eq 'inline'])]|tei:figure|eg:egXML|tei:eg)` — message: "No block-level elements are allowed inside note."

#### `<ptr>`
- `jtei.sch-ptr-multipleTargets` (report) on `ptr` — test: `count(tokenize(normalize-space(@target), '\s+')) > 1` — message: "Multiple targets are only allowed for [@type='crossref']."

#### `<ref>`
- `jtei.sch-biblref-parentheses` (assert) on `ref` — test: `not(matches(., '^\(.*\)$'))` — message: "Parentheses are not part of bibliographic references. Please move them out of ."
- `jtei.sch-biblref-target` (assert) on `ref` — test: `id(substring-after(@target, '#'))/(self::tei:bibl|self::tei:person[ancestor::tei:particDesc/parent::tei:profileDesc])` — message: "A bibliographic reference must point to an entry in the bibliography."
- `jtei.sch-biblref-type` (assert) on `ref` — test: `@type eq 'bibl'` — message: "A bibliographic reference must be typed as @type="bibl"."

#### `<rendition>`
- `jtei.sch-rendition` (assert) on `rendition` — test: `key('idrefs', @xml:id) instance of attribute(rendition)` — message: "Please remove all definitions that aren't actually being used in the article."

#### `<respStmt>`
- `ride.sch-respSmt` (assert) on `respStmt` — test: `ancestor::tei:notesStmt` — message: "can only be used in the context of notesStmt."

#### `<seriesStmt>`
- `ride.sch-editor` (assert) on `seriesStmt` — test: `not(@role)` — message: "the first should note hava a role attribute."

#### `<table>`
- `jtei.sch-table` (assert) on `table` — test: `not(ancestor::tei:list)` — message: "No tables are are allowed inside lists."

#### `<tag>`
- `jtei.sch-tag` (assert) on `tag` — test: `not(matches(., '^[<!?-]|[>/?\-]$'))` — message: "Tag delimiters such as angle brackets and tag-closing slashes are not allowed for : they are completed at processing time."

#### `<text>`
- `jtei.sch-article-keywords` (assert) on `text` — test: `parent::tei:TEI/tei:teiHeader/tei:profileDesc/tei:textClass/tei:keywords` — message: "An article must have a keyword list in the header."
- `jtei.sch-article-abstract` (assert) on `text` — test: `tei:front/tei:div[@type='abstract']` — message: "An article must have a front section with an abstract."

#### `<val>`
- `jtei.sch-att` (assert) on `val` — test: `not(matches(., concat('^', $quotes, '|', $quotes, '$')))` — message: "Attribute value delimiters are not allowed for : they are completed at processing time."
