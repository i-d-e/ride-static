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
- **Erledigt** — was real beendet ist; halbfertige Arbeit gehört nach „Offen".
- **Entscheidungen** — neue Festlegungen, nicht Wiederholungen aus früheren Einträgen. Nenne den Grund.
- **Offen** — präzise und actionable; vermeide Schwammiges wie „weiter testen".
- **Nächster Einstieg** — eine konkrete Anfangsaufgabe, nicht eine Liste.

If a field is genuinely empty for a given session, write "—" rather than omitting it.

## Why this exists

Three persistence layers run in parallel for this project: `CLAUDE.md` for project conventions, the auto-memory under `~/.claude/projects/.../memory/` for facts that Claude carries across sessions, and git commits for code changes. None of these capture the **narrative** of a session: why did we choose this order, what was almost decided differently, what is left undone. The journal fills that gap. It is human-readable, in-repo, and visible to all contributors — including future Claude sessions that read it on startup.

---

## 2026-04-28 — Frontend: Phase-7-Integration abgeschlossen (Buckets + Asset-Pipeline)

**Frontend-Seite des Backend-Pre-Handover „Phase 7 ready" jetzt durch — Cross-Refs sind nach Bucket gestylt, Bilder werden lokal serviert.**

**Ziel:** Den Backend-Output von Phase 7 (Reference.bucket + rewrite_figure_assets) ans Rendering anschließen. Cross-Refs sollen je nach Bucket unterschiedlich erscheinen, eingebettete Bilder aus dem Korpus in `site/issues/.../figures/` landen, der HTML auf die deployte URL zeigen.

**Erledigt:**
- Reference-Bucket (`7d86fe5`): `reference()`-Macro liest `r.bucket`, emittiert `ride-ref--{local|criteria|external|orphan}` per `config/element-mapping.yaml`. Orphans rendern als nicht-klickbarer `<span>` (kein toter Link), Externe bekommen `rel="noopener noreferrer"`. CSS-Modifier in `static/css/ride.css`. 6 neue Tests, parametrisiert über die Buckets.
- Asset-Pipeline (`18a8376`, **mit Backend-Test-Refactor in einem Commit gelandet — Cross-Contamination, siehe Offen**): `src.build._render_one` ruft `rewrite_figure_assets(review, ride_root, site_root)` und sammelt `AssetReport`. Build-Summary zeigt `copied / missing / unparseable`-Zähler, missing/unparseable an stderr.
- `media_path_factory(base_url)` in `src/render/html.py`: prefixt root-absolute URLs mit `site.base_url` (für GH-Pages-Deploy unter `/ride-static`), lässt `http(s)://` und leere Werte unverändert. Aufgerufen via `media_path` im Template-Kontext aus `render_review`, `render_editorial`, allen Aggregationen. 4 Filter-Tests.
- `figure_block`-Macro nutzt `media_path(f.graphic_url)`. Macro-Imports in `review.html`, `partials/section.html`, `partials/apparate.html` umgestellt auf `with context`, sonst sieht das Macro die Page-Variable nicht.
- Smoke-Build über 5 Reviews: 38 Bilder kopiert, 11 missing (anemoskala-Review hat URLs ohne `.png`-Extension — Korpus-Quirk), 0 unparseable. URLs erscheinen als `/issues/17/ride.17.4/figures/picture-1.png`. 326 Tests grün.

**Entscheidungen:**
- `media_path` als per-render Closure (Factory-Pattern) statt Jinja-Filter — Filter sind env-global und können `base_url` nicht pro Build aufnehmen. Konsistent mit `static_path_factory`.
- Macros via `import … with context`: minimaler Eingriff (drei Zeilen), keine Macro-Signatur-Änderung. Alternative wäre `media_path` als Macro-Argument, hätte aber jede Call-Site geändert.
- Orphan-Rendering bleibt `<span class="ride-ref ride-ref--orphan">` mit `data-target="#…"` zur späteren Diagnose; **keine** klickbaren Anker auf nicht-existente Anker, damit Lesefluss und A11y nicht durch broken links gestört werden.
- `rel="noopener noreferrer"` automatisch nur bei `bucket == "external"` — security default, kostet nichts.
- Anemoskala-Bilder NICHT „repariert" — die Frontend-Seite tut das Richtige (verlinkt das, was im TEI steht); fehlende Extensions sind Korpus-Issue, gehört in Phase 13 als Validierung oder ins Backend-Patch-Set.

**Offen:**
- **Cross-Contamination:** Backend hat bei `Phase 7.F` (`18a8376`) wieder per `git add -A` committet und meine 8 Frontend-Dateien (asset pipeline) mit in seinen Test-Refactor-Commit gezogen. Code ist im Tree, aber Attribution stimmt nicht. WORKPLAN-Regel „Pfade explizit nennen" greift nur, wenn beide sie befolgen — Backend bitte beim nächsten Commit `git add <pfad>` statt `-A`.
- **`#abb` → `#img` Orphan-Quirk:** in `ride.17.4` (und vermutlich anderen) referenziert der Body `<ref target="#abb1">figure 1</ref>`, die Figur trägt aber `xml:id="img1"`. Resolver markiert das als orphan (korrekt — der Anker existiert nicht). Frage an Backend: soll `refs_resolver` einen Alias `#abb{n}` ↔ `#img{n}` einbauen, oder ist das ein Korpus-Bug, der in Phase 13 (Validierung) gemeldet werden soll? Heute geht UX leer aus.
- WCAG-Audit-Run, PDF-Pipeline (Phase 14), Matomo + Redirects (Phase 15) als nächste Frontend-Brocken.
- Reviewer-Markdown-Profile, tooltip.js voll, Element-Mapping-Drift-Validator: nicht eingeplant, kein konkreter Bedarf.

