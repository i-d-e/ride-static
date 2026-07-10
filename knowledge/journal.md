# Journal

Session-by-session record of work on ride-static. Append a new dated block at the **top** of the entries section after each working session. Five fixed fields, two to four lines each. Keep it terse: the goal is that a future contributor (or a future Claude session) reads the latest entry and knows in one minute where the project stands and what to do next.

## Entry format

```markdown
## YYYY-MM-DD — Short title

**Ziel:** Was war das Ziel der Session.
**Erledigt:** Was wurde abgeschlossen, mit Hinweisen auf Commits oder Dateien.
**Entscheidungen:** Welche Festlegungen wurden getroffen, mit knapper Begründung.
**Offen:** Was bleibt offen, was wurde nicht erreicht, welche Fragen sind ungeklärt.
**Nächster Einstieg:** Konkrete erste Aufgabe der nächsten Session.
```

Field rules:

- **Ziel** — eine Zeile, das zentrale Vorhaben der Session.
- **Erledigt** — was real beendet ist; halbfertige Arbeit gehört nach „Offen". Das Was-im-Detail (Dateien, Funktionen, Commit-Hashes, Test-Zahlen) lebt in git und im Code, nicht hier — das Journal trägt das Narrativ.
- **Entscheidungen** — neue Festlegungen, nicht Wiederholungen aus früheren Einträgen. Nenne den Grund.
- **Offen** — präzise und actionable; vermeide Schwammiges wie „weiter testen".
- **Nächster Einstieg** — eine konkrete Anfangsaufgabe, nicht eine Liste.

If a field is genuinely empty for a given session, write "—" rather than omitting it.

## Why this exists

Three persistence layers run in parallel for this project: `CLAUDE.md` for project conventions, the auto-memory under `~/.claude/projects/.../memory/` for facts that Claude carries across sessions, and git commits for code changes. None of these capture the **narrative** of a session: why did we choose this order, what was almost decided differently, what is left undone. The journal fills that gap. It is human-readable, in-repo, and visible to all contributors — including future Claude sessions that read it on startup.

---

## 2026-07-10 — WordPress-Paritaet: Legacy-Redirects und RSS-2.0-Feed

**Ziel:** Die dynamisch generierten WordPress-Seiten gegen die Static-Site abgleichen und die Quick Wins schliessen (Redirects der Listing-Seiten, RSS-Feed).

**Erledigt:** Fünf Redirects für die alten WP-Listing-Pfade (Charts zweimal mit Chart-Anker, by-tag, reviewed-resources, list-of-reviewers) in `EDITORIAL_REDIRECTS`; Redirect-Stubs tragen jetzt zusätzlich `location.replace()`. RSS-2.0-Renderer als Geschwister von feed.py (gleiche Einträge, gleiche `tag:`-Identifier), Autodiscovery für beide Feeds in base.html, E2E-Pfade gepinnt. Live-Probe der laufenden WP-Site (Apache/Debian, `/feed/` als kanonische Abo-URL, OAI-Endpoint antwortet real); daraufhin Feed-XML-Kopien an den alten Pfaden `/feed/`, `/feed/rss/`, `/feed/atom/` (`LEGACY_FEED_ALIASES`). Recherche-Evidenz und Begründungen als Vault-Doc [[redirects-feeds]]; URL-Vertrag ergänzt.

**Entscheidungen:**
- Meta-Refresh mit Delay 0 bleibt der tragende Redirect-Mechanismus (Google wertet ihn als permanent, WCAG-2.2.1-konform); JS-replace nur additiv.
- RSS-guid ist der Atom-`tag:`-Identifier mit `isPermaLink="false"`, damit Reader beide Feeds deduplizieren; Entity-Escaping statt CDATA; kein `ttl`.
- Alte Feed-URLs bekommen keine HTML-Stubs (Reader parsen kein Meta-Refresh), sondern Kopien der Feed-XML; bewusster Kompromiss mit Content-Type-Decke (`text/html`), Upgrade-Pfad sind echte 301 auf Server-Ebene beim Domain-Umzug.

**Offen:** OAI-Frage wer den live antwortenden Endpoint harvestet (Snapshot vs. dünner Proxy). Nachtrag am selben Tag: Apache wird abgeschaltet (Redaktionsentscheidung), RDF-Feed auf Wunsch doch gebaut (rdf.py, volle WP-Parität), drei adversariale Verifikationsläufe haben die Content-Sniffing-Aussage geschärft (Miniflux/FreshRSS gaten auf Content-Type, nur .xml-URLs bewerben), Details in [[redirects-feeds]].

**Nächster Einstieg:** OAI- und RDF-Entscheidung bei der Redaktion einholen; danach weiter mit P2 Antwort-Matrix-Heatmap.

---

