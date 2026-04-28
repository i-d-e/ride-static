# Coordination — Backend / Frontend / Documentation

> Two Claude sessions work on this repository in parallel. This file is
> their handshake — who owns which paths, what data shape the frontend
> can rely on, and how to avoid stepping on each other.

## Rollen

| Rolle | Verantwortung | Zuständige Pfade |
|---|---|---|
| **Backend + Doku + Koordination** (Chef-Koordinator) | Parser, Domänenmodell, Aggregate, Wissensbasis, Phasen 5–7, 12, 13 | `src/parser/`, `src/model/`, `scripts/`, `knowledge/`, `Journal.md`, `MEMORY.md`, `CLAUDE.md`, dieses Dokument |
| **Frontend** | HTML-Templates, CSS, JS-Module, Build-CLI, PDF-Renderer, Phasen 8–11, 14, 15 | `templates/`, `static/`, `src/render/`, `src/build.py`, `content/`, `config/element-mapping.yaml` |

Phase 12 (Maschinenschnittstellen — OAI-PMH, JSON-LD, Sitemap) ist Backend-zugehörig, weil sie über das Domänenmodell serialisiert. Phase 13 (Validierung + Build-Bericht) ebenfalls Backend.

Bei Konflikten oder gemeinsamen Berührungspunkten entscheidet der Chef-Koordinator. Der Mensch-Stakeholder kann jederzeit überschreiben.

## Datenvertrag — was die Templates sehen

Templates und Renderer sehen ausschließlich die Datenklassen aus
`src/model/`. Niemals lxml-Elemente, niemals XML-Strings, niemals direkten
Korpus-Zugriff. Eine Template, die `etree.parse(...)` ausführt, ist ein
Bug — gleich beim Code-Review zurückweisen.

**Stand Phase 5 (Stage 2.B abgeschlossen):**

```python
Review:
    id: str                              # ride.13.7 etc.
    issue: str                           # "13"
    title: str
    publication_date: str                # ISO 8601 oder Klartext
    language: str                        # "en" | "de" | …
    licence: str                         # CC-Link
    keywords: tuple[str, ...]
    authors: tuple[Author, ...]          # Person + Affiliation + Email
    editors: tuple[Editor, ...]          # Person + Role
    related_items: tuple[RelatedItem, ...]
    front: tuple[Section, ...]           # meist leer
    body: tuple[Section, ...]            # Hauptinhalt, rekursiv
    back: tuple[Section, ...]            # Bibliographie heute leer (Phase 6)
    figures: tuple[Figure, ...]          # alle Figuren in Dokumentreihenfolge
    notes: tuple[Note, ...]              # alle Footnotes in Dokumentreihenfolge
    source_file: str

Section:
    xml_id: str                          # echter @xml:id oder synthetisch (sec-1.2)
    type: Optional[str]                  # abstract | bibliography | appendix | None
    heading: Optional[tuple[Inline, ...]]
    level: int                           # 1..3
    blocks: tuple[Block, ...]
    subsections: tuple[Section, ...]

Block = Paragraph | List | Table | Figure | Citation

Paragraph:
    inlines: tuple[Inline, ...]
    xml_id: Optional[str]                # Copy-Link-Anker (interface §11)
    n: Optional[str]                     # sichtbare Randnummer

ListItem:
    inlines: tuple[Inline, ...]
    label: Optional[tuple[Inline, ...]]  # nur bei rend="labeled"
    blocks: tuple[Block, ...]            # genested (3 Korpus-Fälle)

TableCell:
    inlines: tuple[Inline, ...]
    is_header: bool                      # @role="label"
    blocks: tuple[Block, ...]            # eingebettete Figures (22 Fälle)

Figure:
    kind: str                            # "graphic" | "code_example"
    head: tuple[Inline, ...]
    xml_id: Optional[str]                # bidirektionaler Apparate-Link (§6)
    graphic_url: Optional[str]
    code: Optional[str]
    code_lang: Optional[str]
    alt: Optional[str]                   # heute immer None (figDesc fehlt im Korpus)

Citation:
    quote_inlines: tuple[Inline, ...]
    bibl: Optional[tuple[Inline, ...]]
    bibl_target: Optional[str]           # erstes <ref @target> in <bibl>

Inline = Text | Emphasis | Highlight | Reference | Note | InlineCode

Reference:
    children: tuple[Inline, ...]
    target: Optional[str]                # roh; Phase 7 löst auf
    type: Optional[str]                  # "crossref" (normalisiert)

Note:
    children: tuple[Inline, ...]
    xml_id: Optional[str]                # ftnN — Anker für <ref target="#ftnN">
    n: Optional[str]
    place: Optional[str]
```