**Nächster Einstieg:** Stakeholder hat zum Sessionende konsolidiert; Phase 11 (Pagefind-Integration) oder Phase 12 (OAI-PMH/JSON-LD/Sitemap) sind die nächsten ungeöffneten Phasen. Vor der nächsten Session: pushen, GH-Pages-Deploy laufen lassen, im Live-Build die `ride-ref--*`-Klassen und die `/issues/.../figures/`-Bilder verifizieren.

---

## 2026-04-29 — Phase 7 abgeschlossen, Reference-Resolver + Asset-Pipeline live

**Phase 7 ready — Reference.bucket ∈ {local, criteria, external, orphan}.**

**Ziel:** Aspekt A aus WORKPLAN.md — Vier-Bucket-Resolver, Asset-Pipeline, Test-Refactor auf Real-Corpus-Drive (vom Stakeholder eingefordert).

**Erledigt:**
- 7.A (`425f2a2`): `Reference.bucket` + `src/parser/refs_resolver.py` (`classify_target` pure, `resolve_references(review)` als Post-Pass mit Re-Aggregation für Figures/Notes-Identity). Wire-up in `parse_review`. 17 Tests.
- 7.B (`8a439df`): `src/parser/assets.py` mit `rewrite_figure_assets` + `AssetReport`. URL-Rewrite Korpus → `/issues/{N}/{review_id}/figures/{file}`; Disk-Pfad `../ride/issues/issue{NN:02d}/{slug}/pictures/{file}`. Fehlende Files = Report, kein Crash. 12 Tests.
- 7.C (`66fbb0d`): Test-Daten-Philosophie als Hard Rule in CLAUDE.md. Phase-7-Tests refaktoriert auf Real-Corpus (1641, anemoskala, bayeux, godwin). Vier File-Existence-Smokes gelöscht, `<list>`-in-`<item>`-Anomalietest gegen anemoskala ergänzt. 315 Tests grün.
- 7.D (`6c36759`): COORDINATION.md, architecture.md (Stakeholder-Sektion + methodische Randnotiz), WORKPLAN-Status, Journal-Handover.

**Entscheidungen:**
- `Reference.bucket` als Inline-Feld statt paralleler `resolved_refs`-Map — kleinster Eingriff, keine zwei Strukturen zu synchronisieren.
- `criteria`-Bucket bleibt im Vertrag trotz 0 Body-Vorkommen: alle 5 209 K-Refs leben im Header (`<catDesc>`), Body-Parser traversiert dort nicht; Future-Proofing.
- Asset-Modul in `src/parser/assets.py` statt `src/build/assets.py` — Frontend hält `src/build.py` als Datei, ein Geschwister-Package würde kollidieren.
- Wayback-Hint deferred → Phase 13: HTTP-HEAD-Probe gehört in den Validation/Bericht-Schritt, nicht in den Resolver.
- Re-Aggregation in Resolver und Asset-Pipeline: separater Walk über die Aggregate erzeugt sonst divergente Kopien gegenüber dem Section-Tree.
- Test-Prinzip als Hard Rule in CLAUDE.md (nicht nur COORDINATION.md): gilt für beide Claudes und alle künftigen Phasen.

**Offen:** Frontend integriert Buckets (`config/element-mapping.yaml` `by_bucket`) und ruft `rewrite_figure_assets` in `src/build.py` auf. Wayback-Hint für Phase 13. Phase 12 (OAI-PMH/JSON-LD/Sitemap) und 13 (Validierung) als nächste Backend-Sprints.

**Nächster Einstieg:** Frontend-Integration abwarten; falls Backend parallel arbeiten soll, Phase 11 (Pagefind-Integration in `src/build.py`) als überbrückendes Vorzieh-Stück.

---

## 2026-04-29 — Phase 6 abgeschlossen, Stage 2.C steht

**Ziel:** Bibliography- und Questionnaire-Modell plus Cross-Korpus-Aggregate (Tags, Reviewer, Reviewed Resources) — die ganze Phase 10-Vorbereitung in einem Schub. Damit ist der Datenvertrag für den Frontend-Claude breit genug, um Rezensionsseite (Bibliographie + Factsheet) und Aggregationsseiten zu bauen.

**Erledigt:**
- Commit 6.A (`70087b7`): `BibEntry`-Dataclass plus `parse_bibliography(text_el)`. `<listBibl>/<bibl>`-strukturierte Bibliographie aus dem `<back>`-Pfad, Filter gegen Inline-cit/bibl und Header-relatedItem. `Review.bibliography` als neues Feld; Section `<div type="bibliography">` behält ihren Heading, blocks bleiben leer (Architektur, kein Bug). 10 Tests, Korpus-Smoke ≥1300 Einträge gegen das Inventar von 1389.
- Commit 6.B (`acdf66e`): `Questionnaire` plus `QuestionnaireAnswer`. Walker `parse_questionnaires(root)` über `teiHeader//taxonomy`, sammelt nur Leaf-Categories (keine geschachtelten `<category>`-Children) damit Sections und Questions nicht ihre Descendant-Nums erben. Korpus-Konvention zwei `<catDesc>` pro Leaf — der erste trägt das Label, der zweite den `<num>`; der Parser scant beide. `value="3"`-Anomalie bleibt als String erhalten. 8 Tests, Korpus-Smoke ≥19000 Antworten über 110 Taxonomien und 4 Kriterien-URLs. *(Anmerkung: dieser Commit hat versehentlich auch Frontend-Files mit-eingecheckt, weil zwischen meinem `git add` und `git commit` weitere Dateien gestaged waren. Hygiene-Lehre für die nächste Session.)*
- Commit 6.C (`53530fe`): `src/parser/datasets.py` mit drei Cross-Korpus-Aggregaten — `aggregate_tags`, `aggregate_reviewers`, `aggregate_reviewed_resources`. Tags case-insensitive merged (TEI=tei), Reviewer per ORCID dedup mit Name-Fallback, Resources per Target-URL dedup. Alle drei sortiert für reproduzierbare URLs. 13 Tests; Korpus produziert 355 Tags, 106 Reviewer (107 Author-Attributionen, 1 deduped — Tobias Hodel mit 3 Reviews ist Top), 110 reviewed resources.