## 2026-07-10 — Refactoring in zwei Wellen: Contracts, Frontend-Angleichung, Realkorpus-Tests, READMEs

**Ziel:** Repo-weiter Refactoring-Durchgang ohne Verhaltensänderung; drei Audits (Pipeline, Frontend, Doku), Umsetzung in zwei parallelen Agent-Wellen.

**Erledigt:** Contracts zentralisiert (`review_url`, `base_ctx` in render/html.py), toter Code entfernt (corpus-stats.json, og-Slot, tooltip.js-Stub), Explore-Frontend angeglichen (Styles in ride.css auf Tokens, explore.js als ES-Modul, geteiltes clipboard.js). Doku auf Code-Wahrheit gebracht (staging.md-Leichen, element-mapping als spec-only, `/data/explore/` im URL-Vertrag, CONTRIBUTING auf TEI-Default). Tests auf gemeinsame Realkorpus-Fixtures in conftest.py umgestellt, AP7-Explorer-Tests, explorer.json-Contract, Build-E2E-Smoke; READMEs für scripts/, src/, config/, static/, tests/.

**Entscheidungen:**
- Wordcloud-PNGs gelten als vendored Source-Assets (kein Generator im Repo, dokumentiert in architecture.md).
- Synthetische Test-Builder nur noch als dokumentierte Pure-Function-Ausnahmen; Randfälle per `dataclasses.replace()` auf echten geparsten Reviews.
- explorer.py und factsheet.py behalten eigene URL-Konstruktion (abweichende Contracts); D3 bleibt Vollbundle bis realer Performance-Druck.

**Offen:** Explore-Ausbau (P2, P4–P7, Story-View AP6; E1–E4, E6, E7, E9). Staging-Entscheidung, CI-Doc-Drift-Politik, fünf menülose TEI-Seiten, submission-guidelines-Doppelung.

**Nächster Einstieg:** P2 Antwort-Matrix-Heatmap je Kriterien-Set; die AP7-Testbasis dafür liegt.

---

## 2026-06-25 — Explorations-Seite: Plan plus erster interaktiver Explore-View

**Ziel:** Klären, was der Korpus an explorierbarem Potenzial hergibt, und einen ersten interaktiven View bauen.

**Erledigt:** Konzept als Vault-Doc [[exploration]] (sieben tragende Vis P1–P7, Forschungsfragen-Katalog, Narrativ-Konzept, Plan AP1–AP7), destilliert aus zwei adversarischen Durchläufen gegen den echten Korpus. View 1 live: `/data/explore/` mit Facetten-Browser (P1, Beeswarm plus Crossfilter) und Issue-Timeline (P3); Datenbasis src/render/explorer.py, D3 v7 vendored.

**Entscheidungen:**
- E0: D3 v7 vendored (kein CDN, kein npm), Scrollytelling später über scrollama; der Ästhetik-Anspruch verlangt eine etablierte Engine.
- E8: Kern zuerst (P1–P3 plus Narrativ-Etappen 1–4), Rest additiv.
- set_slug als Pflicht im Dump, keine globale Ja-Quote; die Set-Leitplanke lebt in der Vis statt als Erklärtext.

**Offen:** P2, P4–P7, Ressourcen-Inventar und der Story-View ungebaut; AP7-Tests fehlen; E1–E7, E9 offen. Volltext-Forschungsfragen brauchen erst Textanalyse.

**Nächster Einstieg:** AP7-Tests für explorer.py, dann P2 Heatmap je Set.

---

## 2026-06-24 — Editorial-URLs hierarchisch (URL-Schema v2)

**Ziel:** Editorial-Seiten spiegeln ihren Navigationsbereich in der URL (`/about/editorial/`), wie vom IDE-Gegencheck angeregt.

**Erledigt:** `discover_pages` rekursiv, der Slug ist der Pfad unter pages/; navigation.yaml, Footer, Redirects und url-scheme.md (v2) nachgezogen, live auf GitHub Pages verifiziert. Nav-Guard-Test prüft jede navigation.yaml-URL gegen die real gebauten Slugs.

**Entscheidungen:**
- Bereichszuordnung aus navigation.yaml, Slug-Quelle ist der Dateipfad; ein Ableiten zur Render-Zeit hätte eine Render-Kopplung erzeugt.
- Aggregationsseiten bleiben flach (eigener Renderpfad); keine Flach-zu-Hierarchie-Redirects, die flachen Slugs liefen nie unter ride.i-d-e.de.

**Offen:** Fünf menülose TEI-Seiten liegen flach, Bereichszuordnung redaktionell offen; echte Doppelung submission-guidelines und suggested-projects-for-review gegen ihre Markdown-Pendants; `content/*.md` mit TEI-Entsprechung ist nach dem Cutover toter Fallback mit Slug-Doppelpflege.

