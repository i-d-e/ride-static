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

## 2026-07-10 — Refactoring in zwei Wellen: Contracts, Frontend-Angleichung, Realkorpus-Tests, READMEs

**Ziel:** Repo-weiter Refactoring-Durchgang ohne Verhaltensänderung: drei parallele Audits (Pipeline, Frontend, Doku), daraus ein Plan in zwei Wellen, umgesetzt mit parallelen Agent-Lanes.

**Erledigt:** Welle 1: Review-URL-Contract und Render-Basiskontext zentralisiert (`review_url`, `base_ctx` in render/html.py, vorher sechs unabhängige Baustellen), toter Code entfernt (corpus-stats.json ohne Konsument, og-Slot, BuildInfo-Leerfelder, tooltip.js-Stub, tote CSS-Selektoren), Explore-Frontend an den Rest angeglichen (Inline-CSS nach ride.css auf Tokens, explore.js als ES-Modul, geteiltes clipboard.js). Doku-Wahrheitsabgleich: staging.md-Leichen raus, exploration.md in CLAUDE.md, element-mapping.yaml als spec-only klargestellt, redirects.yaml-Phantom korrigiert, `/data/explore/` im URL-Vertrag (E5 damit entschieden), CONTRIBUTING auf TEI-Default. Welle 2: gemeinsame Realkorpus-Fixtures in conftest.py, elf test_render_-Dateien von synthetischen Buildern auf echte geparste Reviews umgestellt, AP7-Tests für explorer.py (Zeilen-Contract, set-interne Ja-Quote, exakte Pfade), explorer.json-Schnittstellen-Contract gegen die real von explore.js konsumierten Felder, Build-E2E-Smoke-Test, READMEs für scripts/, src/, config/, static/, tests/.

**Entscheidungen:**
- Die Wordcloud-PNGs gelten als vendored Source-Assets (kein Generator im Repo, dokumentiert in architecture.md), statt sie als verbotene Build-Artefakte zu behandeln.
- Verbleibende synthetische Test-Builder sind auf dokumentierte Pure-Function-Ausnahmen beschränkt; Randfälle entstehen bevorzugt per dataclasses.replace() auf echten geparsten Reviews.
- explorer.py und factsheet.py behalten eigene URL-Konstruktion, weil ihre Contracts abweichen (Fallback-Semantik bzw. /factsheet/-Suffix); nur identische Contracts laufen über review_url.
- D3 bleibt als Vollbundle vendored; Subset-Build erst bei realem Performance-Druck.

**Offen:** Explore-Ausbau unverändert (P2 Heatmap, P4–P7, Ressourcen-Inventar, Story-View AP6; E1–E4, E6, E7, E9). Staging-Redaktionsentscheidung und CI-Doc-Drift-Politik weiter offen. Die fünf menülosen TEI-Seiten und die submission-guidelines-Doppelung ungeklärt. i18n-Gerüst (site.strings) bewusst belassen.

**Nächster Einstieg:** P2 Antwort-Matrix-Heatmap je Kriterien-Set bauen; die AP7-Testbasis dafür liegt jetzt.

---

## 2026-06-25 — Explorations-Seite: Plan plus erster interaktiver Explore-View

**Ziel:** Klären, was der Korpus an explorierbarem Potenzial für eine eigene interaktive Daten-Seite hergibt, welche Forschungsfragen er trägt, und ob ein zweiter, narrativer View machbar ist — mündend in einen Implementierungsplan und einen ersten sichtbaren View.

**Erledigt:** Zwei mehrphasige Expertenteam-Durchläufe gegen den echten Korpus. Durchgang 1 kartierte fünf Datendimensionen, prüfte 24 interaktive Vis-Konzepte adversarisch auf Datentragfähigkeit und destillierte sieben tragende Visualisierungen (P1 Facetten-Browser als Rückgrat, P2 Antwort-Matrix-Heatmap, P3 Issue-Timeline plus Ressourcen-Alter, P4 Review-Anatomie, P5 Editor-Matrix, P6 Reviewer-Karte, P7 Verweisnetz) plus Ressourcen-Inventar. Durchgang 2 erstellte den Forschungsfragen-Katalog (Teil A datasheet-beantwortbar, Teil B volltext-pflichtig, sieben Leitfragen), das datenehrliche Narrativ-Konzept (sechs Etappen) und den gegen den Code verifizierten Implementierungsplan. Festgehalten als Vault-Doc [[exploration]], im INDEX verlinkt. Anschließend den Kern von View 1 gebaut: `/data/explore/` live im Build. Datenbasis `src/render/explorer.py` (eine flache Pro-Review-Zeile, set-interne Ja-Quote, Apparat als Präsenz plus Rohwert), Render via `render_explore` in aggregations.py, Build-Hook in build.py (Seite plus `site/data/explorer.json`), navigation.yaml-Eintrag. Frontend: D3 v7 vendored unter static/js/vendor, `static/js/explore.js` mit Facetten-Browser (Beeswarm plus Crossfilter, umschaltbare X-Achse, gekoppelte sortierbare Tabelle) und Issue-Timeline (P3). App-Layout mit Filter-Sidebar links und dominanter Vis. Suite grün (550 plus 2 Skip), Nav-Guard um `data/explore` ergänzt.

**Entscheidungen:**
- Technik E0 entschieden: D3 v7 modular vendored (kein CDN, kein npm), Karte später über d3-geo plus eingecheckte GeoJSON, Scrollytelling über scrollama. Ersetzt den Team-Default „eigener SVG-Renderer", weil der Ästhetik-Anspruch eine etablierte Engine verlangt und D3 die Offline-Disziplin gleichermaßen hält.
- Scope E8 entschieden: Kern zuerst (P1, P2, P3 plus Narrativ-Etappen 1 bis 4), Rest additiv. Faktisch zuerst P1 plus P3 gebaut.
- Set-Sperre als Daten-Eigenschaft im Dump verankert (set_slug Pflicht, keine globale Ja-Quote); die Leitplanke lebt in der Vis (set-relativer Hinweis an der Yes-ratio-Achse und der Tabellenspalte) statt als Erklärtext.
- Beide Views als Schwestern unter dem Data-Bereich; die statischen `/data/charts/` bleiben als Kanon-Ansicht daneben.

**Offen:** P2 (Heatmap), P4 bis P7 und der Narrativ-View `/data/story/` noch nicht gebaut. Die eigenen TDD-Tests für explorer.py und render_explore (AP7) fehlen — bisher nur der Nav-Guard angepasst. Restliche Entscheidungen E1 bis E7, E9 offen (JSON-Ablage, Ressourcen-Alter 35 gegen 26, Skript-Schnitt, GeoNames, URL-Schema-Eintrag, Etappe 7, Mikro-Anker, Charts-Koexistenz). Volltext-Forschungsfragen brauchen erst Textanalyse.

**Nächster Einstieg:** AP7-Tests für explorer.py nachziehen (Realkorpus-Integrationstest: 111 Zeilen, set_slug-Pflicht, keine globale Ja-Quote, exakte Output-Pfade), dann P2 Heatmap je Set als nächste zentrale Ansicht.

---

## 2026-06-24 — Editorial-URLs hierarchisch (URL-Schema v2)

**Ziel:** Aus dem IDE-Gegencheck kam die Anmerkung, die Bereiche (About, Data) wie auf der alten WP-Site in der URL abzubilden (`/about/editorial/` statt `/editorial/`). Diese Hierarchisierung umsetzen und live auf GitHub Pages prüfbar machen.

**Erledigt:** Editorial-Seiten spiegeln jetzt ihren Navigationsbereich in der URL. Mechanismus: `discover_pages` rekursiv (`rglob`), der Slug ist der relative Pfad unter `pages/`; die `pages/*.xml` der About- und Reviewers-Gruppe wurden in Bereichsordner verschoben. Die Markdown-Fallbacks unter `content/` tragen denselben Slug im Frontmatter, sodass keine Seite doppelt unter dem alten flachen Pfad aufersteht. `navigation.yaml`, Footer, interne content-Links, `EDITORIAL_REDIRECTS` und `docs/url-scheme.md` (v2) nachgezogen, Suite grün (548). Sauberer Rebuild bestätigt: die alten flachen Editorial-URLs sind verschwunden, die hierarchischen aktiv. Als eigener Commit getrennt vom Vault-Refactor geführt, live auf GitHub Pages verifiziert (200 für die neuen Pfade, 404 für die alten flachen). Anschließend README und docs/extending.md auf die hierarchische pages-Struktur und weg von der gelöschten staging.md nachgezogen, plus ein Navigations-Guard-Test, der jede navigation.yaml-URL gegen die real gebauten Seiten-Slugs prüft.

**Entscheidungen:**
- Bereichszuordnung aus `navigation.yaml` abgeleitet, der einzigen im Repo vorhandenen kuratierten Quelle der Sektionszugehörigkeit.
- Slug-Quelle ist der Dateipfad (TEI-Ordner) beziehungsweise der Frontmatter-Slug (Markdown). Ein Ableiten aus der Navigation zur Render-Zeit wurde verworfen, um eine Render-Kopplung zu vermeiden und Seiten ohne Menüeintrag abzudecken.
- Aggregationsseiten (`/tags/`, `/resources/`, `/reviewers/`) bleiben flach, weil sie datengetrieben sind und einen eigenen Renderpfad haben; ein Mitwandern unter `/data/` wäre ein separater, größerer Eingriff.
- Keine Flach-zu-Hierarchie-Redirects, weil die flachen Slugs nur im github.io-Preview liefen und nie unter ride.i-d-e.de.

