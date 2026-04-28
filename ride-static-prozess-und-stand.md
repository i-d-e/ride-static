---
title: Die statische RIDE-Webseite. Konzept, Architektur und Stand
repository: https://github.com/i-d-e/ride-static
version: 2026-04-29
status: Phasen 1–4 abgeschlossen, Phase 5 als nächster Einstieg
---

# Die statische RIDE-Webseite. Konzept, Architektur und Stand

Dieses Dokument vereint Spezifikation, Architekturbegründung und Stand-Bericht
für das Projekt *ride-static*. Es ist sowohl für neue Mitwirkende, externe
Stakeholder und die Selbstdokumentation gedacht und dient zugleich als
Kontextdokument für agentische Arbeit mit Claude Code.

## Glossar der Eigenbegriffe

- **Promptotyping.** Methodische Praxis des iterativen Promptings gegen ein
  Sprachmodell, bei der kompakte Markdown-Wissensdokumente erzeugt und
  kuratiert werden, die später als Kontext für agentische Code-Erzeugung
  dienen.
- **Wissensdokument.** Ein Markdown-Dokument unter `knowledge/`, das entweder
  deterministisch aus dem Korpus generiert oder hand-kuratiert ist und im
  Repository committet liegt.
- **Sonderfall-Branch.** Ein im Parser benannter, mit einem Kommentar
  versehener Code-Pfad, der eine bekannte Korpus-Anomalie behandelt. Was nicht
  als Branch geführt wird und unbekannt auftaucht, soll den Build brechen.
- **Element-Mapping.** Eine YAML-Datei (`config/element-mapping.yaml`), die
  Domänenklassen auf Jinja-Templates und CSS-Klassen abbildet. Die häufigste
  Erweiterung der Site ist eine reine YAML-Änderung.

## Ausgangslage und Ziel

Die RIDE-Zeitschrift (Reviews in Digital Editions) liegt heute als
eXist-basierte Site mit eingebettetem WordPress-Anteil vor. Der
Rezensionskorpus besteht aus 107 TEI-XML-Dateien, strukturiert nach `ride.odd`,
einer projekteigenen TEI-P5-Anpassung. Die bestehende Lösung hält im Betrieb
eine XML-Datenbank vor, kombiniert zwei getrennte Wartungswege für
strukturierte und redaktionelle Inhalte und differenziert die Apparatik der
Rezensionen optisch nicht ausreichend.

Ziel des Projekts ist eine vollständig statisch gebaute Site. Ein einziger
GitHub-Actions-Workflow erzeugt aus dem TEI-Korpus, einem schmalen Bestand
redaktioneller Markdown-Texte und einer pro Heft gepflegten YAML-Konfiguration
den auslieferungsfähigen Output. Die Site läuft auf GitHub Pages, ohne
Backend, ohne Datenbank, ohne Daemon. Pagefind übernimmt die Volltextsuche
client-seitig, WeasyPrint die PDF-Erzeugung zur Build-Zeit, JSON-LD und ein
OAI-PMH-Snapshot bilden die Maschinenschnittstellen.