**Nächster Einstieg:** Bereichszuordnung und Doppelung nach dem Gegencheck der Kolleginnen klären.

---

## 2026-06-24 — knowledge-Vault-Refactor: Auflösung, Code-Audit, Quantitäten-Politik

**Ziel:** Den knowledge-Vault aufräumen, Drift gegen den echten Code korrigieren, leise veraltende Mess-Quantitäten entfernen.

**Erledigt:** AGENTS.md-Duplikat und KI-Bild gelöscht (Mermaid-Diagramm stattdessen); staging.md nach pipeline.md und dynamic-features.md nach architecture.md aufgelöst, keine toten Wikilinks. Code-verifizierter Audit korrigierte drei systematische Drifts (TEI-Cutover, Atom-Feed, Factsheet/R18) über alle Hand-Docs.

**Entscheidungen:**
- Quantitäten-Politik in CLAUDE.md verankert: Hand-Docs hartcodieren keine gemessenen Mengen, nur bewusste Zahlen; gemessene Werte veralten leise.
- staging.md als Entscheidungsvorlage überführt statt gelöscht, die Redaktionsentscheidung ist offen.
- Audit-Befunde vor Übernahme gegen das Korpus verifizieren; ein Falschbefund wurde so verworfen.

**Offen:** Docstring in src/parser/questionnaire.py widerspricht der Korpus-Zählung. WOFF2-Fonts: offen, ob bewusst verworfen oder Lücke.

**Nächster Einstieg:** Den questionnaire.py-Docstring korrigieren.

---

## 2026-06-22 — Doppelte Review-IDs aus DOI korrigiert, Build-Guard, Atom-Feed verifiziert

**Ziel:** Den Atom-Feed verlässlich testbar machen; den daraus aufgedeckten ID-Befund fixen.

**Erledigt:** RFC-4287-Konformitätstest plus W3C-Validierung (valid). Drei doppelte Review-`xml:id` aufgedeckt, zwei Fixes über die DOI-Lokalform, Build-Guard in `_check_corpus_consistency` plus Tests.

**Entscheidungen:**
- Der DOI ist die kanonische Quelle der Review-ID (`ride.{issue}.{n}`), die `xml:id` dessen Ableitung; der DOI ist editoriell vergeben und global eindeutig, die `xml:id` war es nachweislich nicht.
- ID-Validierung bricht den Build hart, DOI-Dubletten warnen weich (redaktioneller Hinweis).

**Offen:** —

**Nächster Einstieg:** Operator-gated Restposten (URL-Scheme, value=1-Zählung, Staging).

---

## 2026-06-22 — TEI-Editorials live geschaltet (Default-Flip), Redirect-Self-Loop behoben

**Ziel:** Die TEI-Begleittexte live bringen, damit die Kolleginnen gegen die alte WP-Fassung prüfen können; eine Endlosschleife klären.

**Erledigt:** Default-Flip auf TEI-Editorials (`content/*.md` nur Fallback, CLI-Notausgang `--no-tei-editorials`). Drei Self-Loop-Redirects entfernt plus Guard. README auf den TEI-Pfad umgeschrieben.

**Entscheidungen:**
- Live-Gang als Code-Default statt CI-Flag, damit lokaler Build und Deploy deckungsgleich bleiben.
- `contact` bewusst als dünner TEI-Body live, damit der Gegencheck die Inhaltslücke sieht; das Füllen ist redaktionell.

**Offen:** contact-Body füllen (redaktionell); URL-Scheme nicht nachgezogen; TEI-Header bewusst minimal.

**Nächster Einstieg:** Gemeldete Korrekturen je Seite einarbeiten, parallel die URL-Scheme-Entscheidung klären.

---

## 2026-06-21 — M3 Build-Cutover als Default-aus-Schalter, Reconciliation-Spur, URL-Scheme zurückgemeldet

**Ziel:** M3 Build-Cutover als lokale, nicht-gepushte Render-Spur bauen; M4 scopen.

**Erledigt:** TEI-Editorialvorrang hinter Schalter (Default aus), Markdown-Fallback für ungedeckte Slugs. Per-Seite-Reconciliation-Diff TEI gegen Markdown als Operator-Spur.

**Entscheidungen:**
- Cutover als Default-aus-Schalter; Live-Gang ist ein späterer operator-gated Default-Flip. Nur so vereinbaren sich „verdrahten", „nicht deployen" und „alles in main".
- Diff als Reconciliation geführt, die Äquivalenzannahme war bereits widerlegt.
- URL-Scheme nicht eigenmächtig umgebaut; die Anweisung hätte R17 gebrochen und nach außen gewirkt, zurück an den Operator.

**Offen:** URL-Scheme blockiert Redirects und Cutover. M4 value=1 operator-gated: Charts und Sidebar zählen `value="1"` flach als Ja, korrekt wäre die echte Ja-Rate über `Questionnaire.questions`.