**Entscheidungen:**
- `<listBibl>` bleibt aus den Section-Blocks raus, lebt auf `Review.bibliography`. Begründung: Bibliographie ist strukturell separat, ein eigener Feld-Typ ist sauberer als ein `Bibliography`-Block-Kind im Section-Tree.
- `BibEntry.inlines` ohne strukturierte Sub-Felder (kein eigener `title`/`date`/`editor`). Begründung: das Korpus benutzt `<bibl>` als annotiertes Freitext-Zitat, kein hochstrukturiertes biblStruct. Renderer kommen mit den Inlines aus; R2 (Citation Export) zielt auf die Rezension selbst, nicht ihre Bibliographie.
- Questionnaire-Parser sammelt nur Leaves. Begründung: das Stage-0-Script `scripts/taxonomy.py` benutzt `cat.iter()` und over-attributiert dadurch jeden Num-Wert an alle Vorfahren. Für die Domänen-Schicht ist das semantisch falsch — Antworten gehören dem Leaf, nicht dem Section-Wrapper.
- `value="3"`-Anomalie als String erhalten statt als sentinel-int. Begründung: ein Renderer kann verlässlich `value == "0"`/`"1"` matchen und „3" als Anomalie-Indikator separat behandeln, ohne dass der Parser inhaltlich entscheidet.
- Aggregat-Datasets in `src/parser/datasets.py` (separate Datei vom per-review `src/parser/aggregate.py`). Begründung: Per-Review-Walks (Figures, Notes) und Cross-Korpus-Walks (Tags, Reviewer, Resources) sind unterschiedliche Konzern-Klassen; eine Datei wäre semantisch überfrachtet.

