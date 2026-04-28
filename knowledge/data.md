---
generated: 2026-04-28
source: scripts/render_data.py
inputs:
  - inventory/elements.json
  - inventory/attributes.json
  - inventory/corpus-stats.json
  - inventory/sections.json
  - inventory/structure.json
  - inventory/cross-reference.json
---

# RIDE Corpus Data

> Generated from `inventory/*.json`. Re-run `python scripts/render_data.py` whenever the corpus or extractor scripts change.

## Overview

- **Reviews:** 107
- **Total elements:** 134,951
- **Distinct elements:** 77
- **Distinct attributes:** 24
- **Publication dates:** 2014-06 – 2026-03
- **Issues:** 22 (no. 1 – 22)
- **Languages:** English (70), German (34), French (2), Italian (1)
- **Distinct editors (ORCID):** 28
- **Licence:** http://creativecommons.org/licenses/by/4.0/ (107/107)

## Section types (`<div type>`)

| Type | Count | Coverage |
| --- | --- | --- |
| abstract | 107 | 100% |
| bibliography | 100 | 93% |
| appendix | 1 | 1% |

- **Sections without `<head>`:** 215
- **Reviews without a bibliography section (7):** `berliner-intellektuelle-tei.xml`, `busoni-nachlass-tei.xml`, `tustep-tei.xml`, `twain-tei.xml`, `victorians-tei.xml`, `wba_upgrade-tei.xml`, `wega-tei.xml`

## Most-used elements (top 20)

| Element | Occurrences | Files |
| --- | --- | --- |
| `catDesc` | 47,755 | 107 |
| `category` | 26,085 | 107 |
| `num` | 20,053 | 107 |
| `ref` | 9,916 | 107 |
| `emph` | 5,055 | 104 |
| `p` | 3,809 | 107 |
| `note` | 1,926 | 98 |
| `head` | 1,917 | 107 |
| `bibl` | 1,670 | 107 |
| `div` | 1,249 | 107 |
| `respStmt` | 1,049 | 95 |
| `resp` | 1,049 | 95 |
| `persName` | 1,049 | 95 |
| `figure` | 874 | 106 |
| `term` | 846 | 107 |
| `gloss` | 844 | 87 |
| `graphic` | 833 | 104 |
| `code` | 727 | 50 |
| `editor` | 712 | 107 |
| `idno` | 645 | 107 |

## Most-used attributes (top 15)

| Attribute | Occurrences | Distinct values |
| --- | --- | --- |
| `@xml:id` | 32,665 | 2788 |
| `@type` | 23,924 | 15 |
| `@value` | 20,053 | 3 |
| `@target` | 10,023 | 3219 |
| `@corresp` | 1,112 | 5 |
| `@url` | 833 | 832 |
| `@ref` | 810 | 161 |
| `@role` | 681 | 6 |
| `@rows` | 251 | 1 |
| `@cols` | 251 | 1 |
| `@rend` | 192 | 18 |
| `@unit` | 164 | 2 |
| `@n` | 124 | 31 |
| `@when` | 114 | 29 |
| `@xml:base` | 110 | 4 |

## Findings

### Attributes outside the P5 spec

- `<taxonomy>`: `@m`

### Closed value-list violations (vs. `ride.odd`)

- `<num>/@type`: corpus uses `boolean`×20053; ODD allows [`cardinal`, `ordinal`, `fraction`, `percentage`]
- `<ref>/@type`: corpus uses `crosssref`×1; ODD allows [`crossref`, `bibl`]
- `<list>/@rend`: corpus uses `numbered`×8, `unordered`×2; ODD allows [`bulleted`, `ordered`, `labeled`]

### Sections without a `<head>`

215 of all `<div>` sections have no immediate `<head>`. Templates must provide a fallback (e.g. derived from `xml:id` or position).

## Element index

Compact reference for every element used in the corpus.

### `<TEI>`
- Occurrences: **107** in 107 review(s)
- Attributes: `@xml:id` (107, 100%)
- Top children: `teiHeader`×107, `text`×107
- Frequent child sequences: `[teiHeader, text]` (107)

### `<add>`
- Occurrences: **5** in 1 review(s)
- Top children: `ref`×2
- Frequent child sequences: `[ref]` (2)

### `<affiliation>`
- Occurrences: **120** in 107 review(s)
- Top children: `orgName`×119, `placeName`×119
- Frequent child sequences: `[orgName, placeName]` (117); `[orgName, placeName, placeName]` (1)

### `<author>`
- Occurrences: **119** in 107 review(s)
- Attributes: `@ref` (105, 88%)
- Top children: `name`×119, `affiliation`×119, `email`×119
- Frequent child sequences: `[name, affiliation, email]` (119)

### `<availability>`
- Occurrences: **107** in 107 review(s)
- Top children: `licence`×107
- Frequent child sequences: `[licence]` (107)

