// copy-link.js — paragraph permalink affordance.
//
// interface.md §11: hovering a numbered paragraph's gutter number reveals a
// copy-link action. The marker is rendered by templates as
// <a class="ride-paragraph__anchor" href="#paragraphId"> ... </a>; this
// module intercepts the click, copies the absolute URL to the clipboard,
// and shows a brief "Copied" feedback at the cursor.
//
// No framework, no bundling — vanilla ES module per interface.md §12.

const FEEDBACK_MS = 1500;

function showFeedback(target, text) {
  const tip = document.createElement('span');
  tip.className = 'ride-copy-feedback';
  tip.textContent = text;
  target.appendChild(tip);
  // Trigger transition by deferring opacity flip to the next frame.
  requestAnimationFrame(() => tip.classList.add('ride-copy-feedback--visible'));
  setTimeout(() => tip.remove(), FEEDBACK_MS);
}

async function copyToClipboard(text) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }
  // Fallback for non-secure contexts (file://, plain http on non-localhost).
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

document.addEventListener('click', async (event) => {
  const anchor = event.target.closest('.ride-paragraph__anchor');
  if (!anchor) return;
  event.preventDefault();
  const url = new URL(anchor.getAttribute('href') || '#', location.href).href;
  try {
    await copyToClipboard(url);
    showFeedback(anchor, 'Copied');
  } catch {
    showFeedback(anchor, 'Failed');
  }
});
