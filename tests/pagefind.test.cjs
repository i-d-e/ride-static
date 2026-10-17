// Exercise the actual bootstrap against the classic Pagefind UI loading contract.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../static/js/pagefind.js'), 'utf8');

async function runBootstrap(bundlePath, failed = false, pageLanguage = 'en') {
  const container = {
    dataset: { pagefindBundlePath: bundlePath },
    classList: { add() {} },
    hidden: false,
  };
  const loaded = [];
  const options = [];
  const window = {};
  const document = {
    documentElement: { lang: pageLanguage },
    readyState: 'complete', baseURI: 'https://i-d-e.github.io/ride-static/',
    querySelector: () => container,
    createElement: () => ({}),
    head: { appendChild(script) {
      loaded.push(script.src);
      queueMicrotask(() => {
        if (failed) { script.onerror(); return; }
        window.PagefindUI = function (config) { options.push(config); };
        script.onload();
      });
    } },
  };
  vm.runInNewContext(source, { document, window, URL, console: { warn() {} } });
  await new Promise(resolve => setImmediate(resolve));
  return { container, loaded, options };
}

test('mounts the generated classic UI with a project-prefixed search base', async () => {
  const result = await runBootstrap('/ride-static/pagefind/');
  assert.equal(result.options.length, 1);
  assert.equal(result.loaded[0], 'https://i-d-e.github.io/ride-static/pagefind/pagefind-ui.js');
  assert.equal(result.options[0].element, '#ride-search');
  assert.equal(result.options[0].baseUrl, '/ride-static/');
  assert.equal(result.options[0].translations.placeholder, 'Search reviews…');
});

test('keeps domain-root previews searchable', async () => {
  const result = await runBootstrap('/pagefind/');
  assert.equal(result.options.length, 1);
  assert.equal(result.options[0].baseUrl, '/');
});

test('omits the unavailable search control when its bundle cannot load', async () => {
  const result = await runBootstrap('/pagefind/', true);
  assert.equal(result.options.length, 0);
  assert.equal(result.container.hidden, true);
});

test('uses the same global index from a German review', async () => {
  const result = await runBootstrap('/pagefind/', false, 'de');
  assert.equal(result.options.length, 1);
  assert.equal(result.options[0].bundlePath, 'https://i-d-e.github.io/pagefind/');
  assert.equal(result.options[0].baseUrl, '/');
});
