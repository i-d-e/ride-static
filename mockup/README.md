# Mockup — visual reference

`ride.css` (21 lines) and `template.html` (313 lines) are a standalone
HTML/CSS prototype written by a colleague to fix the visual direction
of the deployed site against a concrete worked example (a rendering of
the WeGA review, ride.12.4). They live here as a versioned reference,
not as production code.

## What this is

The HTML uses Bootstrap 5 from a CDN as a layout shortcut. The CSS adds
~20 lines of overrides on top. Open `template.html` in a browser to see
the intended visual model: tagline header, dark navigation bar with
five Top-Level dropdowns (About / Issues / Data / Reviewers / Reviewing
Criteria), a search input on the right, two-column main with an article
on the left and a TOC + Meta + Citation Suggestion + Tags sidebar on
the right, and a four-item footer.

## What this is not

- **Not the production stack.** The actual site uses vanilla CSS with
  custom properties (no Bootstrap, no preprocessor) and native
  `<details>` for the dropdowns (no Bootstrap JS). The decision to
  drop Bootstrap is documented in [knowledge/prozess-und-stand.md].
- **Not editable for production effect.** Changing the mockup files
  has no effect on the deployed site. Production templates live in
  `templates/html/` and `static/css/`.

## Where the content has gone

Everything load-bearing from the mockup has been overlaid into the
canonical knowledge documents:

- [knowledge/interface.md] — single Sans-family typography, layout
  ratio 1150 / 720 / 280 / 60, three-part global header with tagline
  and search-in-navbar, sidebar reordering with DOI line, citation
  format with the explanatory micro-copy, footer items
- [knowledge/requirements.md] — R2 with the canonical citation
  format, R10 with the eleven editorial Markdown pages, R11.5 for the
  navigation YAML
- [knowledge/architecture.md] — `Review.doi` and
  `RelatedItem.last_accessed` in the domain model
- [knowledge/data.md] — DOI is in `<publicationStmt>/<idno type="DOI">`

## When this mockup is still useful

Welle 3 (navigation + nine new editorial Markdown stubs) re-references
this mockup for the dropdown contents and the search-input visual.
After Welle 3 ships, this folder is purely historical and could be
deleted — keep it for now as the visual reference.

[knowledge/interface.md]: ../knowledge/interface.md
[knowledge/requirements.md]: ../knowledge/requirements.md
[knowledge/architecture.md]: ../knowledge/architecture.md
[knowledge/data.md]: ../knowledge/data.md
[knowledge/prozess-und-stand.md]: ../knowledge/prozess-und-stand.md