**Nächster Einstieg:** Auf die URL-Scheme-Entscheidung warten, dann Redirects finalisieren.

---

## 2026-06-21 — TEI-Konsumtions-Audit, Element-Coverage-Lock eingezogen

**Ziel:** Systematisch beantworten, ob alles aus dem TEI im Frontend ankommt.

**Erledigt:** Volle Element- und Attribut-Inventur beider Korpora gegen die Parser gestellt; kein still verschluckter Inhaltsträger. Daueranlage: `tests/test_tei_coverage.py` macht jedes neue, nie klassifizierte Element rot.

**Entscheidungen:**
- Coverage-Lock statt Befund-Doku; die belastbare Antwort auf „wird alles getestet" ist, es testbar zu machen.
- Lock auf Element-Granularität begrenzt; Attributwert-Diskriminierung bleibt Sache der feldweisen Tests.

**Offen:** Kein analoger Lock auf Attributwert-Ebene; ob er lohnt, ist offen.

**Nächster Einstieg:** M3-Reconciliation je divergierender Editorialseite oder auf Operator-Entscheidungen warten.

---

## 2026-06-21 — Factsheet-Parität verifiziert, reviewed-resource Publikationsdatum ergänzt

**Ziel:** Das Factsheet (R18) Feld für Feld gegen die Live-Seite stellen.

**Erledigt:** Vollabgleich; die alte Lückenliste war veraltet, die genannten Lücken längst implementiert. Eine reale Restlücke geschlossen: `RelatedItem.publication_date` aus `<date type="publication">`.

**Entscheidungen:**
- Die Live-Differenz beim „Last Updated" nicht nachgebaut; der Live-Wert stammt aus WordPress-Metadaten außerhalb der Quelle, wir geben die TEI treu wieder.

**Offen:** Personnel-Zählung und Questionnaire-Sektionsüberschriften brauchen das rohe Live-HTML.

**Nächster Einstieg:** M3-Reconciliation ausarbeiten oder auf Operator-Entscheidungen warten.

---

## 2026-06-21 — Editorial-Paritätsaudit: M3 ist Reconciliation, nicht Quelltausch

**Ziel:** Das editoriale TEI-HTML gegen die Markdown-Ausgabe diffen, bevor freigegeben wird.

**Erledigt:** Paritätsaudit über alle Editorialseiten. Renderer als treu belegt (eine Seite über beide Pfade byteidentisch); die Divergenzen liegen in den Quellbeständen, nicht im Rendering.

**Entscheidungen:**
- M3 neu gefasst als Editorial-Reconciliation statt mechanischem Cutover; die frühere Äquivalenz-Annahme war falsch.
- Generator-native Seiten (data, charts, questionnaires, about) bleiben auf der Generatorseite.

**Offen:** Redaktionelle Einzelentscheidung je divergierender Seite (contact, imprint, data-Endpunkte).

**Nächster Einstieg:** Factsheet-Paritätsanalyse gegen questionnaire.py.

---

## 2026-06-21 — Editorialseiten komplett (16/16): TEI-Migration plus verbatim Code

**Ziel:** Die Editorial-Migration abschließen; das Seitenprofil nur so weit erweitern, wie der reale Inhalt es erzwingt.

**Erledigt:** Alle Editorialseiten als TEI. Profil minimal um `<eg>` und `<code>` erweitert (writing-guidelines braucht verbatim Code). Neuer Test validiert jede `pages/*.xml` gegen ride-pages.rng. Journal per `git mv` nach knowledge/ umgezogen.

**Entscheidungen:**
- Seal-Badge als Chrome verworfen, nicht modelliert; bei Bedarf über Template/CSS reintegrierbar.
- Code als `<eg>` plus inline `<code>`, TEI-idiomatisch und schema-minimal.

**Offen:** Build-Cutover operator-gated; writing-guidelines-Verbatim redaktionell zu sichten.

**Nächster Einstieg:** Build-Cutover scopen und als Spur vorbereiten.

---

## 2026-06-21 — Factsheet-Parität: R18-Kontrakt plus Factsheet-Vollseite

**Ziel:** Die Volldarstellung des Fragebogens unter `/issues/{N}/{id}/factsheet/` bauen.

**Erledigt:** Drei Modell-Lücken additiv geschlossen (`QuestionnaireQuestion`, `RelatedItem.personnel`); Selektions-Semantik am Korpus verifiziert (value=1 markiert die gewählte Antwort, value=3 Anomalie). R18 als Kontrakt in specification.md; Render-Modul, Template, Sidebar-Link, Legacy-Redirect.

**Entscheidungen:**
- Volle Unterseite in einem Zug (Operator-Entscheidung); Implementierung delegiert und gegen Git, Tests und gerenderten Inhalt abgenommen.
- Sidebar-Aggregation nicht angefasst; deren value=1-Zählung ist ein latenter R1/R9-Fehler und eine eigene Entscheidung.

