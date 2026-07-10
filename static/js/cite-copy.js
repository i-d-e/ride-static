// cite-copy.js — copy BibTeX or CSL-JSON for the current review.
//
// specification.md R2 (Rezension zitieren). The review template embeds
// pre-generated citation strings in two hidden <script> blocks:
//   <script type="application/x-bibtex" class="ride-cite-data" data-format="bibtex">…</script>
//   <script type="application/json"     class="ride-cite-data" data-format="csl-json">…</script>
// Buttons carry data-cite-format="bibtex" or "csl-json"; on click we
// look up the matching block and copy its content.

import { copyToClipboard, FEEDBACK_MS } from './clipboard.js';

function findCitation(format) {
  const el = document.querySelector(
    `.ride-cite-data[data-format="${format}"]`
  );
  return el ? el.textContent.trim() : null;
}

function flashLabel(button, text) {
  const original = button.textContent;
  button.textContent = text;
  button.disabled = true;
  setTimeout(() => {
    button.textContent = original;
    button.disabled = false;
  }, FEEDBACK_MS);
}

document.addEventListener('click', async (event) => {
  const button = event.target.closest('.ride-cite__btn');
  if (!button) return;
  const format = button.dataset.citeFormat;
  if (!format) return;
  const text = findCitation(format);
  if (!text) {
    flashLabel(button, 'No data');
    return;
  }
  try {
    await copyToClipboard(text);
    flashLabel(button, 'Copied');
  } catch {
    flashLabel(button, 'Failed');
  }
});
