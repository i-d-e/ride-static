# Workplan — current sprint

> Two Claude sessions split the remaining work into **exactly two aspects**,
> one each. Both read this file at session start, update the Status block
> at the bottom as work lands, and otherwise keep their hands off the
> other side's paths.
>
> When both aspects are at *done*, we raise to the human stakeholder for
> consolidation to one Claude for Phases 11–15.

## Aspect A — Backend (Chef-Koordinator): Phase 7

**Ziel.** Cross-Refs auflösen und Bilder im Output korrekt verlinken. Heute rendert das Frontend `<a href="#K12345">…</a>` als Sackgasse und `<img src="figures/foo.png">` ohne dass die Datei dort liegt; das ist nach Phase 7 vorbei.

**Scope.**

1. **Vier-Bucket-Reference-Resolver** für jeden `<ref @target>`, gemäß [pipeline.md "Cross-cutting concerns"](knowledge/pipeline.md):
   - `local` — Target ist `#xml-id` und der Anker existiert in derselben Rezension
   - `criteria` — Target beginnt mit `#K…`, wird gegen das `@xml:base` der zugehörigen Taxonomie aufgelöst (5 209 Vorkommen, siehe [data.md](knowledge/data.md))
   - `external` — `http(s)://` — durchgereicht
   - `orphan` — sonst, Build-Warnung, Renderer-Hint
2. **Asset-Pipeline** für eingebettete Bilder: Kopie von `../ride/issues/{n}/figures/*` nach `site/issues/{n}/{review-id}/figures/`, `Figure.graphic_url` rewritet auf den deployten Pfad. Fehlende Bilder = Warnung, kein Crash.
3. **Wayback-Hint** für Bibliographie-`ref_target`: HTTP-HEAD-Probe mit File-Cache, flag bei toten Links als `BibEntry.wayback_url` oder ähnlich. Optional in dieser Phase, kann nach Phase 13 wandern.

**Deliverables.**
- `src/parser/refs.py` mit `resolve_ref(ref, review, criteria_index) → ResolvedRef`
- `src/build/assets.py` (oder `src/parser/assets.py`) für die Bildkopie + URL-Rewrite
- Optional `src/parser/wayback.py`
- Synthetische Tests pro Bucket plus Korpus-Smoke
- Frontend-Vertrag: jede `Reference`-Instanz im gerenderten Modell trägt eine Bucket-Information (z.B. zusätzliches Feld `bucket: str`, oder ein paralleles `Review.resolved_refs`-Mapping); das Frontend dispatcht via `config/element-mapping.yaml` `by_bucket`

**Owned paths.** `src/parser/`, `src/model/`, `src/build/assets.py`, `scripts/`, `knowledge/`, `Journal.md`, `COORDINATION.md`, `CLAUDE.md`, `MEMORY.md`.

**Hands off.** `templates/`, `static/`, `src/render/`, `src/build.py`, `content/`, `config/element-mapping.yaml`, `WORKPLAN.md` (Status-Block ausgenommen).

**Pre-Handover-Note ans Frontend.** Sobald die Bucket-Information am `Reference`-Objekt liegt, eine Zeile ins Journal: *"Phase 7 ready — Reference.bucket ∈ {local, criteria, external, orphan}"*. Frontend nimmt sie auf, vor dem Hinweis tut sich am Cross-Ref-Rendering nichts.

## Aspect B — Frontend: Phase 10 + Phase-8-Citation-Cleanup

**Ziel.** Die Navigations-Außenhaut der Site bauen — sechs Seitentypen aus [interface.md §4](knowledge/interface.md), die heute nur Platzhalter haben. Plus Citation-Daten so embedden, dass die Cite-Buttons echt kopieren.

**Scope.**

