# Requirements — RIDE Static Site

> Produktdefinition. Anker für [[architecture]] (Datenflüsse, Domänenmodell), [[interface]] (Visuelles und interaktives Design) und [[pipeline#Phasenplan]] (Bauabfolge). Korpusbezogene Aussagen verweisen auf [[data]] und [[schema]].

## 1. Zweck und Scope

Dieses Dokument beschreibt die Anforderungen an die statische Neufassung der RIDE-Website. Bisheriger Stand ist die eXist-basierte Lösung mit dynamischer Generierung der meisten Seiten und eingebettetem WordPress-Anteil für statische Inhalte. Zielzustand ist eine vollständig statisch gebaute Site, die aus 107 TEI-XML-Rezensionen, einem schmalen Bestand redaktioneller Markdown-Texte und einer pro Issue gepflegten Konfiguration erzeugt wird.

Das Projekt *ride-static* mit seinen acht Pipeline-Phasen deckt den Inhaltsbereich ab. Dieses Requirements-Dokument erweitert den Scope auf die vollständige Site und benennt vier weitere Funktionsbereiche, die als eigene Bauabschnitte nach Abschluss von Phase 8 anschließen.

Nicht im Scope sind Migration der Redaktionsprozesse, Schulung der Editor-Innen, Hosting-Entscheidungen jenseits GitHub Pages oder ein vollständiges Designsystem.

## 2. Plattform und Architekturgrundsätze

Die Site läuft auf GitHub Pages und wird über einen einzigen GitHub-Actions-Workflow gebaut. Daraus folgen drei Plattformgrenzen, die jede weitere Festlegung passieren muss.

Output ist rein statisch. Alles, was zur Auslieferungszeit ausgeführt werden soll, läuft client-seitig. Kein Backend, kein Daemon, keine Datenbank in Produktion.

Build läuft in einem Linux-Runner mit Python und Node-Toolchain. Externe Bibliotheken sind erlaubt, sofern sie als Build-Time-Dependency arbeiten und ein statisches Artefakt erzeugen.

URL-Struktur folgt der Verzeichnisstruktur des Deploy-Branches. Headers, Redirects und 404-Handling sind nur in dem Maß möglich, das GitHub Pages bietet.

Drei übergreifende Architekturgrundsätze gelten in allen Bereichen. Die Pipeline ist read-only gegenüber TEI; sie schreibt niemals zurück. TEI ist die einzige Quelle der Wahrheit für strukturierte Inhalte. Redaktionelle Texte werden als Markdown im Repository gepflegt und sind ohne Programmierkenntnisse änderbar.

## 3. Rollen

Die **Leserin** ist Wissenschaftlerin oder Studierende; sie liest, zitiert, durchsucht. Sie ist die zahlenmäßig dominante Nutzerin und prägt die meisten Stories des Inhalts- und Funktionsbereichs.

Die **Editorin** pflegt redaktionelle Texte (About, Impressum, Review Criteria, Reviewer-Profile). Sie ist nicht zwingend Programmiererin und braucht niedrigschwellige Bearbeitungswege, idealerweise über die GitHub-Web-UI.

Die **Herausgeberin** verantwortet ein Issue, vergibt DOI, bestimmt Reihenfolge der Beiträge und Status eines Rolling Issue.

Der **Aggregator** ist ein automatisiertes externes System (Bibliothekskatalog, Repository-Crawler, Zotero-Connector). Er verlangt strukturierte Metadaten in standardkonformer Form.

Die **Betreiberin** verantwortet Build, Hosting und Erhebung von Nutzungszahlen.

## 4. Festgelegte Designentscheidungen

Die folgenden sechs Entscheidungen liegen allen Anforderungen zugrunde und sind in einer dedizierten Architekturklausur fixiert worden. Sie sind hier zusammengefasst, weil viele Akzeptanzkriterien direkt von ihnen abhängen.

**A1 Rolling Issue.** Jeder Build ist kanonisch zum Zeitpunkt seiner Erzeugung. Das Zitat enthält bei Rolling Issues ein Abrufdatum. Das URL-Schema reserviert ein optionales Versionssegment, sodass eine spätere Snapshot-Strategie ohne URL-Bruch nachgezogen werden kann.

**A2 Datenquellen.** TEI ist alleinige Quelle für Tags, Reviewer-Liste, reviewed resources und alle aus Rezensionen ableitbaren Aggregate. Vor dem ersten Produktiv-Build läuft eine einmalige redaktionelle Konsolidierung der WordPress-Tags in TEI; danach wird WordPress als Tag-Quelle abgeschaltet.

**A3 Redaktionelle Texte.** About, Impressum, Review Criteria und Reviewer-Profile werden als Markdown im Repository gepflegt, mit Frontmatter für Titel, Sprache und Stand. Reviewer-Profile sind optional; existiert keine Markdown-Datei, wird die Reviewer-Detailseite rein aus TEI-Aggregation erzeugt.

**A4 Volltextsuche.** Pagefind erzeugt zur Build-Zeit einen Suchindex; Suche läuft client-seitig im Browser, mit Kontextausschnitten und Highlighting.

**A5 Maschinenschnittstellen.** Ein statischer OAI-PMH-Snapshot wird zusammen mit einem moderneren Pfad bereitgestellt — JSON-LD pro Seite, vollständiger Korpus-Dump als JSON, Sitemap mit `schema.org/ScholarlyArticle`-Markup.

**A6 PDF-Pfad.** Phase 8 liefert HTML; das bestehende PDF läuft als Übergangslösung weiter. Phase 14 implementiert PDF aus dem Domänenmodell über WeasyPrint mit eigenem Print-Stylesheet. Das Domänenmodell wird ab Phase 1 mit beiden Renderings im Blick entworfen — siehe [[architecture#Domain model]] und [[pipeline#Phasenplan]].

## 5. Funktionale Anforderungen

### 5.1 Inhaltsbereich

**R1 Rezension lesen.** Als Leserin will ich eine Rezension vollständig im Browser lesen, sodass ich keine Funktion gegenüber der heutigen eXist-Version vermisse.

Akzeptanzkriterien
- Inhaltsverzeichnis mit funktionierenden Sprungankern auf alle Sections (Layout siehe [[interface#5 Rezensionsansicht im Detail]])
- Fußnoten als Tooltip oder als Sprung mit Rücksprung (Mikrointeraktionen: [[interface#11 Mikrointeraktionen]])
- Querverweise innerhalb der Rezension funktionieren als In-Page-Links
- Querverweise mit `K`-Präfix verlinken auf das externe Kriteriendokument an `taxonomy/@xml:base` (siehe [[data#Reference resolution]] für die empirische Grundlage)
- Mehrsprachige Inhalte tragen das korrekte `lang`-Attribut bis auf Inline-Ebene (siehe [[interface#8 Mehrsprachigkeit]])
- Bibliographie wird am Ende der Rezension gerendert, mit stabilen Ankern pro Eintrag (paralleles Apparate-Layout: [[interface#6 Apparate als parallele Blöcke]])
- Factsheet wird angezeigt und erklärt die Bewertung knapp
- Tags der Rezension werden angezeigt und verlinken auf die Tag-Übersicht

**R2 Rezension zitieren.** Als zitierende Leserin will ich pro Rezension einen sichtbaren Zitiervorschlag, BibTeX und CSL-JSON zum Kopieren.

Akzeptanzkriterien
- Zitiervorschlag im festgelegten Format `Surname, Forename (Year). "Title." RIDE {Issue}, ed. by {Editors}. DOI: {DOI}. Accessed: {Date}.` — Autoren mit Surname-First, Issue-Nummer, vollständige Editor-Liste, DOI, Erscheinungs- bzw. Abrufdatum
- DOI ist Pflichtfeld; ohne DOI bricht der Build mit klarer Fehlermeldung, weil ohne DOI keine zitierfähige Rezension auslieferbar ist
- Kopier-Button für BibTeX
- Kopier-Button für CSL-JSON
- Bei Rolling Issue zeigt der Zitiervorschlag zusätzlich „Accessed: {Build-Datum}", gemäß A1
- Unter dem Zitiervorschlag erscheint die erklärende Mikrokopie „You can use the running numbers on the left side to refer to a specific paragraph." als Hinweis auf die Zitierbarkeit auf Absatzebene

**R3 Rezension herunterladen.** Als Leserin mit Datenpräferenz will ich pro Rezension TEI-XML und PDF herunterladen.

Akzeptanzkriterien
- TEI-XML-Datei ist die unveränderte Quelle, mit korrektem Content-Type-Header
- PDF trägt DOI sichtbar auf der ersten Seite
- Während der Übergangsphase wird das bestehende PDF ausgeliefert; ab Phase 9 das aus dem Domänenmodell erzeugte PDF, gemäß A6
- Beide Downloads sind über sichtbare Aktion in der Rezensionsansicht erreichbar

**R4 Issue-Ansicht.** Als Leserin will ich pro Issue eine Übersichtsseite mit Issue-Metadaten und Beitragsliste.

Akzeptanzkriterien
- Issue-Titel, Herausgeber, DOI, Erscheinungsdatum sichtbar
- Beitragsliste mit Autoren, Titel, kurzem Abstract
- Reihenfolge der Beiträge ist über die Issue-Konfiguration einstellbar (siehe R11)
- Bei Rolling Issue ist Status sichtbar markiert, gemäß A1

### 5.2 Aggregationsbereich

**R5 Issue-Übersicht.** Als Leserin will ich eine Übersicht aller Issues, sortiert nach Erscheinungsdatum.

Akzeptanzkriterien
- Liste mit Issue-Titel, Erscheinungsdatum, Herausgebern, Anzahl Beiträge
- Verweis auf jeweilige Issue-Ansicht
- Rolling Issues sind als solche markiert

**R6 Tag-Aggregation.** Als Leserin will ich pro Tag eine Übersicht aller Rezensionen, die diesen Tag tragen.

Akzeptanzkriterien
- Globale Tag-Übersicht aus der Navigation erreichbar
- Pro Tag eine Detailseite mit allen Rezensionen, die ihn tragen
- Tags entstammen vollständig den TEI-Quellen, gemäß A2

**R7 Reviewed Resources.** Als Leserin will ich eine vollständige Liste der besprochenen Editionen mit Verweis auf die Rezension.

Akzeptanzkriterien
- Tabellarische Darstellung mit Titel der Edition, Verantwortlichen, Verweis auf die Rezension
- Generierung vollständig aus TEI, ohne manuelle Pflege

**R8 Reviewer-Liste.** Als Leserin will ich eine Liste aller Rezensentinnen mit Anzahl und Verweis auf ihre Beiträge.

Akzeptanzkriterien
- Alphabetisch sortiert, mit Anzahl Beiträge pro Person
- Detailseite pro Person, mit Beitragsliste aus TEI-Aggregation
- Falls eine Markdown-Profil-Datei existiert, wird ihr Inhalt der Beitragsliste vorangestellt, gemäß A3

**R9 Data-Charts.** Als Leserin will ich aggregierte Auswertungen der Fragebogen-Antworten über das Korpus.

Akzeptanzkriterien
- Charts werden zur Build-Zeit aus den Questionnaire-Daten erzeugt, ohne Laufzeit-Backend
- Mindestens die Visualisierungen, die heute existieren, bleiben erhalten
- Anomalie `value=3` wird konsistent als nicht-bewertet behandelt und in Charts ausgewiesen (siehe [[data]] zur Korpus-Realität von `<num>`)

### 5.3 Editorialbereich

**R10 Statische Inhalte pflegen.** Als Editorin will ich die editorialen Seiten der Site niedrigschwellig pflegen, ohne Build-Tooling oder Programmierwissen.

Akzeptanzkriterien
- Pflegeformat ist Markdown mit Frontmatter, gemäß A3
- Bearbeitung über die GitHub-Web-UI ist möglich
- Push auf `main` triggert automatisch einen neuen Build und ein Deployment
- Die folgenden editorialen Seiten existieren als jeweils eigene Markdown-Datei unter `content/`:
  - **About-Untermenü:** Editorial · Publishing Policy · Ethical Code · Team · Peer Reviewers
  - **Reviewers-Untermenü:** Call for Reviews · Submitting a Review · Projects for Review · RIDE Award 2017–2020
  - **Footer-/Standalone:** Imprint · Reviewing Criteria
  - „List of Reviewers" wird **nicht** als Markdown geführt, sondern aus der TEI-Aggregation auf `/reviewers/` erzeugt (R8)
- Im Footer jeder Seite stehen sichtbar: Lizenz-Kürzel, Markenname mit aktuellem Jahr, ISSN (`2363-4952`), Link auf Imprint and Privacy
- Im globalen Header steht die Site-Tagline „A Review Journal for Scholarly Digital Editions and Resources" als Untertitel zur Marke RIDE

**R11 Issue-Metadaten pflegen.** Als Herausgeberin will ich pro Issue Metadaten an einer einzigen Stelle pflegen.

Akzeptanzkriterien
- Eine Konfigurationsdatei pro Issue (YAML) hält DOI, Herausgeberangaben, Beitragsreihenfolge, Status (regulär oder rolling)
- Diese Datei ist die einzige Quelle für die Issue-Ansicht
- Inkonsistenzen zwischen Issue-Konfiguration und TEI-Header brechen den Build mit klarer Fehlermeldung

**R11.5 Globale Navigation pflegen.** Als Herausgeberin will ich die globale Navigation (Header-Dropdowns) konfigurieren können, ohne Templates anzufassen.

Akzeptanzkriterien
- Eine Konfigurationsdatei `config/navigation.yaml` führt die fünf Top-Level-Einträge (About / Issues / Data / Reviewers / Reviewing Criteria) und ihre Untermenüs als Liste mit Label und Ziel-URL
- Issues-Dropdown listet die letzten N Issues plus „All Issues" — N und Sortierreihenfolge sind konfigurierbar
- Templates lesen die Navigation aus dieser Datei; Hinzufügen einer neuen editorialen Seite ändert YAML, nicht Template
- Die Navigation wird mit nativen `<details>`-Elementen umgesetzt, kein JavaScript-Framework

### 5.4 Funktionsbereich

**R12 Volltextsuche.** Als Leserin will ich eine Volltextsuche über alle Rezensionen mit Treffern im Kontext.

Akzeptanzkriterien
- Suchindex wird über Pagefind zur Build-Zeit erzeugt, gemäß A4
- Treffer enthalten Rezensionstitel, Issue, kurze Kontextausschnitte
- Sprung in die Rezension landet an der Trefferstelle
- Suche funktioniert offline, sobald die Site einmal geladen wurde

**R13 Sharing.** Als Leserin will ich eine Rezension teilen, mindestens als kopierbarer Link mit Titel.

Akzeptanzkriterien
- URL ist stabil und enthält die `xml:id` der Rezension
- Open-Graph-Metadaten sind gesetzt, sodass Vorschauen in sozialen Netzen sinnvoll aussehen

**R14 Kontakt.** Als Leserin will ich Redaktion und Herausgebende erreichen.

Akzeptanzkriterien
- Sichtbare Mail-Adresse genügt, kein Formular
- Mail-Adresse ist obfuskiert, sodass triviales Scraping erschwert ist

### 5.5 Infrastrukturbereich

**R15 Maschinenschnittstellen.** Als Aggregator will ich Metadaten aller Rezensionen über standardkonforme Schnittstellen abrufen.

Akzeptanzkriterien, gemäß A5
- OAI-PMH-Snapshot wird zur Build-Zeit erzeugt und mit der Site ausgeliefert; Endpoint liefert mindestens Dublin Core
- Pro Rezensionsseite ist JSON-LD mit `schema.org/ScholarlyArticle`-Markup eingebettet
- Vollständiger Korpus-Dump als JSON ist über stabile URL erreichbar
- Sitemap nach Standard ist vorhanden

**R16 Tracking.** Als Betreiberin will ich Nutzungszahlen ohne personenbezogene Cookies erheben.

Akzeptanzkriterien
- Matomo oder gleichwertig im cookielosen Modus
- Tracking-Consent-Banner entfällt, wenn keine Cookies gesetzt werden
- Sichtbarer Hinweis im Impressum bleibt

**R17 Stabile URLs.** Als Leserin und Aggregator will ich, dass einmal vergebene URLs dauerhaft funktionieren.

Akzeptanzkriterien
- URL-Schema ist in `docs/url-scheme.md` dokumentiert und unter Versionierung
- Anker innerhalb einer Rezension verwenden die `xml:id` der TEI-Quelle (siehe [[data#ID format conformance]] zur Garantie der Eindeutigkeit pro Datei)
- URL-Schema reserviert ein optionales Versionssegment für spätere Snapshot-Strategie, gemäß A1
- Spätere Umbenennungen erzeugen Meta-Refresh-Redirects auf den neuen Pfad

## 6. Nicht-funktionale Anforderungen

**N1 Read-only-Pipeline.** Die Pipeline schreibt niemals in TEI-Dateien zurück. Erweiterungen am TEI sind ausschließlich redaktionell, die Pipeline reagiert lesend und mit dokumentierten Erweiterungspunkten.

**N2 Erweiterbarkeit auf vier Ebenen.** Neue TEI-Elemente, neue Attributwerte, geänderte Textknoten-Behandlung und nachgelagerte Build-Auswirkungen sind in `docs/extending.md` pro Pipeline-Phase dokumentiert. Das Element-zu-Template-Mapping wird deklarativ als `config/element-mapping.yaml` geführt — Spezifikation in [[architecture#Element-Mapping (declarative)]]. Damit ist die häufigste Erweiterung (neuer Variant, anderes Template, andere CSS-Klasse) eine reine YAML-Änderung; nur strukturell neue Semantik erfordert Python.

**N3 Validierung als eigene Schicht.** Eine Pre-Build-Validierung gegen RelaxNG und Schematron erzeugt einen menschenlesbaren Bericht pro Datei. Sie ist unabhängig vom Build aufrufbar.

**N4 Reproduzierbarkeit.** Jeder Build erzeugt eine `build-info.json` mit Korpus-Version, Schema-Version, Kriterien-Version und Commit-Hash.

**N5 Barrierefreiheit.** Mindestziel WCAG 2.2 AA, mit Schwerpunkt auf Sprachpropagation, Tabellen-Header, Alt-Texten und Tastaturnavigation. Operative Ausführung in [[interface#9 Barrierefreiheit]].

**N6 Lizenzklarheit pro Artefakt.** Lizenz pro Rezension ist sichtbar gerendert. README dokumentiert getrennt die Lizenz für HTML-Output, kopierte Bilder und den Code der Pipeline.

**N7 Build-Bericht.** Nach jedem Build entsteht ein aggregierter Bericht aller Warnungen, gruppiert nach Rezension und Typ.

**N8 Übergabefähigkeit.** `CONTRIBUTING.md`, `ARCHITECTURE.md` mit Diagramm und ein Troubleshooting-Abschnitt sind Bestandteil des Repositorys, sodass Mitarbeit innerhalb eines halben Tages produktiv möglich ist.

**N9 Performance.** Build des vollen Korpus innerhalb von zwei Minuten auf einem aktuellen Notebook. Inkrementelles Build ist konzeptionell vorgesehen, aber nicht zwingend implementiert.

**N10 Single-Workflow-Build.** Der gesamte Build läuft in einer einzigen Workflow-Datei `.github/workflows/build.yml`. Trigger sind Pushes auf `main`, die TEI-Quellen, Markdown-Texte oder Pipeline-Code betreffen.

## 7. Out of Scope und zurückgestellt

PDF aus dem Domänenmodell ist als Phase 9 nach Phase 8 vorgesehen, gemäß A6.

Snapshot-Versionierung für Rolling Issues ist als spätere Erweiterung vorgesehen; das URL-Schema lässt sie zu, ohne sie zu erzwingen.

Designsystem jenseits eines minimalistischen CSS ist eigene Iteration.

Migration der WordPress-Tags ist eine einmalige redaktionelle Aufgabe vor dem ersten Produktiv-Build, nicht Teil der Pipeline.

Wordcloud-Slider auf der Startseite sind out, gemäß [[interface#3 Bewertung des heutigen UI]]. Die statischen Wordcloud-Thumbnails als Vorschau-Bilder pro Review-Eintrag auf der Issue-Seite sind seit Welle 6 wieder Teil des Designs — andere Funktion (visueller Anker neben Citation und Abstract-Excerpt), nicht als alleiniger Einstieg.

Kontaktformular mit serverseitiger Verarbeitung ist nicht vorgesehen.

Inkrementelles Build mit Caching ist konzeptionell vorgesehen, wird aber erst implementiert, wenn die Build-Zeit das erforderlich macht.

## 8. Offene Fragen

Drei Punkte sind im Lauf der Implementierung zu klären.

Domain und Hosting-Pfad. Läuft die Site unter einer eigenen Domain oder unter `username.github.io/repo`? Die Antwort prägt das URL-Schema und damit die Stabilitätszusage in N3 und R17.

Auslieferung großer Artefakte. Werden OAI-PMH-Dump und ältere PDF-Versionen über GitHub Pages oder über GitHub Releases distribuiert? Letzteres entlastet das Pages-Repository bei wachsendem Korpus.

Reichweite der Konsolidierung in A2. Ob die einmalige WordPress-zu-TEI-Konsolidierung nur Tags umfasst oder auch redaktionelle Fragmente, die heute in WordPress liegen und in keinem TEI auftauchen, ist redaktionell zu entscheiden.