**Offen:** Sidebar-yes_count-Semantik (mit den Charts gemeinsam zu entscheiden). Text-Collections-Sektionslabels erscheinen als xml:ids.

**Nächster Einstieg:** Operator-Sichtung der Factsheet-Seite, dann Zähl-Entscheidung.

---

## 2026-06-12 — Redaktioneller Zielworkflow: Abgleich, Staging-Dokument, Trigger-Verkabelung

**Ziel:** Den Zielworkflow der Redaktion (ride-editors → Testumgebung → Freischaltung) gegen die Pipeline abgleichen, entscheidungsrobuste Teile sofort bauen.

**Erledigt:** staging.md als Entscheidungsvorlage (fünf Optionen, Bestandsaufnahme). `repository_dispatch`-Verkabelung in build.yml plus Sender-Vorlagen unter docs/upstream-workflows/. Lane-Drift zum Monorepo-Stand gemerged.

**Entscheidungen:**
- Wordclouds bleiben manuell geliefert; programmatische Generierung zerstörte den gestalteten Charakter.
- Draft-Mechanik zurückgestellt bis zur Redaktionsentscheidung; ride-editors ist privat, eine öffentliche Vorschau machte Inhalt erstmals zugänglich.
- Status lebt im Journal und README, nicht in Plan-Dokumenten; Glossar nur im INDEX.

**Offen:** Factsheet-Parität, Staging-Entscheidung mit der Redaktion, Sender-Installation (Repo-Admin), Phase-15-Restposten.

**Nächster Einstieg:** Factsheet-Parität gegen questionnaire.py.

---

## 2026-05-12 — Doku-Refactor: README schlanker, Status-Single-Source, build() zerlegt

**Ziel:** README straffen, das Duplikat prozess-und-stand.md auflösen, Status-Marker aus den Plan-Dokumenten ziehen, build() zerlegen.

**Erledigt:** README deutlich gekürzt (Duplikate zu CLAUDE.md/CONTRIBUTING ausgelagert), prozess-und-stand.md gelöscht, alle Status-Marker aus den Plan-Docs entfernt, `build()` in fünf benannte Helper als lesbare Sequenz zerlegt.

**Entscheidungen:**
- Plan-Dokumente bleiben status- und zeitstempelfrei; mehrere Status-Quellen garantieren Drift.
- build() als innere Faktorierung in einer Datei; ein Paket addierte Indirection ohne Gegenwert.

**Offen:** Phase-15-Restposten (WCAG, Matomo-Secrets, Knowledge-Doc-CI, Custom-Domain).

**Nächster Einstieg:** Matomo-URL als CI-Secret.

---

## 2026-05-12 — Monorepo-Schnitt: TEI-Korpus + Schema in ride-static eingezogen

**Ziel:** Den TEI-Korpus ins eigene Repo holen, damit ride-static nicht von einem zweiten Checkout abhängt.

**Erledigt:** Reviews nach `issues/{N}/reviews/`, Schema nach `schema/`, Issue-Configs nach `issues/{N}/metadata.yaml`. Neues `src/_corpus.py` ersetzt das verteilte Sibling-Pfad-Pattern repo-weit; CI klont `i-d-e/ride` nur noch für Bilder.

**Entscheidungen:**
- Per-Issue-Layout statt flachem Korpusordner; alles zu einem Issue an einem Ort, `biblScope @n` bleibt kanonisch.
- Schema im Root, es ist Validierungs-Vertrag, kein Korpus-Inhalt.
- Bilder bleiben vorerst im Sibling (Repo-Größe, LFS-Quota); die Pipeline degradiert sauber ohne ihn.

**Offen:** Bilder-Migration (vermutlich Git-LFS, eigene Session). Knowledge-Doc-CI-Drift. Phase 15.B.

**Nächster Einstieg:** Build ohne `../ride/` laufen lassen und die saubere Degradation verifizieren.

---

## 2026-05-09 — Knowledge-Vault auf Promptotyping-Konvention gehoben

**Ziel:** knowledge/ als sauberen Promptotyping-Vault refactoren; parallel das Paper im Obsidian-Vault nachziehen.

**Erledigt:** Frontmatter-Pflichtkern auf alle Dateien; `requirements.md` → `specification.md` (git mv, Links nachgezogen); INDEX.md als Navigationsknoten; prozess-und-stand.md aufgelöst, drei Inhalte an Zielstellen gerettet; Paper gepatcht.

**Entscheidungen:**
- Function before filename als drei strukturelle Commitments, keine Funktions-Liste mit Zähler.
- Eine Funktion pro Stelle; Hybrid-Dokumente werden aufgelöst statt reduziert.

