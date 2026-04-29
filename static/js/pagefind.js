// pagefind.js — Pagefind UI bootstrap.
//
// interface.md §11 / requirements.md R12. Welle 9 wires Pagefind into
// the #ride-search container in the navbar. The CI build runs
// `npx pagefind --site site` after `python -m src.build`, which writes
// the runtime to /pagefind/ and the UI bundle to /pagefind/pagefind-ui.js.
//
// Loading is deferred: we only fetch the UI bundle when the container
// scrolls into view, which keeps initial paint cheap and avoids loading
// the bundle on browsers that never scroll near the navbar.

function bundleBase(container) {
  // ES modules can't read document.currentScript, so the deploy-prefixed
  // bundle path lives on the container as data-pagefind-bundle-path.
  return container.dataset.pagefindBundlePath || '/pagefind/';
}

async function mount(container) {
  if (container.dataset.pagefindMounted) return;
  container.dataset.pagefindMounted = '1';
  try {
    // Resolve the bundle path against the document base so a deploy
    // under /ride-static/ still finds /ride-static/pagefind/pagefind-ui.js.
    const base = new URL(bundleBase(container), document.baseURI).href;
    const { PagefindUI } = await import(`${base}pagefind-ui.js`);
    new PagefindUI({
      element: container,
      bundlePath: base,
      showSubResults: true,
      pageSize: 8,
      resetStyles: false,
      autofocus: false,
      placeholder: 'Search reviews…',
      translations: {
        zero_results: 'No reviews found for [SEARCH_TERM]',
      },
    });
  } catch (err) {
    container.classList.add('ride-search--unavailable');
    console.warn('Pagefind unavailable:', err);
  }
}

function init() {
  const container = document.querySelector('#ride-search[data-pagefind-ui]');
  if (!container) return;
  // Mount eagerly when the container is already visible above the fold;
  // otherwise wait for IntersectionObserver to avoid loading the bundle
  // for users who never scroll near it.
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          io.disconnect();
          mount(container);
          return;
        }
      }
    });
    io.observe(container);
  } else {
    mount(container);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init, { once: true });
} else {
  init();
}
