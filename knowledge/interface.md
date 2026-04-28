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

**Sidebar überladen.** Drei Boxen (Social, TOC, Meta) plus eine Citation-Suggestion konkurrieren um Aufmerksamkeit. Auf Heft- und Issue-Seiten werden alle drei mitgeführt, obwohl nur eine sinnvoll ist.

**Wordcloud-Slider auf der Startseite.** Wordclouds zeigen Worthäufigkeit, nicht Bedeutung. Die symbolische Umrissform erschwert die Lesbarkeit zusätzlich. Eine echte Inhaltsvorschau ist informativer.

**Suche marginalisiert.** Das Suchfeld liegt klein rechts in der Navigationsleiste. Bei einem Korpus, das primär durchsucht wird, ist das eine zu schwache Position.

**Bibliografie und Reviewer verschmolzen.** Im Kopf der Rezension stehen die bibliografische Angabe der besprochenen Edition und die Reviewer-Information in einem Fließsatz. Beide haben verschiedene semantische Funktionen und sollten visuell getrennt erscheinen.

**Numbered paragraphs unsichtbar als Zitieranker.** Die Absatznummern sind reine Sprunglinks. Dass jeder Absatz zitierfähig ist, erschließt sich Leser-Innen nicht.

## 4. Layout-Architektur

Das Grundraster hat eine maximale Breite von 1080 Pixeln, mit einer 680 Pixel breiten Inhaltsspalte und einer 220 Pixel breiten Sidebar, dazwischen 60 Pixel Lücke. Diese Breite hält Zeilen unter etwa 75 Zeichen, was für Fließtext ergonomisch ist.

Sechs Seitentypen folgen diesem Raster. Die **Startseite** zeigt drei Inhaltsblöcke ohne Slider — das aktuelle Heft prominent als erste Sektion, eine Auswahl ausgewählter Rezensionen mit Titel und Kurzbeschreibung darunter, News und Call for Reviews kombiniert in der Sidebar. Die **Heftübersicht** ist eine reine Liste der Hefte, sortiert nach Erscheinungsdatum, mit Rolling-Issue-Markern. Die **Heftansicht** trägt Heftmetadaten oben und Beitragskarten mit Abstract-Ausschnitten. Die **Rezensionsansicht** ist die Hauptansicht (Abschnitt 5). **Aggregationsseiten** (Tags, Reviewer, Reviewed Resources, Data) tragen eine Sortier- und Filterleiste oben und eine Liste oder Tabelle als Inhalt. **Editorialseiten** (About, Impressum, Reviewing Criteria) verwenden nur die Inhaltsspalte ohne Sidebar.

Suche bekommt einen eigenen sichtbaren Slot zwischen Header und Inhalt — eine schmale Leiste mit Sucheingabe und globalem Tag-Zugang, auf jeder Seite präsent. Begründung ist die primäre Nutzungsweise eines Korpus dieser Größe, das überwiegend gezielt befragt und nicht linear durchgeblättert wird.

## 5. Rezensionsansicht im Detail

Der **Kopfbereich** trennt drei Funktionen visuell. Titel als h1. Bibliografische Angabe der besprochenen Edition als eigener Block, einschließlich Last-Accessed-Datum bei Online-Quellen. Reviewer-Information als getrennter Block mit ORCID-Icon, Affiliation und Email. Die heutige Verschmelzung beider Blöcke geht damit aufgelöst.

Das **Abstract** erscheint als leicht hinterlegter Block ohne Heading-Wiederholung, da der Block selbst seine Funktion trägt.

Im **Hauptteil** tragen Sektionen h2-Headings; numbered paragraphs zeigen die Absatznummer dezent am linken Rand der Inhaltsspalte, also außerhalb des Lesefließtexts. Hover über die Nummer aktiviert eine Copy-Link-Aktion. Eingebettete Bilder erscheinen mit Caption darunter, Caption-Text in kleinerer Schrift und gedämpfter Farbe. Inline-Verweise auf `Fig. N` zeigen beim Hover eine kleine Vorschau (Tooltip mit Thumbnail und Caption-Beginn).

Der **Apparate-Block** (References, Figures, Notes) wird als drei klar getrennte Sub-Blöcke unter einer gemeinsamen Trennlinie gesetzt, mit eigenem h3-Header pro Sub-Block (Abschnitt 6).