1. **Citation-Export** (~60 Zeilen, davor weil leichtgewichtig):
   - `to_bibtex(review)` und `to_csl_json(review)` als Python-Helper in `src/render/html.py`, registriert als Jinja-Filter
   - Zwei `<script class="ride-cite-data" data-format="…">`-Blöcke in `review.html` mit den generierten Strings
   - `cite-copy.js` liest die Blöcke schon — kein JS-Change nötig
   - Tests für BibTeX-Form und CSL-JSON-Schlüssel
2. **Sechs Seitentypen** gegen die Datasets aus [src/parser/datasets.py](src/parser/datasets.py) (Tags, Reviewer, Resources, alle aus Phase 6.C bereit) plus den Heft-Aggregat aus `Review.issue`:
   - `index.html` — Startseite (aktuelles Heft + ausgewählte Rezensionen + News-Slot)
   - `/issues/` — Heftübersicht
   - `/issues/{n}/` — Heftansicht
   - `/tags/` und `/tags/{slug}/` — Tag-Übersicht und Detail
   - `/reviewers/` und `/reviewers/{slug}/` — Reviewer-Liste und Detail
   - `/resources/` — Reviewed-Resources-Tabelle
3. **Data-Seite (Stretch Goal):** `/data/` mit minimalen SVG-Charts aus den Questionnaire-Aggregaten, vanilla SVG ohne JS-Framework. Falls die ersten beiden Punkte zu groß werden, wandert das in den nächsten Sprint.

**Deliverables.**
- Templates pro Seitentyp unter `templates/html/`
- `src/render/aggregations.py` — Page-Builder, konsumiert `src.parser.datasets`
- `src/build.py` um die neuen Seitentypen erweitert
- Tests für Frontmatter, URL-Schema, BEM-Klassen
- Sidebar-Tag-Links im Review-Template zeigen schon auf `/tags/{slug}/` — nach Phase 10 endet das nicht mehr im 404

**Owned paths.** `templates/`, `static/`, `src/render/`, `src/build.py`, `content/`, `config/element-mapping.yaml`, `tests/test_render_*.py`.

**Hands off.** `src/parser/`, `src/model/`, `src/build/assets.py` (Backend), `scripts/`, `knowledge/`, `COORDINATION.md`, `CLAUDE.md`, `MEMORY.md`.

## Regeln, an die sich beide halten

- **Commits per logischem Schritt**, niemals `git add -A`. Pfade explizit nennen.
- **Journal-Eintrag** am Sessionende, oben in [Journal.md](Journal.md), die fünf festen Felder.
- **Datenvertrag-Änderungen** (neue Felder an `Review`, `Reference`, …) sind Backend-Hoheit. Frontend fragt im Journal an, Backend implementiert.
- **Keine Domain-Modell-Imports im Frontend ändern.** Wenn `Reference.bucket` neu ist, **wartet** das Frontend auf den Pre-Handover-Note. Vorher rendert es Refs als rohe Anker (ist heute so).
- **WORKPLAN.md** darf jeder im Status-Block am Fuß ändern. Sonst nur der, der den Sprint-Plan überholt — und nur in Absprache.

## Sync-Punkte (in Reihenfolge)

1. Backend startet Phase 7. Frontend startet **gleichzeitig** mit Citation-Cleanup + Heftübersicht/Heftansicht (datenvertraglich unabhängig).
2. Backend liefert Pre-Handover-Note ins Journal, sobald `Reference.bucket` (oder Äquivalent) und Asset-Pipeline live sind.
3. Frontend integriert die Buckets ins Reference-Rendering und die rewritten Bildpfade — das ist im Wesentlichen CSS plus zwei Macro-Updates.
4. Beide *done*. Stakeholder konsolidiert auf einen Claude.

## Status

| Aspekt | Stand | Letzte Aktualisierung |
|---|---|---|
| A — Phase 7 (Backend) | nicht begonnen | 2026-04-29 |
| B — Phase 10 + Citation (Frontend) | nicht begonnen | 2026-04-29 |
