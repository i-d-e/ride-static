---
status: befund
updated: 2026-07-10
---

# Publikationsworkflow — Zielbild und Ablösung des Alt-Stacks

Abgleich der Workflow-Skizze der Projektpartnerin (GitHub-Issue, Schritte 0 bis 3) mit dem Stand von ride-static. Evidenzbasis sind drei Recherchen vom 2026-07-10: die Transformations- und Skript-Repos `i-d-e/ride-tech` und `i-d-e/ride-scripts` sowie ein Live-Inventar der eXist-Oberfläche von ride.i-d-e.de. Ergänzt [[redirects-feeds]] (Feeds, OAI-Harvester-Recherche) und [[pipeline]] (Build, Staging).

## Gesamtbefund zum Alt-Stack

Die Live-Site ist für alle menschenlesbaren Seiten WordPress. eXist bedient öffentlich genau eine Funktion, den OAI-PMH-Endpoint `/apis/oai` (Formate `oai_dc`, `oai_marcxml`, `oai_doajxml`; Quelle ist die eXist-App `ride-oai` aus `ride-scripts/oai-api`). Alles andere, was dynamisch wirkt, ist entweder statisches WordPress, extern (TEI/PDF-Downloads über GitHub raw, LimeSurvey, Zenodo, Kriterienkataloge auf i-d-e.de) oder wurde offline aus dem eXist-Korpus generiert und in WordPress-Seiten eingebettet (Charts, Reviewer-Liste, Ressourcen-Liste, Wordclouds). „Weg von eXist" reduziert sich damit auf eine einzige bewusste Entscheidung, die Ablösung des OAI-Endpoints.

## Zielworkflow in der statischen Architektur

### Schritt 0 — Questionnaires aus LimeSurvey

Die Transformationen `limesurvey2tei-se`/`-te` in ride-tech erzeugen aus den LimeSurvey-Antworten je ein TEI-Gerüst mit der `<taxonomy>`/`<category>`/`<num @value>`-Struktur, die unser Parser vollständig liest. Redaktioneller Vorschritt, bleibt unverändert; ride-static hat hier keine Paritätspflicht über das korrekte Konsumieren hinaus.

### Schritt 1 — Testumgebung (Begutachtung vor Freischaltung)

