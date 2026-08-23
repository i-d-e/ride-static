---
title: RIDE-Pilot mit drei Self-Audits
project:
  name: ride-static
status: verified
created: 2026-08-22
updated: 2026-08-23
language: de
related:
  - "[[workflow]]"
  - "[[pipeline]]"
  - "[[specification]]"
  - "[[architecture]]"
---

# RIDE-Pilot mit drei Self-Audits

## Auftrag und Ergebnis

Der Pilot erprobt den neuen RIDE-Workflow mit drei realen Forschungswerkzeugen: teiCrafter, SZD-HTR und ZBZ-OCR-TEI. Für jedes Werkzeug liegt ein englischer, als Draft und Self-Audit gekennzeichneter Review-Entwurf vor. Alle drei Entwürfe erläutern die Beteiligung agentischer KI an Analyse, Formulierung, Fragebogenzuordnung und Diagrammerstellung. Die fachliche Prüfung und Verantwortung bleiben ausdrücklich bei den menschlichen Autor:innen.

Der technische Zielzustand ist für Drafts erreicht. Ein Review wird als selbstständiger Ordner mit `review.xml` und optionalen Abbildungen hinzugefügt. Der Build entdeckt und validiert das Bundle und erzeugt Reviewseite, Factsheet, TEI-Download, Abbildungen, Wortwolke und PDF. Drafts sind von allen öffentlichen Publikationsausgaben getrennt. Eine offizielle Veröffentlichung erfordert weiterhin redaktionelle Freigabe, registrierten DOI, publizierbare Metadaten und die in RIDE vorgesehene externe Begutachtung.

## Pilot-Bundles

| Review | Vorläufige ID | Fragebogen | Zentrale Funktion |
|---|---|---:|---|
| teiCrafter | `draft.teicrafter-pilot` | 44/44 beantwortet | browserbasierte TEI-XML-Bearbeitung mit optionalen, prüfbaren LLM-Vorschlägen |
| SZD-HTR | `draft.szd-htr-self-audit` | 43/44 beantwortet | projektspezifische VLM-Transkription und redaktionelle Bearbeitung für den Stefan-Zweig-Nachlass |
| ZBZ-OCR-TEI | `draft.zbz-ocr-tei-self-audit` | 44/44 beantwortet | projektspezifische OCR-zu-TEI-Pipeline für die digitale Neuedition von Jeanne Hersch |

Jedes Bundle enthält eine selbst erstellte SVG-Workflowgrafik mit `<figDesc>` als Alternativtext und einer ausführlicheren Legende im Review. Geschützte Projektquellen und Faksimiles wurden nicht in die Bundles übernommen.

## Bestätigter Workflow

1. Unter `issues/{N}/reviews/{slug}/` werden `review.xml` und bei Bedarf `pictures/` angelegt.
2. Abbildungen werden relativ als `pictures/{datei}` referenziert. Ein kurzer `<figDesc>` beschreibt jede inhaltlich relevante Grafik.
3. Eine Arbeitsfassung erhält `<revisionDesc status="draft">` und eine eindeutige ID im Format `draft.{lowercase-slug}`. Der DOI darf im Draft fehlen.
4. `uv run python -m src.build --include-drafts` erzeugt die lokale Vorschau. Unter Linux oder in CI ergänzt `--pdf --pdf-drafts-only` die Draft-PDFs.
5. Nach inhaltlicher und redaktioneller Freigabe werden DOI, endgültige `xml:id` und Publikationsstatus gesetzt. Commit und Push lösen anschließend die Qualitätsprüfungen und den Build aus.

Der gewünschte Ablauf „Ordner hinzufügen und committen“ funktioniert damit für technisch vollständige Draft-Bundles. Das Verfassen und Prüfen des Reviews sowie die formale Publikationsfreigabe bleiben vorgelagerte redaktionelle Aufgaben.

## Erzeugte und geprüfte Ausgaben

