// The generated Pagefind UI is a classic bundle exposing window.PagefindUI.
// Keep this adapter as a module and load that local vendor bundle explicitly.

async function mount(container) {
  if (container.dataset.pagefindMounted) return;
  container.dataset.pagefindMounted = '1';
  try {
    const base = new URL(container.dataset.pagefindBundlePath || '/pagefind/', document.baseURI);
    await new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = new URL('pagefind-ui.js', base).href;
      script.onload = resolve;
      script.onerror = () => reject(new Error('Pagefind UI bundle could not load'));
      document.head.appendChild(script);
    });
    const baseUrl = new URL('../', base).pathname;
    new window.PagefindUI({
      element: '#ride-search',
      bundlePath: base.href,
      baseUrl,
      showSubResults: true,
      pageSize: 8,
      resetStyles: false,
      autofocus: false,
      translations: {
        placeholder: 'Search reviews…',
        zero_results: 'No reviews found for [SEARCH_TERM]',
      },
    });
  } catch (err) {
    container.hidden = true;
    console.warn('Pagefind unavailable:', err);
  }
}

function init() {
  const container = document.querySelector('#ride-search[data-pagefind-ui]');
  if (container) mount(container);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init, { once: true });
} else {
  init();
}