**Offen:** interface.md-Spaltung in design.md/ui.md (eigene Session). README veraltet. site/-Eincheck-Frage.

**Nächster Einstieg:** interface-Spaltung oder Phase-15-Restposten.

---

## 2026-04-29 — Phase 10-Rest: Data-Charts (R9) live

**Ziel:** Aggregierte Bar-Charts auf `/data/charts/` aus dem realen Korpus statt Placeholder.

**Erledigt:** `src/render/charts.py`: kanonische Slug-Map über die Kriterien-URLs, Aggregation nach Top-Level-Section, Inline-SVG-Charts, separate value=3-Anomalie-Note; Marker-Substitution im Editorial-Renderer.

**Entscheidungen:**
- Slug-Map hartkodiert, die URLs sind ein geschlossenes Set; der `(other)`-Bucket dient als Drift-Sensor mit Pin-Test.
- Aggregation auf Top-Level-Sections; hunderte Leaves wären unlesbar.
- Marker-Pattern statt Sonder-Template, Editorinnen sehen die Position ohne Build.

**Offen:** Phase-15-Restposten; fehlende Wordclouds älterer Issues (kosmetisch).

**Nächster Einstieg:** WCAG-Vollaudit oder Matomo-Secrets.

---

## 2026-04-29 — Phase 14 + 15.A: PDF live, Compliance-Block geschlossen

**Ziel:** Compliance- und UX-Items (R14, R16, N5, N6) abräumen und Phase 14 (PDF) implementieren.

**Erledigt:** Contact-Seite, cookieless Matomo (deploy-konfigurierbar), Lizenzfelder in allen JSON/XML-Artefakten, focus-visible und Target-Size-Polish. `src/render/pdf.py` mit WeasyPrint, print-only DOI-Zeile, Print-Stylesheet; CI installiert GTK.

**Entscheidungen:**
- PDF nutzt das fertige HTML mit `@media print`, kein zweiter Template-Baum, eine Drift-Quelle weniger.
- Matomo gated auf beide Felder; ein halbkonfigurierter Deploy sendete sonst still.
- WeasyPrint-Import in `try/except (ImportError, OSError)`; Windows ohne GTK wirft OSError aus ctypes.

**Offen:** CI-Verifikation des ersten PDF-Runs; Data-Charts als letzter inhaltlicher Brocken.

**Nächster Einstieg:** CI prüfen, dann Data-Charts.

---

## 2026-04-28 — Backend Session-Ende: Test-Refactor-Welle 2 angestoßen, Übergabe

**Ziel:** Den Phase-7-Test-Audit gegen die neue Real-Corpus-Hard-Rule auf den Rest der Suite anwenden.

**Erledigt:** `test_parser_review.py` auf Realkorpus umgestellt; Fixture-Kandidaten für die nächste Welle dokumentiert, damit die nächste Session direkt schreiben kann.

**Entscheidungen:**
- Welle 2 in vier einzeln prüfbare Schritte gesplittet.
- Die Field-Echo-Tests in test_model.py bleiben; sie sind der Vertragstest für frozen/tuple, die Audit-Bewertung „Tautologie" war zu hart.
- `#abb`/`#img` ist ein Korpus-Bug, kein Resolver-Alias; ein Alias hebelte „anomalies are explicit" aus, Phase 13 meldet.

**Offen:** Restliche Parser-Tests auf Realkorpus. Hygiene-Incident: ein Commit zog Fremd-Pfade mit; Regel seitdem: vor jedem Commit `git diff --cached --stat`.

**Nächster Einstieg:** test_parser_metadata.py umstellen.

---

## 2026-04-28 — Frontend: Phase-7-Integration abgeschlossen (Buckets + Asset-Pipeline)

**Ziel:** Reference-Buckets und Asset-Pipeline ans Rendering anschließen.

**Erledigt:** Bucket-Klassen am `reference()`-Macro, Orphans als nicht-klickbarer span, Asset-Pipeline mit AssetReport im Build, `media_path_factory` für base_url-Prefixing; Smoke-Build verifiziert.

**Entscheidungen:**
- media_path als per-render Closure statt env-globalem Jinja-Filter, der base_url nicht pro Build aufnehmen kann.
- Orphans nicht-klickbar mit data-target zur Diagnose; Lesefluss und A11y leiden nicht unter broken links.
- Fehlende Bild-Extensions sind Korpus-Issue, das Frontend verlinkt, was im TEI steht.

**Offen:** Cross-Contamination-Incident (künftig gezieltes `git add <pfad>`); `#abb`-Frage ans Backend.

**Nächster Einstieg:** Live-Deploy verifizieren, dann Phase 11 oder 12.

---

## 2026-04-29 — Phase 7 abgeschlossen, Reference-Resolver + Asset-Pipeline live

