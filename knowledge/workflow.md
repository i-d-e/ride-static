---
status: befund
updated: 2026-07-17
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

TEI-Datei wandert von `ride-editors` in `issues/{N}/reviews/` dieses Repos (Mechanik offen, naheliegend als Pull Request). Issue-Einrichtung ist `issues/{N}/metadata.yaml`. Übersichtslisten, Charts, Feeds, Sitemap, Suchindex und Korpus-Dump erzeugt der Build automatisch; die eXist-Abfragen hinter den alten Charts-, Reviewer- und Ressourcen-Seiten sind bereits statisch ersetzt.

- **Wordcloud-Generierung.** Portiert als `scripts/wordclouds.py` (fixierter Seed, byte-reproduzierbar; Stopwörter und Maske gebündelt). Läuft als Maintenance-Schritt bei Freischaltung eines neuen Beitrags, das PNG wird nach `static/images/wordclouds/` committet; dokumentiert in CONTRIBUTING.
- **DOI-Metadaten.** `tei2doi` (ride-tech) erzeugt DataCite-Kernel-4-XML, manuell pro Beitrag (Issue-DOI beim jeweils ersten Beitrag eines Issues). Das XML wird an die USB Köln übergeben, die den DOI über ihren DataCite-Client registriert (Client-Symbol `zbmed.unikoeln`, Provider University of Cologne, Präfix 10.18716; verifiziert gegen die DataCite-API). Kein API-Aufruf aus dem RIDE-Workflow, kein eXist beteiligt. Bekannte Schwächen der Transformation, die eine Portierung beheben sollte: naive Namens-Trennung am ersten Leerzeichen, hartkodiertes ROR-Schema für Affiliations, manuell gesetzte Issue-Sprache.

### Schritt 3 — Postpublishing

- **eXist-Upload entfällt** im Zielbild ersatzlos; einzige Restfunktion ist der OAI-Endpoint (unten).
- **DOAJ.** `tei2doaj` (ride-scripts) erzeugt DOAJ-Artikel-XML über den ganzen Korpus (Feldmapping vollständig dokumentiert: Sprache, Publisher, eISSN, DOI, Autoren mit ORCID, Abstract, fullTextUrl, Keywords). Der Übermittlungsweg ist in keinem Repo dokumentiert; kein Uploader-Skript existiert. DOAJ nimmt Metadaten ausschließlich per XML-Upload im Publisher-Dashboard oder per REST-API an, ein Harvesting von Publisher-OAI-Endpoints gibt es nicht (verifiziert 2026-07-10 gegen doaj.org/docs); das `oai_doajxml`-Format des OAI-Endpoints ist demnach ein Convenience-Export zur Erzeugung der Upload-Datei. Die Frage Dashboard-Upload vs. API-Push liegt bei der Redaktion (siehe [[redirects-feeds]]).

## Ablösetabelle

| Legacy-Komponente | Ort | Statischer Ersatz | Status |
|---|---|---|---|
| tei2wp Artikel + Factsheet | ride-tech | Parser + Templates dieses Repos | ersetzt; die früheren Paritätslücken sind geschlossen (unten) |
| tei2pdf (vierstufige Kette) | ride-scripts | WeasyPrint-Rendering im Build | ersetzt (nummerierte Absätze, Endnoten, DOI auf Seite 1, Figuren, laufende Fußzeilen via `@page`-Margin-Boxes) |
| Charts-, Reviewer-, Ressourcen-Abfragen | eXist-Mirrors in ride-tech | `/data/charts/`, `/reviewers/`, `/data/reviewed-resources/` | ersetzt |
| OAI-PMH `/apis/oai` | eXist-App ride-oai | statische OAI-Dumps im Build (nur `oai_dc`; live gibt es auch `oai_marcxml`, `oai_doajxml`) | stillgelegt mit Snapshot-Export (entschieden 2026-07-17, siehe [[oai-pmh-statisch]]); die Abschaltung des alten eXist-Endpoints folgt nach der DOAJ-Klärung |
| wordclouds.py | ride-scripts | `scripts/wordclouds.py`, deterministisch (fixierter Seed), Ergebnis wird committet | ersetzt als Maintenance-Skript |
| tei2doi (DataCite XML) | ride-tech | nicht portiert | Entscheidung offen: in den Build oder manuell bei USB Köln |
| tei2doaj (DOAJ XML) | ride-scripts | nicht portiert | Entscheidung offen: Dashboard-Upload oder API-Push |
| limesurvey2tei | ride-tech | bleibt als redaktioneller Vorschritt | kein Ersatz nötig |
| tei2zotero (Zotero-Export) | ride-tech helpers | `/data/ride-corpus.bib` + `/data/ride-corpus.csl.json` aus den Zitations-Formatierern | ersetzt (Zotero importiert beide Formate; JSON-LD je Seite zusätzlich) |

