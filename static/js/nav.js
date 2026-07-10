// nav.js — exclusive-open behaviour for the <details> dropdowns.
//
// The global navigation uses native <details> (interface.md §4) so the
// menu works without JS. Native <details> do not know about each other:
// every opened dropdown stays open until clicked again, so two or three
// submenus can stack up. This module adds the conventional menu
// behaviour on top — opening one dropdown closes the others, a click
// outside the navigation or Escape closes all. Purely additive: it never
// intercepts the summary click, so without JS the native toggle remains.
//
// No framework, no bundling — vanilla ES module per interface.md §12.

const dropdowns = Array.from(document.querySelectorAll('.ride-nav__dropdown'));

for (const dropdown of dropdowns) {
  dropdown.addEventListener('toggle', () => {
    if (!dropdown.open) return;
    for (const other of dropdowns) {
      if (other !== dropdown) other.open = false;
    }
  });
}

document.addEventListener('click', (event) => {
  if (event.target.closest('.ride-nav__dropdown')) return;
  for (const dropdown of dropdowns) dropdown.open = false;
});

document.addEventListener('keydown', (event) => {
  if (event.key !== 'Escape') return;
  for (const dropdown of dropdowns) {
    if (dropdown.open && dropdown.contains(document.activeElement)) {
      dropdown.querySelector('summary')?.focus();
    }
    dropdown.open = false;
  }
});