**Offen:** Fünf TEI-Seiten ohne Menüplatz (dissemination-discussion, submission-guidelines, suggested-projects-for-review, projects-currently-under-review, writing-guidelines) liegen vorerst flach, ihre Bereichszuordnung ist redaktionell offen. Eine echte Doppelung besteht: submission-guidelines (TEI, flach) gegen `/reviewers/submitting-a-review/` (Markdown) und suggested-projects-for-review (TEI) gegen `/reviewers/projects-for-review/` (Markdown), wobei das Menü auf die Markdown-Variante zeigt. Offen auch, ob imprint top-level bleibt oder unter `/about/` wandert, sowie der gemischte `/reviewers/`-Namespace (Editorial plus Profile, aktuell kollisionsfrei). Refactoring-Kandidat: die `content/*.md` mit TEI-Entsprechung sind nach dem Cutover toter Fallback und erzwingen Slug-Doppelpflege (heute beim Move spürbar geworden), ein Aufräumen steht aus.

**Nächster Einstieg:** Nach der Live-Verifikation der Kolleginnen die Bereichszuordnung der fünf flachen TEI-Seiten sowie die Doppelung submission-guidelines/suggested-projects-for-review klären und die betroffenen Seiten analog verschieben.

---

## 2026-06-24 — knowledge-Vault-Refactor: Auflösung, Code-Audit, Quantitäten-Politik

**Ziel:** Den knowledge-Vault aufräumen — Redundanzen auflösen, veraltete Aussagen gegen den echten Code korrigieren, leise veraltende Mess-Quantitäten aus den Hand-Docs entfernen.