### `<back>`
- Occurrences: **100** in 100 review(s)
- Top children: `div`×100
- Frequent child sequences: `[div]` (100)

### `<bibl>`
- Occurrences: **1,670** in 107 review(s)
- Attributes: `@xml:id` (588, 35%)
- Top children: `emph`×1078, `respStmt`×1049, `ref`×1016, `date`×220, `title`×110
- Frequent child sequences: `[emph, ref]` (518); `[emph]` (417)

### `<biblScope>`
- Occurrences: **107** in 107 review(s)
- Attributes: `@unit` (107, 100%), `@n` (107, 100%)

### `<body>`
- Occurrences: **107** in 107 review(s)
- Top children: `div`×622, `p`×40, `cit`×3
- Frequent child sequences: `[div, div, div, div, div, div]` (27); `[div, div, div, div, div]` (16)

### `<catDesc>`
- Occurrences: **47,755** in 107 review(s)
- Top children: `num`×20053, `ref`×5209, `gloss`×844
- Frequent child sequences: `[num]` (20053); `[ref]` (5209)

### `<category>`
- Occurrences: **26,085** in 107 review(s)
- Attributes: `@xml:id` (24526, 94%), `@corresp` (1112, 4%)
- Top children: `catDesc`×47755, `category`×25458, `desc`×416
- Frequent child sequences: `[catDesc, catDesc]` (14881); `[catDesc]` (3420)

### `<cell>`
- Occurrences: **349** in 8 review(s)
- Attributes: `@role` (241, 69%), `@rows` (213, 61%), `@cols` (213, 61%)
- Top children: `ref`×22, `figure`×22, `hi`×10, `note`×8, `emph`×3
- Frequent child sequences: `[ref]` (22); `[figure]` (22)

### `<change>`
- Occurrences: **7** in 2 review(s)
- Attributes: `@when` (7, 100%), `@resp` (7, 100%), `@xml:id` (7, 100%)

### `<cit>`
- Occurrences: **84** in 34 review(s)
- Top children: `quote`×84, `bibl`×64
- Frequent child sequences: `[quote, bibl]` (64); `[quote]` (20)

### `<classDecl>`
- Occurrences: **107** in 107 review(s)
- Top children: `taxonomy`×110
- Frequent child sequences: `[taxonomy]` (105); `[taxonomy, taxonomy]` (1)

### `<code>`
- Occurrences: **727** in 50 review(s)

### `<date>`
- Occurrences: **327** in 107 review(s)
- Attributes: `@type` (220, 67%), `@when` (107, 33%)

### `<del>`
- Occurrences: **9** in 3 review(s)
- Top children: `ref`×2, `emph`×1
- Frequent child sequences: `[ref]` (2); `[emph]` (1)

### `<desc>`
- Occurrences: **417** in 20 review(s)

### `<div>`
- Occurrences: **1,249** in 107 review(s)
- Attributes: `@xml:id` (1040, 83%), `@type` (208, 17%)
- Top children: `p`×3660, `head`×1034, `div`×420, `listBibl`×102, `table`×5
- Frequent child sequences: `[head, p, p]` (190); `[head, p, p, p]` (167)

### `<editor>`
- Occurrences: **712** in 107 review(s)
- Attributes: `@ref` (597, 84%), `@role` (374, 52%)

### `<eg>`
- Occurrences: **41** in 14 review(s)
- Attributes: `@xml:space` (14, 34%)
- Top children: `lb`×362, `space`×57
- Frequent child sequences: `[lb, lb, lb, lb, lb]` (5); `[lb, lb, lb, lb, lb, lb, lb, lb, lb]` (3)

### `<email>`
- Occurrences: **119** in 107 review(s)

### `<emph>`
- Occurrences: **5,055** in 104 review(s)
- Top children: `ref`×16, `emph`×1
- Frequent child sequences: `[ref]` (16); `[emph]` (1)

### `<encodingDesc>`
- Occurrences: **107** in 107 review(s)
- Top children: `classDecl`×107
- Frequent child sequences: `[classDecl]` (107)

### `<figure>`
- Occurrences: **874** in 106 review(s)
- Attributes: `@xml:id` (874, 100%)
- Top children: `head`×874, `graphic`×833, `eg`×41
- Frequent child sequences: `[graphic, head]` (833); `[eg, head]` (41)

### `<fileDesc>`
- Occurrences: **107** in 107 review(s)
- Top children: `sourceDesc`×108, `titleStmt`×107, `publicationStmt`×107, `seriesStmt`×107, `notesStmt`×107
- Frequent child sequences: `[titleStmt, publicationStmt, seriesStmt, notesStmt, sourceDesc]` (106); `[titleStmt, publicationStmt, seriesStmt, notesStmt, sourceDesc, sourceDesc]` (1)

