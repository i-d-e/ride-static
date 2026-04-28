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