Für alle drei Reviews wurden HTML-Review, separates Factsheet, TEI-Download, SVG-Abbildung, deterministische Wortwolke und neunseitiges PDF erzeugt. Reviewseiten und Factsheets tragen `noindex, nofollow`, enthalten keine kanonische URL und keine JSON-LD-Publikationsdaten und sind vom Pagefind-Index ausgeschlossen. Die Reviewseiten wurden bei 1440, 768 und 390 Pixel Breite geprüft. Lange Commit-Hashes und URLs brechen auf kleinen Bildschirmen um; Grafiken bleiben innerhalb der Textspalte. Alle 27 PDF-Seiten wurden als Bilder auf leere Seiten, Überlagerungen, abgeschnittene Inhalte und unlesbare Diagramme geprüft.

Der abschließende Build verarbeitete 114 TEI-Dateien ohne Validierungsfehler, erzeugte drei Draft-Vorschauen, drei Wortwolken und drei PDFs ohne PDF-Fehler. Die vollständige Testsuite bestand mit 727 Tests; zwei optionale Tests wurden übersprungen. Ruff und `git diff --check` bestanden ebenfalls.

## Was funktioniert

- Das selbstständige Review-Bundle beseitigt für neue Reviews die Abhängigkeit vom getrennten Bilder-Repository.
- Draft-IDs ohne DOI werden kontrolliert akzeptiert und auf ein festes Format geprüft.
- Neue Bundles werden strikt gegen Relax NG validiert; fehlende, unsichere oder nicht auflösbare Bildreferenzen stoppen den Build.
- Drafts bleiben aus Issue-Seiten, Navigation, Feeds, Sitemap, OAI-PMH, Korpusdaten, Bibliografieexporten und Redirects ausgeschlossen.
- Factsheet, Wortwolke, TEI-Download und PDF entstehen aus derselben TEI-Quelle.
- Der Workflow funktioniert unverändert für drei inhaltlich und technisch unterschiedliche Review-Texte.
- `<figDesc>` wird durch Schema, Parser, HTML und Tests bis zum Bildalternativtext durchgereicht.
- Der Frontend-Test entdeckt neue Drafts dynamisch; weitere Bundles benötigen keine testspezifische Registrierung.

## Offene Punkte und Lösungswege

| Befund | Auswirkung | Vorgesehener Lösungsweg |
|---|---|---|
| Es gibt keine gemeinsam erreichbare, zugriffsgeschützte Staging-Seite. | Die ausdrücklich freigegebenen Self-Audits sind als öffentliche `noindex`-Beispiele auf GitHub Pages prüfbar; vertrauliche Drafts bleiben auf lokale Builds, das private Repository oder CI-Artefakte beschränkt. | Geschütztes Hosting für vertrauliche Drafts festlegen. |
| Der Build führt Relax-NG-Validierung aus, aber keine ausführbare Schematron-Prüfung. | Einige redaktionelle Regeln im ODD, darunter Metadatenanforderungen, werden nicht automatisch erzwungen. | Schematron kompilieren und als eigenes, getestetes Qualitätsgate in Build und CI integrieren. |
| PDF-Erzeugung benötigt native WeasyPrint-Bibliotheken, die in der aktuellen Windows-Umgebung fehlen. | Der Standardbefehl unter Windows erzeugt kein PDF. | PDF weiterhin reproduzierbar unter Linux, WSL und CI erzeugen; Windows-Anleitung entsprechend eindeutig halten. |
| Der historische Bestand meldet 62 Schemahinweise und ohne das Schwester-Repository 63 fehlende Bilder. | Ein lokaler Komplettbuild ist ohne Zusatz-Checkout bei alten Reviews visuell unvollständig. | Legacy-Bestand schrittweise in Bundles migrieren oder das Bilder-Repository im vollständigen Build mit auschecken. |
| Zwei historische Reviews teilen den DOI `10.18716/ride.a.21.2`. | Bei passender Ausgabekonfiguration kann eine Seite überschrieben werden. | DOI-Zuordnung redaktionell prüfen und korrigieren. |
| Der reine Python-Vorschau-Build erzeugt keinen Pagefind-Suchindex. | Die lokale Navigation funktioniert; das Suchfeld bleibt bis zum getrennten Pagefind-Schritt ohne Funktion und protokolliert eine Warnung. | Für vollständige lokale Suche anschließend Pagefind ausführen oder das Suchfeld in Draft-Artefakten gezielt deaktivieren. Die Produktions-CI führt den Pagefind-Schritt bereits aus. |
| Der RIDE-Fragebogen wird weiterhin außerhalb des Repository-Schritts ausgefüllt und in TEI überführt. | Das Hinzufügen eines Ordners automatisiert die Publikation, aber nicht die Review-Erstellung. | Eine dokumentierte Export- oder Konvertierungsstrecke vom Fragebogen zur Bundle-TEI ergänzen. |

