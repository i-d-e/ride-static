---
title: Index
project:
  name: ride-static
  repository: https://github.com/i-d-e/ride-static
method:
  name: Promptotyping
  url: https://dhcraft.org/excellence/blog/Promptotyping
status: active
created: 2026-05-09
updated: 2026-06-12
version: 0.2
language: en
related:
  - "[[specification]]"
  - "[[architecture]]"
  - "[[interface]]"
  - "[[pipeline]]"
  - "[[staging]]"
  - "[[data]]"
  - "[[schema]]"
---

# knowledge/

This is the project-internal knowledge base for *ride-static*, the static-site generator for [ride.i-d-e.de](https://ride.i-d-e.de). It addresses three readers at once: a human reviewer onboarding into the project, a coding agent reading the vault as context, and the maintainer returning after weeks. The directory holds the design-intent documents (specification, architecture, interface, pipeline) and the generated corpus references (data, schema). Operational concerns — code, templates, configuration, build artefacts — live elsewhere in the repository and are not duplicated here.

## Documents

Reading order follows the eight Promptotyping functions, not alphabetical order. Identity lives in [README.md](../README.md) at the repository root; agent socialisation lives in [CLAUDE.md](../CLAUDE.md) at the repository root; both are referenced from here but are not part of `knowledge/` itself.

| Document | Function | Update rhythm |
|---|---|---|
| [[data]] | Material — empirical reality of the TEI corpus (111 reviews) | regenerated when corpus changes (script-driven) |
| [[schema]] | Material — `ride.odd` customisations and schema-vs-corpus diff | regenerated when ODD changes (script-driven) |
| [[specification]] | Substance — 17 R-clauses, 10 N-clauses, 6 A-decisions, 5 roles | incremental, when scope shifts |
| [[architecture]] | Construction — domain model, parser anomalies, render pipeline | when architectural commitments change |
| [[pipeline]] | Construction — discovery DAG, phase plan, GitHub-Actions workflow | when phases land or CI changes |
| [[staging]] | Substance — pre-publication review environment, solution options, decision open | when the staging decision advances |
| [[interface]] | Form — design stance, seven page types, parallel apparate, WCAG | when design decisions are revised |
| [Journal](../Journal.md) | Genesis — session-by-session record (`Ziel/Erledigt/Entscheidungen/Offen/Nächster Einstieg`) | one entry per working session |

The two generated documents (`data`, `schema`) carry `generated:`, `source:`, and `inputs:` frontmatter and must not be edited by hand — changes go into `scripts/render_data.py` and `scripts/render_schema.py`. The hand-written documents are the only place where wikilinks are added directly.

## Reading paths

**Onboarding a new contributor.** [README.md](../README.md) → [[specification]] → [[architecture]] → [[interface]] → [Journal](../Journal.md). Establishes what the project is, what it must do, how it is built, how it should look, and where it currently stands. About one hour for someone with TEI background.

**Understanding a corpus anomaly in code.** [[data]] (find the anomaly in *Document patterns* or *Reference resolution*) → [[architecture]] *Domain model* (which parser branch handles it) → the parser file under `src/parser/` itself. The empirical observation drives the named code path.

**Adding or changing a TEI element rendering.** [[architecture]] *Element-Mapping* → [docs/extending.md](../docs/extending.md) (the mechanical recipe) → [[interface]] (visual rules the new variant must respect) → tests under `tests/test_render_*.py`. Most extensions are YAML-only; only structurally new semantics need a dataclass plus parser function.

**Reproducing the build pipeline.** [[pipeline]] *Local development* → run the eleven discovery scripts in dependency order → `python -m src.build` → inspect `site/` plus `site/api/build-info.json`. The pipeline is read-only against TEI; nothing writes back.

## Convention

This knowledge base follows the Promptotyping Documents convention: Markdown with frontmatter, wikilinks as connective tissue, function before filename, and inclusion by trigger rather than checklist. The convention regulates frontmatter schema and reading heuristic. The diagnostic rule applies here: output factually wrong → check Knowledge documents; output formally wrong → check `CLAUDE.md` (Action layer); decision logic unclear → check [Journal](../Journal.md) (Process layer).

## Glossary

Project-defining terms used consistently across multiple documents. Sibling documents link here rather than redefining the term in place.

### Apparate-Block

The three parallel sub-blocks at the end of a review — References, Figures, Notes — set side by side under a shared horizontal rule, each with its own h3 sub-header. The parallel layout replaces the legacy site's sequential single-list rendering and makes the three different functions (citation evidence, visual apparatus, commentary) visually distinct. Bidirectional linking is mandatory: every figure number, footnote, and reference links back to its inline call site. Defined in [[interface#6 Apparate als parallele Blöcke]].

### Element-Mapping

The YAML file `config/element-mapping.yaml` that binds domain classes to Jinja templates and CSS classes. The most frequent extension of the site — a new visual variant for a known element — is a YAML change, not a Python change. Only structurally new semantics require a new dataclass plus parser function. Defined in [[architecture#Element-Mapping]].

### K-Ref

A `<ref target="#K…">` element in the corpus. Despite the `#`-prefix, K-refs are **not** local anchors — they point to a RIDE criterion ID defined in the external criteria document at the matching `<taxonomy>/@xml:base`. The corpus carries 5,209 K-refs (98.7 percent of all internal-prefix references), all in `<teiHeader>/<catDesc>`, none in body text. The reference resolver categorises them as `Reference.bucket = "criteria"` and the renderer dispatches them to the external taxonomy URL, not the per-review file. Defined in [[data#Reference resolution]].

### Promptotyping

Methodical practice of iterative prompting against a language model in which compact Markdown knowledge documents are produced and curated, later serving as context for agentic code generation. Distinguishes itself from ad-hoc LLM use through structured preparation, persistent documentation, and verification at defined checkpoints. ride-static itself is built through Promptotyping; this `knowledge/` folder is the project's *Promptotyping vault* in the sense of the convention.

### Sonderfall-Branch

A named, comment-marked code path in the parser that handles a known corpus anomaly. The contract is asymmetric: known anomalies become explicit branches, unknown anomalies must raise. Silent coercion of unexpected structures is forbidden — the build breaks rather than producing quietly wrong output. Examples: seven reviews without `<back>`, `<num value="3">`, flat-content reviews without top-level `<div>` wrapping. Catalogued in [[data#Document patterns]] and [[architecture#Domain model]].

### Wissensdokument / Knowledge Document

A Markdown document under `knowledge/` that is either deterministically generated from the corpus (`data.md`, `schema.md`) or hand-curated (`specification.md`, `architecture.md`, `interface.md`, `pipeline.md`, this index). Committed in the repository, read both by humans and by coding agents as project context. The two generated documents may not be edited by hand.

## What is missing and why

- **No `design.md` separate from `interface.md`.** The Form function is currently carried by a single document that holds both design stance (haltung, four principles) and UI realisation (layout, seven page types, components, typography, accessibility). The seventh page type is the per-review factsheet full page under `/issues/{N}/{id}/factsheet/`, rendered via `src/render/factsheet.py`. A future split into `design.md` (stance, agent value source) and `ui.md` (realisation) is a planned refactor; until then, [[interface]] carries both functions, with the design stance located in §2 *Designhaltung*.
- **No `editorial-guidelines.md`.** The TEI editing of reviews happens in the sibling repository `../ride/`, not here; review editorial conventions belong upstream. The editorial pages themselves are now fed from TEI in this repo: `pages/<slug>.xml` is the source, validated against `schema/ride-pages.rng`, parsed via `src/model/page.py` and `src/parser/page.py`, rendered via `src/render/page.py`. The build cutover (rendering `pages/` into the build) is not yet wired.
- **No `agents.md` / `team.md`.** The project runs in single-agent mode (one Claude Code instance, one `CLAUDE.md`). Multi-agent organisation is not yet relevant for the scope of ride-static.