**Offen:** Phase 7 — Ref-Resolver. Vier-Bucket-Logik für `<ref @target>`: lokal (`#xml-id` im selben Review), kriterien-extern (`#K…` gegen das Taxonomie-`@xml:base`), externe URL, sonstige. Asset-Pipeline für `<graphic @url>`-Bilder aus `../ride/issues/{n}/`. Wayback-Detector für Bibliographie-Refs. Sobald Phase 7 landet, kann der Frontend-Claude die Tooltip-Vorschau aus [[interface#11]] inhaltlich befüllen und Bilder korrekt referenzieren — heute rendern Figures noch mit den rohen TEI-`@url`-Werten.

**Nächster Einstieg:** `src/parser/refs.py` (oder `src/resolver.py`) mit `resolve_ref(ref, review_context, criteria_index) -> ResolvedRef` als Vier-Bucket-Funktion. Dazu Asset-Pipeline-Vorbereitung: `src/build/assets.py` als Modul, das Bild-Pfade von `../ride/issues/{n}/figures/` nach `site/issues/{n}/{review_id}/figures/` umschreibt. Beides hat klare Test-Pfade (Synthetik + Korpus-Smoke). Der Frontend-Claude wartet darauf — frühe Auslieferung priorisieren.

---

## 2026-04-29 — Phase 10 + Citation: Site hat ihre Außenhaut

**Ziel:** Aspekt B aus dem [WORKPLAN](WORKPLAN.md) abräumen — Citation-Daten so embedden, dass die `cite-copy.js`-Buttons echt funktionieren, plus die sechs Aggregations- und Übersichtsseiten aus [interface.md §4](knowledge/interface.md) bauen, damit die Site eine Navigations-Außenhaut hat (heute nur Platzhalter-`index.html`).

**Erledigt:**
- Citation-Cleanup (`511e753`): `_to_bibtex(review)` und `_to_csl_dict(review)` als Python-Helper in `src/render/html.py`, registriert als Jinja-Filter. Zwei `<script class="ride-cite-data">`-Blöcke in `review.html` — `application/x-bibtex` für BibTeX (mit Sentinel-Pass-Brace-Escape und `</`-Defence), `application/json` mit `tojson(indent=2)` für CSL-JSON. Acht Tests (canonical shape, Brace- und Backslash-Escape, `</script>`-Defence, autorenlose Reviews, partielle Daten, Single-Name-Personen, Embed-Marker im HTML).
- Phase 10 Aggregationen (`469d4d6`): `src/render/aggregations.py` mit acht `render_*`-Entry-Points; acht Templates für Startseite, Heftübersicht, Heftansicht, Tags-Übersicht + Detail, Reviewer-Liste + Detail, Reviewed-Resources-Tabelle, plus ein `partials/review_card.html` für die wiederkehrende Beitragskarte. `_render_aggregations` in `src/build.py` ersetzt die Platzhalter-Index-Methode. 12 Tests.
- Korpus-Reorganisation (`cd85e44`, vor Phase 10): `image-workflow.png` und das Stakeholder-Narrativ `prozess-und-stand.md` aus dem Repo-Root in `knowledge/` verschoben — Stakeholder-Doku gehört in den Wissensvault. CLAUDE.md hard rule auf "Markdown plus referenzierte Image-Attachments" relaxed (vorher `.md only` — der Sinn der Regel war kein generierter JSON, nicht "keine Bilder").

**Entscheidungen:**
- Aggregationsseiten als `ride-page--solo` (eine Spalte, keine Sidebar). Begründung: interface.md §4 schreibt das so vor — Aggregations- und Editorialseiten haben keine Apparate, also keine Sidebar.
- BibTeX-Brace-Escape mit Sentinel-Pass statt naivem Replace-Chain. Begründung: `\\textbackslash{}` enthält selbst Braces, naive Replace-Reihenfolgen produzieren `\\textbackslash\\{\\}`. Sentinel `\x00BIBSLASH\x00` umgeht das.
- Reviewer-Slug ist `surname-forename`. Begründung: macht Slugs stabil bei Namensgleichheit von Personen, eindeutig durchsuchbar, und gleichzeitig lesbar in der URL.
- Tag-Liste als zweispaltige Markup-Liste (CSS `column-count`) statt Word-Cloud-Visualisierung. Begründung: barrierefrei, scannbar, ohne Visualisierungs-Library; eine echte Cloud wäre Designer-Arbeit und prägt Lesbarkeit nicht positiv.
- Data-Charts (`/data/`) deferred. Begründung: ohne K-Ref-Auflösung aus Phase 7 wären die Achsen-Labels rohe `seXXX`-IDs — nicht lesbar. Sobald Phase 7 die Labels liefert, kommen die Charts in einem Folge-Sprint.

**Offen:**
- Phase 7 (Backend): Ref-Resolver und Asset-Pipeline. Sobald `Reference.bucket` am Modell liegt (Pre-Handover-Marker im Journal erwartet), kann das Frontend Cross-Refs Bucket-aware rendern — heute werden sie als rohe Anker emittiert. Bilder zeigen heute noch auf rohe TEI-`@url`-Pfade; nach Phase 7 sind sie unter `site/issues/{n}/{review-id}/figures/` real.
- Data-Charts (Stretch aus Aspekt B) wartet auf Phase 7.
- JS-Modul `tooltip.js` ist Stub bis Phase 7, `pagefind.js` Stub bis Phase 11.
- Heft-YAML-Schema (Phase-Plan-Punkt) ist noch nicht eingehängt — die Heftansichten generieren ihre Metadaten aktuell aus den Review-Headern. Sobald das Schema steht, wird `templates/html/issue.html` um die YAML-Felder erweitert (Heft-DOI, Hrsg.-Liste, Status-Marker bei Rolling Issues).

**Nächster Einstieg:** Live-Deploy auf GitHub Pages testen — Push auf `main` triggert den Workflow, der mit dem `--base-url=/ride-static`-Fix sauber durch alle 599 Seiten läuft. Anschließend von Stakeholder-Seite einmal durchklicken, was visuell auffällt. Parallel zum Backend-Phase-7-Ergebnis warten — sobald `Reference.bucket` da ist, ist die Cross-Ref-Integration ein 30-Minuten-Patch in den Render-Macros plus ein paar CSS-Modifier-Klassen.

---

## 2026-04-29 — Phase 8 First Light, Frontend rendert 107 Reviews End-to-End

**Ziel:** Aus dem Stage-2.B-Datenvertrag heraus den ersten lauffähigen Frontend-Strang aufsetzen — Jinja-Render-Macros für alle Block- und Inline-Kinds, Rezensionsseiten-Template gemäß [[interface#5]], Render-Layer plus Build-CLI, dazu der CI-Workflow für GitHub-Pages-Deploy. Ziel: ein `python -m src.build` baut alle 107 Reviews ohne Raise.

**Erledigt:**
- Render-Macros (`templates/html/partials/render.html`): rekursive Block- und Inline-Dispatcher auf `__class__.__name__`, je Kind eine spezialisierte Macro. Whitespace-Strategie an Sequenz-Rändern via Jinja-Trim, BEM-Klassen aus `config/element-mapping.yaml`.
- Section-Partial (`partials/section.html`): rekursiv mit `Section.level + 1` als Heading-Level (h2..h4); h1 reserviert für den Seitentitel.
- Apparate-Partial (`partials/apparate.html`): paralleles Dreispalten-Layout mit Figures + Notes, leere Panels kollabieren, References-Slot wartet auf Phase 7.
- Rezensionsseiten-Template (`templates/html/review.html`): Kopfbereich (Titel, reviewed item aus `related_items`, Reviewer-Block mit ORCID + Mail obfuscated), Abstract-Section gesondert, Body, Apparate, Sidebar mit TOC + Meta + Cite.
- Render-Layer (`src/render/html.py`): Jinja-Env mit ChainableUndefined (für optionale UI-Strings), drei Filter (`slugify`, `obfuscate_mail`, `inlines_to_text`), `SiteConfig`+`BuildInfo`-Dataclasses, `render_review(review, site, env)`. Abstract wird via `split_abstract` aus `Review.body` separiert.
- Build-CLI (`src/build.py`): walks `../ride/tei_all/`, parst, rendert, schreibt nach `site/issues/{n}/{id}/index.html`, kopiert `static/` und das originale TEI; Platzhalter-Index für die Site-Wurzel; `--reviews N` und `--base-url` als Optionen; per-Datei-Failure crasht nicht den ganzen Build.
- 16 Render-Tests in `tests/test_render_html.py` — Filter-Units, `split_abstract`, Skelett-Marker, alle Block-Kinds rendern ohne Raise, Apparate kollabiert/erscheint, Reference rendert mit `data-ref-type`, alle Templates laden ohne Syntax-Error, Real-Korpus-Smoke gegen ein Review.
- Voller Korpus-Build: **107/107 Reviews rendern ohne Fehler**, Pages 36–63 KB, `site/static/css/ride.css` mit deployt.
- `.gitignore` um `site/` ergänzt.
- CI-Workflow `.github/workflows/build.yml` mit Build- + Deploy-Job (actions/upload-pages-artifact + actions/deploy-pages); `/docs`-Variante explizit verworfen.

**Entscheidungen:**
- `ChainableUndefined` statt `StrictUndefined` für die Jinja-Env. Begründung: UI-Strings sind ein optional-deeply-nested dict; mit StrictUndefined müsste jede Default-Falle als `{% if %}`-Branch geschrieben werden, das bläht jedes Template auf. Tippfehler bei domain-objekten fängt der Test-Layer.
- Render-Macros zentral in einer Datei statt eine Datei pro Block/Inline-Kind. Begründung: rekursive Dispatcher müssen sich gegenseitig sehen, und 11 Kinds × eigene Datei wäre Overhead ohne Gewinn — die Datei ist 110 Zeilen, weiterhin lesbar.
- Block-Dispatch über `__class__.__name__` statt isinstance-Kette. Begründung: Templates kennen den String-Namen aus `element-mapping.yaml`, Konvention bleibt eindeutig parallel zur YAML.
- Apparate kollabiert komplett wenn weder Figures noch Notes da sind, statt leere Panel zu rendern. Begründung: paralleles Layout aus [[interface#6]] braucht Inhalt, sonst wirkt es als Skelett-Bug.
- References werden als rohe Anker mit `data-ref-type` gerendert; Resolver-Logik (4-Bucket) ist Phase 7. Templates können Phase-7-Buckets später per CSS-Selector adressieren ohne Markup-Änderung.
- Build-CLI fängt Per-Datei-Failures, statt den Lauf abzubrechen. Begründung: ein einzelner anomaler Review soll nicht 106 fehlerfreie Renderings blockieren; aggregierte Fehlerausgabe genügt für jetzt, Phase 13 wird daraus den `build-info.json`-Bericht machen.

**Offen:** 
- Phase 7 (Ref-Resolver, Asset-Pipeline) — Voraussetzung für Tooltip-Vorschau und korrekte Figure-Pfade. Aktuell rendern Figures mit den rohen TEI-`@url`-Werten; Bilder sind im Output noch broken.
- Phase 6 (Bibliography, Questionnaire) — sobald `Review.bibliography` und `Review.questionnaire` da sind, bekommen Rezensionsseite (Bibliographie-Apparat) und Sidebar (Factsheet) ihre fehlenden Blöcke.
- JS-Module (`copy-link.js`, `tooltip.js`, `cite-copy.js`, `pagefind.js`) sind in `base.html` referenziert, aber noch nicht implementiert.
- CSS-Komponenten-Regeln für die Apparate-Sub-Blöcke und Sidebar-Boxen sind als Klassen-Hooks definiert, brauchen aber noch konkrete Styles (Hover-States, Spacing-Feinschliff).
- Aggregations- und Editorialseiten (Phase 9, 10) noch nicht angelegt.

**Nächster Einstieg:** Editorial-Markdown-Stubs (`content/about.md`, `imprint.md`, `criteria.md`) plus `templates/html/editorial.html`, weil diese Achse vom Backend-Status unabhängig ist und die Site eine Navigations-Außenhaut bekommt. Anschließend die vier JS-Module als jeweils 30–60-Zeilen-ES-Module ohne Bundling, zuerst `copy-link.js` und `cite-copy.js`. Sobald Phase 6 landet, Sidebar-Factsheet aus `Review.questionnaire` befüllen und einen Bibliographie-Apparat im Apparate-Block einhängen.

---

## 2026-04-29 — Phase 5 abgeschlossen, Stage 2.B steht; Rollen-Split etabliert

**Ziel:** Stage 2.B abschließen — `parse_inlines` überall einhängen, Block-in-Paragraph-Anomalie auflösen, `parse_review` integrieren, Aggregate für Figures und Notes materialisieren. Parallel die Koordinationsschicht zwischen Backend- und Frontend-Claude einrichten.

**Erledigt:**
- Commit 5.A (`7662712`): Refactor von `UnknownTeiElement`/`locate_hint` nach `common.py`, parse_inlines in alle Per-Kind-Parser eingehängt, sections.py-Heading auf Walker umgestellt. Modell additiv erweitert: `Paragraph.xml_id`, `Figure.xml_id`, `Figure.alt`. Long-Tail-Inlines (mod, del, seg, affiliation, plus Bib-Strukturelemente) als Passthrough-Text.
- Commit 5.B (`f09e707`): `parse_paragraph_or_split` zerlegt `<p>` mit Block-Kindern in alternierende Paragraph-/Block-Sequenz; erste Chunk erbt `@xml:id`/`@n`, Continuations sind synthetisch. `parse_block_sequence` als neuer Section-Block-Walker. ListItem und TableCell um `blocks`-Feld erweitert für nested Lists/Figures. `<p>` in `<note>` als transparenter Wrapper unwrapped.
- Commit 5.C (`fd25fbb`): `parse_review` zieht front/body/back über `parse_sections`. `src/parser/aggregate.py` neu — Tiefen-Walker für Figures und Notes in Dokumentreihenfolge, durch alle Inline-tragenden Flächen. `<listBibl>` (102×) als `_DEFERRED_BLOCKS` für Phase 6 markiert. Korpus-Smoke gegen alle 107 Reviews durchläuft mit ≥800 Figures und ≥1800 Notes.

**Entscheidungen:**
- Drei Spec-Frage aus dem UI-Audit defensibel beantwortet: figDesc warn (Phase 13), Wayback-Detector deferred to Phase 7, inline xml:lang-Spec entschärft auf Section-/Review-Level (Korpus markiert keine Inline-Sprache, redaktionell nachzuziehen).
- `<listBibl>` skip-and-defer statt Placeholder-Block. Begründung: Phase 6 ersetzt den Branch ohnehin, Placeholder-Klasse wäre toter Code.
- Nested Blocks in Items/Cells als zusätzliches `blocks: tuple[Block, ...]`-Feld am ListItem/TableCell statt Mixed-Typ-Children. Dokument-Order-Interleaving zwischen Inlines und Blocks ist konventionell aufgelöst (Inlines first, Blocks second).
- Aggregate (Figures, Notes) am Parse-Zeitpunkt materialisiert statt lazy. Begründung: Templates bekommen pure Domänenobjekte, keine Iterator-Aufrufe — entspricht N1 (Read-only-Pipeline).
- Rollen-Split: Backend + Doku + Koordination = ich; Frontend (Templates, CSS, JS, HTML-Build) = anderer Claude. Datenvertrag = Domänenobjekte; gemeinsame Doku = `COORDINATION.md`.

**Offen:** Phase 6 — Bibliography-Parser (`<bibl>` strukturiert), Questionnaire-Parser (`<num value="0|1|3">`), und Aggregat-Datasets (Tags, Reviewer, Reviewed Resources). Phase 7 — Ref-Resolver (4-Bucket-Logik, Wayback-Detection, K-Ref-Auflösung gegen externes Kriteriendokument). Phase 8 — der Frontend-Claude beginnt sobald `Review.bibliography` und `Review.questionnaire` aus Phase 6 verfügbar sind, kann aber heute schon mit dem Stage-2.B-Modell-Stand auf der Rezensionsansicht arbeiten.

**Nächster Einstieg:** `src/model/bibliography.py` mit `BibEntry`-Dataclass plus `src/parser/bibliography.py` für `<listBibl>`/`<bibl>`-strukturierte Bibliografieeinträge. Korpus-Konvention prüfen (welche TEI-Felder pro bibl?), dann Synthetik plus Real-Korpus-Smoke gegen ein Review mit voller Bibliographie. Anschließend Questionnaire-Parser für die `<num>`-Boolean-Antworten gemäß `taxonomy.json`.

---

## 2026-04-29 — Phase 4 abgeschlossen, Inline-Parser steht

**Ziel:** Mixed-Content-Walker `parse_inlines(host)` für die sechs verifizierten Inline-Kinds (Text, Emphasis, Highlight, Reference, Note, InlineCode), inklusive Whitespace-Strategie an Sequenz-Rändern und Normalisierung der `crosssref`-Typo.

**Erledigt:** Commit `6d9f05e` — `src/parser/inlines.py` mit Walker, Per-Kind-Helfern, Whitespace-Logik (internal collapse, edge strip, drop empties, coalesce adjacent text). 26 Tests in `tests/test_parser_inlines.py`: Walker-Basics, Whitespace, jeder Kind einzeln, Nesting (Emph-in-Ref und Ref-in-Emph), Soft-Skip von `<lb/>`, Comment-Tail-Erhalt, Unknown-Raise. Zwei Real-Korpus-Smokes: zehn `<head>`-Parse-ohne-Raise und die eine `crosssref`-Stelle wird zu `crossref` normalisiert. Modell-Erweiterung: `Note.xml_id: Optional[str] = None` als Footnote-Anker für Phase 7. 170/170 Tests.

**Entscheidungen:**
- `<lb/>` soft-skip als Single-Space statt eigener Inline-Klasse. Begründung: 30 Vorkommen, fast ausschließlich in `<quote>`; das Modell hält an sechs Kinds fest, der Walker dokumentiert die Ausnahme. Phase 8/14 können bei Bedarf Whitespace-pre-line setzen.
- `Note.xml_id` ergänzt, nicht in Phase 1 vorausgenommen. Begründung: Korpus zeigt 1919/1926 Notes mit `xml:id="ftnN"`, ohne den Wert kann Phase 7 (Ref-Resolver) das `<ref target="#ftnN">`/`<note xml:id="ftnN">`-Paar nicht verbinden. Additiv, default `None`.
- Block-Elemente in `<p>` (figure, list, cit, table mit zusammen ~1000 Vorkommen unter `<p>`) raisen sauber via `UnknownTeiElement`. Phase 5 muss diese Pre-Extraction als Integrations-Concern lösen — das ist nicht Sache des Inline-Walkers.
- `crosssref→crossref`-Map als Daten, nicht als Code-Branch. Falls künftige RIDE-Submissions neue Typen einführen, passieren die unverändert durch — kein Whitelist-Raise an dieser Stelle.

**Offen:** Phase 5 — Integration in `parse_review`. `parse_sections` und `parse_block` füllen ihre `inlines=()`-Felder via `parse_inlines`. Block-in-Paragraph-Anomalie (figure/list/cit/table inline-in-p) muss vor dem Inline-Walker abgegriffen werden, sonst raised der gesamte Korpus. Strategie: Pre-Pass über `<p>`, der Block-Children herauslöst und als Sibling-Blöcke einreiht; der inlines-Anteil bleibt rein. Anschließend Real-Korpus-Smoke gegen alle 107 Reviews.

**Nächster Einstieg:** `src/parser/integration.py` (oder Erweiterung in `blocks.py`) mit `_split_paragraph(p)` → `(Paragraph, list[Block])`, das Block-Kinder aus dem Mixed-Content auslagert. Dann `parse_review` so erweitern, dass `Review.body` für alle 107 Reviews vollständig befüllt ist. Stage 2.B abgeschlossen, sobald der Korpus-Smoke ohne Anomalien durchläuft.

---

## 2026-04-29 — Phase 3 abgeschlossen, Block-Parser steht

**Ziel:** Block-Parser für die fünf verifiziert vorkommenden Block-Kinds (Paragraph, List, Table, Figure, Citation), inklusive List-Rend-Normalisierung, Figure-Kind-Detection und Dispatcher mit klarer Fehlermeldung bei Unbekanntem.

**Erledigt:** Commit `bf7d794` — `src/parser/blocks.py` mit fünf Per-Kind-Funktionen (`parse_paragraph`, `parse_list`, `parse_table`, `parse_figure`, `parse_cit`), `parse_block(el)` als Dispatcher, `UnknownTeiElement` als Exception mit Localname-Feld und Div-xml:id-Hint. `tests/test_parser_blocks.py` mit 20 Cases inklusive Real-Korpus-Smoke gegen ein `<figure>/<eg>`-Vorkommen.

**Entscheidungen:**
- Block-Parser als ein Commit statt drei. Der Plan sah 3.1/3.2/3.3 vor; die Trennung wäre artificial gewesen, weil Dispatcher und die fünf Funktionen sich gegenseitig brauchen.
- Inlines bleiben in Phase 3 durchgängig `()`. Phase 4 wird sie befüllen, sobald der Mixed-Content-Walker steht. Das Phase-3-Contract ist „richtige Block-Kind mit korrekter struktureller Metadaten", nicht „vollständiger Inhalt".
- `UnknownTeiElement` als eigene Exception statt `ValueError`, damit Catch-Branches und Build-Berichte den Anomaly-Typ präzise erkennen können.
- Tabellen-Header über `@role="label"` erkannt — Korpus-Konvention; in den 12 vorhandenen Tabellen die einzige verlässliche Markierung.

**Offen:** Phase 4 — Inline-Parser. Mixed-Content-Walker für `<p>`, `<head>`, `<cell>`, `<quote>`, `<bibl>`, `<item>`, `<note>`. Whitespace-Behandlung an den Rändern (lstrip/rstrip), Erhalt im Inneren. Pro Inline-Kind eine Funktion: Text, Emphasis, Highlight, Reference, Note, InlineCode. Normalisierung von `<ref type="crosssref">` zu `crossref`.

**Nächster Einstieg:** `src/parser/inlines.py` mit `parse_inlines(el)` als Walker und einem `_parse_inline(child)`-Dispatch. Synthetische Fixtures für Mixed-Content-Walker (Text-Tail-Text), jeden Inline-Typ einzeln, geschachtelte Inlines.

---

## 2026-04-29 — Phase 2 abgeschlossen, Section-Parser steht

**Ziel:** Rekursiver Section-Parser für `<front>`, `<body>`, `<back>`. Body-Wrap-Anomalie für die sieben Reviews mit direktem `<p>`- oder `<cit>`-Kind unter `<body>`.

**Erledigt:**
- Commit 2.1 (`52d4d7d`): `src/parser/sections.py` mit `parse_sections(host)` und rekursivem `_parse_div()`. Anomalien: fehlende `@xml:id` → positionsbasierter Fallback `sec-1.2.3`; fehlendes `<head>` → `heading=None`; unbekannte `@type`-Werte → `None`; Schachtelung > 3 → ValueError; `parse_sections(None)` → `()` für No-Back-Reviews. 11 Tests inkl. Real-Korpus-Smoke.
- Commit 2.2 (`07b3e66`): Body-Wrap-Branch für die sieben anomalen Reviews. Verifiziert gegen Korpus: bdmp, commedia, whistler (cit-first); phi, ps, varitext, wba (p-first). Drei synthetische Tests plus zwei Real-Korpus-Smokes (bdmp gezielt, alle 107 Reviews fehlerfrei).

**Entscheidungen:**
- Section.blocks bleibt `()` in Phase 2; Phase 5 wird sie befüllen, sobald Phase 3 (Block-Parser) und Phase 4 (Inline-Parser) liegen. Heading wird vorerst als `(Text(text),)` ohne Mixed-Content-Walker abgelegt.
- Wrap-Detection element-basiert über `etree.QName(child).localname`, mit Skip von Kommentaren und PIs. Das verhindert False Negatives bei stilistisch formatierten Quelldateien.
- Synthese-ID-Format ist `sec-` plus Punkt-getrennter Position. Begründung: kollisionsfrei mit echten `xml:id`s der Form `divN.M.K`, weil das Präfix `sec-` im Korpus nirgends vergeben ist.

**Offen:** Phase 3 — Block-Parser. Erfordert eine Funktion pro Block-Typ (Paragraph, List, Table, Figure, Citation), Normalisierung der List-Rends (`numbered→ordered`, `unordered→bulleted`), und einen `parse_block`-Dispatcher, der bei unbekannten Elementen mit klarem Kontext raises (gemäß CLAUDE.md hard rule).

**Nächster Einstieg:** `src/parser/blocks.py` anlegen. Erste Funktion `_parse_p(p)` → `Paragraph` mit `inlines=()` (Phase 4 füllt mixed content) und `n=p.get('n')`. Synthetische Fixture, dann inkrementell weitere Block-Typen.

---

## 2026-04-29 — Phase 1 abgeschlossen, Stage 2.B Modell steht

**Ziel:** Datenmodell für Section, Block und Inline als frozen dataclasses anlegen, ohne Parser-Logik. Review-Klasse um die drei body-Felder erweitern.

**Erledigt:**
- Commit 1.1 (`e9a0be9`): `src/model/{section,block,inline}.py` plus `tests/test_model.py` mit 18 Cases. Block-Liste auf fünf verifizierte Kinds reduziert (Paragraph, List, Table, Figure, Citation); Note und InlineCode in Inline.
- Commit 1.2 (`5060990`): Review erweitert um `front`, `body`, `back` als `tuple[Section, ...]` mit Default `()`. Additive Änderung, keine Breaking Changes für Stage-2.A-Aufrufer. Ein neuer Test pinnt das Default-Verhalten.
- Refactoring-Vorlauf (Commits `e944ba1`, `2bff731`, `93b957d`): Architecture-Doc auf verifizierten Block-Stand gebracht, README auf akademisch-nüchtern, requirements.txt angelegt, Forward-References explizit markiert.

**Entscheidungen:**
- `List` als Klassennamen behalten trotz Konflikt mit `typing.List` — kein Konflikt im Code, da typing nicht importiert wird; `typing.List` ist seit Python 3.9 ohnehin deprecated zugunsten von `list[]`.
- `Paragraph.n` als optionales Feld für die Citation-Anchor-Nummern aus interface.md §11.
- `Figure.kind` ∈ {graphic, code_example} statt zwei separater Klassen — die Felder `graphic_url` und `code` sind je nach kind gesetzt; einfacher zu rendern als Polymorphie.

**Offen:** Phase 2 — Section-Parser. Erfordert die Body-Wrap-Anomalie für die sieben Reviews mit direktem `<p>` oder `<cit>` unter `<body>`.

**Nächster Einstieg:** `src/parser/sections.py` mit `parse_sections(host)` und `_parse_div(div, level, position)`. Synthetische Fixtures plus ein Real-Korpus-Smoke-Test gegen ein Wrap-Review (z. B. `tustep-tei.xml`).

---

## 2026-04-29 — Konsolidierung K1-K4 vor Phase 1

**Ziel:** Vor dem Start der eigentlichen Implementierungsphasen den Knowledge-Vault vereinheitlichen, das Repo selbsterklärend machen, das YAML-Mapping als Architekturentscheidung verankern und eine Journal-Konvention etablieren.

**Erledigt:**
- K1 (Commit `a39856b`): `requirements.md` und `interface.md` in den Knowledge-Vault integriert, Naming auf lowercase vereinheitlicht, Wikilinks durchgängig gesetzt.
- K3 (Commit `6b40d27`): YAML-Element-Mapping als Architektursektion in `architecture.md`; N2 in `requirements.md` mit Verweis auf das Schema.
- K2 (Commit `5f85f01`): `README.md`, `CONTRIBUTING.md`, `docs/extending.md`, `docs/url-scheme.md` neu — Repo ist self-explaining.
- K4 (dieser Commit): Journal-Konvention etabliert.

**Entscheidungen:**
- Naming-Konvention: alle hand-geschriebenen Knowledge-Dokumente lowercase; Generierte ebenso. Begründung: Konsistenz, Case-Insensitivity-Vermeidung zwischen Windows-Filesystem und Linux-CI.
- YAML-Mapping als formale Architekturentscheidung statt nur Konvention. Begründung: macht N2 (Erweiterbarkeit) ausführbar prüfbar statt nur prosaisch.
- Journal getrennt von Memory führen. Begründung: Memory speichert dauerhafte Fakten, Journal speichert Sessionverlauf — Trennung verhindert Wildwuchs in beiden.

**Offen:**
- Custom-Domain-Frage (eigene Domain vs. `<owner>.github.io/<repo>`) ist weiter offen, prägt URL-Schema-Stabilität, ist vor Phase 15 zu entscheiden.
- Distribution großer Artefakte (Pages vs. Releases) noch nicht festgelegt.
- Modus für regenerierte Knowledge-Docs in CI (strict vs. auto-commit) offen.

**Nächster Einstieg:** Phase 1 starten — Datenmodell für Section / Block / Inline als frozen dataclasses in `src/model/{section,block,inline}.py`. Keine Parser-Logik. Plus kleiner Doc-Patch in `architecture.md` zur Anomalietabelle für `<list rend="labeled">` und `<figure>` mit `<eg>`.

## 2026-04-28 — Requirements und Interface integriert, Gesamtplan erstellt

**Ziel:** `requirements.md` und `interface.md` als Wissensdokumente einarbeiten; den Acht-Phasen-Plan auf einen Fünfzehn-Phasen-Plan erweitern; einen Gesamt-Implementierungsplan erzeugen.

**Erledigt:** Wikilink-Netz zwischen sechs Knowledge-Dokumenten hergestellt. Fünfzehn-Phasen-Plan in `pipeline.md` Phasenplan verankert, anchored an alle siebzehn R- und zehn N-Klauseln aus `requirements.md`. Memory-Einträge `project_requirements.md` und `project_interface.md` neu. Gesamt-Implementierungsplan in `~/.claude/plans/ride-static-gesamt-implementierungsplan.md`.

**Entscheidungen:**
- Acht Phasen reichen nicht; der Scope laut Requirements verlangt fünfzehn. Begründung: Aggregationen, Editorialschicht, Suche, Maschinen-APIs, Validierung, PDF und Deploy sind eigene Bauabschnitte.
- Phase 9 (Editorial) vor Phase 10 (Aggregation), weil Aggregationsseiten Markdown- und YAML-Inhalte aus Phase 9 konsumieren.
- Kein separates `reader-current.md`; Bestandskritik landet in `interface.md` §3.

**Offen:** Plan-Freigabe stand aus, ist mit dieser Session erteilt.

**Nächster Einstieg:** K1 (Naming-Vereinheitlichung) ausführen — siehe Journal-Eintrag oben.
