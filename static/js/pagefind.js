// pagefind.js — Pagefind UI bootstrap (stub).
//
// interface.md §11 / requirements.md R12. Phase 11 wires the actual
// Pagefind runtime into the #ride-search container; until the search
// index is built and the Pagefind library is bundled into static/, this
// module is a no-op so base.html does not 404.
//
// When Phase 11 lands the bootstrap will look roughly like:
//   import { PagefindUI } from '/static/js/vendor/pagefind-ui.js';
//   new PagefindUI({ element: '#ride-search', showSubResults: true });
export {};
