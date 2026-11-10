// Query-string addresses of the former WordPress site: /?p={id} through
// static/js/legacy-query.js, /?s={term} through static/js/pagefind.js.
// Post ids are real entries of config/legacy-urls.json (recorded 2026-11-10:
// 19 is the Nietzschesource review, 5 the issue overview).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import vm from "node:vm";
import { legacyTarget } from "../static/js/legacy-query.js";

const table = JSON.parse(await readFile(new URL("../config/legacy-urls.json", import.meta.url), "utf-8"));

test("a recorded post id leads to its former address on the static site", () => {
  assert.equal(table.posts["19"], "/issues/issue-1/nietzschesource/");
  const result = legacyTarget("?p=19", table.posts, "/ride-static");
  assert.deepEqual(result, { href: "/ride-static/issues/issue-1/nietzschesource/" });
  assert.deepEqual(legacyTarget("?page_id=5", table.posts, ""), { href: "/issues/" });
});

test("an unknown post id yields a notice, other queries nothing", () => {
  assert.match(legacyTarget("?p=999999", table.posts, "").notice, /\?p=999999/);
  assert.equal(legacyTarget("?s=nietzsche", table.posts, ""), null);
  assert.equal(legacyTarget("", table.posts, ""), null);
});

test("/?s= runs the search with the term", async () => {
  const source = await readFile(new URL("../static/js/pagefind.js", import.meta.url), "utf-8");
  const searched = [];
  const container = { dataset: { pagefindBundlePath: "/pagefind/" }, hidden: false };
  const window = { location: { search: "?s=nietzsche" } };
  const document = {
    readyState: "complete",
    baseURI: "https://i-d-e.github.io/ride-static/",
    querySelector: () => container,
    createElement: () => ({}),
    head: {
      appendChild(script) {
        queueMicrotask(() => {
          window.PagefindUI = function () {
            this.triggerSearch = (term) => searched.push(term);
          };
          script.onload();
        });
      },
    },
  };
  vm.runInNewContext(source, { document, window, URL, URLSearchParams, console });
  await new Promise((resolve) => setImmediate(resolve));
  assert.deepEqual(searched, ["nietzsche"]);
});