**Ziel:** Vier-Bucket-Resolver, Asset-Pipeline, Test-Refactor auf Real-Corpus-Drive.

**Erledigt:** `Reference.bucket` plus refs_resolver.py (Post-Pass in parse_review), assets.py mit `rewrite_figure_assets`/AssetReport. Test-Daten-Philosophie als Hard Rule in CLAUDE.md verankert, Phase-7-Tests entsprechend refaktoriert.

**Entscheidungen:**
- bucket als Inline-Feld statt paralleler Map, keine zwei Strukturen zu synchronisieren.
- criteria-Bucket bleibt trotz null Body-Vorkommen im Vertrag; alle K-Refs leben im Header.
- Wayback-Hint nach Phase 13 verschoben, HTTP-Probes gehören in den Validierungs-Schritt.

**Offen:** Frontend-Integration der Buckets; Phasen 12 und 13.

**Nächster Einstieg:** Frontend abwarten, ggf. Phase 11 vorziehen.

---

## 2026-04-29 — Phase 6 abgeschlossen, Stage 2.C steht

**Ziel:** Bibliography- und Questionnaire-Modell plus Cross-Korpus-Aggregate in einem Schub.

**Erledigt:** `BibEntry`/`parse_bibliography`, `Questionnaire` mit Leaf-only-Walker, `datasets.py` mit drei deduplizierten, sortierten Aggregaten (Tags, Reviewer, Resources).

**Entscheidungen:**
- `<listBibl>` als Review-Feld, nicht Block-Kind; die Bibliographie ist strukturell separat.
- BibEntry ohne Sub-Felder, das Korpus nutzt `<bibl>` als Freitext-Zitat.
- Nur Leaf-Categories sammeln (sonst erben Sections die Antworten); value=3 als String erhalten, der Renderer entscheidet.

**Offen:** Phase 7 (Resolver, Assets).

**Nächster Einstieg:** Vier-Bucket-Resolver plus Asset-Pipeline, früh liefern, das Frontend wartet.

---

## 2026-04-29 — Phase 10 + Citation: Site hat ihre Außenhaut

**Ziel:** Citation-Daten für die Copy-Buttons embedden, die Aggregations- und Übersichtsseiten bauen.

**Erledigt:** BibTeX/CSL-Filter plus Embed-Blöcke in review.html; `aggregations.py` mit acht Entry-Points und Templates, review_card-Partial; Platzhalter-Index ersetzt.

**Entscheidungen:**
- Aggregationsseiten einspaltig ohne Apparate (interface §4).
- BibTeX-Brace-Escape per Sentinel-Pass, eine naive Replace-Kette produziert kaputte Sequenzen.
- Reviewer-Slug surname-forename; Tag-Liste statt Word-Cloud (barrierefrei, scannbar).

**Offen:** Buckets und Bilder warten auf Phase 7; tooltip.js und pagefind.js sind Stubs; Issue-YAML noch nicht eingehängt.

**Nächster Einstieg:** Live-Deploy testen, auf Phase 7 warten.

---

## 2026-04-29 — Phase 8 First Light, Frontend rendert den Korpus End-to-End

**Ziel:** Erster lauffähiger Frontend-Strang: Render-Macros, Review-Template, Build-CLI, CI.

**Erledigt:** Rekursive Block-/Inline-Dispatcher mit BEM aus element-mapping.yaml, Review-Template mit Apparaten und Sidebar, Build-CLI mit Per-Datei-Fehlerfang, voller Korpus-Build ohne Fehler, CI-Workflow für GH-Pages.

**Entscheidungen:**
- ChainableUndefined statt StrictUndefined; UI-Strings sind optional-verschachtelt, Domain-Tippfehler fängt der Test-Layer.
- Block-Dispatch über Klassennamen, Macros zentral in einer Datei (rekursive Dispatcher müssen sich sehen).
- Apparate kollabieren komplett, wenn leer; Per-Datei-Fehlerfang, damit ein anomaler Review den Lauf nicht blockiert.

**Offen:** Phasen 6/7 als Voraussetzung für Factsheet, Bibliographie, Bilder; CSS-Komponenten und JS-Module ausstehend.

**Nächster Einstieg:** Editorial-Stubs plus editorial.html, dann die JS-Module.

---

## 2026-04-29 — Phase 5 abgeschlossen, Stage 2.B steht; Rollen-Split etabliert

**Ziel:** Inlines integrieren, Block-in-Paragraph-Anomalie auflösen, parse_review komplettieren, Aggregate materialisieren.

**Erledigt:** `parse_inlines` in allen Per-Kind-Parsern; `parse_paragraph_or_split` zerlegt `<p>` mit Block-Kindern; `parse_review` über front/body/back; `aggregate.py` als Dokumentordnungs-Walker; Korpus-Smoke grün.

