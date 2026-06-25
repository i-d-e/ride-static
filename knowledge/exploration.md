---
title: Data Exploration & Story
project:
  name: ride-static
  repository: https://github.com/i-d-e/ride-static
method:
  name: Promptotyping
  url: https://dhcraft.org/excellence/blog/Promptotyping
status: proposal
created: 2026-06-25
updated: 2026-06-25
version: 0.1
language: de
related:
  - "[[specification]]"
  - "[[interface]]"
  - "[[architecture]]"
  - "[[data]]"
  - "[[pipeline]]"
---

# Explorations-Seite und Narrativ-View

Konzept und Implementierungsplan für zwei neue datengetriebene Seiten von [ride.i-d-e.de](https://ride.i-d-e.de): einen interaktiven Explorations-View (`/data/explore/`) und einen narrativen Scrollytelling-View (`/data/story/`). Das Dokument hält fest, was der Korpus an explorierbarem Potenzial hergibt, welche Forschungsfragen er trägt, welche zwei Views daraus folgen und wie sie gebaut werden. Status ist Vorschlag, mehrere Grundsatzentscheidungen sind offen (Abschnitt *Offene Entscheidungen*).

Die gemessenen Korpus-Zahlen in diesem Dokument geben den Analysestand vom 2026-06-25 wieder. Sie begründen Designentscheidungen und Leitplanken, sind aber nicht die Wahrheitsquelle. Die laufende Strukturreferenz ist [[data]]; die hier neu erhobenen Kennzahlen werden mit der Umsetzung in den generierten `explorer-dump` (AP2/AP3) überführt und von dort regenerierbar.

## 1. Kontext und Abgrenzung

Die Site trägt bereits eine vollständige `Data`-Sektion, durchgängig build-time-statisch: `/data/charts/` (eine SVG-Balkengrafik je Kriterien-Set, aufgeschlüsselt nach Top-Level-Sektion, Anteil Ja-Antworten, gerendert von `src/render/charts.py`), `/data/questionnaires/`, `/data/` mit Korpus-Download und `/api/corpus.json` (`src/render/corpus_dump.py`), `/resources/`, `/tags/`, `/reviewers/` (`src/render/aggregations.py`). Keine dieser Seiten bietet Cross-Filtering, gekoppeltes Brushing, die Einzel-Review als manipulierbares Objekt, eine Zeitachse, eine Karte oder ein Verweisnetz.

Genau diese Lücke füllen die zwei neuen Views. Sie ergänzen die bestehende Sektion, ersetzen nichts. Die statischen Charts bleiben die schnelle, zitierbare, JS-freie Kanon-Ansicht; die neuen Seiten sind der interaktive Tiefenzugang und die erzählte Lesart. Bezug zur bestehenden Anforderung [[specification#R9 Data-Charts]].

## 2. Was die Daten hergeben

Der Korpus sind 111 Reviews in 22 Issues über zwölf Jahre (Review-Daten 2014-06 bis 2026-05). Der universelle Join-Schlüssel ist der Review-Dateiname; er verbindet `taxonomy.json`, `refs.json`, `sections.json`, `corpus-stats.json` und den Issue-Ordnerpfad lückenlos (111/111). Fünf Dimensionen tragen, jede mit eigener Reichweite und eigenen Grenzen. Die Strukturdetails stehen in [[data]]; hier die explorationsrelevante Verdichtung.

**Fragebogen / Kriterien-Matrix.** Die dichteste Dimension: rund 25.000 Antwortzellen (Ja/Nein je Kriterium). Vier criteria-URLs kollabieren zu drei logischen Sets (digital-editions 76 Reviews, text-collections 20, tools 15). Härteste Grenze: Die drei Sets sind **inkommensurabel** (224/245/282 Kategorien, verschiedene Kataloge). Ja-Anteile sind nur set-intern vergleichbar. Zweite Grenze: Die semantisch tragende Ebene sind die label-führenden **Frageknoten** (DE 49 / tools 44 / text-collections 25), nicht die rohe `<num>`-Knotenzahl. Die `value="3"`-Anomalie (sieben Zellen, nur text-collections) ist ein dritter Zustand und darf nie zu 0/1 verrechnet werden.

**Bibliografie / Zeit / Sprache / Issue / Herausgeber.** Die saubere Filterebene: Sprache, Issue-Datum, DOI und Keywords sind vollständig belegt. Grenzen: Sprache ist faktisch binär en/de (fr und it sind drei Einzelfälle), und **jedes Issue ist set-homogen** — das Kriterien-Set ist eine Issue-Eigenschaft, keine pro Review variierende Größe. Die belastbare Editor-Achse kommt aus `seriesStmt`, nach ORCID-Dedup rund 23 distinkte Personen; die Editorenliste in `metadata.yaml` ist für diese Auswertung unbrauchbar (fehlerhafte Namenssplits).

**Personen, Geografie, Institutionen.** Tragfähig sind zwei Achsen: die Reviewer-Geografie über rund 51 GeoNames-IDs (DACH-zentriert, DE/AT dominieren) und die Editor-Issue-Matrix (Kern-Peripherie-Struktur, ein Editor in 21 von 22 Issues). Die GeoNames-IDs sind Identifier, keine Koordinaten; ein Lookup ist ein echter Vorarbeitsschritt. Die rund 1.000 Personen der besprochenen Projekte sind ganz überwiegend Singletons ohne Identifier und tragen kein Netz, nur eine Rollen- und Projektgrößen-Verteilung.

**Besprochene Ressourcen und Referenznetz.** 114 besprochene Ressourcen mit eigenem Titel, Datum, Personnel und URI. Das dominante Referenzsignal: web.archive.org trägt knapp 59 Prozent aller externen Verweise, und www.i-d-e.de wird von allen 111 Reviews referenziert (echte Selbstreferenz). Das Verweisnetz ist bipartit (Review zu Host) und wird erst auf den geteilten Hosts (Grad 2+) lesbar. Ressourcen-Alter zum Reviewzeitpunkt ist als Verteilung berechenbar (Median rund 4 Jahre, langer rechter Schwanz).

**Struktur und Umfang.** Die sauberste Dimension, weil rein strukturell und frei von der Set-Falle: Zeichenumfang, Absätze, Figuren, Fußnoten, Bibliografie, Code, Tabellen je Review. Wichtig: stark rechtsschief (Code und Tabellen meist 0). Aggregate gehören als Präsenz plus Verteilung geführt, nie als Mittelwert. Keine dieser Metriken liegt vorberechnet vor; alle brauchen einen neuen Mess-Lauf.

Drei verifizierte Querbefunde korrigieren naheliegende Fehlschlüsse: Code ist **kein** Tool-Marker (von 52 code-tragenden Reviews sind 33 digital-editions). Tools-Reviews sind code-reicher, aber **nicht länger**. Und Umfang oder Apparat korrelieren **kaum** mit der Ja-Quote (r etwa 0,33). Jede Visualisierung, die Apparat-Reichtum als Prädiktor des Urteils inszeniert, reanimiert eine widerlegte Hypothese.

### Was die Daten nicht hergeben

Streng ehrlich geführt, weil es bestimmt, was die Seiten behaupten dürfen:

- **Keine** thematische Schwerpunktverschiebung digital-editions zu tools/text-collections (jedes Issue set-homogen, DE dominiert durchgehend).
- **Kein** Sprach-Trend (binär en/de).
- **Kein** set-übergreifender Strenge- oder Qualitätsvergleich (inkommensurable Kataloge) — die häufigste Versuchung und die härteste Sperre.
- **Kein** belastbarer Archivierungs-Trend als aufsteigende Linie (nur moderat, volatil, das 26-auf-78-Prozent-Framing ist Endpunkt-Cherry-Picking).
- **Keine** dichten Personennetze außer Geografie und Editoren (Co-Autorschaft rund 14 Kanten, Projekt-Personnel singleton-lastig).
- **Keine** Korrelation Struktur gegen Urteil (widerlegt).

## 3. Forschungsfragen

Der Katalog trennt zwei Datenebenen. **Teil A** ist aus den strukturierten Datasheet-Feldern direkt beantwortbar. **Teil B** liegt im TEI-Volltext (`<body>`) und braucht erst Textanalyse. Die vollständige Fassung mit Tragfähigkeitsmarkierung je Frage liegt im Arbeitsmaterial der Konzeptphase; hier die tragenden Leitfragen und die Volltext-Grenze.

### Leitfragen (Teil A, dichteste Datengrundlage)

1. **Strenge des Urteils set-intern.** Die set-interne Ja-Quote als Verteilung (DE in einem auffallend schmalen Band). Das zentrale, oft als Qualität missverstandene Signal. Vis P1.
2. **Konsens und Dissens je Kriterium.** Welche Kriterien fast alle erfüllen oder ablehnen, welche umstritten sind. Vis P2.
3. **Stabilität des herausgebenden Kollektivs.** Kern-Peripherie-Struktur des Boards über 22 Issues. Vis P5.
4. **Geografie der Reviewerschaft.** DACH-Zentrierung, die der Site bislang fehlende geografische Eintrittsschicht. Vis P6.
5. **Archivierung als Sicherungspraxis.** web.archive.org als durchgängige redaktionelle Praxis. Vis P7.
6. **DOI-Asymmetrie Rezension gegen Gegenstand.** Zwei von 114 Ressourcen gegen 22 von 22 Issues — Persistenz liegt auf der Publikationsseite. Ressourcen-Inventar.
7. **Alter der besprochenen Ressource.** Median rund 4 Jahre, langer Schwanz. Verbindet Zeitachse und Nachhaltigkeit. Vis P3.

### Volltext-Grenze (Teil B, braucht Erschließung)

Die Fragen, die der Nutzer mit „aus dem TEI-XML könnte man noch was" anspricht, liegen sämtlich im Fließtext und sind mit dem heutigen Build nicht darstellbar: genanntes Standard- und Tool-Vokabular (TEI, RDF, IIIF, GND), Bewertungston der Reviews, normalisierte Kapiteltypen, zitierte Vergleichsprojekte, Diskursfunktion der Referenzen, Argumentationsstruktur. Aufwand jeweils mittel bis hoch (NER, zweisprachiges Sentiment, Heading-Normalisierung, Gold-Annotation). Die kuratierten `<term>`-Keywords sind redaktionelle Schlagworte, **keine** systematische Tool-Erfassung; sie tragen eine inhaltliche Sachachse (Epoche, Gattung, Disziplin) ohne Textanalyse, mehr nicht.

## 4. Die zwei Views

### View 1 — Explorations-Seite (`/data/explore/`)

Ein Rückgrat, sieben angedockte Ansichten plus Ressourcen-Inventar, alle über den Review-Dateinamen-Join gekoppelt.

- **P1 Facetten-Browser (Rückgrat, Landeansicht).** Beeswarm aller 111 Reviews, Facetten-Sidebar (Jahr, Sprache, Set, Umfangsquartil, Code-Präsenz), gekoppelte Tabelle, Crossfilter und Brushing. Jede andere Ansicht ist eine andere Projektion derselben 111 Objekte.
- **P2 Antwort-Matrix-Heatmap je Set.** Die volle Antwort-Matrix, die die statischen Charts zu einem Prozent je Sektion kollabieren. Harter Set-Tab (nie zwei Sets nebeneinander), Spalten-Konsens, Reihen-Sortierung, Sektions-Drilldown.
- **P3 Issue-Timeline plus Ressourcen-Alters-Scatter.** 22 Issue-Bänder, Set als 22-Zellen-Farbstreifen (kein Stack, Issues set-homogen), Datums-Umschalter Issue gegen Review, gekoppeltes Alters-Streudiagramm.
- **P4 Review-Anatomie als Small-Multiples.** 111 Strukturfingerabdrücke (front/body/back), Segmentfarbe ehrlich auf die typisierten Sektionen beschränkt.
- **P5 Editor-Kontinuitäts-Matrix.** 23 Editoren mal 22 Issues, Rollenfarbe, Lebenslinien.
- **P6 Reviewer-Herkunftskarte.** Punktkarte über die GeoNames-Koordinaten, gekoppelte Länder-Rangliste.
- **P7 Selbstreferenz-Verweisnetz.** Bipartites Netz auf den geteilten Hosts, web.archive.org als Hub, Wrapper-Auflösungs-Toggle.
- **Ressourcen-Inventar (8. Ansicht).** Sortier- und filterbare Tabelle der 114 Ressourcen (Titel, URI-Host, Jahr, Personnel-Zahl, DOI-Flag).

### View 2 — Narrativ (`/data/story/`)

Die Issue-Reihe als erzählte kleine Geschichte. Ehrliche Rahmung: Der Korpus erzählt **primär die Geschichte des Rezensierens** digitaler Editionen; über die Editionen selbst tragen nur die Datasheet-Felder. Das Narrativ instanziiert dieselben Vis-Komponenten wie der Explorer, vorkonfiguriert im Scroll-Modus, und baut keine zweite Implementierung. Die sechs vom Daten-Skeptiker bestätigten Etappen (plus eine optionale):

| Etappe | Aussage | Vis |
|---|---|---|
| 1 Gegenstand durchgehend | DE dominiert bis Issue 22, 16 von 22 Issues tragen den Titel „Scholarly Editions" | P3, monochromer Set-Streifen |
| 2 Sechs Sonderfälle verstreut | text-collections und tools je drei isolierte Issues, kein Trend | P3, sechs Zellen leuchten auf |
| 3 Katalog als set-internes Instrument | rund 25.000 Antwortzellen, streng set-intern | P2, DE-Set vorgewählt |
| 4 Wer begutachtet, von wo | stabiles Board, DACH-Geografie | P5 plus P6 gekoppelt |
| 6 Anker Carolingian Scholarship | Makro zu Mikro, ein verifizierter Einzelfall | P4-Anatomie dieses Falls |
| 5 Was rezensiert, wie alt | Median-Delta rund 4, rechtsschief, kein Drift | P3-Alters-Scatter |
| 7 (optional) Verweisnetz | hohe konstante Archivquote, Selbstreferenz | P7, statische Endansicht |

Empfohlene Sequenz: 1, 2, 3, 4, 6 (Scharnier Makro zu Mikro), 5, 7. Jede Etappe trägt ein Ebenen-Badge (RIDE-Praxis gegen Feld-durch-RIDE), einen „Was diese Etappe nicht sagt"-Block und einen Deep-Link in den vorgefilterten Explorer. Die Set-Sperre gilt auch im Scroll-Modus; die Issue-Untertitel (Correspondence, FAIR, Crowdsourcing) sind kuratierte Programmsetzungen je ein bis zwei Issues, kein aus dem Volltext gemessenes Themensignal und keine eigene Etappe.

## 5. Implementierungsplan

Verifiziert gegen den echten Code. Drei Korrekturen gegenüber den naheliegenden Annahmen: `criteria_slug()` und die Set-Merge-Logik liegen in `src/render/charts.py` (nicht in `aggregations.py`); die Heatmap-Labels (`section_label`, `question_label`, `question_text`, `criteria_ref_label`) existieren bereits in `QuestionnaireQuestion`; die einzige echte Modell-Erweiterung ist `Affiliation.geo_ref`.

### Grundsatzentscheidung Technik

**Build-time-erzeugtes JSON plus D3.js als clientseitige Vis-Engine, vendored, kein Framework, kein Backend, kein npm-Build.** Bei 111 Reviews liegt der Datendump im niedrigen dreistelligen KB-Bereich. Crossfilter, Heatmap-Drilldown, Karte und Force-Netz (P1, P2, P6, P7) verlangen Client-JS und sind der eigentliche Neuwert gegenüber den statischen Charts. Timeline, Anatomie, Editor-Matrix und Inventar (P3, P4, P5) werden server-vorgerendert und nur per JS angereichert, bleiben also ohne JS lesbar (Progressive Enhancement). Die Set-Sperre wird im Dump als Daten-Eigenschaft verankert (set_slug ist Pflichtfeld, keine globale Ja-Quote), nicht erst als UI-Konvention.

Engine-Wahl D3.js statt eigenem SVG-Renderer: Der erklärte Anspruch ist ästhetisch hochwertig und voll nutzbar. Die geplanten Vis-Typen sind D3-Kerngebiet (Force-Beeswarm `d3-force`, Geo-Karte `d3-geo`, Brushing `d3-brush`, geschmeidige Übergänge `d3-transition`). D3 ist eine reine Client-Bibliothek, berührt den Python/Jinja-Build nicht und wird als fertiges ES-Modul lokal unter `static/js/vendor/` abgelegt (kein CDN, kein Bundler). Das hält die Offline-Build-Disziplin und ist konsistent mit dem bereits clientseitig laufenden Pagefind. Scrollytelling über `scrollama.js` (vendored), die Karte über `d3-geo` plus eingecheckte GeoJSON (Europa-/DACH-Ausschnitt, kein Tile-Server). Die Ästhetik kommt aus dem Zusammenspiel von D3 mit den vorhandenen CSS-Design-Tokens aus [[interface]] und sorgfältigen Micro-Transitions, unter WCAG-Treue (Tastatur, Kontrast, `prefers-reduced-motion`). Modular importiert bleibt der Footprint schlank.

### Arbeitspakete (abhängigkeitsgeordnet)

```
AP0  Technikentscheidung + JSON-Vertrag            (bindet alles)
AP1  Parser-/Modell-Erweiterung  (Affiliation.geo_ref, Editor-Dedup-Funktion)
AP2  Stage-1-Skripte  scripts/ -> inventory/  (explorer-dump roh, host-edges, geonames-lookup)
AP3  Build-Artefakt   src/render/explorer.py -> site/data/explorer.json
AP4  Navigation + Routen + Template-Gerüst
AP5  Explorer View 1  /data/explore/   (P1 Verteiler, dann P2-P7 + Inventar additiv)
AP6  Narrativ View 2  /data/story/      (instanziiert dieselben Vis vorkonfiguriert)
AP7  Test-Anbindung durchgehend je AP   (TDD mit Realkorpus, nicht am Ende)
```

- **AP1 Modell/Parser.** `Affiliation` um `geo_ref` (der `placeName/@ref` ist im Korpus eine volle GeoNames-URL, heute verworfen von `parse_authors()`). `RelatedItem` trägt bereits Datum/Titel/Personnel/Targets, kein Wachstum nötig. Editor-ORCID-Dedup und Rollen-pro-Zelle-Regel als reine Aggregationsfunktion.
- **AP2 Stage-1-Skripte** nach dem `scripts/taxonomy.py`-Muster (`run()`/`main()`, Ausgabe nach `inventory/`, gitignored): `explorer_dump.py` (Pro-Review-Zeile mit Umfang, Apparat als Präsenz plus Rohwert, set-interne Ja-Quote ohne value=3, Ressourcen-Felder), `host_edges.py` (bipartite Review-Host-Kanten plus web.archive.org-Wrapper-Parser), `geonames_lookup.py` (die GeoNames-IDs einmalig auf Koordinaten auflösen). Die Frageknoten-Matrix kommt direkt aus `Review.questionnaires[].questions`, kein neues Skript.
- **AP3 Build-Artefakt** `src/render/explorer.py` nach dem `corpus_dump.py`-Muster, `to_explorer_dump(...)` bündelt Pro-Review-Zeilen, Host-Kanten, Geo-Koordinaten, Frageknoten-Matrix je Set und Editor-Matrix; geschrieben nach `site/data/explorer.json` über einen neuen `_write_explorer_dump()`-Helfer in `src/build.py`.
- **AP4 Schale.** `config/navigation.yaml` um die Data-Kinder Explore und Story ergänzen (reine YAML-Änderung, `navigation.py` liest daraus). Neue Templates `explore.html` und `story.html` plus Vis-Partials; Render-Modul `src/render/explore.py` mit `render_explore()` und `render_story()` nach dem `aggregations.py`-Muster.
- **AP5/AP6.** P1 zuerst als Verteiler, P2 bis P7 und Inventar additiv. Der Narrativ-View hängt an AP5 und triggert je Etappe den vorkonfigurierten Zustand der geteilten Vis-Module.
- **AP7 Tests** gemäß der Hard-Rule TDD-mit-Realkorpus: synthetische Fixtures nur für den Modell-Contract und Pure-Function-Parser (Wrapper, Datumsbereiche, Docstring nennt die Ausnahme); Realkorpus-Integrationstests je `run()` und für `to_explorer_dump` (111 Zeilen, set_slug-Pflicht, keine globale Ja-Quote, exakte Output-Pfade), `needs_corpus`-Skip; JS-Module als statischer Contract wie `test_js_modules.py`. Unbekannte Frageknoten-Strukturen, unauflösbare GeoNames-IDs und unparsebare Ressourcen-Datumsbereiche werden benannte Branches oder raisen.

## 6. Offene Entscheidungen

- **E0 — Client-Bibliothek. Entschieden (2026-06-25):** D3.js v7 modular plus `scrollama.js`, vendored als ES-Module unter `static/js/vendor/`, Karte über `d3-geo` plus eingecheckte GeoJSON. Begründung im Technik-Abschnitt; ersetzt den ursprünglichen Team-Default „eigener SVG-Renderer", weil der Ästhetik-Anspruch eine etablierte Vis-Engine verlangt und D3 die Offline-Disziplin gleichermaßen hält.
- **E1 — JSON-Ablageort.** `site/data/explorer.json` als Build-Artefakt (Empfehlung) plus Roh-Aggregate in `inventory/`.
- **E2 — Ressourcen-Alter.** Maximalwert 35 (D1) gegen 26 (Katalog); beim Bau von AP2 gegen den Korpus klären (vermutlich Ongoing-Marker-Behandlung), keine Zahl hartkodieren.
- **E3 — Skript-Schnitt.** Zwei fokussierte Stage-1-Skripte plus statische Geo-Tabelle (Empfehlung) gegen ein gebündeltes Skript.
- **E4 — GeoNames-Koordinaten.** Einmalige Online-Auflösung und eingecheckter Ablageort unter `config/`, damit der Build offline bleibt.
- **E5 — URL-Schema.** `/data/explore/` und `/data/story/` als Aggregation-Pages in [docs/url-scheme.md](../docs/url-scheme.md) aufnehmen (additiv, kein Versionssprung).
- **E6 — Narrativ-Etappe 7** (Verweisnetz) aufnehmen oder streichen, je nachdem ob die Archiv-Streuung sauber als Sekundärsignal führbar ist.
- **E7 — Mikro-Anker.** Carolingian Scholarship (Issue 1, verifiziert) als Etappe-6-Anker bestätigen oder ersetzen.
- **E8 — Scope. Entschieden (2026-06-25):** Kern zuerst — P1, P2, P3 plus Narrativ-Etappen 1 bis 4, danach P4 bis P7 und Inventar additiv.
- **E9 — Verhältnis zu `/data/charts/`.** Die statischen Charts neben P2 belassen (Empfehlung: statisch gleich Kanon, interaktiv gleich Tiefe) gegen perspektivisches Aufgehen in der Explorations-Seite.