## Paritätslücken gegenüber den Alt-Transformationen — geschlossen am 2026-07-10

Korpus-verifiziert erhoben und noch am selben Tag umgesetzt:

1. **Amendments-Apparat** (war: `mod`/`del` als Text-Passthrough, melville konkatenierte gestrichenen und neuen Text, sandrarts Korrektur-Fußnote lag im Fließtext). Jetzt strukturierter `Amendment`-Inline-Typ, viertes Apparate-Panel mit bidirektionalen Links, Datum aus `revisionDesc` über `@change` gejoint; Amendment-Notizen bleiben aus dem Fußnoten-Apparat draußen.
2. **Identifier-Autoritäten** (war: alles als ORCID beschriftet). Jetzt `Person.identifier_url` + `identifier_authority` (orcid/gnd/viaf), nackte ORCID-IDs normalisiert zur kanonischen URL, Datenmüll degradiert zu keinem Link; JSON-LD emittiert VIAF/GND-URIs, die vorher verworfen wurden.
3. **Factsheet-Hilfetexte** (war: nur in den erweiterten Questionnaire-Dateien in ride-tech). Jetzt editierbares Markdown unter `content/factsheet-help/{se,tc,te}.md` (ein `## {Kriterium-ID}`-Abschnitt pro Definition), gerendert als natives `<details>` je Kriterium, im Druck ausgeblendet.
4. **Select-Antworten** (war: Freitext-`gloss` ging verloren). Jetzt trägt `QuestionnaireAnswer.gloss` den Freitext und die Antwort rendert als „Other: doc, rtf, epub"-Muster.
5. **Compound-Reviews** (war: ungeprüft). Jede Questionnaire-Block bekommt eine Überschrift mit dem Titel seiner Ressource (Zuordnung über die `revN-`-Präfixe der Kategorie-IDs); die mehrspaltige Tabelle der Alt-Ansicht ist bewusst durch sequenzielle, beschriftete Blöcke ersetzt (Upgrade-Pfad im Code kommentiert).

Bewusst nicht reproduziert: die generierten Überschriften-Anker `#hN` der Alt-Ansicht (unsere Anker kommen aus `@xml:id`; Absatz-Anker sind kompatibel, Seiten-Redirects existieren). Die Citation-Suggestion-Box stammte aus dem WordPress-Theme; unsere R2-Umsetzung ist davon unabhängig.

## Offene Redaktionsentscheidungen

1. Staging: gilt „passwortgeschützt" wörtlich (Optionen in [[pipeline]])?
2. DOI: DataCite-XML künftig im Build erzeugen oder Übergabe an die USB Köln manuell belassen? Wer führt sie aus?
3. DOAJ: Dashboard-Upload des erzeugten XML oder API-Push aus der Pipeline (dann API-Key als Secret)?
4. OAI-Endpoint: stilllegen (kein Harvester nachweisbar) oder dünner zustandsloser Proxy über den statischen Snapshot-Dateien, in jedem Fall ohne eXist?
5. Freischaltungs-Mechanik: PR-basierter Move von ride-editors, wer führt aus?
6. Bilder: dauerhaft im Sibling-Repo `ride` oder Umzug hierher (Pipeline kann beides)?