### `<forename>`
- Occurrences: **119** in 107 review(s)

### `<front>`
- Occurrences: **107** in 107 review(s)
- Top children: `div`×107
- Frequent child sequences: `[div]` (107)

### `<gloss>`
- Occurrences: **844** in 87 review(s)

### `<graphic>`
- Occurrences: **833** in 104 review(s)
- Attributes: `@url` (833, 100%)

### `<head>`
- Occurrences: **1,917** in 107 review(s)
- Attributes: `@type` (874, 46%)
- Top children: `emph`×131, `ref`×84, `note`×16, `code`×13, `hi`×1
- Frequent child sequences: `[emph]` (77); `[ref]` (64)

### `<hi>`
- Occurrences: **71** in 25 review(s)
- Attributes: `@rend` (70, 99%), `@xml:space` (1, 1%), `@style` (1, 1%)

### `<idno>`
- Occurrences: **645** in 107 review(s)
- Attributes: `@type` (645, 100%)

### `<item>`
- Occurrences: **496** in 45 review(s)
- Attributes: `@n` (6, 1%)
- Top children: `emph`×110, `code`×92, `ref`×45, `note`×36, `label`×6
- Frequent child sequences: `[emph]` (38); `[code]` (32)

### `<keywords>`
- Occurrences: **107** in 107 review(s)
- Attributes: `@xml:lang` (107, 100%)
- Top children: `term`×846
- Frequent child sequences: `[term, term, term, term, term]` (24); `[term, term, term, term, term, term]` (18)

### `<label>`
- Occurrences: **6** in 1 review(s)

### `<langUsage>`
- Occurrences: **107** in 107 review(s)
- Top children: `language`×107
- Frequent child sequences: `[language]` (107)

### `<language>`
- Occurrences: **107** in 107 review(s)
- Attributes: `@ident` (107, 100%)

### `<lb>`
- Occurrences: **396** in 18 review(s)

### `<licence>`
- Occurrences: **107** in 107 review(s)
- Attributes: `@target` (107, 100%)

### `<list>`
- Occurrences: **121** in 45 review(s)
- Attributes: `@rend` (121, 100%)
- Top children: `item`×496, `figure`×1
- Frequent child sequences: `[item, item, item]` (37); `[item, item, item, item]` (22)

### `<listBibl>`
- Occurrences: **102** in 99 review(s)
- Top children: `bibl`×1389, `head`×4
- Frequent child sequences: `[bibl, bibl, bibl, bibl, bibl, bibl, bibl, bibl, bibl, bibl, bibl]` (9); `[bibl, bibl, bibl, bibl, bibl, bibl, bibl, bibl, bibl, bibl]` (8)

### `<listChange>`
- Occurrences: **2** in 2 review(s)
- Attributes: `@type` (2, 100%)
- Top children: `change`×7
- Frequent child sequences: `[change, change, change, change, change, change]` (1); `[change]` (1)

### `<mod>`
- Occurrences: **7** in 2 review(s)
- Attributes: `@change` (7, 100%), `@xml:id` (7, 100%), `@n` (7, 100%)
- Top children: `note`×7, `subst`×5, `del`×1
- Frequent child sequences: `[subst, note]` (5); `[del, note]` (1)

### `<name>`
- Occurrences: **274** in 107 review(s)
- Top children: `forename`×119, `surname`×119
- Frequent child sequences: `[forename, surname]` (119)

### `<note>`
- Occurrences: **1,926** in 98 review(s)
- Attributes: `@xml:id` (1919, 100%)
- Top children: `ref`×1675, `emph`×453, `code`×51, `hi`×5, `p`×1
- Frequent child sequences: `[ref]` (1017); `[ref, ref]` (122)

### `<notesStmt>`
- Occurrences: **107** in 107 review(s)
- Top children: `relatedItem`×217
- Frequent child sequences: `[relatedItem, relatedItem]` (105); `[relatedItem, relatedItem, relatedItem]` (1)

### `<num>`
- Occurrences: **20,053** in 107 review(s)
- Attributes: `@type` (20053, 100%), `@value` (20053, 100%)

### `<orgName>`
- Occurrences: **119** in 107 review(s)

### `<p>`
- Occurrences: **3,809** in 107 review(s)
- Attributes: `@xml:id` (3590, 94%), `@rend` (1, 0%), `@style` (1, 0%)
- Top children: `emph`×3250, `note`×1843, `ref`×1838, `figure`×850, `code`×525
- Frequent child sequences: `[emph]` (266); `[note]` (206)

### `<persName>`
- Occurrences: **1,049** in 95 review(s)
- Top children: `name`×155
- Frequent child sequences: `[name]` (155)

### `<placeName>`
- Occurrences: **119** in 106 review(s)
- Attributes: `@ref` (108, 91%)

