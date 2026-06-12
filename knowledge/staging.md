---
title: Staging
project:
  name: ride-static
  repository: https://github.com/i-d-e/ride-static
method:
  name: Promptotyping
  url: https://dhcraft.org/excellence/blog/Promptotyping
status: draft
created: 2026-06-12
updated: 2026-06-12
version: 0.1
topics:
  - "[[Static Site Generation]]"
  - "[[Deployment]]"
related:
  - "[[specification]]"
  - "[[pipeline]]"
---

# Staging — Begutachtungsumgebung für unveröffentlichte Beiträge

> Festgehaltenes offenes Problem aus dem Abgleich mit dem redaktionellen
> Zielworkflow (2026-06). Die Entscheidung ist nicht getroffen; dieses
> Dokument sammelt Anforderung, Problemstellung und Lösungsoptionen (§1–4),
> die Bestandsaufnahme der beteiligten Repositories (§6) und den
> Umsetzungsvorschlag als Entscheidungsvorlage (§7–8) für die Diskussion
> mit der Redaktion. Verwandte Festlegungen:
> [[specification#2 Plattform und Architekturgrundsätze]],
> [[pipeline#GitHub Actions workflow (Phase 15)]].

## 1. Anforderung

Der Zielworkflow der Redaktion sieht vor der Freischaltung eines Beitrags
eine Begutachtungsphase vor:

- Die vorbereitete TEI-Datei wird in ein eigenes Repository (`ride-editors`)
  eingespielt; eine GitHub Action erzeugt daraus automatisch Artikelansicht,
  Factsheet und PDF.
- Der Beitrag wird in einer **passwortgeschützten Testumgebung**
  bereitgestellt und an AutorInnen und das IDE zur finalen Begutachtung
  weitergeleitet.
- Änderungen an der TEI-Datei lösen automatisch eine Aktualisierung aller
  generierten Ansichten aus.
- Nach Abschluss der Begutachtung wandert der Beitrag von `ride-editors`
  in das publizierte Korpus (`ride`) und wird damit Teil des öffentlichen
  Builds.

RIDE publiziert im Rolling-Release-Modus: Issues werden beitragsweise
gefüllt, ein Issue kann teilveröffentlicht sein. Die Begutachtungsumgebung
betrifft also laufend einzelne Beiträge, nicht gebündelte Issue-Releases.

## 2. Problemstellung

Die Deploy-Plattform der Site ist GitHub Pages
([[specification#2 Plattform und Architekturgrundsätze]]). GitHub Pages
bietet keinen Zugriffsschutz; Zugriffsbeschränkung für Pages-Sites ist
GitHub-Enterprise-Plänen vorbehalten. Eine Staging-Umgebung kommt in der
Spezifikation bislang nicht vor — die Anforderung ist neu, sie widerspricht
keiner bestehenden Festlegung, ist aber unbeplant.

Der Schutzbedarf ist redaktionell zu präzisieren: Es geht um
Begutachtungsschutz (der Beitrag soll vor der Freischaltung nicht als
publiziert wahrgenommen, verlinkt oder indexiert werden), nicht um
Geheimhaltung. Da `ride-editors` privat ist (§6), ist der Inhalt vor der
Freischaltung derzeit nirgends öffentlich einsehbar — eine öffentlich
erreichbare Vorschau (4.1) würde das ändern und ist deshalb
Gesprächspunkt 3 in §8.

## 3. Anforderungen an eine Lösung

1. Mehrere externe Personen (AutorInnen, IDE) können den Beitrag im Browser
   lesen, ohne lokale Werkzeuge zu installieren.
2. Die Vorschau ist renderidentisch zur späteren Produktion: gleicher
   Parser, gleiche Templates, gleiches PDF.
3. Ein Push auf die TEI-Datei aktualisiert die Vorschau automatisch.
4. Der Schutzgrad entspricht dem tatsächlichen Bedarf (Begutachtungsschutz,
   siehe §2).
5. Geringer dauerhafter Betriebsaufwand; keine zweite, abweichende
   Build-Pipeline.

## 4. Mögliche Lösungen

### 4.1 Unverlinkte Bereitstellung im öffentlichen Build

Die zu begutachtenden Beiträge werden mit dem regulären Build erzeugt und
öffentlich deployt, aber nirgends verlinkt: Sie erscheinen nicht in
Issue-Ansicht und Übersichten, nicht im Suchindex, nicht in Sitemap,
OAI-PMH und Korpus-Dump, und tragen `noindex`-Metadaten. Erreichbar sind
sie nur über die direkte URL (oder über das Repository selbst).

- **Schutzgrad:** kein technischer Schutz, ausschließlich Nichtverlinkung.
  Wer die URL kennt, findet den Beitrag. Da das TEI in `ride-editors`
  privat liegt, macht diese Option Inhalt erstmals vor der Freischaltung
  öffentlich erreichbar (§2, §8 Punkt 3).
- **Aufwand:** Draft-Mechanik im Build — ein Statuskennzeichen pro Beitrag
  (Quelle zu klären: Verzeichniskonvention, Konfigurationsliste oder
  TEI-Header), das alle Verlinkungs- und Indexflächen ausnimmt. Die
  vollständige Liste dieser Flächen ist zu inventarisieren.
- **Implikation:** kein separates Deploy-Ziel, keine Zugangsdaten, ein
  einziger Build. Passt zum Rolling-Release-Modus. Erfüllt die
  Anforderung „passwortgeschützt" dem Wortlaut nach nicht — wäre mit der
  Redaktion als bewusste Abschwächung abzustimmen.

### 4.2 Lokaler Build (verworfen)

Die Vorschau wird nur lokal erzeugt und nicht bereitgestellt.

- **Verworfen,** weil mehrere externe Personen korrekturlesen: AutorInnen
  und IDE haben keinen Zugriff auf eine lokale Arbeitsumgebung mit
  Build-Toolchain. Verfehlt Anforderung 1.

### 4.3 Geschützter Bereich auf dem IDE-Server

Die GitHub Action deployt die Vorschau (z.B. per rsync/SSH) in einen
Bereich des vorhandenen IDE-Servers, der per HTTP Basic Auth geschützt ist.

- **Schutzgrad:** echte Zugriffsbeschränkung mit geteilten Zugangsdaten;
  für Begutachtungszwecke angemessen.
- **Aufwand:** Deploy-Schritt mit Server-Zugangsdaten als CI-Secrets,
  Webserver-Konfiguration (Auth, Pfad), Pflege der Zugangsdaten.
- **Implikation:** Abhängigkeit von Serververfügbarkeit und -administration
  außerhalb der GitHub-Plattform. Der Server existiert bereits (heutiges
  Bilder-Hosting), es entsteht aber ein zweites Deploy-Ziel neben Pages.

### 4.4 Zugriffsschutz-Dienst vor einer Vorschau-Subdomain

Die Vorschau wird auf einer eigenen Subdomain bereitgestellt, vor die ein
Zugriffsschutz-Dienst geschaltet wird (z.B. Cloudflare Access: Anmeldung
per E-Mail-Code vor Auslieferung der Seite).

- **Schutzgrad:** echte Zugriffsbeschränkung, personengebunden statt
  geteiltem Passwort.
- **Aufwand:** DNS-Hoheit über die Subdomain, Konfiguration des Dienstes,
  Pflege der Zugriffsliste.
- **Implikation:** kein eigener Server, aber Abhängigkeit von einem
  Drittanbieter und dessen Kontomodell.

### 4.5 Vorschau im privaten Repository

Die generierten Ansichten werden in das private `ride-editors`-Repository
zurückgespielt; die Zugriffsbeschränkung des Repositories ersetzt den
Passwortschutz. Bearbeitung und Begutachtung finden ohnehin dort statt.

- **Schutzgrad:** echte Zugriffsbeschränkung — aber nur für Personen mit
  Repository-Zugriff.
- **Begrenzung 1 — Darstellung:** GitHub zeigt HTML-Dateien im
  Datei-Viewer als Quelltext, nicht als gerenderte Seite; ein
  „gespiegeltes UI" im Repository ist nicht klickbar. GitHub Pages auf
  privaten Repositories publiziert öffentlich (zugriffsbeschränktes
  Pages-Hosting ist Enterprise-Plänen vorbehalten). **PDF-Dateien
  rendert der Datei-Viewer dagegen vollständig** — die PDF-Ansicht eines
  Beitrags ist im privaten Repository direkt lesbar.
- **Begrenzung 2 — Adressaten:** AutorInnen haben keinen Zugriff auf
  `ride-editors`. Sie pro Beitrag als Collaborator einzuladen gewährte
  ihnen Einsicht in sämtliche Beiträge in Vorbereitung samt Historie —
  administrativ aufwendig und vom Zuschnitt zu breit.
- **Bewertung:** als alleinige Lösung ungeeignet, weil der an AutorInnen
  weiterleitbare Link fehlt; als **Teilbaustein** brauchbar — das in das
  Repository zurückgespielte PDF deckt die IDE-interne Prüfung ohne
  weitere Infrastruktur ab.

## 5. Gemeinsame Bausteine unabhängig von der Wahl

Drei Bausteine braucht jede der Optionen 4.1, 4.3 und 4.4:

1. **Overlay-Build.** Die Vorschau baut nicht den Einzelbeitrag, sondern
   die ganze Site: publiziertes Korpus auschecken, eingereichte TEI-Dateien
   aus `ride-editors` in das Korpus überlagern, regulärer `src.build`-Lauf.
   AutorInnen sehen ihren Beitrag im echten Site-Kontext, renderidentisch
   zur Produktion (Anforderung 2).
2. **Trigger-Verkabelung.** Der Build-Workflow liegt in `ride-static` und
   reagierte bislang nur auf Pushes in dieses Repository. **Umgesetzt
   (2026-06-12):** `build.yml` nimmt `repository_dispatch`-Events
   (`corpus-updated`, `editors-updated`) entgegen; Sender-Vorlagen für
   `ride` und `ride-editors` liegen unter `docs/upstream-workflows/` und
   werden je einmalig im Quell-Repository installiert (eine Datei, ein
   Token-Secret) — siehe [[pipeline#GitHub Actions workflow (Phase 15)]].
3. **Sichtbarkeit von `ride-editors`.** Soll der Begutachtungsschutz mehr
   als Nichtverlinkung sein, muss `ride-editors` privat bleiben (Stand
   2026-06: das Repository ist privat); der Checkout im Build-Workflow
   braucht dann ein Zugriffstoken.

## 6. Bestandsaufnahme der vorhandenen Repositories (2026-06-12)

Für den Umsetzungsvorschlag in §7 erhoben:

- **`i-d-e/ride`** (öffentlich): hält `tei_all/`, `schema/`, `issues/`
  (Bilder). Keine GitHub-Actions-Workflows vorhanden.
- **`i-d-e/ride-editors`** (privat): existiert bereits und trägt eine
  klare Ablagekonvention — pro Issue ein Ordner (`issue-{name}/`), darin
  pro Beitrag ein Ordner `{slug}/` mit `{slug}-tei.xml`, `pictures/` und
  `{slug}-wordcloud.png`; daneben Arbeitsmaterial (`review/`, `v1/`,
  `v2/`, Questionnaire, PDF) und ein `archive/`-Ordner. Keine Workflows.
  Die Wordcloud liegt also bereits konventionsgemäß neben dem TEI — die
  Lieferkonvention für neue Beiträge ist damit faktisch geklärt.
- **Befund Dublette:** bereits publizierte Beiträge verbleiben nach der
  Publikation in `ride-editors` (Beispiel: `tei-publisher` liegt dort
  samt finalem PDF und ist zugleich im publizierten Korpus). Jede
  Vorschau-Mechanik muss deshalb gegen das publizierte Korpus
  deduplizieren: existiert die Review-ID in `tei_all/`, gewinnt die
  publizierte Fassung, der Eintrag in `ride-editors` wird ignoriert.

## 7. Umsetzungsvorschlag (Entscheidungsvorlage)

Empfehlung: **Option 4.1 als Default** umsetzen, ergänzt um den
PDF-Rückspiel-Baustein aus 4.5 für die IDE-interne Prüfung; Upgrade auf
4.3/4.4 bleibt jederzeit möglich, weil sich nur das Deploy-Ziel der
Vorschau ändert, nicht die Build-Mechanik. Konkret:

1. **Draft-Quelle.** Der Build erhält eine zweite, optionale Korpusquelle
   `../ride-editors`. Discovery folgt der vorhandenen Konvention
   (`issue-*/{slug}/{slug}-tei.xml`, `archive/` ausgenommen); gefundene
   Beiträge werden als Draft markiert und gegen das publizierte Korpus
   dedupliziert (§6). In CI wird `ride-editors` nur ausgecheckt, wenn ein
   Zugriffstoken als Secret hinterlegt ist; fehlt es, baut die Site wie
   bisher — der Draft-Pfad ist strikt additiv.
2. **Asymmetrische Fehlerbehandlung.** Parse-Fehler in einem Draft
   erzeugen eine Warnung und überspringen den Beitrag; sie dürfen den
   öffentlichen Build niemals brechen. Parse-Fehler im publizierten
   Korpus bleiben harte Fehler.
3. **Vorschau-Flächen.** Drafts rendern unter `/drafts/{id}/` (HTML, PDF,
   Abbildungen aus dem `pictures/`-Ordner des Draft-Verzeichnisses, per
   Dateinamen aufgelöst), dazu eine unverlinkte Indexseite `/drafts/` als
   einzige Einstiegs-URL für die Redaktion. Draft-Seiten tragen ein
   sichtbares Vorschau-Banner, `noindex`-Metadaten und keinen
   Pagefind-Index-Anker.
4. **Ausschluss-Flächen.** Drafts erscheinen nicht in: Issue-Ansicht und
   Issue-Übersicht, Tag-/Reviewer-/Resources-Aggregationen, Data-Charts,
   Suchindex, Sitemap, OAI-PMH, `corpus.json`, Navigation, Redirects.
   Technisch: die Aggregations- und Schnittstellen-Renderer erhalten
   ausschließlich die publizierte Liste; Drafts laufen als getrennte
   Liste nur durch Seiten-Render und Asset-Kopie.
5. **Freischaltung** bleibt der Git-Move: TEI und `pictures/` von
   `ride-editors` nach `ride`, Wordcloud nach
   `static/images/wordclouds/{id}.png` in `ride-static`, bei Bedarf
   Issue-YAML anlegen. Der Dispatch-Trigger baut die Site neu; die
   Draft-URL verschwindet, die kanonische URL `/issues/{N}/{id}/`
   entsteht.

**Bereits umgesetzt** (entscheidungsrobust, 2026-06-12): die
Trigger-Verkabelung (§5 Punkt 2) und die Bedienungs-Anleitung im
`README.md` von ride-static. **Zurückgestellt bis zur Entscheidung:**
die Draft-Mechanik (Punkte 1–4) und der PDF-Rückspiel-Baustein.

## 8. Status und Gesprächsagenda

Entscheidung offen; vor der Umsetzung der Draft-Mechanik mit der
Redaktion zu klären:

1. Ist „passwortgeschützt" wörtlich verbindlich, oder genügt
   Begutachtungsschutz durch Nichtverlinkung (4.1)? Falls wörtlich:
   IDE-Server (4.3) oder Zugriffsschutz-Dienst (4.4)?
2. Genügt für die IDE-interne Prüfung das in `ride-editors`
   zurückgespielte PDF (4.5 als Teilbaustein)?
3. Dürfen unveröffentlichte Beiträge als gerenderte Seiten öffentlich
   erreichbar sein, solange sie unverlinkt und unindexiert sind —
   auch unter der Bedingung, dass das TEI im privaten Repository liegt
   und damit erstmals Inhalt vor der Freischaltung öffentlich würde?
4. Wer führt den Freischaltungs-Move aus (Managing Editors direkt,
   oder per Pull Request mit Vier-Augen-Prinzip)?

Die Vorfestlegung auf GitHub Pages als einzige Plattform
([[specification#2 Plattform und Architekturgrundsätze]]) bleibt von 4.1
unberührt und wird von 4.3/4.4 um ein zweites Deploy-Ziel ergänzt.
