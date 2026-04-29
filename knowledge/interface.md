# Interface — RIDE Static Site

> Visuelles und interaktives Design. Geschwistermodul zu [[requirements]] (was) und [[architecture]] (Datenflüsse, Domänenmodell). Ableitbar in Phase 8 ff. ([[pipeline#Phasenplan]]).

## 1. Zweck

Dieses Dokument beschreibt das visuelle und interaktive Design der statischen RIDE-Site und begründet die Designentscheidungen. Es steht als drittes Wissensdokument neben [[requirements]] (was) und [[architecture]] (Datenflüsse) und behandelt, wie die Site gesehen und bedient wird. Ziel ist keine vollständige Designsystem-Spezifikation, sondern eine knappe, begründete Festlegung, aus der die Templates ab [[pipeline#Phasenplan|Phase 8]] direkt ableitbar sind.

## 2. Designhaltung

Vier Prinzipien tragen das Design.

**Strukturelle Strenge vor visueller Geste.** Die akademische Qualität der Rezensionen liegt in ihrer Apparatik, nicht in ihrer Optik. Das UI macht die Apparatik sichtbar und gibt ihr formales Gewicht, ohne ornamentale Mittel.

**Lesbarkeit als primäre Funktion.** Eine RIDE-Rezension wird gelesen, oft länger als 20 Minuten. Schriftwahl, Größe, Zeilenhöhe und Spaltenbreite werden auf Lesedauer ausgelegt, nicht auf Erstwirkung.

**Apparate visuell differenziert.** References, Figures, Notes und Meta sind verschiedene Funktionen und brauchen erkennbar verschiedene Formen.

**Designsparsamkeit, nicht Designarmut.** Wenig Farbe, wenig Variation, klare Hierarchien, aber gepflegt. Sparsamkeit ist eine Entscheidung, kein Ausweg.

## 3. Bewertung des heutigen UI

Die heutige Site funktioniert und bewahrt die akademische Strenge der Inhalte. Sie hat aber sechs konkrete Schwächen, die in der Neufassung adressiert werden.

**Apparate undifferenziert.** References, Figures und Notes erscheinen im gleichen kleinen grauen Listenstil. Der Lesefluss zwischen ihnen ist mühsam, die Funktion jeder Liste verschwimmt.

**Sidebar überladen.** Drei Boxen (Social, TOC, Meta) plus eine Citation-Suggestion konkurrieren um Aufmerksamkeit. Auf Issue- und Rezensionsseiten werden alle drei mitgeführt, obwohl nur eine sinnvoll ist.

**Wordcloud-Slider auf der Startseite.** Wordclouds zeigen Worthäufigkeit, nicht Bedeutung. Die symbolische Umrissform erschwert die Lesbarkeit zusätzlich. Eine echte Inhaltsvorschau ist informativer.

**Suche zu klein.** Das Suchfeld liegt rechts in der Navigationsleiste, ist aber visuell schwach. Bei einem Korpus, das primär durchsucht wird, braucht die Suche prominente Eingabe und sichtbaren Submit-Button — die Position rechts in der Navbar ist richtig, die Größe nicht.

**Bibliografie und Reviewer verschmolzen.** Im Kopf der Rezension stehen die bibliografische Angabe der besprochenen Edition und die Reviewer-Information in einem Fließsatz. Beide haben verschiedene semantische Funktionen und sollten visuell getrennt erscheinen.

**Numbered paragraphs unsichtbar als Zitieranker.** Die Absatznummern sind reine Sprunglinks. Dass jeder Absatz zitierfähig ist, erschließt sich Leser-Innen nicht.

## 4. Layout-Architektur

Das Grundraster hat eine maximale Breite von 1150 Pixeln, mit einer 720 Pixel breiten Inhaltsspalte und einer 280 Pixel breiten Sidebar, dazwischen 60 Pixel Lücke. Die Breite hält Zeilen unter etwa 80 Zeichen, was für eine Sans-Serif-Lesefläche (Abschnitt 7) ergonomisch ist; die Sidebar bekommt Platz für Citation Suggestion und Meta ohne Umbruch-Akrobatik.

Über dem Inhaltsraster steht ein zweiteiliger globaler Header. Die obere Zeile ist eine **Brand-Zeile** mit zwei festen Bestandteilen: links die Marke RIDE als Wortmarke (28 Pixel, Bold) plus die **Tagline** „A Review Journal for Scholarly Digital Editions and Resources" als zweite Zeile direkt darunter, rechts das **kombinierte IDE/RIDE-Logo** als Bildmarke (PNG unter `static/images/logo-ide.png`, Höhe maximal 60 Pixel) als Link auf [https://www.i-d-e.de](https://www.i-d-e.de). Das Logo trägt den Alt-Text „IDE — Institute for Documentology and Scholarly Editing", weil es semantisch das herausgebende Institut markiert; die Wortmarke RIDE links bildet die Marke des Journals selbst ab. Die **Navigationsleiste** liegt unmittelbar darunter als eigenes dunkelgraues Band (`#333`, weiße Links, mockup-aligned) mit fünf Top-Level-Einträgen (siehe unten); ein dediziertes **Suchfeld** liegt rechts in derselben Zeile (Phase 11 — Pagefind-UI).

Die globale Navigation hat fünf Top-Level-Einträge:

| Top-Level | Untermenüs |
|---|---|
| **About** | Editorial · Publishing Policy · Ethical Code · Team · Peer Reviewers |
| **Issues** | All Issues plus die letzten N Issues als Schnellzugriff (Reihenfolge in `config/navigation.yaml`) |
| **Data** | Overview / Download / API · Questionnaires · Charts · Tags · Reviewed Resources |
| **Reviewers** | Call for Reviews · Submitting a Review · Projects for Review · RIDE Award 2017–2020 · List of Reviewers |
| **Reviewing Criteria** | Direkter Link, kein Dropdown |

Die Dropdowns werden mit nativen `<details>`-Elementen umgesetzt (kein JavaScript-Framework, keine Bootstrap-Komponente); CSS gibt ihnen die Anmutung einer klassischen Hover-/Click-Navigation. Die Liste der Untermenüs ist in `config/navigation.yaml` konfigurierbar, sodass redaktionelle Erweiterungen ohne Template-Änderung möglich sind.

Sechs Seitentypen folgen dem Inhaltsraster unter dem Header. Die **Startseite** zeigt drei Inhaltsblöcke ohne Slider — einen knappen Hero-Header mit Titel und Kennzahlen, das aktuelle Issue prominent als zweite Sektion mit Beitragskarten, danach einen **redaktionellen Widget-Bereich** als drei-spaltiges Grid (`Welcome` · `News` · `Call for Reviews` in einer Reihe, `Open Data` · `Follow us` in der zweiten Reihe). Die Widgets liegen als Markdown unter `content/home/<NN-slug>.md` und werden von `src.render.editorial.discover_home_widgets` geladen; Ordnung folgt dem numerischen Präfix. Redaktion ändert Inhalt ohne Template-Anfassen. Die **Issue-Übersicht** ist eine reine Liste der Issues, sortiert nach Erscheinungsdatum, mit Rolling-Issue-Markern. Die **Issue-Ansicht** trägt Issue-Metadaten oben und Beitragskarten mit Abstract-Ausschnitten. Die **Rezensionsansicht** ist die Hauptansicht (Abschnitt 5). **Aggregationsseiten** (Tags, Reviewer, Reviewed Resources, Data) tragen eine Sortier- und Filterleiste oben und eine Liste oder Tabelle als Inhalt. **Editorialseiten** (About, Impressum, Reviewing Criteria, plus die acht weiteren editorialen Pages aus den About- und Reviewers-Untermenüs) verwenden nur die Inhaltsspalte ohne Sidebar.

## 5. Rezensionsansicht im Detail

Der **Kopfbereich** trägt drei Bestandteile in dieser Reihenfolge. Der **Titel** als prominentes Heading-Element. Direkt darunter die **bibliografische Angabe der besprochenen Edition** als eigener Absatz: Werktitel in Italic, Editorenliste mit `(ed.)`, Erscheinungsjahr, URL und Last-Accessed-Datum bei Online-Quellen. Im selben Absatz nahtlos angeschlossen die **Reviewer-Information** in der Form „Reviewed by ⟨ORCID-Icon⟩ Vorname Nachname (Affiliation), email@example.org." — Inline-Prosa statt strukturierter Liste, damit die bibliografische und die Reviewer-Information zusammen als ein zusammenhängender Eingangssatz lesbar sind. Strukturelle Auszeichnung (BEM-Klassen, ORCID-Link, mailto-obfuskiert) bleibt darunter erhalten.

Das **Abstract** erscheint als leicht hinterlegter Block mit einem eigenen Heading „Abstract", das den Block sowohl visuell als auch semantisch (für Screenreader) öffnet. Begründung der Heading-Wiederholung: das Heading dient hier nicht der Hierarchie-Information, sondern als deutlicher Funktions-Anker — Leser:innen erkennen den Abstract sofort, Screenreader können in Heading-Listen navigieren.

Im **Hauptteil** tragen Top-Level-Sektionen h3-Headings, Sub-Sektionen h4 (der Review-Titel ist h2, die globale Tagline-Zeile h1). Numbered paragraphs zeigen die Absatznummer dezent am linken Rand der Inhaltsspalte, außerhalb des Lesefließtexts. Hover über die Nummer aktiviert eine Copy-Link-Aktion. Eingebettete Bilder erscheinen mit Caption darunter, Caption-Text in kleinerer Schrift und gedämpfter Farbe. Inline-Verweise auf `Fig. N` zeigen beim Hover eine kleine Vorschau (Tooltip mit Thumbnail und Caption-Beginn).

Der **Apparate-Block** (References, Figures, Notes) wird als drei klar getrennte Sub-Blöcke unter einer gemeinsamen Trennlinie gesetzt, mit eigenem h3-Header pro Sub-Block (Abschnitt 6).

**Lizenz und Provenance** stehen am Seitenende in einer dezenten Footer-Zeile innerhalb der Inhaltsspalte. Lizenz, Build-Datum, optional Commit-Hash. Begründung ist [[requirements#N6 Lizenzklarheit pro Artefakt]]. Die DOI selbst lebt im Sidebar (siehe nächster Absatz), nicht im Footer — sie ist Identifier, nicht Provenance-Marker.

Die **Sidebar** trägt vier Boxen in dieser Reihenfolge:

1. **Table of Contents** — immer, mit den Section-Headings als Sprung-Anker.
2. **Meta** — Published-Datum, DOI als Plaintext-Zeile, ein Link „Factsheet of this project" auf den separat verlinkten Factsheet-Apparat, ein Download-Link „XML of this review, including formal evaluation data", ein Download-Link „PDF of this review article", als letzte Zeile das Lizenz-Kürzel (z.B. „CC BY 4.0", abgeleitet aus der Lizenz-URL).
3. **Citation Suggestion** — der Zitiervorschlag im Format `Surname, Forename (Year). "Title." RIDE {Issue}, ed. by {Editors}. DOI: {DOI}. Accessed: {Date}.`, gefolgt von einer italic-Mikrokopie „You can use the running numbers on the left side to refer to a specific paragraph." Direkt darunter die Kopier-Buttons für BibTeX und CSL-JSON.
4. **Tags** — alphabetisch sortierte Liste der Keywords als Inline-Tag-Pillen, jeweils mit Link zur Tag-Detailseite.

Share-Buttons entfallen zugunsten von Open-Graph-Metadaten und der Copy-Link-Aktion auf Absatzebene. Begründung ist die geringe tatsächliche Nutzung von Share-Buttons in akademischen Kontexten.

## 6. Apparate als parallele Blöcke

Die heutige sequenzielle Anordnung — References, Figures, Notes als drei aufeinanderfolgende Listen in identischem Stil — wird ersetzt durch ein paralleles Layout. Die drei Apparate stehen unter einer gemeinsamen Trennlinie, jeder mit eigenem Sub-Header, in einem dreispaltigen Block auf Desktop und gestapelt auf Mobile.

Die Begründung ist funktional. References dienen dem Beleg, Figures dem visuellen Apparat, Notes dem Kommentar. Ihre parallele Setzung macht ihre parallele Funktion sichtbar und erlaubt Leser-Innen, gezielt auf den jeweiligen Apparat zuzugreifen, statt sich durch alle drei zu lesen.

Bidirektionale Verlinkung ist in allen drei Apparaten Pflicht. Jede Figure-Nummer in der Liste verlinkt zurück zur Bildposition im Text, jede Footnote zur Aufrufstelle, jede Reference auf die Inline-Erwähnung (sofern eindeutig). Das ist heute uneinheitlich und wird normalisiert.

References tragen drei Varianten je nach Quellen-Status. Direkter Link auf eine lebendige Quelle. DOI-Link, wenn vorhanden. Webarchiv-Link mit sichtbarem Hinweis "via Wayback Machine, archiviert am ..." bei toten Quellen. Letzteres ist heute redaktionelle Praxis, wird aber im Datenmodell als formale Variante markiert. Die Wayback-Erkennung selbst landet erst in Phase 13 (Build-Validation), nicht in Phase 7.

Cross-References im Fließtext werden seit Phase 7 nach `Reference.bucket` ∈ `{local, criteria, external, orphan}` getypt. Templates dispatchen über `config/element-mapping.yaml` `inlines.Reference.by_bucket` auf vier CSS-Klassen (`ride-ref--local`, `ride-ref--criteria`, `ride-ref--external`, `ride-ref--orphan`). Local-Refs zeigen Tooltip-Vorschau (Footnote-Text, Figure-Thumbnail), criteria-Refs öffnen das externe Kriteriendokument am Anker, external-Refs sind reine Out-Links, orphan-Refs werden als grauer Plain-Text mit `aria-disabled` gerendert.

## 7. Typografie und Lesbarkeit

Schriftwahl ist **eine** seriöse Sans-Serif für die gesamte Site — Body, UI, Headings. Source Sans 3 ist die primäre Wahl, lokal als WOFF2 unter `static/fonts/` ausgeliefert, nicht über externes Font-CDN. Begründung der Single-Family-Entscheidung: einheitliche moderne Anmutung, keine sichtbare Font-Übergangs-Spannung zwischen UI und Lesetext, Reduktion der Familien-Anzahl auf eine Open-Source-Familie mit voller Glyph-Abdeckung für Deutsch, Englisch und romanische Inline-Zitate. Die frühere Doppelschrift-Spec (Serif für Body, Sans für UI) ist mit dem Mockup-Vorbild aufgegeben worden — die Praxis zeigt, dass eine gut gesetzte Sans bei 17–18 Pixel und 1.6 Zeilenhöhe auch für längere Lesedauern tragfähig ist. Mono bleibt für Code (`<code>`, `<pre>`) als zweite Familie.

Größen sind 18 Pixel für Lesefließtext, 22 Pixel für h3 (Top-Level-Section), 28 Pixel für h2 (Rezensionstitel), 14 Pixel für Sidebar, Apparate und Footer, 12 Pixel als harte Untergrenze auch in Footnoten. Die globale Tagline-Zeile als h1 ist visuell klein gesetzt (etwa 16 Pixel, gedämpft), weil sie als Site-Brand fungiert und nicht mit dem Review-Titel konkurrieren soll. Zeilenhöhe 1.6 für Lesetext, 1.4 für UI.

Hierarchie entsteht primär durch Größe und Weight (Regular 400, Medium 500), nicht durch Farbe oder Hintergrund. Die Farbpalette ist seit Welle 4 verbindlich gesetzt und mockup-aligned:

| Token | Wert | Verwendung |
|---|---|---|
| `--ride-fg-primary` | `#212529` | Body-Text, Headings |
| `--ride-fg-secondary` | `#4b5560` | Sidebar-Labels, Tagline, Untertitel |
| `--ride-fg-tertiary` | `#7a8694` | Meta-Zeilen, Trennzeichen |
| `--ride-bg` | `#ffffff` | Hauptfläche |
| `--ride-bg-muted` | `#f4f6f8` | Abstract-Block, Code, Tag-Pillen |
| `--ride-rule` | `#d4d9df` | Haarlinien, Rule-Trenner |
| `--ride-accent` | `#0d6efd` | Links, Querverweise, ORCID-Badges |
| `--ride-accent-hover` | `#0a58ca` | Link-Hover-State |
| `--ride-navbar-bg` | `#333333` | Navigationsleisten-Band (mockup line 12) |
| `--ride-navbar-fg` | `#ffffff` | Nav-Links |

Branding-Refresh (Logo, eigene Farbidentität) bleibt als spätere Iteration zurückgestellt. Die Tokens leben in [`static/css/ride.css`](../static/css/ride.css) und sind die einzige Farbquelle — Komponenten referenzieren ausschließlich Variablen.

## 8. Mehrsprachigkeit

Rezensionen sind auf Englisch oder Deutsch verfasst, mit häufigen Inline-Zitaten in weiteren Sprachen (Italienisch, Französisch, Spanisch). Das `lang`-Attribut wird auf jeder Ebene korrekt gesetzt, vom `html`-Element für die Seitensprache über die Section-Ebene bei mehrsprachigen Beiträgen bis zum Inline-Span für einzelne fremdsprachige Zitate. Begründung ist sowohl Barrierefreiheit (Screenreader sprechen das Zitat in der richtigen Sprache aus) als auch Suchmaschinen-Korrektheit.

Schriftwahl muss alle relevanten Glyphen sauber tragen, einschließlich Diakritika und korrekter Anführungszeichen pro Sprache. Das schließt einige weitverbreitete Web-Defaults aus.

## 9. Barrierefreiheit

Mindestziel ist WCAG 2.2 AA gemäß [[requirements#N5 Barrierefreiheit]]. Vier Schwerpunkte sind operativ.

Tastaturnavigation reicht bis in jede Sidebar-Box und jeden Apparat-Sub-Block. Fokus-Indikatoren sind sichtbar mit ausreichendem Kontrast.

Alt-Texte für alle Figures werden aus dem TEI-`figDesc`-Element bezogen. Fehlt `figDesc`, wird `Figure N` als Fallback gesetzt und eine Build-Warnung erzeugt, sodass redaktionelle Lücken sichtbar werden.

Tabellen-Header verwenden `th`-Elemente mit `scope`-Attribut, nicht nur visuelle Auszeichnung.

Sprach-Annotation wie in Abschnitt 8.

Kein Inhalt ist ausschließlich über Hover erreichbar. Hover zeigt zusätzliche Hilfen, nie kritische Information.

## 10. Responsive

Drei Breakpoints. Unter 720 Pixel klappt die Sidebar unter den Inhalt und reduziert sich auf das Wesentliche — TOC als ausklappbares Element, Meta knapp, Cite ausklappbar. Zwischen 720 und 1080 Pixel zwei Spalten mit voller Sidebar. Über 1080 Pixel zentriertes Raster mit symmetrischem Außenraum.

Der Apparate-Block stapelt unter 720 Pixel auf eine Spalte, behält aber die visuelle Trennung der drei Sub-Blöcke. Eingebettete Bilder werden auf voller Inhaltsbreite gesetzt. Vorschau-Tooltips entfallen auf Touch-Geräten zugunsten direkter Sprünge zur Figures-Liste.

## 11. Mikrointeraktionen

Vier Interaktionen sind designentscheidend.

**Copy-Link auf Absätze.** Hover über die Absatznummer (oder Tap auf Mobile) zeigt eine Aktion zum Kopieren des Links. Der Link enthält die Rezensions-URL plus Anker auf die `xml:id` des Absatzes. Begründung ist, dass die Zitierfähigkeit auf Absatzebene heute zwar technisch existiert, aber für Leser-Innen nicht entdeckbar ist.

**Tooltip-Vorschau für Inline-Cross-References.** Hover über `Fig. N`, Footnote-Anker oder K-Verweise zeigt eine kleine Vorschau (Bild-Thumbnail, Footnote-Text, Kriteriumstitel). Das spart Sprünge im Text.

**Suche mit Kontextausschnitt.** Pagefind liefert Trefferliste mit Kontextzeile. Klick führt direkt zur Stelle in der Rezension.

**Cite-Aktion.** Kopier-Button für BibTeX und CSL-JSON, mit visuellem Feedback "kopiert" für 1.5 Sekunden.

Alle anderen Interaktionen sind Browser-Standard. Animationen jenseits dezenter Hover-Übergänge entfallen.

## 12. Konsequenzen für die Build-Phasen

**[[pipeline#Phasenplan|Phase 8]]** erzeugt ein Template pro semantische Einheit, plus ein Seitentyp-Template pro Seitentyp aus Abschnitt 4. Templates erhalten ausschließlich Domänenobjekte, kein XML, gemäß [[requirements#N1 Read-only-Pipeline]] und der Architektur-Designentscheidung „Domain model first" in [[architecture#Renderers]].

Das CSS ist ein einzelnes Stylesheet von etwa 600 bis 800 Zeilen, ohne Build-Schritt und ohne Preprocessor. Begründung ist [[requirements#N8 Übergabefähigkeit]] — wer das CSS später anpassen will, soll keine Toolchain installieren müssen.

JavaScript ist auf vier kleine Module beschränkt (Copy-Link, Tooltip-Vorschau, Pagefind-Integration, Cite-Kopieraktion), ohne Framework und ohne Bundling-Pipeline. Das hält das Build-Budget überschaubar und passt in den Single-Workflow-Build aus [[requirements#N10 Single-Workflow-Build]]. Die Dropdown-Navigation aus Abschnitt 4 ist bewusst kein eigenes JS-Modul — sie wird über `<details>` plus CSS realisiert, weil ein Dropdown-Mechanismus nativ in der Plattform existiert.

Die Pagefind-Integration aus Abschnitt 11 wird in [[pipeline#Phasenplan|Phase 11]] ausgeführt, die Cite-Kopieraktion in [[pipeline#Phasenplan|Phase 8]], die Mehrsprachigkeit aus Abschnitt 8 als Querschnittsanforderung über alle Render-Phasen.

## 13. Bewusst nicht behandelt

Ein vollständiges Designsystem mit Tokens, Themes und Komponenten-Bibliothek ist eigene Iteration. Branding-Refresh (Logo, Farbidentität) ebenfalls. Dark-Mode ist gewünscht, aber nicht für die erste Iteration. Komplexere Visualisierungen für die Data-Seite (interaktive Filter, kombinierte Charts) werden in einer eigenen Iteration auf Basis der dann vorliegenden Statisch-Charts beurteilt.