**Lizenz und Provenance** stehen am Seitenende in einer dezenten Footer-Zeile innerhalb der Inhaltsspalte. Lizenz, Build-Datum, DOI, optional Commit-Hash. Begründung ist [[requirements#N6 Lizenzklarheit pro Artefakt]].

Die **Sidebar** ist auf drei Blöcke reduziert. Table of Contents (immer). Meta mit Published, DOI, Factsheet-Link und Download-Aktionen für TEI-XML und PDF. Cite mit Suggestion und Kopier-Buttons für BibTeX und CSL-JSON. Share-Buttons entfallen zugunsten von Open-Graph-Metadaten und einer Copy-Link-Aktion in der Meta-Box. Begründung ist die geringe tatsächliche Nutzung von Share-Buttons in akademischen Kontexten.

## 6. Apparate als parallele Blöcke

Die heutige sequenzielle Anordnung — References, Figures, Notes als drei aufeinanderfolgende Listen in identischem Stil — wird ersetzt durch ein paralleles Layout. Die drei Apparate stehen unter einer gemeinsamen Trennlinie, jeder mit eigenem Sub-Header, in einem dreispaltigen Block auf Desktop und gestapelt auf Mobile.

Die Begründung ist funktional. References dienen dem Beleg, Figures dem visuellen Apparat, Notes dem Kommentar. Ihre parallele Setzung macht ihre parallele Funktion sichtbar und erlaubt Leser-Innen, gezielt auf den jeweiligen Apparat zuzugreifen, statt sich durch alle drei zu lesen.

Bidirektionale Verlinkung ist in allen drei Apparaten Pflicht. Jede Figure-Nummer in der Liste verlinkt zurück zur Bildposition im Text, jede Footnote zur Aufrufstelle, jede Reference auf die Inline-Erwähnung (sofern eindeutig). Das ist heute uneinheitlich und wird normalisiert.

References tragen drei Varianten je nach Quellen-Status. Direkter Link auf eine lebendige Quelle. DOI-Link, wenn vorhanden. Webarchiv-Link mit sichtbarem Hinweis "via Wayback Machine, archiviert am ..." bei toten Quellen. Letzteres ist heute redaktionelle Praxis, wird aber im Datenmodell als formale Variante markiert. Die Wayback-Erkennung selbst landet erst in Phase 13 (Build-Validation), nicht in Phase 7.

Cross-References im Fließtext werden seit Phase 7 nach `Reference.bucket` ∈ `{local, criteria, external, orphan}` getypt. Templates dispatchen über `config/element-mapping.yaml` `inlines.Reference.by_bucket` auf vier CSS-Klassen (`ride-ref--local`, `ride-ref--criteria`, `ride-ref--external`, `ride-ref--orphan`). Local-Refs zeigen Tooltip-Vorschau (Footnote-Text, Figure-Thumbnail), criteria-Refs öffnen das externe Kriteriendokument am Anker, external-Refs sind reine Out-Links, orphan-Refs werden als grauer Plain-Text mit `aria-disabled` gerendert.

## 7. Typografie und Lesbarkeit

Schriftwahl ist eine seriöse Sans-Serif für UI und Headings, eine Serif für den Lesefließtext der Rezensionen. Die engere Auswahl umfasst Inter oder Source Sans für UI und Source Serif oder Crimson Pro für Lesetext. Beide sind Open-Source und werden lokal als WOFF2 ausgeliefert, nicht über externe CDN. Begründung der Doppelschrift ist die längere Lesedauer von Rezensionen — Serif-Schriften reduzieren Ermüdung in Fließtext, Sans-Serif unterstützt schnelle Orientierung in UI-Elementen.

Größen sind 17 Pixel für Lesefließtext, 22 Pixel für h2 (Section), 28 Pixel für h1 (Rezensionstitel), 14 Pixel für Sidebar und Apparate. Zeilenhöhe 1.6 für Lesetext, 1.4 für UI. Kein Text unter 12 Pixel, auch nicht in Footnoten.

Hierarchie entsteht primär durch Größe und Weight (Regular 400, Medium 500), nicht durch Farbe oder Hintergrund. Akzentfarbe ist ein einziges gedämpftes Blau für Links, Anker und Querverweise. Schwarz und drei Grauwerte (primary, secondary, tertiary) decken den Rest ab.

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

JavaScript ist auf vier kleine Module beschränkt (Copy-Link, Tooltip-Vorschau, Pagefind-Integration, Cite-Kopieraktion), ohne Framework und ohne Bundling-Pipeline. Das hält das Build-Budget überschaubar und passt in den Single-Workflow-Build aus [[requirements#N10 Single-Workflow-Build]].

Die Pagefind-Integration aus Abschnitt 11 wird in [[pipeline#Phasenplan|Phase 11]] ausgeführt, die Cite-Kopieraktion in [[pipeline#Phasenplan|Phase 8]], die Mehrsprachigkeit aus Abschnitt 8 als Querschnittsanforderung über alle Render-Phasen.

## 13. Bewusst nicht behandelt

Ein vollständiges Designsystem mit Tokens, Themes und Komponenten-Bibliothek ist eigene Iteration. Branding-Refresh (Logo, Farbidentität) ebenfalls. Dark-Mode ist gewünscht, aber nicht für die erste Iteration. Komplexere Visualisierungen für die Data-Seite (interaktive Filter, kombinierte Charts) werden in einer eigenen Iteration auf Basis der dann vorliegenden Statisch-Charts beurteilt.