## Inhaltliche Befunde der Reviews

### teiCrafter

Der deterministische Bearbeitungskern wurde mit realen Jeanne-Hersch-TEI-Dateien geprüft. Laden, Faksimile- und Seitenwechsel, Korrektur, Indexierung, Annotation, GND-Abgleich, Speichern, Download und erneutes Öffnen funktionierten. Projektübliche GND- und Provenienzangaben blieben im Roundtrip erhalten. Der optionale LLM-Pfad trennt Vorschläge von bestätigten Inhalten und weist strukturell unvollständige TEI-Ausgaben zurück. Das geprüfte lokale Modell lieferte zugleich fachlich unzuverlässige und teilweise halluzinierte Vorschläge. Weitere Arbeit betrifft projektspezifische Relax-NG- und Schematron-Validierung, versionierte Releases mit Software-DOI, Browsermatrix, externe Usability-Prüfung, Barrierefreiheitsaudit und fachlich annotierte LLM-Evaluationsdaten.

### SZD-HTR

Der Self-Audit beschreibt eine projektspezifische VLM-Transkriptions- und Redaktionsumgebung auf dem geprüften Stand `0001f9ea1f1aa40c8839b218798a264f28bac3ed`. Achtzehn Pytest-Tests und 93 eigenständige Prüfungen bestanden. Von 2.452 Objekten waren 44 freigegeben und 85 als agentisch geprüft markiert; kein Objekt war als Ground Truth verifiziert. Offene Qualitätsrisiken betreffen einen Fehler in der Vertrauensstatuslogik, persistentes Undo-Verhalten, gemischte CER-Kohorten, eine doppelte Diagrammzählerfassung und unvollständige Exporte. Die konkrete Deployment-Plattform ist mangels belastbarer Evidenz im Factsheet als unbeantwortet ausgewiesen. Eine Veröffentlichung des Viewers setzt dokumentierte Rechte-, Datenschutz- und Providerfreigaben voraus.

### ZBZ-OCR-TEI

Der Self-Audit bezieht sich auf den geprüften Stand `c0cc741739c8610c2b316db13c1319f86f8ce305`. 2.440 Tests bestanden; 285 von 285 geprüften TEI-Dokumenten waren strukturell valide. Zugleich traten 2.003 Warnungen in 252 Dokumenten auf, und sämtliche Datenströme waren menschlich unverifiziert. Die CER-Stichprobe von 25 Seiten ergab einen Mittelwert von 2,0804 Prozent und einen Median von 1,2763 Prozent; ihre Zusammensetzung erlaubt keine Verallgemeinerung auf den Gesamtbestand. Weitere Risiken betreffen zwei öffentlich versionierte Dateien mit personenbezogenen Angaben, eine nicht dokumentierte Publikationslizenz für Faksimiles, den Wechsel vom historischen Mistral-Pfad zum aktuellen Gemini-Standard sowie fehlende Releases, DOI und Abhängigkeits-Lock. Der Review empfiehlt eine grundlegende Überarbeitung vor einer wissenschaftlich belastbaren Veröffentlichung.

## Geltungsgrenze

Die drei Texte sind interne Self-Audits und Workflow-Piloten. Sie ersetzen keine unabhängigen RIDE-Reviews. Ihr nachgewiesener Nutzen liegt in der technischen Erprobung des Bundle-Workflows, der strukturierten Selbstprüfung der Werkzeuge und der Ableitung konkreter Verbesserungsaufgaben für die drei Projekte.