**Erledigt:** `AGENTS.md` (byteidentisches `CLAUDE.md`-Duplikat) und das KI-generierte `image-workflow.png` gelöscht, das Bild durch ein Mermaid-Pipelinediagramm in architecture.md ersetzt. `staging.md` und `dynamic-features.md` aufgelöst: Staging als verdichteter Entscheidungsabschnitt nach pipeline.md, die Vier-Interfaces-Abgrenzung als Abschnitt „Data interfaces" nach architecture.md — Substanz erhalten, Vault jetzt 8 statt 10 Docs, keine toten Wikilinks. Ein code-verifizierter Korrektheits-Audit (vier Subagenten gegen `src/`) deckte drei systematische Drifts auf: TEI-Editorial-Cutover (vollzogen, stand als „ausstehend"), Atom-Feed (existiert, fehlte in Outputs), Factsheet/R18 (implementiert, stand als „Lücke") — über alle Hand-Docs korrigiert. schema.md-Generator gestrafft und regeneriert. Volle Suite grün.

**Entscheidungen:**
- Quantitäten-Politik (in CLAUDE.md verankert): Hand-Docs hartcodieren keine gemessenen Mengen (Korpus-Counts, Zeilenzahlen) — die leben in den generierten data.md/schema.md oder `inventory/`, Hand-Docs verweisen; nur bewusste Zahlen (Design-Tokens, Schwellen, IDs) bleiben. Grund: „5 209 K-refs" stand 4x hartcodiert und veraltet leise.
- staging.md nicht ersatzlos gelöscht, sondern als Entscheidungsvorlage nach pipeline.md überführt (Thema ist Deploy-Mechanik), weil die Redaktionsentscheidung offen ist.
- Agenten-Befund „Taxonomie nur 107 Reviews" gegen das Korpus geprüft und verworfen (real 111, 109/1/1) — Beleg, dass Audit-Befunde vor Löschung zu verifizieren sind.

**Offen:** Parser-Docstring in `src/parser/questionnaire.py` widerspricht der Korpus-Realität (114 taxonomy über 111 Reviews) — Code-Kommentar, nicht Doc. WOFF2-Fonts: interface.md beschreibt jetzt den Ist-Stand (System-Stack, `static/fonts/` leer); offen, ob bewusst verworfen oder Lücke. data.md nicht angefasst (generiert).

**Nächster Einstieg:** Den Docstring in `src/parser/questionnaire.py` gegen die verifizierte Korpus-Zählung (111 Reviews, 114 taxonomy-Elemente) korrigieren.

---

## 2026-06-22 — Doppelte Review-IDs aus DOI korrigiert, Build-Guard, Atom-Feed verifiziert

**Ziel:** Den Atom-Feed verlässlich testbar machen; aus dem daraus aufgedeckten Datenbefund einen konkreten, getesteten Fix-Vorschlag bauen.

**Erledigt:** Atom-Feed mit algorithmischem RFC-4287-Konformitätstest und W3C-Validator abgesichert (valid Atom 1.0). Die Validator-Warnung deckte drei doppelte Review-`xml:id` auf; korpusweite Analyse ergab: der Review-DOI ist der kanonische Schlüssel, die `xml:id` muss dessen Lokalform `ride.{issue}.{n}` sein, alle 111 Reviews tragen einen solchen DOI. Zwei datengestützte ID-Fixes (everynamecounts, godwin) nur an der Wurzel-`xml:id`, keine eingehenden Verweise betroffen. Build-Guard in `_check_corpus_consistency` (ID-Validierung hart, DOI-Dublettenprüfung weich) plus Tests.

**Entscheidungen:**
- DOI als kanonische Quelle der Review-ID festgelegt, nicht die freie `xml:id`; die `xml:id` ist dessen Ableitung. Grund: der DOI ist editoriell vergeben und global eindeutig, die `xml:id` war es nachweislich nicht.
- ID-Validierung als harter Build-Bruch, DOI-Dublettenwarnung weich. Grund: eine falsche ID bricht Anker und Feed, eine DOI-Dublette ist ein redaktioneller Hinweis.

**Offen:** —

**Nächster Einstieg:** Offene Restposten der Vorsessions (URL-Scheme-Entscheidung, value=1-Zählung, Staging) — alle operator-/redaktions-gated.

---

## 2026-06-22 — TEI-Editorials live geschaltet (Default-Flip), Redirect-Self-Loop behoben

**Ziel:** Die teiisierten Begleittexte (`pages/*.xml`) auf GitHub Pages live bringen, damit die IDE-internen Kolleginnen jede Seite gegen die alte WP-Fassung prüfen können; zugleich eine im Review aufgefallene Endlosschleife klären.

**Erledigt:** M3 Default-Flip: `build()` rendert die `pages/*.xml`-TEI per Default mit Vorrang (`tei_editorials=True`), `content/*.md` nur noch als Fallback, CLI-Notausgang `--no-tei-editorials`; CI und `build.yml` unverändert. Redirect-Self-Loop behoben: drei Identitäts-Einträge (`about`, `ethical-code`, `data`) leiteten per meta-refresh auf sich selbst (Endlos-Reload, live bestätigt), entfernt plus Self-Loop-Guard. README auf den TEI-Pfad umgeschrieben.

**Entscheidungen:**
- Live-Gang als Default-Flip im Code, nicht als CI-Flag. Grund: nur der Code-Default hält lokalen Build und Deploy deckungsgleich; ein CI-only-Flag ließe `python -m src.build` lokal weiter Markdown rendern.
- `contact` bewusst als dünner TEI-Body live (ein Satz + E-Mail), obwohl `content/contact.md` voller ist. Grund: der Preview soll genau solche Inhaltslücken für den Gegencheck sichtbar machen; das Füllen ist redaktionell.

**Offen:** `contact`-Body füllen (redaktionell). URL-Scheme: neue TEI-Slugs weichen von den alten WP-Pfaden und teils vom Menü ab; `navigation.yaml` und Redirects noch nicht nachgezogen. TEI-Header bewusst minimal — offen, ob/was ergänzt wird.

**Nächster Einstieg:** Nach dem Gegencheck der Kolleginnen die gemeldeten Inhalts-/Header-Korrekturen je Seite in `pages/*.xml` einarbeiten; parallel die URL-Scheme-Entscheidung (flache Slugs + Redirects vs. WP-Spiegelung) klären.

---

## 2026-06-21 — M3 Build-Cutover als Default-aus-Schalter, Reconciliation-Spur, URL-Scheme zurückgemeldet

**Ziel:** M3 Build-Cutover bauen (pages/-TEI mit Vorrang vor content/*.md) als lokale, nicht-gepushte Render-Spur; M4 scopen.

**Erledigt:** TEI-Editorialvorrang in `_render_editorials` hinter Schalter `tei_editorials` (Default zunächst `False`), Markdown-Fallback nur für nicht von TEI gedeckte Slugs (16 TEI + 5 Fallback). Voller lokaler TEI-Build als Spur (nicht ins Repo, `site/` ist gitignored). Per-Seite-Reconciliation-Diff TEI gegen Markdown als Operator-Spur: contact-Stub gegen volle Markdown-Seite, imprint Piwik gegen Matomo, divergierende Daten-Endpunkte, editorial/team/imprint voller, der Rest nahezu gleich.

**Entscheidungen:**
- Cutover als Default-aus-Schalter statt direkter Umverdrahtung. Grund: die order verlangt „pages-Vorrang verdrahten", „nicht nach main pushen (Push deployt)" und „alles in main" zugleich — nur ein Default-aus-Schalter vereinbart alle drei, Live-Gang = späterer operator-gated Default-Flip.
- Diff als Reconciliation geführt, nicht als Äquivalenzbeweis. Grund: das Editorial-Audit hat die Äquivalenzannahme bereits widerlegt; die Quellbestände sind verschiedene Dokumente, der Diff liefert die per-Seite-Entscheidungsgrundlage.
- URL-Scheme nicht eigenmächtig umgebaut. Grund: die order-Anweisung „WP-Pfade spiegeln" erreicht ihr Ziel nicht (die Spiegel-Pfade sind keine realen Live-URLs), bricht den gepinnten R17-Vertrag und wirkt nach außen — zurück an den Operator.

**Offen:** URL-Scheme-Entscheidung (flach + Redirects vs. echte WP-Spiegelung) blockiert Redirect-Finalisierung und Live-Cutover. contact-Reconciliation (Stub füllen oder Markdown behalten). value=1 (M4) bleibt operator-gated.

**Nächster Einstieg:** Auf die URL-Scheme-Entscheidung warten; bei „flach" die Redirect-Strecke finalisieren und `EDITORIAL_REDIRECTS` um die neuen Slugs ergänzen; sonst die contact/imprint/data-Reconciliation als Vorlage ausarbeiten.

### M4 value=1-Korrektur (gescoped, nicht gebaut)

R9-Charts und R1-Sidebar zählen heute flach `<num value="1">` als „Ja". Korrekt ist die echte Ja-Rate über `Questionnaire.questions`/`selected`: pro binärer Frage zählt, ob die Ja-Option gewählt ist; kategoriale Fragen separat ausweisen statt in die Ja-Rate mischen. Operator-gated, erst nach Freigabe bauen.

---

## 2026-06-21 — TEI-Konsumtions-Audit, Element-Coverage-Lock eingezogen

**Ziel:** Die Frage „kommt alles aus dem TEI im Frontend an" systematisch über die volle Element-Inventur beider Korpora beantworten, nicht feldweise.

**Erledigt:** Jeden Element- und Attributpfad aus `pages/*.xml` und `issues/**/*.xml` gegen die Referenzmenge aller `src/parser/*.py` gestellt und jeden Treffer am echten TEI trianguliert. Ergebnis: kein still verschluckter Inhaltsträger; die Treffer sind teiHeader-Verwaltung, leere Platzhalter (`<gloss/>`, `<desc/>`) oder Präsentationsmarkup, das kein Journal-Frontend rendert. Aus dem Einmal-Audit eine dauerhafte Absicherung gemacht: `tests/test_tei_coverage.py` prüft, dass die Korpus-Element-Inventur Teilmenge einer bewusst klassifizierten Universumsmenge ist; ein neues, nie klassifiziertes Element macht den Test rot.

**Entscheidungen:**
- Coverage-Lock autonom gesichert statt nur als Befund dokumentiert (Prinzip: Drift fixen statt wegdokumentieren). Die belastbare Antwort auf „wird alles getestet" ist, es testbar zu machen.
- Lock bewusst auf Element-Granularität begrenzt. Attributwert-Diskriminierung (`@type`, `num/@value`) liegt darunter und bleibt Sache der feldweisen Parser-/Render-Tests — genau dort saßen die zwei bekannten Punkte (reviewed-resource publication_date, value=1).

**Offen:** Attributwert-Ebene hat keinen analogen Lock — ob ein solcher lohnt, ist offen. Editorial-Seitenkörper (`page.py`) hat keinen element-mapping-Kontrakt wie der Review-Body, ist aber jetzt vom Coverage-Lock mitgedeckt.

**Nächster Einstieg:** M3-Reconciliation-Vorschlag je divergierender Editorialseite (`contact`, `imprint`, `data`), oder auf die Operator-Entscheidungen zu URL-Scheme und value=1 warten.

---

## 2026-06-21 — Factsheet-Parität verifiziert, reviewed-resource Publikationsdatum ergänzt

**Ziel:** Das Factsheet (R18) Feld für Feld gegen die Live-Seite stellen, die alte Lückenliste prüfen, reale Restlücken schließen.

**Erledigt:** Live-Factsheet (makingandknowing) vollständig gegen das gerenderte Factsheet verglichen. Die als offen geführten Lücken (Reviewer-ORCID, E-Mail, Affiliation, Date-of-Last-Access, Personnel-Rollenlisten) sind längst implementiert — die Liste war veraltet. Eine reale Restlücke geschlossen: die rezensierte Ressource trägt `<date type="publication">`, der Parser zog bisher nur `type="accessed"`; `RelatedItem.publication_date` ergänzt, im Parser extrahiert, im Factsheet zwischen URI und Last accessed gerendert.

**Entscheidungen:**
- Fix als treuer additiver Paritäts-Fix gesichert: gibt ein in TEI-Quelle und Live-Seite vorhandenes Feld wieder, reversibel, durch Test belegt, keine strittige Wahl.
- Kein Fix für die Live-Differenz Publikationsdatum gegen „Last Updated": die TEI trägt nur `2026-05`, die Live-Anzeige `Mar 2026` stammt aus WordPress-Metadaten außerhalb der Quelle — wir geben die Quelle treu wieder.

**Offen:** Rigoroser Abgleich der Personnel-Zählung und der Questionnaire-Sektionsüberschriften braucht das rohe Live-HTML, nicht den WebFetch-Auszug. M3-Editorial-Reconciliation und value=1 unverändert operator-gated.

**Nächster Einstieg:** M3 Reconciliation-Vorschlag je divergierender Editorialseite ausarbeiten, oder auf die Operator-Entscheidungen warten.

---

## 2026-06-21 — Editorial-Paritätsaudit: M3 ist Reconciliation, nicht Quelltausch

**Ziel:** Das editoriale TEI-HTML gegen die bisherige Markdown-Ausgabe diffen, um vor jeder Freigabe zu zeigen, welche Seiten sich beim Cutover ändern.

**Erledigt:** Paritätsaudit über alle Editorialseiten, je Slug Body-Vergleich beider Renderstrecken. Renderer als treu belegt: `publishing-policy` ist über beide Pfade byteidentisch, die Divergenz aller anderen Seiten liegt im Inhalt der Quellbestände, nicht im Rendering. Lokale Sichtungsspur aller 16 TEI-Seiten gerendert (Wegwerf).

**Entscheidungen:**
- M3 neu gefasst, kein mechanischer Cutover, sondern Editorial-Reconciliation. Die frühere Äquivalenz-Annahme war falsch und ist offen korrigiert.
- Architekturtrennung festgehalten: die generator-nativen Seiten (`data`, `data/charts`, `data/questionnaires`, `about`) bleiben auf der Generatorseite und werden nicht durch TEI ersetzt — Tatsache, keine redaktionelle Wahl.

**Offen:** Redaktionelle Einzelentscheidung je divergierender Seite (`contact` Stub gegen voll, `imprint` Piwik gegen Matomo, `data`-Endpunkte). Slug-Entscheidungen und URL-Scheme-Frage. value=1 operator-gated.

**Nächster Einstieg:** Factsheet-Paritätsanalyse — das Live-Factsheet Feld für Feld gegen `questionnaire.py` stellen und die Lückenliste als R-Klausel-Ergänzung formulieren.

---

## 2026-06-21 — Editorialseiten komplett (16/16): TEI-Migration plus verbatim Code

**Ziel:** Die Editorial-Migration abschließen — die drei wegen einer Profilentscheidung zurückgestellten Seiten (writing-guidelines, publishing-policy, criteria) nach TEI überführen, das Seitenprofil nur so weit erweitern, wie der reale Inhalt es erzwingt. Plus: Journal kanonisch nach `knowledge/journal.md`.

**Erledigt:** Profilentscheidung am Inhalt getroffen: publishing-policy und criteria sind reine Prosa und passen ohne Profilumbau; das einzige Bild auf criteria ist WordPress-Dekoration und entfällt. writing-guidelines erzwingt verbatim Code (TEI-Header- und Python-Beispiel) — Seitenprofil minimal um Block `<eg>` und Inline `<code>` erweitert (Schema, Modell, Parser, Renderer). Damit 16/16 Editorialseiten als TEI. Schema-Verifikationslücke geschlossen: neuer Test validiert jede `pages/*.xml` gegen `ride-pages.rng`. Journal per `git mv` nach `knowledge/journal.md` umgezogen, Verweise nachgezogen.

**Entscheidungen:**
- Seal als Chrome verworfen, nicht modelliert. Ein dekoratives Badge mit leerem Linktext rechtfertigt keine figure/graphic-Familie im minimalen Seitenprofil; bei Bedarf über Template/CSS reintegrierbar.
- Code als `<eg>` plus inline `<code>`, nicht egXML oder figure. TEI-idiomatisch für literale Beispiele, schema-minimal.
- writing-guidelines wortgetreu aus der Live-Quelle (nicht in `content/` vorhanden); Verbatim-Korrektheit ist vor dem Cutover noch menschlich zu prüfen.

**Offen:** Build-Cutover (pages/ mit Präzedenz) unverändert verhaltensändernd und nicht verdrahtet, operator-gated mit Render-Spur, hängt zusätzlich an URL-Scheme und About-Landing-Frage. value=1-Zählfehler weiter operator-gated. writing-guidelines-Verbatim-Sichtung durch die Redaktion.

**Nächster Einstieg:** Build-Cutover scopen und als Spur vorbereiten — den `pages/`-Renderpfad vor `content/*.md` schalten, lokal einen Voll-Build erzeugen, das editoriale HTML gegen die Markdown-Ausgabe diffen. Nicht nach main bis Operator-Freigabe und URL-Scheme-Entscheidung.

---

## 2026-06-21 — Factsheet-Parität: R18-Kontrakt plus Factsheet-Vollseite (R18)

**Ziel:** Das Live-Factsheet rendert den vollständigen Fragebogen als eigene Unterseite; ride-static zeigt bislang nur eine Aggregat-Box in der Sidebar. Ziel: die Volldarstellung unter `/issues/{N}/{id}/factsheet/`, inklusive Bau und Redirects.

**Erledigt:** Feldabgleich Live-Factsheet vs. Domänenmodell gegen den TEI-Header der Referenz-Review geerdet. Befund: die meisten Felder lagen bereits im Modell vor; drei Lücken (Questionnaire-Modell verwarf Frage-Label/Volltext/K-Ref, `RelatedItem` erfasste die Personnel-Beteiligten nicht) waren additiv zu ergänzen. Selektions-Semantik am Korpus verifiziert: der `<num value>` kodiert die Auswahl, „Yes"-Leafs tragen sowohl value=1 als value=0; pro Frage ist die gewählte Antwort die Menge der value=1-Leafs (binär genau eine, kategorial mehrere), value=3 = Anomalie. R18 als Spezifikations-Kontrakt in specification.md festgehalten. Gebaut: `QuestionnaireQuestion` plus `Questionnaire.questions`, `RelatedItem.personnel`, Render-Modul `factsheet.py` und Template, Factsheet-Unterseite plus „Full factsheet"-Sidebar-Link und Legacy-Redirect. Beide Taxonomie-Familien inhaltlich geprüft.

**Entscheidungen:**
- Volle Unterseite in einem Zug (Operator-Entscheidung), nicht nur Analyse oder Redirects; Reviewer-Kontaktdaten wie auf der Live-Site inklusive obfuskierter E-Mail.
- Implementierung an einen Opus-Subagenten delegiert, Abnahme beim Lane-Kopf — die Kopplung über Modell/Parser/Render/Template/Build rechtfertigte einen fokussierten Implementierer; das Ergebnis gegen Git, Tests und gerenderten Inhalt verifiziert.
- Sidebar-Aggregation nicht angefasst — der Bau ist strikt additiv. Die bestehende Sidebar zählt value=1-Leafs als „yes", was gewählte Optionen zählt, nicht bejahte Fragen (latenter R1/R9-Fehler, eigene Entscheidung).

**Offen:** Sidebar-`yes_count`-Semantik (betrifft R1 und R9) — vor einer Korrektur zu entscheiden, ob die Charts dieselbe Zählung verwenden. Kosmetik Text-Collections-Familie: Sektions-Labels erscheinen als xml:ids, weil diese Kriterienfamilie die Sektionsüberschrift nicht als `catDesc` führt. Bild-URL-Konvention, Sender-Workflow-Installation, Staging-Variantenwahl unverändert gated.

**Nächster Einstieg:** Operator-Sichtung der Factsheet-Seite im Browser; danach Entscheidung zur Sidebar-/Charts-Zählung. Falls gewünscht, ein Label-Mapping für die Text-Collections-Sektionslabels im Render.

---

## 2026-06-12 — Redaktioneller Zielworkflow: Abgleich, Staging-Dokument, Trigger-Verkabelung

**Ziel:** Den Zielworkflow der Redaktion (ride-editors → Testumgebung → Freischaltung) gegen die gebaute Pipeline abgleichen und die entscheidungsrobusten Teile sofort umsetzen.

**Erledigt:** Abgleich ergab: die Freischaltung per Git-Move ist abgedeckt, die passwortgeschützte Testumgebung ist unbeplant. `knowledge/staging.md` als Entscheidungsvorlage angelegt (Anforderung, fünf Lösungsoptionen, Repo-Bestandsaufnahme, Gesprächsagenda). Bestandsaufnahme: `ride-editors` ist privat und trägt eine klare Ablagekonvention; publizierte Beiträge verbleiben dort (Dubletten-Befund → Dedupe-Pflicht). Trigger-Verkabelung umgesetzt: `build.yml` nimmt `repository_dispatch` an, Sender-Vorlagen plus Anleitung unter `docs/upstream-workflows/`. README um „Editorial workflow" ergänzt. Lane-Drift aufgelöst: `origin/main` war seit dem Monorepo-Schnitt fünf Commits voraus, gemerged (fünf Konflikte) und die Tagesarbeit aufs Monorepo-Layout nachgezogen.

**Entscheidungen:**
- Wordclouds bleiben manuell geliefert — programmatische Generierung würde den gestalteten Charakter zerstören; `{slug}-wordcloud.png` wird bei Publikation kopiert.
- Draft-Mechanik (unverlinkte Vorschau im öffentlichen Build) zurückgestellt — die Varianten-Wahl will der User erst mit den Editorinnen diskutieren; `ride-editors` ist privat, eine öffentliche Vorschau machte Inhalt erstmals zugänglich.
- Statusfreie Plan-Dokumente übernommen (von origin/main): Status lebt im Journal und README, nicht im Phasenplan.
- Glossar nur im INDEX: die „Eigenbegriffe"-Sektion in architecture.md durch einen Verweis aufs INDEX-Glossar ersetzt (eine Definitionsstelle pro Begriff).

**Offen:** Factsheet-Parität (Feld-Abgleich, eigene Unterseite, Redirects). Staging-Entscheidung mit der Redaktion. Sender-Workflow manuell installieren (Repo-Admin). Bild-URL-Konvention für neue TEI. Restposten 2026-05-09: interface.md-Spaltung, site/-Eincheck-Frage, WCAG-Vollaudit, Matomo-CI-Secrets.

**Nächster Einstieg:** Factsheet-Parität — Live-Factsheet (makingandknowing) Feld für Feld gegen `questionnaire.py` stellen und die Lückenliste in specification.md als R-Klausel-Ergänzung formulieren.

---

## 2026-05-12 — Doku-Refactor: README schlanker, Status-Single-Source, build() zerlegt

**Ziel:** Dokumentations- und Code-Refactor: README straffen, das nicht-deklarierte Duplikat `prozess-und-stand.md` auflösen, Status-Marker aus den Plan-Dokumenten ziehen, `build()` zerlegen.

**Erledigt:** README deutlich gekürzt (Layout-Duplikat, Pointer-Tabelle, Setup, Skript-Tabelle und CI-Schritte zu CLAUDE.md/CONTRIBUTING ausgelagert, Status-Absatz in Feature-Sprache statt Phasen-Nummern). `prozess-und-stand.md` (nicht im Vault-Layout deklariert) gelöscht, Glossar-Terms nach architecture.md migriert. Status-Single-Source festgelegt und alle done/partial/Welle-Marker aus Phasenplan, Stages-Tabelle und interface.md entfernt; Sentinel „static plan, not a tracker" gesetzt. `build()` durch fünf benannte Helper (`_run_parse_pass`, `_check_corpus_consistency`, `_run_render_pass`, `_run_validation_layer`, `_print_build_summary`) als Neun-Schritt-Sequenz lesbar gemacht.

**Entscheidungen:**
- Plan-Dokumente bleiben zeitstempel- und statusfrei; eine erweiterte Phase wird umgeschrieben, nicht mit Statusmarkern ergänzt. Grund: vier Status-Single-Sources garantieren Drift.
- `build()` als innere Faktorierung in einer Datei statt als Paket. Grund: die Helper sind klein und einmal aufgerufen, ein Paket addierte Indirection ohne Gegenwert.
- Methodologie-Inhalt aus `prozess-und-stand.md` nicht migriert (Duplikat oder historisches Artefakt); falls als eigenständige Doku gewollt, wäre `docs/methodology.md` der Ort — auf Anfrage offen gelassen.

**Offen:** Keine direkten Folgepunkte. Aus der Roadmap weiter offen: WCAG-Vollaudit, Matomo-URL als CI-Secret, Knowledge-Doc-CI-Verhalten (strict vs. auto-commit), Custom-Domain.

**Nächster Einstieg:** Aus den Phase-15-Restposten — am einfachsten Matomo-URL als CI-Secret (nur Repo-Secret setzen und Workflow verdrahten); die anderen brauchen redaktionelle oder externe Entscheidungen.

---

## 2026-05-12 — Monorepo-Schnitt: TEI-Korpus + Schema in ride-static eingezogen

**Ziel:** Den TEI-Korpus aus `i-d-e/ride` ins eigene Repo holen, damit ride-static nicht mehr von einem zweiten Checkout abhängt, und die Issue-Metadaten neben den TEI-Dateien gruppieren.

**Erledigt:** 111 TEI-Reviews per `biblScope @n` nach `issues/{N}/reviews/{slug}-tei.xml` einsortiert, Schema nach `schema/` im Repo-Root, 22 Issue-Configs nach `issues/{N}/metadata.yaml`. Neues Helfermodul `src/_corpus.py` ersetzt den verteilten `REPO_ROOT.parent / "ride" / "tei_all"`-Pattern in ~35 Dateien; alle Pfad-Konstanten und Globs umgestellt, Test-Dateien auf `find_tei("slug")` migriert. CI verschlankt: `i-d-e/ride` wird nur noch wegen der Picture-Assets geklont. Doku synchronisiert (inkl. „107 reviews" → „111 reviews").

**Entscheidungen:**
- Per-Issue-Layout `issues/{N}/{metadata.yaml, reviews/*}` statt flachem `corpus/tei_all/`. Grund: alles zu einem Issue an einem Ort; die TEI-Header-Zuordnung (`biblScope @n`) bleibt kanonisch statt einer zweiten YAML-Wahrheit.
- Schema unter `schema/` im Root, nicht unter `corpus/`. Grund: Schema ist Validierungs-Vertrag, nicht Korpus-Inhalt.
- Pictures bleiben vorerst im Sibling `i-d-e/ride` (Repo-Größe, LFS-Quota); die Asset-Pipeline degradiert sauber, wenn der Sibling fehlt.
- `src/_corpus.py` als zentrale Pfad-Wahrheit, damit die nächste Layout-Änderung nur ein Modul anfasst.

**Offen:** Bilder-Migration (~437 MB, vermutlich via Git-LFS, eigene Session). `RIDE_ROOT` zeigt noch auf den Sibling — entfällt erst mit den Bildern. Knowledge-Doku-CI-Drift (generiertes data.md vs. Korpus). Phase 15.B (WCAG, Matomo-Secrets, Custom-Domain).

**Nächster Einstieg:** Lokal `python -m src.build` ohne `../ride/` laufen lassen und prüfen, dass der AssetReport fehlende Bilder sauber meldet statt zu crashen — dann ist die Layout-Migration end-to-end verifiziert.

---

## 2026-05-09 — Knowledge-Vault auf Promptotyping-Konvention gehoben

**Ziel:** Den `knowledge/`-Ordner als sauberen Promptotyping-Vault refactoren — Frontmatter-Pflichtkern, Funktionsabbildung, Hybrid-Dokument `prozess-und-stand.md` auflösen, INDEX als Navigationsknoten anlegen. Parallel das Promptotyping-Paper im Obsidian-Vault auf den Stand der Konvention bringen.

**Erledigt:** Frontmatter-Lift auf alle Knowledge-Dateien (Pflichtkern plus topics/related), generierte Docs behalten ihr `generated:`-Frontmatter. `requirements.md` → `specification.md` umbenannt (`git mv`), Wikilinks und Code-Erwähnungen nachgezogen, `aliases: [requirements]` als Puffer. `INDEX.md` angelegt (Dokumentenmatrix in Funktions-Reihenfolge, vier Lesepfade, Glossar, „Was fehlt und warum"). `prozess-und-stand.md` sektionsweise gegen Zielstellen geprüft und aufgelöst; drei Inhalte gerettet (Personenliste nach specification §3, Promptotyping-Methode-Anker nach architecture, Migrationstabelle nach specification §8). Paper im Obsidian-Vault gepatcht (Two Modes, drei strukturelle Commitments statt Acht-Funktionen-Liste).

**Entscheidungen:**
- Function before filename als strukturelles Argument, nicht als Funktions-Liste mit Zähler. Grund (ide-Einwand): die Zahl ist Beifang; korrekt sind drei Commitments (function before filename, inclusion by trigger, diagnostic decoupling).
- `requirements.md` umbenannt statt nur Topic ergänzt; specification.md ist der kanonische Träger der Substanz-Funktion, History via `git mv` erhalten.
- `design.md`/`ui.md`-Spaltung als spätere Aktion offen gelassen — invasiv genug für eine eigene Session; INDEX markiert die Lücke.
- `prozess-und-stand.md` vollständig aufgelöst statt zu `overview.md` reduziert. Eine Funktion pro Stelle ist Konvention; ein Hybrid widerspricht dem.

**Offen:** interface.md in design.md + ui.md spalten. architecture.md und pipeline.md als gespaltene Bauweise koppeln (Lead-Hinweis am Kopf). CLAUDE.md auf design.md als Werteebene verweisen (wartet auf die Spaltung). Vault-Konvention parallel zum Paper umbauen. README veraltet. site/ ist eingecheckt — klären, ob raus oder begründen.

**Nächster Einstieg:** interface.md in design.md (Designhaltung) + ui.md (Layout/Seitentypen/Typografie/A11y) spalten, CLAUDE.md um eine Designprinzipien-Sektion plus „vor UI-Generierung design.md lesen" ergänzen. Wenn nicht im Knowledge-Refactor: Phase-15-Restposten (WCAG-Audit oder Matomo-Secrets).

---

## 2026-04-29 — Phase 10-Rest: Data-Charts (R9) live

**Ziel:** Aggregierte Bar-Charts auf `/data/charts/` aus dem realen Korpus statt des stehenden Placeholder-Markdown.

**Erledigt:** Renderer `src/render/charts.py`: kanonische Slug-Map über die vier Kriterien-URLs (drei logische Sets), per Slug nach Top-Level-Section über das geparste Korpus aggregiert, inline-SVG-Bar-Chart mit Achsen-Ticks und In-Bar-Annotation, getrennte value=3-Anomalie-Note. Parser-Helfer liest die `<taxonomy>`-Struktur per criteria_url (innerhalb eines Reviews mehrere Taxonomien derselben URL gemerged, dann über alle Files vereinigt). Marker-Substitution `<!-- ride:charts -->` im Editorial-Renderer.

**Entscheidungen:**
- Kanonische Slug-Map als hartkodiertes Dict statt Heuristik. Grund: vier URLs sind ein geschlossenes Set; eine fünfte fällt sauber durch den Slug-Fallback, nur ohne hübschen Label.
- `(other)`-Bucket als Drift-Sensor: ein Leaf außerhalb jeder geparsten Taxonomie wird nicht verworfen, sondern landet im Bucket; ein Test pinnt, dass er über das echte Korpus nicht entsteht.
- Marker-Pattern statt Sonder-Template: Editor:innen sehen die Position, können ohne Build vorschauen.
- Auf Top-Level-Sections aggregiert, nicht pro Leaf: hunderte Leaves wären unbrauchbar, 5–8 Sections sind lesbar (R9-Akzeptanz).

**Offen:** Phase-15-Restposten (WCAG, Matomo, Knowledge-Doc-CI, Custom-Domain). Inhaltlich kein offener Brocken mehr nach Phase 10. 39 fehlende Wordclouds (kosmetisch).

**Nächster Einstieg:** Phase-15-Restposten — am ehesten WCAG-Vollaudit über die Live-Site mit axe-DevTools, oder Matomo-URL/Site-ID als CI-Secrets verdrahten.

---

## 2026-04-29 — Phase 14 + 15.A: PDF live, Compliance-Block geschlossen

**Ziel:** Die verbliebenen Compliance- und UX-Items (Kontaktseite R14, Cookieless-Matomo R16, Lizenzhinweise N6, WCAG-Polish N5) abräumen und Phase 14 (PDF aus Domänenmodell) implementieren, damit der tote Sidebar-PDF-Link produktiv wird.

**Erledigt:** Phase 15.A: Contact-Seite mit zwei Mail-Adressen, Console-Banner mit Build-Commit (silent ohne build_info), `licence: {name, url}` in den JSON-Artefakten, cookieless Matomo via `--matomo-url`/`--matomo-site-id` (gated auf beide Felder), generisches `:focus-visible` über alle interaktiven Elemente, Tag-Pills `min-height: 24px` für WCAG 2.5.8. Phase 14: `src/render/pdf.py` mit lazy-importierter WeasyPrint, PDF-Geschwister je HTML, print-only DOI-Zeile im Header, ausgebautes Print-Stylesheet; CI installiert GTK/Pango und ruft `--pdf` auf. WeasyPrint-Tests skippen sauber, wenn GTK fehlt.

**Entscheidungen:**
- PDF reuses HTML, kein separates Template. Grund: WeasyPrint schluckt das fertige `index.html`, `@media print` strippt Chrome — kein zweiter Template-Baum, eine Drift-Quelle weniger.
- DOI-Zeile als print-only Element (`display:none` default, `block` im Print). Grund: A6 verlangt DOI auf Seite 1, im Web zeigt die Meta-Sidebar sie bereits.
- Matomo-Snippet gated auf beide Felder (`parser.error` bei nur einem). Grund: ein halbkonfigurierter Deploy sendete sonst still mit leerer Site-ID.
- WeasyPrint-Import in `try/except (ImportError, OSError)`. Grund: lokaler Windows-Stand hat WeasyPrint, aber GTK fehlt → OSError aus ctypes; `importorskip` allein fängt das nicht.

**Offen:** CI-Run für Phase 14 läuft noch (erste WeasyPrint-Verifikation auf Linux); bei Erfolg wird der Sidebar-PDF-Link live, A6 erfüllt. Data-Charts (R9, Phase-10-Rest) nicht angefasst — letzter offener inhaltlicher Brocken. 39 fehlende Wordclouds (kosmetisch). pipeline.md-Phasentabelle noch nicht auf Phase 14 „done".

**Nächster Einstieg:** Den CI-Run prüfen; wenn grün, Phase 14/15 im Stand vermerken und `memory/project_phase.md` aktualisieren. Dann Data-Charts angehen — Einstiegspunkt: ein neues `charts.py`-Modul, das pro Kategorie ein Bar-Chart-SVG aus den value=0/1-Antworten produziert.

---

## 2026-04-28 — Backend Session-Ende: Test-Refactor-Welle 2 angestoßen, Übergabe

**Ziel:** Nach Phase-7-Abschluss eine zweite Test-Refactor-Welle gegen die neue Real-Corpus-Drive-Hard-Rule anstoßen — den Phase-7-Audit auf den Rest der Suite anwenden, statt Schulden mitzunehmen.

**Erledigt:** `test_parser_review.py` von synthetischen Fixtures auf Real-Corpus umgestellt (drei reale Reviews: 1641 für Metadaten + Sections, bayeux für Figures/Notes, tustep für No-Back). Korpus-Probing für die nächste Welle dokumentiert (1641 als Maximalfall, ehd für Editor-ohne-ORCID, busoni-nachlass für Author-ohne-ORCID), damit der nächste Claude direkt schreiben kann. Cross-Contamination beim Commit (siehe Offen).

**Entscheidungen:**
- Test-Refactor-Welle 2 in vier kleinere Schritte gesplittet (Review, Metadata, Sections/Blocks, Model); jeder Schritt ein einzeln prüfbarer Commit.
- `test_model.py` Field-Echo-Tests bleiben: sie sind der Vertragstest für die Domänen-Dataclass (pinnen `tuple[...]` und `frozen=True`); die Audit-Bewertung „Tautologie" war zu hart.
- Antwort auf die `#abb`/`#img`-Frage des Frontend-Claude: Korpus-Bug, kein Resolver-Alias. Grund: ein Alias hebelte die „anomalies are explicit"-Regel aus; stattdessen wird Phase 13 (Validierung) jede nicht auflösbare Ref als Build-Warning melden, der Resolver bleibt korrekt.

**Offen:** `test_parser_metadata.py` auf Real-Corpus (Fixtures benannt: 1641, ehd, busoni-nachlass; die rein-defensiven Branches existieren im Korpus nicht, dort bleibt synthetisch). `test_parser_sections.py`/`test_parser_blocks.py` audit-Pass (Dispatcher synthetisch, Walker auf Real-Corpus). Hygiene-Incident: ein Commit zog Fremd-Code-Pfade mit; künftige Regel: vor jedem Commit `git diff --cached --stat` prüfen. `#abb`-Korpus-Bug als Phase-13-Schematron-Erwartung dokumentiert. Wayback-Hint deferred → Phase 13.

**Nächster Einstieg:** Welle 2 mit `test_parser_metadata.py` fortsetzen (Fixtures stehen), dann `test_parser_sections.py`/`test_parser_blocks.py`. Danach Phase 12 (OAI-PMH/JSON-LD/Sitemap) oder Phase 13 (Validierung inkl. `#abb`-Schematron und Wayback-Hint).

---

## 2026-04-28 — Frontend: Phase-7-Integration abgeschlossen (Buckets + Asset-Pipeline)

**Ziel:** Den Backend-Output von Phase 7 (Reference.bucket + rewrite_figure_assets) ans Rendering anschließen — Cross-Refs je Bucket gestylt, eingebettete Bilder lokal serviert, HTML auf die Deploy-URL zeigend.

**Erledigt:** Reference-Bucket: das `reference()`-Macro emittiert `ride-ref--{local|criteria|external|orphan}` per `element-mapping.yaml`; Orphans rendern als nicht-klickbarer `<span>` (kein toter Link), Externe mit `rel="noopener noreferrer"`. Asset-Pipeline: der Build ruft `rewrite_figure_assets` und sammelt einen `AssetReport` (copied/missing/unparseable). `media_path_factory(base_url)` prefixt root-absolute URLs mit `base_url` (für GH-Pages unter `/ride-static`), lässt `http(s)://` unverändert; Macros via `import … with context`. Smoke-Build über fünf Reviews: Bilder kopiert, anemoskala-URLs ohne Extension als missing erkannt (Korpus-Quirk).

**Entscheidungen:**
- `media_path` als per-render Closure (Factory) statt Jinja-Filter — Filter sind env-global und können `base_url` nicht pro Build aufnehmen.
- Macros via `import … with context`: minimaler Eingriff, keine Signatur-Änderung.
- Orphan-Rendering bleibt nicht-klickbarer `<span>` mit `data-target` zur Diagnose, damit Lesefluss und A11y nicht durch broken links leiden.
- Anemoskala-Bilder nicht „repariert" — das Frontend verlinkt das, was im TEI steht; fehlende Extensions sind Korpus-Issue für Phase 13 oder ein Backend-Patch.

**Offen:** Cross-Contamination: Backend zog acht Frontend-Dateien in seinen Test-Refactor-Commit (Code im Tree, Attribution falsch) — beim nächsten Commit `git add <pfad>` statt `-A`. `#abb` → `#img`-Orphan-Quirk: Body referenziert `#abb1`, Figur trägt `xml:id="img1"`; Frage an Backend (Alias oder Phase-13-Meldung) — heute geht die UX leer aus. WCAG-Audit, PDF (Phase 14), Matomo + Redirects (Phase 15) als nächste Frontend-Brocken.

**Nächster Einstieg:** Phase 11 (Pagefind) oder Phase 12 (OAI-PMH/JSON-LD/Sitemap) als nächste ungeöffnete Phasen. Vorab pushen, GH-Pages-Deploy laufen lassen, im Live-Build die `ride-ref--*`-Klassen und die `/issues/.../figures/`-Bilder verifizieren.

---

## 2026-04-29 — Phase 7 abgeschlossen, Reference-Resolver + Asset-Pipeline live

**Ziel:** Aspekt A aus WORKPLAN — Vier-Bucket-Resolver, Asset-Pipeline, Test-Refactor auf Real-Corpus-Drive.

**Erledigt:** `Reference.bucket` plus `src/parser/refs_resolver.py` (`classify_target` pure, `resolve_references` als Post-Pass mit Re-Aggregation für Figures/Notes-Identity), eingehängt in `parse_review`. `src/parser/assets.py` mit `rewrite_figure_assets` und `AssetReport` (URL-Rewrite Korpus → site-relativ, Disk-Pfad aus dem Sibling, fehlende Files als Report statt Crash). Test-Daten-Philosophie als Hard Rule in CLAUDE.md verankert, Phase-7-Tests auf Real-Corpus refaktoriert.

**Entscheidungen:**
- `Reference.bucket` als Inline-Feld statt paralleler Map — kleinster Eingriff, keine zwei Strukturen zu synchronisieren.
- `criteria`-Bucket bleibt im Vertrag trotz 0 Body-Vorkommen: alle K-Refs leben im Header (`<catDesc>`), wo der Body-Parser nicht traversiert — Future-Proofing.
- Asset-Modul in `src/parser/assets.py` statt `src/build/assets.py` — das Frontend hält `src/build.py` als Datei, ein Geschwister-Package kollidierte.
- Wayback-Hint deferred → Phase 13 (HTTP-Probe gehört in den Validation-/Bericht-Schritt, nicht in den Resolver).

**Offen:** Frontend integriert Buckets (`by_bucket`) und ruft `rewrite_figure_assets` in `src/build.py`. Wayback-Hint für Phase 13. Phase 12 (OAI-PMH/JSON-LD/Sitemap) und 13 (Validierung) als nächste Backend-Sprints.

**Nächster Einstieg:** Frontend-Integration abwarten; falls Backend parallel arbeitet, Phase 11 (Pagefind in `src/build.py`) als überbrückendes Vorzieh-Stück.

---

## 2026-04-29 — Phase 6 abgeschlossen, Stage 2.C steht

**Ziel:** Bibliography- und Questionnaire-Modell plus Cross-Korpus-Aggregate (Tags, Reviewer, Reviewed Resources) in einem Schub — der Datenvertrag für Rezensions- und Aggregationsseiten.

**Erledigt:** `BibEntry` plus `parse_bibliography` (strukturierte Bibliographie aus dem `<back>`-Pfad, gegen Inline-cit und Header-relatedItem gefiltert; `Review.bibliography` als Feld). `Questionnaire` plus `QuestionnaireAnswer` mit Walker über `teiHeader//taxonomy`, der nur Leaf-Categories sammelt (sonst erben Sections die Descendant-Nums); value=3-Anomalie als String erhalten. `src/parser/datasets.py` mit drei Cross-Korpus-Aggregaten (Tags case-insensitive gemerged, Reviewer per ORCID dedup, Resources per Target-URL dedup), alle sortiert für reproduzierbare URLs. (Ein Commit zog versehentlich Frontend-Files mit — Hygiene-Lehre.)

**Entscheidungen:**
- `<listBibl>` lebt auf `Review.bibliography`, nicht in den Section-Blocks. Grund: Bibliographie ist strukturell separat, ein Feld-Typ ist sauberer als ein Block-Kind im Tree.
- `BibEntry` ohne strukturierte Sub-Felder. Grund: das Korpus nutzt `<bibl>` als annotiertes Freitext-Zitat; R2 (Citation Export) zielt auf die Rezension, nicht ihre Bibliographie.
- Questionnaire-Parser sammelt nur Leaves. Grund: das Stage-0-Script over-attribuiert per `cat.iter()` jeden Num-Wert an alle Vorfahren; für die Domänen-Schicht gehört die Antwort dem Leaf.
- value=3 als String erhalten statt sentinel-int, damit ein Renderer `"0"`/`"1"` matchen und „3" separat behandeln kann, ohne dass der Parser inhaltlich entscheidet.
- Aggregat-Datasets in eigener Datei (getrennt vom per-review Aggregate-Walk) — unterschiedliche Concern-Klassen.

**Offen:** Phase 7 — Ref-Resolver (Vier-Bucket-Logik), Asset-Pipeline für `<graphic @url>`, Wayback-Detector. Sobald Phase 7 landet, kann das Frontend Tooltip-Vorschau und Bilder korrekt befüllen.

**Nächster Einstieg:** `src/parser/refs.py` mit `resolve_ref(...)` als Vier-Bucket-Funktion plus Asset-Pipeline-Vorbereitung (Bild-Pfade vom Sibling nach `site/`). Frühe Auslieferung priorisieren — der Frontend-Claude wartet darauf.

---

## 2026-04-29 — Phase 10 + Citation: Site hat ihre Außenhaut

**Ziel:** Aspekt B aus WORKPLAN — Citation-Daten so embedden, dass die `cite-copy.js`-Buttons funktionieren, plus die sechs Aggregations- und Übersichtsseiten bauen, damit die Site eine Navigations-Außenhaut bekommt.

**Erledigt:** Citation-Cleanup: `_to_bibtex`/`_to_csl_dict` als Jinja-Filter, zwei Embed-`<script>`-Blöcke in `review.html` (BibTeX mit Brace-Escape und `</`-Defence, CSL-JSON). Phase-10-Aggregationen: `src/render/aggregations.py` mit acht `render_*`-Entry-Points plus acht Templates (Startseite, Heftübersicht/-ansicht, Tags, Reviewer, Reviewed-Resources) und ein `review_card`-Partial; ersetzt den Platzhalter-Index. Davor eine Korpus-Reorganisation: `image-workflow.png` und `prozess-und-stand.md` aus dem Root nach `knowledge/` verschoben, CLAUDE.md-Regel auf „Markdown plus referenzierte Image-Attachments" relaxed.

**Entscheidungen:**
- Aggregationsseiten als eine Spalte ohne Sidebar (interface.md §4 — keine Apparate, keine Sidebar).
- BibTeX-Brace-Escape per Sentinel-Pass statt naivem Replace-Chain (naive Reihenfolge produziert kaputte `\textbackslash`-Sequenzen).
- Reviewer-Slug als `surname-forename` — stabil bei Namensgleichheit, lesbar in der URL.
- Tag-Liste als zweispaltige Markup-Liste (`column-count`) statt Word-Cloud — barrierefrei, scannbar, ohne Visualisierungs-Library.
- Data-Charts deferred bis Phase 7: ohne K-Ref-Auflösung wären die Achsen-Labels rohe IDs.

**Offen:** Phase 7 (Backend): sobald `Reference.bucket` am Modell liegt, Cross-Refs bucket-aware rendern; Bilder zeigen heute noch auf rohe TEI-`@url`. tooltip.js (bis Phase 7) und pagefind.js (bis Phase 11) sind Stubs. Heft-YAML-Schema noch nicht eingehängt — die Heftansichten generieren Metadaten aus den Review-Headern.

**Nächster Einstieg:** Live-Deploy auf GitHub Pages testen (Push triggert den Workflow mit `--base-url=/ride-static`), durchklicken. Parallel auf das Backend-Phase-7-Ergebnis warten — die Cross-Ref-Integration ist danach ein kurzer Patch in den Render-Macros plus CSS-Modifier.

---

## 2026-04-29 — Phase 8 First Light, Frontend rendert 107 Reviews End-to-End

**Ziel:** Aus dem Stage-2.B-Datenvertrag den ersten lauffähigen Frontend-Strang aufsetzen — Render-Macros, Rezensionsseiten-Template (interface §5), Render-Layer plus Build-CLI, CI-Workflow für GH-Pages. Ziel: ein `python -m src.build` baut alle Reviews ohne Raise.

**Erledigt:** Render-Macros (`partials/render.html`): rekursive Block-/Inline-Dispatcher auf `__class__.__name__`, BEM-Klassen aus `element-mapping.yaml`. Section-Partial rekursiv (h2..h4, h1 für den Seitentitel), Apparate-Partial als Dreispalten-Layout (leere Panels kollabieren, References-Slot wartet auf Phase 7). Rezensions-Template mit Kopf/Abstract/Body/Apparate/Sidebar. Render-Layer mit `ChainableUndefined`, drei Filtern und `SiteConfig`/`BuildInfo`. Build-CLI walkt, parst, rendert, kopiert static und Original-TEI, fängt Per-Datei-Failures. Voller Korpus-Build: 107/107 Reviews ohne Fehler. CI-Workflow mit Build- und Deploy-Job.

**Entscheidungen:**
- `ChainableUndefined` statt `StrictUndefined` — UI-Strings sind ein optional-tief-verschachteltes dict; Strict bliese jedes Template mit Default-Branches auf, Tippfehler an Domain-Objekten fängt der Test-Layer.
- Render-Macros zentral in einer Datei — rekursive Dispatcher müssen sich gegenseitig sehen, eine Datei pro Kind wäre Overhead.
- Block-Dispatch über `__class__.__name__` statt isinstance-Kette — parallel zur YAML-Konvention.
- Apparate kollabiert komplett ohne Figures/Notes statt leerer Panel (sonst wirkt es als Skelett-Bug).
- Build-CLI fängt Per-Datei-Failures, damit ein anomaler Review nicht den ganzen Lauf blockiert; Phase 13 macht daraus den Bericht.

**Offen:** Phase 7 (Resolver, Assets) — Voraussetzung für Tooltip-Vorschau und korrekte Figure-Pfade; Bilder heute broken. Phase 6 (Bibliography, Questionnaire) — füllt Bibliographie-Apparat und Sidebar-Factsheet. JS-Module sind referenziert, aber Stubs. CSS-Komponenten-Styles für Apparate/Sidebar fehlen. Aggregations- und Editorialseiten (Phase 9/10) noch nicht angelegt.

**Nächster Einstieg:** Editorial-Stubs plus `editorial.html` (vom Backend-Status unabhängig, gibt der Site eine Navigations-Außenhaut), dann die vier JS-Module als kleine ES-Module (zuerst copy-link und cite-copy). Sobald Phase 6 landet, Sidebar-Factsheet und Bibliographie-Apparat befüllen.

---

## 2026-04-29 — Phase 5 abgeschlossen, Stage 2.B steht; Rollen-Split etabliert

**Ziel:** Stage 2.B abschließen — `parse_inlines` überall einhängen, Block-in-Paragraph-Anomalie auflösen, `parse_review` integrieren, Figures/Notes-Aggregate materialisieren. Parallel die Koordinationsschicht zwischen Backend- und Frontend-Claude einrichten.

**Erledigt:** `parse_inlines` in alle Per-Kind-Parser eingehängt, Modell additiv erweitert (`Paragraph.xml_id`, `Figure.xml_id`/`alt`, Long-Tail-Inlines als Passthrough-Text). `parse_paragraph_or_split` zerlegt `<p>` mit Block-Kindern in alternierende Paragraph-/Block-Sequenz (erster Chunk erbt `@xml:id`/`@n`); ListItem/TableCell um `blocks`-Feld für nested Lists/Figures erweitert. `parse_review` zieht front/body/back; `src/parser/aggregate.py` als Tiefen-Walker für Figures und Notes in Dokumentreihenfolge; `<listBibl>` für Phase 6 markiert. Korpus-Smoke über alle Reviews durchläuft.

**Entscheidungen:**
- Drei Spec-Fragen aus dem UI-Audit beantwortet: figDesc warn (Phase 13), Wayback-Detector deferred (Phase 7), inline xml:lang auf Section-/Review-Level entschärft (Korpus markiert keine Inline-Sprache).
- `<listBibl>` skip-and-defer statt Placeholder-Block (Phase 6 ersetzt den Branch ohnehin, Placeholder wäre toter Code).
- Nested Blocks als `blocks`-Feld am ListItem/TableCell statt Mixed-Typ-Children; Order konventionell (Inlines first, Blocks second).
- Aggregate am Parse-Zeitpunkt materialisiert statt lazy — Templates bekommen pure Domänenobjekte (N1).
- Rollen-Split: Backend + Doku + Koordination = ich; Frontend = anderer Claude; Datenvertrag = Domänenobjekte; gemeinsame Doku = COORDINATION.md.

**Offen:** Phase 6 (Bibliography, Questionnaire, Aggregat-Datasets). Phase 7 (Ref-Resolver, Wayback, K-Ref-Auflösung). Phase 8 startet, sobald `Review.bibliography`/`Review.questionnaire` da sind, kann aber heute schon auf dem Stage-2.B-Modell arbeiten.

**Nächster Einstieg:** `src/model/bibliography.py` plus `src/parser/bibliography.py` für `<listBibl>`/`<bibl>`-Einträge (Korpus-Konvention prüfen, dann Synthetik + Real-Korpus-Smoke). Anschließend der Questionnaire-Parser für die `<num>`-Boolean-Antworten.

---

## 2026-04-29 — Phase 4 abgeschlossen, Inline-Parser steht

**Ziel:** Mixed-Content-Walker `parse_inlines(host)` für die sechs verifizierten Inline-Kinds (Text, Emphasis, Highlight, Reference, Note, InlineCode), inklusive Whitespace-Strategie und Normalisierung der `crosssref`-Typo.

**Erledigt:** `src/parser/inlines.py` mit Walker, Per-Kind-Helfern und Whitespace-Logik (internal collapse, edge strip, drop empties, coalesce adjacent text); Nesting, Soft-Skip von `<lb/>`, Comment-Tail-Erhalt, Unknown-Raise. Real-Korpus-Smokes (zehn `<head>` ohne Raise, die eine `crosssref`-Stelle wird zu `crossref` normalisiert). Modell um `Note.xml_id` als Footnote-Anker für Phase 7 erweitert.

**Entscheidungen:**
- `<lb/>` soft-skip als Single-Space statt eigener Inline-Klasse — wenige Vorkommen, fast nur in `<quote>`; das Modell hält an sechs Kinds fest.
- `Note.xml_id` ergänzt (additiv, default `None`): fast alle Notes tragen `xml:id="ftnN"`, ohne den Wert kann Phase 7 das `<ref>`/`<note>`-Paar nicht verbinden.
- Block-Elemente in `<p>` raisen sauber via `UnknownTeiElement` — Phase 5 löst die Pre-Extraction als Integrations-Concern, nicht der Inline-Walker.
- `crosssref→crossref` als Daten-Map, nicht Code-Branch: künftige neue Typen passieren unverändert durch.

**Offen:** Phase 5 — Integration in `parse_review`: `parse_sections`/`parse_block` füllen ihre `inlines=()`-Felder; die Block-in-Paragraph-Anomalie muss vor dem Inline-Walker abgegriffen werden (Pre-Pass über `<p>`, der Block-Children als Sibling-Blöcke einreiht), sonst raised der ganze Korpus.

**Nächster Einstieg:** `_split_paragraph(p)` → `(Paragraph, list[Block])`, das Block-Kinder aus dem Mixed-Content auslagert; dann `parse_review` so erweitern, dass `Review.body` für alle Reviews befüllt ist. Stage 2.B abgeschlossen, sobald der Korpus-Smoke durchläuft.

---

## 2026-04-29 — Phase 3 abgeschlossen, Block-Parser steht

**Ziel:** Block-Parser für die fünf verifiziert vorkommenden Block-Kinds (Paragraph, List, Table, Figure, Citation), inklusive List-Rend-Normalisierung, Figure-Kind-Detection und Dispatcher mit klarer Fehlermeldung bei Unbekanntem.

**Erledigt:** `src/parser/blocks.py` mit fünf Per-Kind-Funktionen, `parse_block(el)` als Dispatcher und `UnknownTeiElement` (mit Localname-Feld und Div-xml:id-Hint); Real-Korpus-Smoke gegen ein `<figure>/<eg>`-Vorkommen.

**Entscheidungen:**
- Block-Parser als ein Commit statt drei — Dispatcher und die fünf Funktionen brauchen sich gegenseitig, eine Trennung wäre artificial.
- Inlines bleiben in Phase 3 durchgängig `()`; Phase 4 füllt sie. Das Phase-3-Contract ist „richtige Block-Kind mit korrekter Struktur-Metadatik", nicht „vollständiger Inhalt".
- `UnknownTeiElement` als eigene Exception statt `ValueError`, damit Catch-Branches und Berichte den Anomaly-Typ präzise erkennen.
- Tabellen-Header über `@role="label"` erkannt — Korpus-Konvention, die einzige verlässliche Markierung.

**Offen:** Phase 4 — Inline-Parser: Mixed-Content-Walker für `<p>`, `<head>`, `<cell>`, `<quote>`, `<bibl>`, `<item>`, `<note>`; Whitespace an den Rändern; eine Funktion pro Inline-Kind; Normalisierung `crosssref` → `crossref`.

**Nächster Einstieg:** `src/parser/inlines.py` mit `parse_inlines(el)` als Walker und einem `_parse_inline(child)`-Dispatch; synthetische Mixed-Content-Fixtures plus geschachtelte Inlines.

---

## 2026-04-29 — Phase 2 abgeschlossen, Section-Parser steht

**Ziel:** Rekursiver Section-Parser für `<front>`, `<body>`, `<back>`. Body-Wrap-Anomalie für die sieben Reviews mit direktem `<p>`- oder `<cit>`-Kind unter `<body>`.

**Erledigt:** `src/parser/sections.py` mit `parse_sections(host)` und rekursivem `_parse_div()`; Anomalien: fehlende `@xml:id` → positionsbasierter Fallback, fehlendes `<head>` → `heading=None`, unbekannte `@type` → `None`, Schachtelung > 3 → ValueError, `parse_sections(None)` → `()` für No-Back. Body-Wrap-Branch für die sieben anomalen Reviews, gegen Korpus verifiziert (drei cit-first, vier p-first) plus Real-Korpus-Smokes.

**Entscheidungen:**
- `Section.blocks` bleibt `()` in Phase 2; Phase 5 füllt sie. Heading vorerst als `(Text(text),)` ohne Mixed-Content-Walker.
- Wrap-Detection element-basiert über `QName(child).localname`, mit Skip von Kommentaren/PIs — verhindert False Negatives bei formatierten Quelldateien.
- Synthese-ID-Format `sec-` plus Punkt-Position — kollisionsfrei mit echten `xml:id`s, weil das Präfix im Korpus nirgends vergeben ist.

**Offen:** Phase 3 — Block-Parser: eine Funktion pro Block-Typ, List-Rend-Normalisierung (`numbered→ordered`, `unordered→bulleted`), `parse_block`-Dispatcher mit klarem Raise bei Unbekanntem.

**Nächster Einstieg:** `src/parser/blocks.py` anlegen, erste Funktion `_parse_p(p)` → `Paragraph` mit `inlines=()` und `n=p.get('n')`; synthetische Fixture, dann inkrementell weitere Block-Typen.

---

## 2026-04-29 — Phase 1 abgeschlossen, Stage 2.B Modell steht

**Ziel:** Datenmodell für Section, Block und Inline als frozen dataclasses anlegen, ohne Parser-Logik. Review-Klasse um die drei body-Felder erweitern.

**Erledigt:** `src/model/{section,block,inline}.py` plus Modell-Tests; Block-Liste auf fünf verifizierte Kinds reduziert (Note und InlineCode wandern zu Inline). Review um `front`/`body`/`back` als `tuple[Section, ...]` mit Default `()` erweitert (additiv, keine Breaking Changes). Refactoring-Vorlauf: Architecture-Doc auf den verifizierten Block-Stand, README nüchterner, requirements.txt angelegt.

**Entscheidungen:**
- `List` als Klassenname behalten trotz `typing.List` — kein Konflikt, da typing nicht importiert wird.
- `Paragraph.n` als optionales Feld für die Citation-Anchor-Nummern (interface §11).
- `Figure.kind` ∈ {graphic, code_example} statt zwei Klassen — Felder je nach kind gesetzt, einfacher zu rendern als Polymorphie.

**Offen:** Phase 2 — Section-Parser; erfordert die Body-Wrap-Anomalie für die sieben Reviews mit direktem `<p>`/`<cit>` unter `<body>`.

**Nächster Einstieg:** `src/parser/sections.py` mit `parse_sections(host)` und `_parse_div(div, level, position)`; synthetische Fixtures plus ein Real-Korpus-Smoke gegen ein Wrap-Review (z. B. tustep).

---

## 2026-04-29 — Konsolidierung K1-K4 vor Phase 1

**Ziel:** Vor dem Start der Implementierungsphasen den Knowledge-Vault vereinheitlichen, das Repo selbsterklärend machen, das YAML-Mapping als Architekturentscheidung verankern und eine Journal-Konvention etablieren.

**Erledigt:** `requirements.md` und `interface.md` in den Vault integriert, Naming auf lowercase, Wikilinks durchgängig. YAML-Element-Mapping als Architektursektion in architecture.md, N2 mit Verweis aufs Schema. `README.md`, `CONTRIBUTING.md`, `docs/extending.md`, `docs/url-scheme.md` neu — Repo ist self-explaining. Journal-Konvention etabliert.

**Entscheidungen:**
- Naming-Konvention: alle Knowledge-Dokumente lowercase. Grund: Konsistenz, Vermeidung von Case-Insensitivity-Konflikten zwischen Windows und Linux-CI.
- YAML-Mapping als formale Architekturentscheidung statt nur Konvention — macht N2 (Erweiterbarkeit) ausführbar prüfbar.
- Journal getrennt von Memory führen — Memory speichert dauerhafte Fakten, das Journal den Sessionverlauf.

**Offen:** —

**Nächster Einstieg:** Phase 1 — Datenmodell für Section/Block/Inline als frozen dataclasses.
