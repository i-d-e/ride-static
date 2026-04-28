# Extending ride-static

How to add a new TEI element, attribute, or render variant. Anchored to `requirements.md` clause N2 (four extension levels) and `architecture.md` section "Element-Mapping (declarative)".

## The two extension paths

| You want to … | Path |
|---|---|
| Render an existing element with a different template or CSS class | YAML only |
| Add a new variant of an existing kind (e.g. a fourth list type) | YAML only |
| Add a new TEI element with structurally new semantics | Python + YAML |
| Change how text-node whitespace is treated | Python (parser) |
| Add a new aggregation page or feed | Python (renderer) + template |

Most extensions are the first two — pure YAML. The remainder require Python work.

## Path 1 — YAML-only extension

The file `config/element-mapping.yaml` maps domain classes to Jinja templates and CSS classes. Edit it, run `python -m pytest tests/test_mapping.py`, run the build. No Python touched.

### Example: rewire the Figure template

```yaml
blocks:
  Figure:
    template: blocks/figure.html        # change to: blocks/figure-card.html
    css_class: ride-figure
    variants:
      graphic:      ride-figure--image
      code_example: ride-figure--code
```

Save, rebuild. Every Figure on every review page now renders through the new template.

### Example: add a fourth list variant

If the corpus introduces `<list rend="checklist">` and you want to render it differently:

1. In `src/parser/blocks.py`, extend the `kind` normalisation to accept `"checklist"` (one line).
2. In `config/element-mapping.yaml`, add `checklist: ride-list--checklist` under `blocks.List.variants`.
3. Add CSS for `.ride-list--checklist` in `static/css/ride.css`.
4. Done.

No new Python class, no new template file (the existing `blocks/list.html` handles all variants via the `kind` field).

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

3. **Mapping.** Add an entry in `config/element-mapping.yaml`:

   ```yaml
   blocks:
     Diplomatic:
       template: blocks/diplomatic.html
       css_class: ride-diplomatic
   ```

4. **Template.** Create `templates/html/blocks/diplomatic.html`. Use the same conventions as the existing block templates.

5. **CSS.** Add `.ride-diplomatic` styles to `static/css/ride.css`.

6. **Real-corpus smoke test.** If the new element appears in the corpus, run the parser against `../ride/tei_all/` and confirm no exception.

That is the full ceremony. Six files touched, none of them surprising.

## Rules and traps

**Unknown elements must raise.** The default strategy in `config/element-mapping.yaml` is `unknown_element_strategy: warn-and-render-text`, which is safe for production but masks bugs during development. Set it to `raise` locally to catch unhandled elements early.

**The mapping file is validated at build start.** CI fails if the mapping references a template path that does not exist or a domain class the parser does not produce. So you cannot ship a half-finished mapping; either it is consistent or the build refuses.

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

## Validation

After any extension, run the full test suite plus the real-corpus smoke test:

```sh
python -m pytest tests/ -v
python -m src.build --dry-run        # planned in Phase 8: parses everything, renders nothing
```

A clean run means no element raised, the mapping is consistent, and all 107 reviews parse end-to-end.