**Entscheidungen:**
- `<listBibl>` skip-and-defer statt Placeholder (Phase 6 ersetzt den Branch ohnehin).
- Nested Blocks als `blocks`-Feld; Aggregate am Parse-Zeitpunkt materialisiert, Templates bekommen pure Domänenobjekte (N1).
- Rollen-Split Backend/Frontend etabliert; der Datenvertrag sind die Domänenobjekte.

**Offen:** Phasen 6 und 7.

**Nächster Einstieg:** Bibliography-Modell und -Parser.

---

## 2026-04-29 — Phase 4 abgeschlossen, Inline-Parser steht

**Ziel:** Mixed-Content-Walker für die sechs verifizierten Inline-Kinds.

**Erledigt:** `inlines.py` mit Whitespace-Strategie, Nesting, Unknown-Raise; `crosssref`-Typo normalisiert; `Note.xml_id` als Footnote-Anker ergänzt; Real-Korpus-Smokes.

**Entscheidungen:**
- `<lb/>` als Soft-Skip statt eigener Klasse, wenige Vorkommen.
- Typo-Fix als Daten-Map, nicht Code-Branch; neue Typen passieren unverändert.
- Block-Elemente in `<p>` raisen sauber; Phase 5 löst die Pre-Extraction als Integrations-Concern.

**Offen:** Phase 5 muss die Block-in-Paragraph-Anomalie vor dem Walker abfangen, sonst raised der Korpus.

**Nächster Einstieg:** `_split_paragraph`, dann parse_review komplettieren.

---

## 2026-04-29 — Phase 3 abgeschlossen, Block-Parser steht

**Ziel:** Block-Parser für die fünf verifizierten Block-Kinds mit klarem Fehlerverhalten.

**Erledigt:** `blocks.py` mit Per-Kind-Funktionen, `parse_block`-Dispatcher und `UnknownTeiElement` (Localname plus Div-Hint); Real-Korpus-Smoke.

**Entscheidungen:**
- UnknownTeiElement als eigene Exception, damit Berichte den Anomalie-Typ präzise erkennen.
- Tabellen-Header über `@role="label"`, die einzige verlässliche Korpus-Markierung.
- Inlines bleiben in Phase 3 leer; das Contract ist die korrekte Block-Struktur, nicht der Inhalt.

**Offen:** Phase 4 (Inline-Walker).

**Nächster Einstieg:** `inlines.py` anlegen.

---

## 2026-04-29 — Phase 2 abgeschlossen, Section-Parser steht

**Ziel:** Rekursiver Section-Parser inklusive Body-Wrap-Anomalie für die anomalen Reviews.

**Erledigt:** `sections.py` mit benannten Anomalie-Branches (ID-Fallback, fehlendes head, Tiefen-Limit, No-Back); Wrap-Branch gegen die betroffenen Reviews verifiziert plus Real-Korpus-Smokes.

**Entscheidungen:**
- Wrap-Detection element-basiert mit Kommentar-Skip, verhindert False Negatives.
- Synthese-ID-Präfix `sec-` kollisionsfrei, im Korpus nirgends vergeben.

**Offen:** Phase 3 (Block-Parser mit List-Rend-Normalisierung).

**Nächster Einstieg:** `blocks.py` anlegen, erste Funktion `_parse_p`.

---

## 2026-04-29 — Phase 1 abgeschlossen, Stage 2.B Modell steht

**Ziel:** Datenmodell für Section, Block und Inline als frozen dataclasses, ohne Parser-Logik.

**Erledigt:** `model/{section,block,inline}.py` plus Tests; Review additiv um front/body/back erweitert; Architecture-Doc auf den verifizierten Stand.

**Entscheidungen:**
- `Figure.kind` als Feld statt zweier Klassen, einfacher zu rendern als Polymorphie.
- `Paragraph.n` für die Citation-Anker-Nummern (interface §11).

**Offen:** Phase 2 (Section-Parser mit Body-Wrap-Anomalie).

**Nächster Einstieg:** `sections.py` anlegen.

---

## 2026-04-29 — Konsolidierung K1-K4 vor Phase 1

**Ziel:** Vor den Implementierungsphasen den Vault vereinheitlichen, das Repo selbsterklärend machen, die Journal-Konvention etablieren.

**Erledigt:** Vault-Naming lowercase mit Wikilinks; YAML-Mapping als Architekturentscheidung verankert; README, CONTRIBUTING, docs/extending.md, docs/url-scheme.md neu; Journal-Konvention etabliert.

**Entscheidungen:**
- lowercase-Naming wegen Case-Sensitivity-Konflikten zwischen Windows und Linux-CI.
- Journal getrennt von Memory; Memory hält dauerhafte Fakten, das Journal den Sessionverlauf.

**Offen:** —

**Nächster Einstieg:** Phase 1, Datenmodell als frozen dataclasses.
