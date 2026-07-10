# Extending ride-static

How to add a new TEI element, attribute, or render variant. Anchored to `specification.md` clause N2 (four extension levels) and `architecture.md` section "Element-Mapping (declarative)".

## The two extension paths

| You want to … | Path |
|---|---|
| Render an existing element with a different template or CSS class | YAML only |
| Add a new variant of an existing kind (e.g. a fourth list type) | YAML only |
| Add a new bucket-aware variant for `Reference` (e.g. distinguish DOIs) | YAML only — extend `inlines.Reference.by_bucket` plus the resolver classifier |
| Add a new TEI element with structurally new semantics | Python + YAML |
| Change how text-node whitespace is treated | Python (parser) |
| Add a new aggregation page or feed | Python (renderer) + template |
| Edit or add an editorial page (Editorial, Team, Imprint, …) | TEI — `pages/*.xml`, see [Editorial pages](#editorial-pages-pagesxml) |

Most extensions are the first two — pure YAML. The remainder require Python work.

## Path 1 — presentation-only change

Changing how an existing element renders touches the dispatcher template and CSS, not the parser or model.

The relevant fact about `config/element-mapping.yaml`: **`src.build` does not load it.** The dispatcher partial `templates/html/partials/render.html` dispatches directly on dataclass class names and emits hard-coded BEM classes; the charts and aggregation renderers emit their markup in Python. The YAML is documentation of the domain-class-to-template-and-CSS contract plus a CI pin. `tests/test_element_mapping.py` and `tests/test_tei_coverage.py` assert that every modelled Block/Inline kind and every `Reference` bucket has an entry, so the file cannot silently drift from the model. See [[architecture#Element-Mapping (declarative)]] for the spec-only status.

The operative edit is therefore in the template and CSS; update the YAML in the same change so the documented contract stays true and the pin stays green.

### Example: rewire the Figure rendering

1. Edit the Figure branch in `templates/html/partials/render.html` (and, if you split into a new template file, add it under `templates/html/blocks/`).
2. Add or adjust the CSS in `static/css/ride.css`.
3. Update the `blocks.Figure` entry in `config/element-mapping.yaml` to describe the new template and CSS class:

   ```yaml
   blocks:
     Figure:
       template: blocks/figure.html
       css_class: ride-figure
       variants:
         graphic:      ride-figure--image
         code_example: ride-figure--code
   ```

4. Run `python -m pytest tests/test_element_mapping.py`, rebuild.

### Example: add a fourth list variant

If the corpus introduces `<list rend="checklist">` and you want to render it differently:

1. In `src/parser/blocks.py`, extend the `kind` normalisation to accept `"checklist"` (one line).
2. In `templates/html/partials/render.html`, emit the `ride-list--checklist` class for the new `kind`.
3. Add CSS for `.ride-list--checklist` in `static/css/ride.css`.
4. Record `checklist: ride-list--checklist` under `blocks.List.variants` in `config/element-mapping.yaml` so the documented contract and the coverage test agree.

No new Python class, no new template file (the existing list rendering handles all variants via the `kind` field).

## Path 2 — Python + YAML extension

Required when the new element has different semantics, not just different appearance. Example: introducing `<diplomatic>` as a new block kind.

1. **Model.** Add a frozen dataclass in `src/model/block.py`:

   ```python
   @dataclass(frozen=True)
   class Diplomatic:
       inlines: tuple[Inline, ...]
       hand: Optional[str] = None
   ```

   Extend the `Block` union type accordingly.

2. **Parser.** Add `_parse_diplomatic(el) -> Diplomatic` in `src/parser/blocks.py` and dispatch to it from `parse_block()`. Synthetic test in `tests/test_parser_blocks.py`.

3. **Dispatch and template.** Add the `Diplomatic` branch to the dispatcher partial `templates/html/partials/render.html` (this is what the build actually renders), creating `templates/html/blocks/diplomatic.html` if the branch warrants its own file. Use the same conventions as the existing block templates.

4. **Mapping entry.** Record the contract in `config/element-mapping.yaml` so the coverage tests pass and the file documents the new kind:

   ```yaml
   blocks:
     Diplomatic:
       template: blocks/diplomatic.html
       css_class: ride-diplomatic
   ```

   The build does not read this file; `tests/test_element_mapping.py` does, and it fails if a modelled Block kind has no entry.

5. **CSS.** Add `.ride-diplomatic` styles to `static/css/ride.css`.

6. **Real-corpus smoke test.** If the new element appears in the corpus, run the parser against `issues/*/reviews/` and confirm no exception.

That is the full ceremony. Six files touched, none of them surprising.

## Editorial pages (`pages/*.xml`)

Everything outside the reviews and factsheets, Editorial, Team, Imprint, Criteria and the rest, is a TEI editorial page, a separate and much smaller model than the review pipeline above. Each page lives at `pages/{slug}.xml`, or at `pages/{section}/{slug}.xml` to carry a navigation section in its URL. It validates against the page profile `schema/ride-pages.rng`: a reduced `teiHeader` plus a body of `div`/`head`/`p`/`list`/`table`/`eg` blocks with `ref`/`persName`/`email`/`hi`/`code`/`lb` inline. The build renders these with precedence over the legacy `content/*.md`; pass `--no-tei-editorials` to fall back to Markdown.

### Edit a page

Edit the body of `pages/{slug}.xml`. Stay within the elements `ride-pages.rng` allows, or `tests/test_pages_schema.py` fails. No code, no ceremony beyond the build itself.

### Add a page

Drop a new file under `pages/` that validates against the profile. Put it in a section folder (`pages/about/{newslug}.xml` → `/about/{newslug}/`) or at the top level for a flat `/{newslug}/`. The slug is the path under `pages/` without the suffix, so `src.parser.page.discover_pages()` finds it automatically and renders it through `editorial.html`. Add an entry to `config/navigation.yaml` to surface it in the menu; `tests/test_render_navigation.py` checks that the URL resolves to a built page. No Python touched.

### Extend the page grammar

A genuinely new element in the page body — one `ride-pages.rng` does not yet allow — is a five-file change, parallel to Path 2 but on the page model:

1. **Schema.** Allow the element in `schema/ride-pages.rng`.
2. **Model.** Add a frozen dataclass in `src/model/page.py` and extend the `Inline` or `Block` union.
3. **Parser.** Handle it in `src/parser/page.py` (`_parse_inlines` or `_parse_block`). Unknown inline elements already fall through to their text, so nothing is silently dropped.
4. **Render.** Emit its HTML in `src/render/page.py` (`_inlines_html` or `_block_html`).
5. **Test.** Cover it in `tests/test_parser_page.py` / `tests/test_render_page.py`; the page-schema test pins the new grammar.

The TEI page renderer and the Markdown editorial renderer share one shell (`src.render.html.render_editorial_shell`) so both feed `editorial.html` the same way; the per-page work above stops at the body HTML.

## Rules and traps

**Unknown elements must raise.** The default strategy in `config/element-mapping.yaml` is `unknown_element_strategy: warn-and-render-text`, which is safe for production but masks bugs during development. Set it to `raise` locally to catch unhandled elements early.

**The mapping file is a documented contract, pinned by pytest, not by the build.** `src.build` never loads `config/element-mapping.yaml`; the render dispatches directly in `templates/html/partials/render.html`. What keeps the file honest is CI: `tests/test_element_mapping.py` and `tests/test_tei_coverage.py` fail if a modelled Block/Inline kind or a `Reference` bucket is missing an entry. So a half-finished mapping breaks the test suite rather than the build, and editing the YAML alone changes no rendered output.

**Inventory updates first.** If the corpus changes (new element, new attribute value), regenerate `inventory/` before extending the parser:

```sh
python scripts/inventory.py
python scripts/structure.py
python scripts/render_data.py
```

This updates `knowledge/data.md` so the new element shows up in the corpus reference. Without this step, the new element appears nowhere except in your code, and reviewers won't know why it's there.

**Anomalies stay named.** If the new element is in fact an anomaly to be normalised (like the `crosssref` typo), document the normalisation in the architecture's anomaly table, not just in code.

## Pipeline phases that change

Most YAML-only extensions do not affect any pipeline phase boundary. Python extensions affect the parser phase (Phase 1 dataclasses, Phase 3 block parser, Phase 4 inline parser) — see `knowledge/pipeline.md` Phasenplan for the phase breakdown. New aggregation pages are Phase 10 work.

## Reference buckets and the resolver post-pass

Phase 7 added `Reference.bucket` ∈ `{local, criteria, external, orphan, None}`. The classifier sits in `src/parser/refs_resolver.py::classify_target` and is called from `resolve_references(review)` as the last step of `parse_review`. Two extension shapes are common:

- **Add a new bucket value.** Extend `classify_target` with the new branch, extend `inlines.Reference.by_bucket` in `config/element-mapping.yaml` with the matching CSS class, and add a unit test for the classifier plus a real-corpus integration test if the corpus has the case.
- **Move targets between buckets.** For example, treating `mailto:` as `external` instead of `orphan`. Edit only the classifier and adjust the unit test; the renderer dispatch follows automatically.

## Asset pipeline

Figure URL rewriting and image copying live in `src/parser/assets.py::rewrite_figure_assets`. The function is pure with respect to the dataclasses (returns a new `Review`) and reports filesystem outcomes via `AssetReport`. Extending it for a new URL form means extending the `_URL_PATTERN` regex; the surrounding walker stays unchanged.

## Validation

After any extension, run the full test suite. Real-corpus smoke tests in `tests/test_parser_*.py` exercise every review shipped under `issues/{N}/reviews/` (corpus size in `knowledge/data.md`). Per the test data philosophy in `CLAUDE.md`, integration tests should drive off real corpus reviews; only pure-function unit tests (regex, classifier) may use synthetic inputs.

```sh
python -m pytest tests/ -v
```

A clean run means no element raised, the mapping is consistent, and every review parses end-to-end with its references classified.