### `<profileDesc>`
- Occurrences: **107** in 107 review(s)
- Top children: `langUsage`×107, `textClass`×107
- Frequent child sequences: `[langUsage, textClass]` (107)

### `<publicationStmt>`
- Occurrences: **107** in 107 review(s)
- Top children: `idno`×321, `publisher`×107, `date`×107, `availability`×107
- Frequent child sequences: `[publisher, date, idno, idno, idno, availability]` (107)

### `<publisher>`
- Occurrences: **107** in 107 review(s)

### `<quote>`
- Occurrences: **84** in 34 review(s)
- Top children: `lb`×25, `emph`×16, `note`×11, `code`×10, `ref`×7
- Frequent child sequences: `[note]` (8); `[emph]` (7)

### `<ref>`
- Occurrences: **9,916** in 107 review(s)
- Attributes: `@target` (9916, 100%), `@type` (1705, 17%)
- Top children: `emph`×11
- Frequent child sequences: `[emph]` (11)

### `<relatedItem>`
- Occurrences: **217** in 107 review(s)
- Attributes: `@type` (217, 100%), `@xml:id` (5, 2%)
- Top children: `bibl`×217
- Frequent child sequences: `[bibl]` (217)

### `<resp>`
- Occurrences: **1,049** in 95 review(s)

### `<respStmt>`
- Occurrences: **1,049** in 95 review(s)
- Top children: `resp`×1049, `persName`×1049
- Frequent child sequences: `[resp, persName]` (1049)

### `<revisionDesc>`
- Occurrences: **2** in 2 review(s)
- Top children: `listChange`×2
- Frequent child sequences: `[listChange]` (2)

### `<row>`
- Occurrences: **73** in 8 review(s)
- Attributes: `@role` (66, 90%), `@rows` (38, 52%), `@cols` (38, 52%)
- Top children: `cell`×349
- Frequent child sequences: `[cell, cell, cell, cell]` (23); `[cell, cell]` (17)

### `<seg>`
- Occurrences: **1** in 1 review(s)
- Attributes: `@xml:space` (1, 100%)

### `<seriesStmt>`
- Occurrences: **107** in 107 review(s)
- Top children: `editor`×602, `idno`×214, `title`×107, `biblScope`×107
- Frequent child sequences: `[title, editor, editor, editor, editor, editor, editor, biblScope, idno, idno]` (36); `[title, editor, editor, editor, editor, editor, editor, editor, biblScope, idno, idno]` (23)

### `<sourceDesc>`
- Occurrences: **108** in 107 review(s)
- Top children: `p`×108
- Frequent child sequences: `[p]` (108)

### `<space>`
- Occurrences: **57** in 2 review(s)
- Attributes: `@unit` (57, 100%), `@quantity` (57, 100%)

### `<subst>`
- Occurrences: **5** in 1 review(s)
- Top children: `del`×5, `add`×5
- Frequent child sequences: `[del, add]` (5)

### `<surname>`
- Occurrences: **119** in 107 review(s)

### `<table>`
- Occurrences: **12** in 8 review(s)
- Attributes: `@xml:id` (2, 17%)
- Top children: `row`×73, `head`×5
- Frequent child sequences: `[row, row]` (2); `[row, row, row]` (2)

### `<taxonomy>`
- Occurrences: **110** in 107 review(s)
- Attributes: `@xml:base` (110, 100%), `@n` (4, 4%), `@m` (1, 1%)
- Top children: `category`×627, `desc`×1
- Frequent child sequences: `[category, category, category, category, category]` (73); `[category, category, category, category, category, category, category, category]` (19)

### `<teiHeader>`
- Occurrences: **107** in 107 review(s)
- Top children: `fileDesc`×107, `encodingDesc`×107, `profileDesc`×107, `revisionDesc`×2
- Frequent child sequences: `[fileDesc, encodingDesc, profileDesc]` (104); `[fileDesc, encodingDesc, profileDesc, revisionDesc]` (2)

### `<term>`
- Occurrences: **846** in 107 review(s)

### `<text>`
- Occurrences: **107** in 107 review(s)
- Top children: `front`×107, `body`×107, `back`×100
- Frequent child sequences: `[front, body, back]` (100); `[front, body]` (7)

### `<textClass>`
- Occurrences: **107** in 107 review(s)
- Top children: `keywords`×107
- Frequent child sequences: `[keywords]` (107)

### `<title>`
- Occurrences: **324** in 107 review(s)
- Attributes: `@level` (107, 33%)
- Top children: `emph`×1
- Frequent child sequences: `[emph]` (1)

### `<titleStmt>`
- Occurrences: **107** in 107 review(s)
- Top children: `author`×119, `title`×107
- Frequent child sequences: `[title, author]` (97); `[title, author, author]` (8)
