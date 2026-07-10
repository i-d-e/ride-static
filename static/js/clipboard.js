// clipboard.js — shared clipboard helper for the copy affordances.
//
// copy-link.js (paragraph permalink) and cite-copy.js (BibTeX / CSL-JSON)
// both copy a string to the clipboard and both flash the same brief
// feedback. The write path prefers the async Clipboard API and falls back
// to a hidden <textarea> + execCommand for non-secure contexts (file://,
// plain http off localhost).

export const FEEDBACK_MS = 1500;

export async function copyToClipboard(text) {
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
