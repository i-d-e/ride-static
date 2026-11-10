# OAI-PMH request router

The static build writes every OAI-PMH response RIDE can give as a file under `/oai/` (see `src/render/oai_pmh.py`). GitHub Pages ignores query strings, so a harvester asking `…?verb=ListRecords&metadataPrefix=oai_dc` cannot reach those files directly. `router.mjs` is the missing piece: it validates the request as OAI-PMH 2.0 requires, maps it onto the file named in the build's `oai/routes.json`, filters by `from`/`until` and answers protocol errors. It keeps no state and needs no database.

## What the operator has to set up

1. A host that runs a small script per request. `worker.mjs` is written for Cloudflare Workers; any runtime with `fetch` (a serverless function, a Node process behind the existing IDE web server) can call `handle()` the same way.
2. One variable, `SNAPSHOT`, pointing at the published snapshot directory, for example `https://ride.i-d-e.de/oai/` once the domain serves the static site.
3. A route for the address harvesters know. Keeping `https://ride.i-d-e.de/apis/oai` preserves the base URL the live endpoint announces; this needs a proxy in front of the domain that sends that path to the router and everything else to GitHub Pages, for example Cloudflare serving ride.i-d-e.de with the Worker bound to the route `ride.i-d-e.de/apis/oai*`. DNS alone cannot split by path. A new address also works, but then every harvester and registry entry has to be told.
4. After deployment, validate the base URL with a public OAI-PMH validator and compare a harvest with the static files (`scripts/parity.py` reads the same snapshot).

## What it does not do

It issues no `resumptionToken`; lists come back complete. A harvester follows a token only when a response carries one, so complete lists need nothing on its side; the live endpoint pages by twenty, which a harvester that has used it already handles either way. Sets do not exist (as on the live endpoint). The snapshot changes only with a build, so `responseDate` is the time of the request while the content is the build state.

## Test

`node --test tests/oai-router.test.mjs` runs the router against a real two-record snapshot under `tests/fixtures/oai-router/`, which `tests/test_render_oai_pmh.py` keeps equal to current build output.