Artikelansicht, Factsheet und PDF erzeugt der Build nativ bei jedem Push; die beiden tei2wp-Transformationen und die vierstufige lokale PDF-Kette (Regex-Vorreinigung, Java-Prozessor, HTML-Fixup, WeasyPrint) entfallen komplett. Die Trigger-Verkabelung für `ride` (Bilder) und `ride-editors` (Drafts) ist umgesetzt (`repository_dispatch`, Sender-Vorlagen in `docs/upstream-workflows/`). Offen ist die Staging-Entscheidung ([[pipeline#Staging — Begutachtungsumgebung (Entscheidung offen)]]), an ihr hängt die zurückgestellte Draft-Render-Mechanik.

### Schritt 2 — Freischaltung

TEI-Datei wandert von `ride-editors` in `issues/{N}/reviews/` dieses Repos (Mechanik offen, naheliegend als Pull Request). Issue-Einrichtung ist `issues/{N}/metadata.yaml`. Übersichtslisten, Charts, Feeds, Sitemap, Suchindex und Korpus-Dump erzeugt der Build automatisch; die eXist-Abfragen hinter den alten Charts-, Reviewer- und Ressourcen-Seiten sind bereits statisch ersetzt. Zwei Teilschritte sind nicht portiert:

- **Wordcloud-Generierung.** `wordclouds.py` (ride-scripts) läuft lokal; die vorhandenen Wordclouds sind einmalig importiert (`static/images/wordclouds/`). Als Build-Schritt portierbar, braucht dafür einen fixierten Seed (die Layout-Bibliothek ist stochastisch) und das Mitführen von Font und Maske.
- **DOI-Metadaten.** `tei2doi` (ride-tech) erzeugt DataCite-Kernel-4-XML, manuell pro Beitrag (Issue-DOI beim jeweils ersten Beitrag eines Issues). Das XML wird an die USB Köln übergeben, die den DOI über ihren DataCite-Client registriert (Client-Symbol `zbmed.unikoeln`, Provider University of Cologne, Präfix 10.18716; verifiziert gegen die DataCite-API). Kein API-Aufruf aus dem RIDE-Workflow, kein eXist beteiligt. Bekannte Schwächen der Transformation, die eine Portierung beheben sollte: naive Namens-Trennung am ersten Leerzeichen, hartkodiertes ROR-Schema für Affiliations, manuell gesetzte Issue-Sprache.

### Schritt 3 — Postpublishing

- **eXist-Upload entfällt** im Zielbild ersatzlos; einzige Restfunktion ist der OAI-Endpoint (unten).
- **DOAJ.** `tei2doaj` (ride-scripts) erzeugt DOAJ-Artikel-XML über den ganzen Korpus (Feldmapping vollständig dokumentiert: Sprache, Publisher, eISSN, DOI, Autoren mit ORCID, Abstract, fullTextUrl, Keywords). Der Übermittlungsweg ist in keinem Repo dokumentiert; kein Uploader-Skript existiert. DOAJ nimmt Metadaten ausschließlich per XML-Upload im Publisher-Dashboard oder per REST-API an, ein Harvesting von Publisher-OAI-Endpoints gibt es nicht (verifiziert 2026-07-10 gegen doaj.org/docs); das `oai_doajxml`-Format des OAI-Endpoints ist demnach ein Convenience-Export zur Erzeugung der Upload-Datei. Die Frage Dashboard-Upload vs. API-Push liegt bei der Redaktion (siehe [[redirects-feeds]]).

## Ablösetabelle

| Legacy-Komponente | Ort | Statischer Ersatz | Status |
|---|---|---|---|
| tei2wp Artikel + Factsheet | ride-tech | Parser + Templates dieses Repos | ersetzt; Paritätslücken unten |
| tei2pdf (vierstufige Kette) | ride-scripts | WeasyPrint-Rendering im Build | ersetzt (nummerierte Absätze, Endnoten, DOI auf Seite 1, Figuren); laufende Fußzeilen der Alt-Kette (Seitenzahl, Zitierzeile) fehlen noch |
| Charts-, Reviewer-, Ressourcen-Abfragen | eXist-Mirrors in ride-tech | `/data/charts/`, `/reviewers/`, `/data/reviewed-resources/` | ersetzt |
| OAI-PMH `/apis/oai` | eXist-App ride-oai | statische OAI-Dumps im Build (nur `oai_dc`; live gibt es auch `oai_marcxml`, `oai_doajxml`) | Entscheidung offen: Endpoint stilllegen oder dünner Dienst; kein Harvester nachweisbar ([[redirects-feeds]]) |
| wordclouds.py | ride-scripts | Anzeige ja, Generierung nicht portiert | Entscheidung offen |
| tei2doi (DataCite XML) | ride-tech | nicht portiert | Entscheidung offen: in den Build oder manuell bei USB Köln |
| tei2doaj (DOAJ XML) | ride-scripts | nicht portiert | Entscheidung offen, Übermittlungsweg ungeklärt |
| limesurvey2tei | ride-tech | bleibt als redaktioneller Vorschritt | kein Ersatz nötig |
| tei2zotero (Zotero-Export) | ride-tech helpers | nicht portiert | optionaler Kanal, Bedarf klären |

## Paritätslücken gegenüber den Alt-Transformationen

Korpus-verifiziert am 2026-07-10:

1. **Amendments-Apparat.** Post-Publication-Korrekturen (`<mod>`/`<del>`/`<add>` mit `<listChange type="post-publication">`) existieren in melville (Issue 3) und sandrart (Issue 1). Die Alt-Ansicht rendert `add` im Text plus einen eigenen Amendments-Abschnitt mit dem Original (`del`) und der Korrektur-Notiz. Unser Parser behandelt `mod`/`del` als Text-Passthrough; in melville erscheinen gestrichener und neuer Text konkateniert im Fließtext, in sandrart wird die in `<mod>` steckende Korrektur-Fußnote als Fließtext flachgeklopft. Echte Lücke, wenn auch auf wenige Reviews begrenzt.
2. **Identifier-Autoritäten.** Der Korpus trägt neben ORCID auch VIAF- und GND-Refs (plus ORCID-IDs ohne URL-Präfix und vereinzelten Datenmüll). Unser `Person`-Modell legt `@ref` undifferenziert im Feld `orcid` ab, das Template beschriftet alles als ORCID. Die Alt-Ansicht wählte das Label nach Autorität.
3. **Factsheet-Hilfetexte.** Die Alt-Factsheets blenden pro Kriterium Definitionen ein, die aus separaten erweiterten Questionnaire-Dateien (ride-tech `tei2wp/questionnaires/`) stammen, eine zweite Datenquelle plus Client-JS. Nicht in unserer Pipeline; klären, ob gewünscht.
4. **Select-Antworten.** Die Alt-Factsheets rendern neben Booleans auch Select-Werte mit Freitext („Other: …" aus `gloss`). `gloss` kommt im Korpus vor; prüfen, ob unser Questionnaire-Parser (liest `num @value`) solche Antworten verliert.
5. **Compound-Reviews.** Reviews mit mehreren rezensierten Ressourcen (collationtools mit drei, carlyle-addams mit zwei) bekamen mehrspaltige Factsheet-Tabellen, Spaltenzuordnung über xml:id-Suffixe. Prüfen, wie unser Factsheet diese Fälle darstellt.
6. **Anker-Kontrakt.** Die Alt-Ansicht generierte Überschriften-Anker `h{n}` (laufende Zählung, nicht aus dem TEI). Unsere Anker kommen aus `@xml:id`; Absatz-Anker sind damit kompatibel, alte Deep-Links auf `#hN` laufen dagegen ins Leere. Relevanz gering (Seiten-Redirects existieren), aber benennen.

Die Citation-Suggestion-Box stammte aus dem WordPress-Theme, nicht aus den Transformationen; unsere R2-Umsetzung ist davon unabhängig und keine Lücke.

## Offene Redaktionsentscheidungen

1. Staging: gilt „passwortgeschützt" wörtlich (Optionen in [[pipeline]])?
2. DOI: DataCite-XML künftig im Build erzeugen oder Übergabe an die USB Köln manuell belassen? Wer führt sie aus?
3. DOAJ: Dashboard-Upload des erzeugten XML oder API-Push aus der Pipeline (dann API-Key als Secret)?
4. OAI-Endpoint: stilllegen (kein Harvester nachweisbar) oder dünner Ersatzdienst?
5. Wordclouds: Generierung in den Build (deterministisch) oder redaktioneller Schritt mit Commit?
6. Freischaltungs-Mechanik: PR-basierter Move von ride-editors, wer führt aus?
7. Bilder: dauerhaft im Sibling-Repo `ride` oder Umzug hierher (Pipeline kann beides)?
8. Hilfetexte im Factsheet und Zotero-Export: Bedarf ja/nein.
