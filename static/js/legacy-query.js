// Addresses of the former WordPress site that carry their meaning in the query
// string: /?p={id} (shortlink by post id) and /?s={term} (search). GitHub Pages
// serves the home page for both and ignores the query, so the browser resolves
// them here. The post map is recorded from the live site (config/legacy-urls.json)
// and embedded by the build; /?s= is handed to the search in pagefind.js.

export function legacyTarget(search, posts, base) {
  const params = new URLSearchParams(search);
  const post = params.get('p') || params.get('page_id');
  if (post) {
    return posts[post] ? { href: `${base}${posts[post]}` } : { notice: `No page is known for the former address ?p=${post}.` };
  }
  return null;
}

function init() {
  const data = document.getElementById('ride-legacy-posts');
  if (!data) return;
  const result = legacyTarget(window.location.search, JSON.parse(data.textContent), data.dataset.base || '');
  if (!result) return;
  if (result.href) {
    window.location.replace(result.href);
    return;
  }
  const notice = document.getElementById('ride-legacy-notice');
  if (notice) {
    notice.textContent = result.notice;
    notice.hidden = false;
  }
}

if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
}