Alle Klassen sind `frozen=True`-Dataclasses, alle Sequenzen sind `tuple[...]`.

## Was vom Frontend NICHT angenommen werden darf (Phase 5 Stand)

- `Review.bibliography` existiert noch nicht — Phase 6.
- `Review.questionnaire` existiert noch nicht — Phase 6.
- `Reference.target` ist nicht aufgelöst — Phase 7. Render solange als rohes Attribut, ohne Tooltip-Vorschau und ohne Wayback-Branch.
- `Figure.alt` ist im aktuellen Korpus immer `None`. Frontend muss Fallback liefern (`head`-Text oder `"Figure N"`); Phase 13 wird die Lücke als Build-Warnung aggregieren.
- `Section.back` enthält den Bibliographie-`<div>`, aber dessen `blocks` sind heute `()` (Phase-6-Defer). Die Bibliographie selbst kommt in Phase 6 als eigenes `Review.bibliography`-Feld, nicht über `back.blocks`.

## Wo darf wer Dateien anlegen?

| Pfad | Wer | Anmerkung |
|---|---|---|
| `src/parser/`, `src/model/` | Backend | Frontend liest, schreibt nicht |
| `src/render/`, `src/build.py` | Frontend | Backend liest |
| `templates/` | Frontend | komplett |
| `static/` | Frontend | CSS ≤ 800 Zeilen, vier JS-Module |
| `content/` | Frontend (mit redaktioneller Eingabe) | Markdown + Frontmatter |
| `config/element-mapping.yaml` | Frontend (mit Backend-Review) | Render-Bindings |
| `scripts/` | Backend | Discovery + Knowledge-Renderer |
| `knowledge/` | Backend | Wissensvault, .md only, Wikilinks |
| `inventory/` | Backend (generiert) | gitignored |
| `tests/test_parser_*` | Backend | Parser-Tests |
| `tests/test_render_*`, `tests/test_build_*` | Frontend | Render-Tests |
| `Journal.md` | Beide (in eigener Phase) | Append-only mit Datum + Phase-Marker |
| `COORDINATION.md` (dieses Dokument) | Backend | Frontend schlägt Änderungen vor, Backend committet |
| `CLAUDE.md` | Backend | Projekt-Instruktionen |
| `MEMORY.md` (auto-memory) | Beide (eigene Memory-Pfade) | siehe Memory-Konvention unten |

## Memory-Konvention

Beide Claudes pflegen ihren eigenen Memory-Pfad unter
`~/.claude/projects/.../memory/`. Geteilte Erkenntnisse landen primär hier
und im Journal. Stale-Memory-Pflege liegt beim jeweiligen Claude.

Für gegenseitige Sichtbarkeit gilt: **Wer einen wichtigen Fakt für den
anderen Claude festhalten will, schreibt ihn ins Journal oder direkt in
dieses Dokument.** Memory ist privat, das Repo ist geteilt.

## Handover-Punkte (was wann fertig sein muss)

- **Phase 6 abgeschlossen** → Frontend kann mit Bibliographie-Apparat,
  Questionnaire/Factsheet und Tag-Aggregation beginnen.
- **Phase 7 abgeschlossen** → Frontend kann Cross-Refs auflösen und die
  Tooltip-Vorschau auf Inline-References (interface §11) wirklich
  inhaltlich befüllen. Vorher: Refs als rohe Anker rendern.
- **Phase 8 unter Frontend-Hoheit** → Backend liefert Domänenobjekte
  und prüft den Datenvertrag, mischt sich in Templates / CSS / JS aber
  nicht ein.

## Konflikt-Regeln

- Wenn beide Claudes denselben Pfad anfassen wollen, reicht der
  betreffende Claude den Konflikt an den Chef-Koordinator. Der entscheidet
  pragmatisch.
- Modell-Erweiterungen (neue Felder an `Review`, `Section`, `Block`,
  `Inline`) sind Backend-Hoheit. Frontend kann sie *anfragen* via
  Notiz im Journal oder hier; Backend implementiert.
- Neue Render-Konventionen (CSS-Klassen, JS-Module, Templates) sind
  Frontend-Hoheit. Backend reviewt nur, ob der Datenvertrag eingehalten
  wird.
- `git add -A` ist riskant in dieser Setzung — beide Claudes sollten
  Dateien explizit benennen, um nicht versehentlich die Arbeit des
  anderen mit-zu-committen.
