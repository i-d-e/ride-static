// cite-copy.js — copy BibTeX or CSL-JSON for the current review.
//
// requirements.md R2 (Rezension zitieren). The review template embeds
// pre-generated citation strings in two hidden <script> blocks:
//   <script type="application/x-bibtex" class="ride-cite-data" data-format="bibtex">…</script>
//   <script type="application/json"     class="ride-cite-data" data-format="csl-json">…</script>
// Buttons carry data-cite-format="bibtex" or "csl-json"; on click we
// look up the matching block and copy its content.

const FEEDBACK_MS = 1500;

function findCitation(format) {
  const el = document.querySelector(
    `.ride-cite-data[data-format="${format}"]`
  );
  return el ? el.textContent.trim() : null;
}

async function copyToClipboard(text) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.setAttribute('readonly', '');
  ta.style.position = 'absolute';
  ta.style.left = '-9999px';
  document.body.appendChild(ta);
  ta.select();
  document.execCommand('copy');
  ta.remove();
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