Das Projekt entsteht im Repository
[`github.com/i-d-e/ride-static`](https://github.com/i-d-e/ride-static), das
deployte Ergebnis liegt als GitHub-Pages-Site unter dem dortigen
Hosting-Pfad. Inhaltlich und konzeptionell beteiligt sind Martina Scholger,
Georg Vogeler und Stephan Dumont. Pflege und Weiterarbeit nach Abschluss
übernehmen Ulrike Henny und Martina Scholger. Beide arbeiten direkt im
GitHub-Repository, redaktionelle Texte werden über die GitHub-Web-UI
gepflegt, Templating und Pipeline lassen sich lokal mit Python anpassen,
ohne weitere Toolchain.

## Architektur im Überblick

Die Pipeline lässt sich in vier produktive Schichten gliedern, die linear
aufeinander aufbauen. Jede Schicht überführt das Format ihrer Eingabe in ein
anderes Format, bis am Ende eine ausschließlich statische Site steht.

![Architektur der statischen RIDE-Pipeline. Vier Schichten von Quellen über
Domänenmodell und Renderer bis zum Build- und Deploy-Schritt.](image-workflow.png)

Die oberste Schicht zeigt die drei Eingabequellen, also TEI-XML, redaktionelles
Markdown und Heft-YAML. Die mittlere Schicht trägt das Domänenmodell mit
Parser und immutablen Datenklassen für `Review`, `Section` und `Block` und
ist die einzige Schicht, die rohes XML sieht. Aus dem Domänenmodell entstehen
parallel die Render-Formate (HTML, PDF, Aggregationsseiten) und die
Maschinenschnittstellen (JSON-LD, OAI-PMH, Pagefind-Index). Die unterste
Schicht orchestriert den Single-Workflow-Build über GitHub Actions und
deployt das `site/`-Verzeichnis auf GitHub Pages.

Der Implementierung vorgeschaltet ist eine Wissensbasis, die als Kontext für
einen agentischen Bauprozess dient (siehe Abschnitt „Methodisches Vorgehen
und Wissensbasis"). Sie ist nicht Teil der produktiven Pipeline, sondern
deren Bauvoraussetzung.

## Methodisches Vorgehen und Wissensbasis

Der Implementierung vorgeschaltet ist eine Wissensbasis, die als Kontext
für einen agentischen Bauprozess mit Claude Code dient. Sie entsteht durch
*Promptotyping*, also iteratives Prompting gegen ein Sprachmodell (im
aktuellen Stand Claude Opus 4.7), bei dem kompakte Markdown-Wissensdokumente
vom Sprachmodell erzeugt und kuratiert werden. Beim späteren Bauen liest
das Sprachmodell diese Wissensdokumente und erzeugt phasenweise Code, der
an Anforderungen, Architektur und Korpusrealität gleichzeitig ausgerichtet
ist.

Die Wissensbasis hat zwei funktional getrennte Schichten. Die erste Schicht
entsteht deterministisch und beschreibt die Korpusrealität sowie das
verwendete Schema. Konkret laufen elf Python-Skripte unter `scripts/` über
die 107 TEI-Dateien und `ride.odd`, schreiben strukturierte Inventar-JSONs
nach `inventory/` und rendern daraus die zwei generierten Wissensdokumente
`knowledge/data.md` und `knowledge/schema.md`. Die Begründung für diesen
Umweg ist pragmatisch. 107 Volltexte plus Schema sind zu umfangreich, als
dass ein Agent sie pro Buildphase durchgehen könnte; die deterministische
Aggregation einmal vorzuschalten und nur die kompakten Wissensdokumente in
den Agent-Kontext zu reichen, ist sowohl billiger als auch reproduzierbarer.
Die zweite Schicht entsteht durch kuratiertes Prompting und legt
Anforderungen, Architektur, Interface und Bauabfolge fest, also
`requirements.md`, `architecture.md`, `interface.md` und `pipeline.md`.

Beide Schichten verweisen wechselseitig aufeinander. Jede Anforderung der
zweiten Schicht hat in der ersten ihre Grundlage, jede Auffälligkeit der
ersten findet in der zweiten einen benannten Umgang. Zur Sicherung der
Konsistenz über die Erstphase hinaus tritt eine dritte Schicht hinzu, eine
sessionbezogene Narrationsschicht in `Journal.md`, die festhält, warum eine
Entscheidung getroffen wurde und was als nächster Einstieg gilt.

### Skripte zur Korpusanalyse

Die elf Skripte unter `scripts/` laufen in vier Abhängigkeitsstufen und
schreiben ihre Ergebnisse als JSON nach `inventory/`. Die JSONs sind
regenerierbar und bewusst nicht eingecheckt; die zwei daraus gerenderten
Wissensdokumente sind committet, sodass eine frische Clone die strukturelle
Wissensbasis ohne Pipeline-Lauf trägt.

- `inventory.py` zählt Elemente und Attribute im Korpus und erzeugt
  `elements.json`, `attributes.json` und `corpus-stats.json`.
- `structure.py` erfasst Eltern-Kind-Muster pro Element.
- `sections.py` bildet die Sektionsschachtelung pro Rezension ab.
- `ids.py` prüft alle `xml:id`-Werte gegen die Schematron-Format-Regeln.
- `refs.py` klassifiziert sämtliche `<ref @target>` in vier Klassen
  (lokal, Kriterien-extern, externe URL, sonstiges) und markiert dangling
  references.
- `taxonomy.py` extrahiert die vier verwendeten Kriteriensets von i-d-e.de
  und die per-Rezension gegebenen Boolean-Antworten aus den
  `<num>`-Elementen.
- `odd_extract.py` extrahiert die Schema-Anpassungen aus `ride.odd`.
- `p5_fetch.py` lädt die TEI-P5-Modulinformationen und gleicht sie mit den
  im Korpus tatsächlich verwendeten Elementen ab.
- `cross_reference.py` gleicht Schema-Aussagen gegen Korpus-Realität ab und
  benennt Diskrepanzen.
- `render_data.py` erzeugt das Wissensdokument zur Korpusrealität.
- `render_schema.py` erzeugt das Wissensdokument zum RIDE-Schema.

Die Trennung folgt einem einfachen Prinzip. Was im Korpus nicht durch eines
dieser Skripte erfasst ist, wird im späteren Code nicht behandelt. Was
erfasst ist, wird vollständig behandelt, entweder als Regelfall oder als
benannter Sonderfall.

### Sechs Wissensdokumente

Die zwei deterministisch gerenderten Dokumente bilden die korpusbezogene
Schicht. `data.md` beschreibt die Korpusrealität, also Document Patterns,
vier Klassen der Reference-Resolution, Questionnaire-Kriteriensets,
ID-Format-Konformität und Schema-vs-Korpus-Mismatches. `schema.md`
beschreibt, was `ride.odd` aus TEI P5 importiert, anpasst und einschränkt.
Beide tragen Frontmatter mit Generierungsquelle und Inputs, sodass jederzeit
erkennbar ist, welche Skripte sie speisen. Beide dürfen ausschließlich
durch erneutes Rendern aktualisiert werden, nicht von Hand.

Die vier hand-geschriebenen Dokumente bilden die Spezifikationsschicht.
`requirements.md` definiert das Was, also 17 funktionale Anforderungen R1
bis R17, 10 nicht-funktionale Anforderungen N1 bis N10, sechs gesperrte
Architekturentscheidungen A1 bis A6 und fünf Rollen. `architecture.md`
definiert das Wie auf Datenflussebene mit Domänenmodell, Sonderfallbehandlung
als benannte Parser-Branches und einem deklarativen Element-Mapping in
YAML. `interface.md` definiert das visuelle und interaktive Wie mit sechs
Seitentypen, parallel gesetzten Apparaten (References, Figures, Notes),
Typografieentscheidungen und WCAG 2.2 AA als Mindestziel. `pipeline.md`
definiert das Wann, also den Phasenplan mit Anker an jede R- und N-Klausel,
GitHub-Actions-Workflow und Deployment.

Alle sechs Dokumente sind durch Obsidian-Wikilinks miteinander verknüpft.
Jede R- oder N-Klausel ist im Phasenplan einer oder mehreren Phasen
zugeordnet, jede Phase nennt ihrerseits die abgedeckten Klauseln. Das
ergibt eine vollständige beidseitige Zuordnung, in der keine Klausel ohne
Phase und keine Phase ohne Klauselrückbindung bleibt.

## Domänenmodell und Sonderfälle

Die Architektur trennt drei Verarbeitungsstufen. TEI wird durch einen
Parser in Python-Datenklassen überführt (`Review`, `Section`, `Block`,
`Inline` und Subtypen). Diese Datenklassen sind die einzige Schnittstelle
zur Renderer-Schicht. Templates und PDF-Erzeugung sehen niemals rohes XML.
Damit lässt sich das Datenmodell unabhängig vom Output testen, und HTML-
und PDF-Renderer können aus derselben Quelle bedient werden.

Das Block-Modell ist gegen den Korpus verifiziert auf fünf Kinds beschränkt,
also Paragraph, List, Table, Figure und Citation. `<head>` ist
Sektionsüberschrift und nie ein eigener Block. `<note>` und `<code>` sind
im RIDE-Korpus durchgängig inline. `<eg>` lebt ausschließlich in `<figure>`
und ist als `Figure(kind="code_example")` modelliert statt als eigene
Klasse. Inlines sind sechs Kinds, also Text, Emphasis, Highlight, Reference,
Note und InlineCode.

Sonderfälle werden im Parser als benannte Branches geführt, sodass der
Build bricht, wenn unbekannte Strukturen auftauchen, statt sie
stillschweigend zu vereinheitlichen.

- Sieben Rezensionen ohne `<back>`.
- Eine Rezension mit dupliziertem `<sourceDesc>`.
- Sieben Rezensionen mit flachem `<body>` ohne `<div>`-Wrapping.
- Sieben `<num value="3">`-Vorkommen in sechs Rezensionen außerhalb des
  Boolean-Schemas (`celt`, `europarl` mit zwei, `intercorp`,
  `theatreclassique`, `varitext`, `wwr`).
- Listenrendering-Werte `numbered` und `unordered` außerhalb der ODD-Liste.
- Ein Tippfehler `crosssref`.
- Etwa fünftausend interne Verweise auf das externe Kriteriendokument.
- Rund siebzig dangling references mit verschiedenen Präfixen.

Jeder dieser Fälle hat einen eigenen Branch im Parser oder ist redaktionell
in der Anomalietabelle benannt. Was nicht aufgeführt ist und unbekannt im
Korpus auftaucht, soll den Build brechen.

Das Element-Mapping ist ein zweites Konstruktionsprinzip. Die Bindung
Domänenklasse zu Template plus CSS-Klasse steht in
`config/element-mapping.yaml`. Eine neue visuelle Variante eines bekannten
Elements ist damit eine reine YAML-Änderung. Nur strukturell neue Semantik
erfordert eine Datenklasse plus Parser-Funktion. Der mechanische Pfad
dafür ist in `docs/extending.md` mit zwei Tabellen ausgearbeitet.

## Interface und Seitentypen

Vier Designprinzipien tragen das Interface. Strukturelle Strenge vor
visueller Geste, Lesbarkeit als primäre Funktion bei Lesedauern jenseits
von zwanzig Minuten pro Rezension, Apparate visuell differenziert statt
im einheitlichen kleinen Listenstil, und Designsparsamkeit als Entscheidung
statt Designarmut.

Sechs Seitentypen sind festgelegt.

- **Startseite** mit drei Inhaltsblöcken ohne Slider, also aktuelles Heft
  prominent, eine Auswahl ausgewählter Rezensionen mit Titel und
  Kurzbeschreibung, und News plus Call for Reviews kombiniert in der
  Sidebar.
- **Heftübersicht** als reine Liste der Hefte, sortiert nach
  Erscheinungsdatum, mit Rolling-Issue-Markern.
- **Heftansicht** mit Heftmetadaten oben und Beitragskarten mit
  Abstract-Ausschnitten.
- **Rezensionsansicht** als Hauptansicht mit Kopfbereich, Abstract,
  Hauptteil und drei parallel gesetzten Apparat-Sub-Blöcken statt der
  heutigen sequenziellen Anordnung.
- **Aggregationsseiten** für Tags, Reviewer, Reviewed Resources und Data,
  jeweils mit Sortier- und Filterleiste plus Liste oder Tabelle.
- **Editorialseiten** für About, Impressum und Reviewing Criteria, in
  einer einspaltigen Inhaltsspalte ohne Sidebar.

Das Stylesheet ist ein einzelnes CSS von etwa 600 bis 800 Zeilen, ohne
Build-Schritt und ohne Preprocessor. JavaScript ist auf vier kleine
Module beschränkt, also Copy-Link auf Absätze, Tooltip-Vorschau für
Cross-References, Pagefind-Integration und Cite-Kopieraktion. Schriftwahl
ist eine seriöse Sans-Serif für UI und Headings, eine Serif für den
Lesefließtext. Akzentfarbe ist ein einziges gedämpftes Blau für Links,
Anker und Querverweise. Mindestziel der Barrierefreiheit ist WCAG 2.2 AA,
mit Schwerpunkt auf Sprachpropagation, Tabellen-Header, Alt-Texten aus
dem TEI-`figDesc` und Tastaturnavigation.

## Phasenplan

Der Phasenplan ist in fünfzehn sequentielle Phasen geteilt. Jede Phase
produziert einen Commit, bringt synthetische Test-Fixtures plus einen
Korpus-Smoke-Test mit und deckt namentlich genannte R- und N-Klauseln ab.
Die folgende Tabelle gibt den Plan in der Reihenfolge wieder, in der
gebaut wird; Stand-Marker zeigen, was abgeschlossen ist.

| Phase | Inhalt | Stand |
|---|---|---|
| 1 | Datenmodell für Section, Block, Inline | abgeschlossen |
| 2 | Section-Parser inklusive Body-Wrap-Anomalie | abgeschlossen |
| 3 | Block-Parser (Paragraph, List, Table, Figure, Citation) | abgeschlossen |
| 4 | Inline-Parser (Mixed-Content-Walker plus sechs Inline-Kinds) | abgeschlossen |
| 5 | Integration in `parse_review`; `Review.body` für alle 107 Reviews voll | nächster Einstieg |
| 6 | Bibliography- und Questionnaire-Modell, Aggregate für Tags, Reviewer, Resources | offen |
| 7 | Reference-Resolver, Asset-Pipeline für eingebettete Bilder | offen |
| 8 | HTML-Rezensionsseiten plus Zitierexport, Copy-Link, Tooltip-Vorschau, JS-Module | offen |
| 9 | Editorialschicht (Markdown plus Heft-YAML mit Konsistenzcheck) | offen |
| 10 | Aggregations- und Übersichtsseiten | offen |
| 11 | Pagefind-Volltextsuche | offen |
| 12 | Maschinenschnittstellen (OAI-PMH, JSON-LD, Korpus-Dump, Sitemap) | offen |
| 13 | Validierung gegen RelaxNG plus Schematron, `build-info.json`, Build-Bericht | offen |
| 14 | PDF aus Domänenmodell via WeasyPrint | offen |
| 15 | Deploy, cookieloses Matomo, WCAG-Audit, Meta-Refresh-Redirects | offen |

Die Verortung der PDF-Phase ist absichtlich auf Phase 14 belassen. Beide
Renderer hängen am gleichen Domänenmodell, eine frühere Implementierung
wäre technisch möglich. Die Beibehaltung in Phase 14 ist eine
Reihenfolge-Entscheidung zugunsten einer früher produktiv schaltbaren
HTML-Schiene und einer XSLT-Übergangslösung für PDF. Die Entscheidung ist
in `requirements.md` A6 fixiert.

## Output und Schnittstellen

Der Output ist rein statisch. Pro Rezension entstehen mehrere Artefakte,
die auf der Verzeichnisstruktur des Deploy-Branches liegen.

- Eine HTML-Seite unter `/issues/{issue_no}/{review_id}/`.
- Eine PDF-Datei unter `/issues/{issue_no}/{review_id}/{review_id}.pdf`.
- Ein TEI-Download unter `/issues/{issue_no}/{review_id}/{review_id}.xml`.
- Eingebettete JSON-LD mit `schema.org/ScholarlyArticle`-Markup.
- Figures unter `/issues/{issue_no}/{review_id}/figures/`.

Anker innerhalb einer Rezension verwenden die `xml:id` der TEI-Quelle, was
Zitierbarkeit auf Absatzebene technisch ermöglicht und in der UI durch
eine Copy-Link-Mikrointeraktion sichtbar wird. Das URL-Schema reserviert
ein optionales Versionssegment `/v/{version}/` für eine spätere
Snapshot-Strategie bei Rolling Issues, ohne bestehende URLs zu brechen.

Daneben stehen die übergreifenden Site-Artefakte, also Heftseiten,
Aggregationsseiten für Tags, Reviewer, Reviewed Resources und Data-Charts,
der OAI-PMH-Snapshot mit statisch dispatchten Verb-Endpoints (`Identify`,
`ListIdentifiers`, `ListRecords`, `GetRecord`), ein vollständiger
Korpus-Dump als JSON unter `/api/corpus.json`, eine Sitemap mit
Last-Modified-Daten und die Pagefind-Suchindex-Dateien unter `/pagefind/`.
Jeder Build erzeugt eine `build-info.json` mit Korpus-Version,
Schema-Version, Kriterien-Version und Commit-Hash. Damit ist jeder
ausgelieferte Stand reproduzierbar nachvollziehbar.

## Komponenten der heutigen Site und ihre Zukunft

Die folgende Tabelle bildet jede heutige Komponente der RIDE-Site auf den
geplanten Bauabschnitt der neuen Architektur ab. Wo Stakeholder-Notizen
offene Fragen aufwerfen, sind sie als solche in der Spalte „Offene
Fragen" formuliert.

| Komponente | Heute | Künftig | Phase | Offene Fragen |
|---|---|---|---|---|
| Startseite | Statische Texte plus Slider | Drei Inhaltsblöcke ohne Slider gemäß `interface.md` | 8, 10 | Sind „ausgewählte Rezensionen" händisch in der Heftkonfiguration kuratiert oder algorithmisch ausgewählt? |
| About | Statische Texte | Markdown mit Frontmatter unter `content/about.md`, Pflege über GitHub-Web-UI | 9 | — |
| Issues (Hefte) | Heft-Titel, Hrsg., Beiträge mit Autor, DOI | Heft-YAML als alleinige Quelle, Konsistenzcheck gegen TEI-Header bricht den Build | 9 | Welche Hefte erscheinen in der Hauptnavigation, alle, kuratiert oder die letzten N? |
| Rolling Issue | implizit | Statusmarker in Heft-YAML, Zitiervorschlag mit Abrufdatum, optionales Versionssegment in URL reserviert | 8, 9 | Wann gilt ein Rolling Issue als fertig, welcher Statuswechsel im YAML markiert das? Welche zusätzlichen Felder gegenüber regulären Heften? |
| Navigation | Manuell gepflegt | YAML-konfigurierte Hauptnavigation plus Aggregations-Links | 9, 10 | Speist sich die Navbar aus Content oder aus manueller YAML-Konfiguration? |
| Beitrag (Rezensionsansicht) | XSLT-Layout | Jinja-HTML aus dem Domänenmodell, Apparate parallel, reduzierte Sidebar (TOC, Meta, Cite) | 8 | Soll „first / last updated"-Information neben dem reinen Build-Datum sichtbar werden? |
| Tags | TEI plus WordPress, teils divergent | Aus TEI generiert; einmalige Konsolidierung der WordPress-Tags vor erstem Produktiv-Build, danach WordPress als Tag-Quelle abgeschaltet (A2) | Vor 6 (redaktionell), 10 | — |
| Factsheet | XSLT-organisiert | Aus Questionnaire-Datenmodell gerendert, separate Meta-Box entfällt | 8 | — |
| Data | Intro plus iframe-Charts aus eXist via XQuery, Erfassung über LimeSurvey → HTML → TEI | Charts zur Build-Zeit aus Questionnaire-Daten, ohne Laufzeit-Backend; Anomaliewert `value=3` als nicht-bewertet ausgewiesen | 10 | — |
| Reviewed Resources | Aus eXist generiert | Aus TEI generiert, ohne manuelle Pflege | 10 | — |
| Reviewers | Statisch plus „project under review" | Liste alphabetisch aus TEI; optionale Markdown-Profildatei wird der Beitragsliste vorangestellt | 9, 10 | Wo wird „project under / for review" geführt, eigene Editorialseite oder Reviewer-Detailseite? |
| Review Criteria | Statisch | Markdown unter `content/criteria.md`; `#K`-Refs aus Rezensionen werden gegen externe Kriteriendokument-URL aufgelöst | 7, 9 | — |
| Kontaktformular | Mailto plus Formular | Sichtbare obfuskierte Mail-Adresse; kein Formular | 9 | — |
| Volltextsuche | Eigene Implementierung | Pagefind, Index zur Build-Zeit, Suche client-seitig mit Kontextausschnitt | 11 | — |
| Impressum | Statisch | Markdown mit Hinweis auf cookieloses Tracking | 9 | — |
| Tracking | Matomo mit Cookie-Snippets | Matomo cookielos, ohne Consent-Banner | 15 | — |
| Social-Buttons | Vorhanden | Entfallen zugunsten von Open-Graph-Metadaten und Copy-Link | 8 | Eigene Iteration zu einer Social-Media-Strategie? |
| OAI-PMH | Dynamisch | Statischer Snapshot mit Query-String-Routing, Dublin-Core-Mindestmetadaten | 12 | — |
| Statische Texte (WordPress) | In WordPress gepflegt | In TEI oder Markdown überführt | Vor 9 (redaktionell) | Wieviel davon sauber in TEI überführen versus als Markdown-Editorial führen? |

## Stand der Implementierung

Stage Discovery und Stage Knowledge sind abgeschlossen. Stage Domain-Model
2.A (Header-Parser) ist abgeschlossen. Aus dem Phasenplan sind Phasen 1
bis 4 abgeschlossen, mit 170 von 170 grünen Tests inklusive
Real-Korpus-Smokes; jüngster Stand ist Commit `6d9f05e` (Inline-Parser,
2026-04-29).

Konkret liegt im Repository ein gefrorenes Domänenmodell unter `src/model/`
(`review.py`, `section.py`, `block.py`, `inline.py`, alle Subtypen als
immutable `@dataclass(frozen=True)`) und die parsenden Module unter
`src/parser/`: `metadata.py` für den Header (Stage 2.A), `sections.py`
mit rekursivem `<div>`-Walk inklusive Body-Wrap-Anomalie, `blocks.py` mit
fünf Per-Kind-Funktionen plus Dispatcher und einer dedizierten
`UnknownTeiElement`-Exception, `inlines.py` mit dem Mixed-Content-Walker
und sechs Inline-Kinds. Sonderfall-Branches sind im Code für
Body-Wrap-Anomalie, List-Rend-Normalisierung, `crosssref`-Normalisierung,
`<lb/>`-Soft-Skip und unbekannte Elemente vollständig umgesetzt; das
duplizierte `<sourceDesc>` und die `<num value="3">`-Ausreißer sind in
`data.md` benannt und werden in Phase 6 (Stage 2.C, Bibliography- und
Questionnaire-Parser) implementiert.

Phase 5 (Integration in `parse_review`) ist der nächste Einstieg: ein
Pre-Pass über `<p>` muss Block-Kinder (figure, list, cit, table, in Summe
~1 000 Vorkommen unter `<p>`) aus dem Mixed-Content auslagern und als
Sibling-Blöcke einreihen, bevor der Inline-Walker greift. Ist das
geleistet, läuft der Real-Korpus-Smoke gegen alle 107 Reviews fehlerfrei
und Stage 2.B ist abgeschlossen. Spezifiziert, aber noch nicht
implementiert sind elf der fünfzehn Phasen, also Phase 5 bis Phase 15.

## Pflege nach Abschluss

Die Site ist mit Blick auf laufende Pflege gebaut. Vier Stellen sind
dafür entscheidend.

Redaktionelle Texte werden als Markdown mit Frontmatter im Repository
gepflegt und sind über die GitHub-Web-UI direkt editierbar. Heftmetadaten
liegen in einer YAML-Konfigurationsdatei pro Heft, die als alleinige
Quelle für die Heftansicht dient; Inkonsistenzen zur TEI-Header-Information
brechen den Build mit klarer Fehlermeldung. Visuelle Anpassungen erfolgen
in einem einzigen CSS-Stylesheet ohne Preprocessor. Wer Templates anpasst,
arbeitet mit Jinja-Dateien, die ausschließlich Domänenobjekte sehen.
Strukturelle Erweiterungen sind in `docs/extending.md` pro Pipeline-Phase
dokumentiert.

`CONTRIBUTING.md` und ein Troubleshooting-Abschnitt sind Bestandteil des
Repositorys, sodass Mitarbeit innerhalb eines halben Tages produktiv
möglich sein soll (N8). `Journal.md` führt eine session-bezogene Narration
mit fünf festen Feldern (Ziel, Erledigt, Entscheidungen, Offen, Nächster
Einstieg), die zwischen Memory, Git-Historie und Projektkonventionen
vermittelt.

## Offene Fragen

Drei größere Bereiche sind im Lauf der Implementierung zu klären.

**Erstens, redaktionelle Schnittstelle.** Wie sieht der heutige Weg eines
Beitrags vom Autor bis ins TEI aus, also welche Tools für TEI-Authoring
(oXygen, anderer Editor, Vorlagen), entstehen TEI-Dateien per Hand aus
einem Template oder gibt es Vorprozessierungs-Skripte, an welcher Stelle
laufen heute Validierungen (vor dem Commit, nach dem Push)? Welche Felder
sind beim Anlegen eines neuen Hefts zu pflegen, die nicht ohnehin im
TEI-Header eines Beitrags stehen, und wie wird die Beitragsreihenfolge
festgelegt? Welche Felder werden heute redundant in WordPress und TEI
gepflegt und sollen in der neuen Architektur in YAML oder TEI konsolidiert
werden? Was ist beim Anlegen eines Rolling Issue zusätzlich zu erfassen?
In welchem Format kommen Beiträge typischerweise an (Word, LibreOffice,
Markdown, bereits TEI), und wäre eine automatisierte Konversion (Pandoc
plus Post-Processing oder ein Stylesheet-Weg) als optionale spätere
Erweiterung sinnvoll?

**Zweitens, Komponenten-Detailfragen aus den Stakeholder-Notizen.** Diese
sind in der Tabelle oben pro Komponente verortet und brauchen
redaktionelle Antworten. Sie betreffen vor allem die Auswahllogik der
Startseiten-Beiträge, die Befüllung der Hauptnavigation, die Sichtbarkeit
von „first / last updated", den Statuswechsel bei Rolling Issues und die
Reichweite der Konsolidierung statischer Textfragmente.

**Drittens, Infrastruktur und Reichweite.** Domain und Hosting-Pfad, also
eigene Domain versus `username.github.io/repo`, prägen das URL-Schema und
damit die Stabilitätszusage in N3 und R17. Auslieferung großer Artefakte,
also OAI-PMH-Dump und ältere PDF-Versionen, über GitHub Pages oder GitHub
Releases. Reichweite der Konsolidierung in A2, also ob neben den Tags
auch andere heute in WordPress liegende redaktionelle Fragmente in TEI
oder Markdown überführt werden.

Die Antworten der ersten beiden Bereiche prägen direkt den
Validierungsschritt aus Phase 13, der entweder vor oder nach dem Push
platziert werden kann, sowie eine mögliche Konversionsschicht vor der
Korpusanalyse, die heute nicht im Phasenplan steht, aber als optionale
Vorstufe nachträglich ergänzbar wäre. Die Antworten des dritten Bereichs
prägen Phase 15.