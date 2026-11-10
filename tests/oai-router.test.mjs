// Contract tests for docs/oai-router/router.mjs against a real two-record
// snapshot (ride.4.2 and the issue 16 editorial) written by write_oai_pmh into
// tests/fixtures/oai-router/. Expected error codes follow the live endpoint
// responses recorded on 2026-11-10 (badVerb, badArgument,
// cannotDisseminateFormat, idDoesNotExist, noSetHierarchy).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { handle } from "../docs/oai-router/router.mjs";

const root = new URL("./fixtures/oai-router/oai/", import.meta.url);
const loadFile = async (path) => {
  try {
    return await readFile(fileURLToPath(new URL(path, root)), "utf-8");
  } catch {
    return null;
  }
};
const NOW = "2026-11-10T12:00:00Z";
const ask = (query) => handle(new URLSearchParams(query), loadFile, NOW);
const errorCode = (body) => (body.match(/<error code="([^"]+)"/) || [])[1];
const ids = (body) => [...body.matchAll(/<identifier>([^<]+)<\/identifier>/g)].map((m) => m[1]);

test("Identify and ListMetadataFormats come from the snapshot", async () => {
  const identify = await ask("verb=Identify");
  assert.match(identify.body, /<baseURL>https:\/\/i-d-e\.github\.io\/ride-static\/oai\/<\/baseURL>/);
  assert.match(identify.body, /<responseDate>2026-11-10T12:00:00Z<\/responseDate>/);
  const formats = await ask("verb=ListMetadataFormats");
  for (const prefix of ["oai_dc", "oai_marcxml", "oai_doajxml"]) {
    assert.match(formats.body, new RegExp(`<metadataPrefix>${prefix}</metadataPrefix>`));
  }
});

test("a deployed router announces its own address as baseURL", async () => {
  const res = await handle(new URLSearchParams("verb=Identify"), loadFile, NOW, "https://oai.example.org/ride");
  assert.match(res.body, /<baseURL>https:\/\/oai\.example\.org\/ride<\/baseURL>/);
  assert.match(res.body, /<request verb="Identify">https:\/\/oai\.example\.org\/ride<\/request>/);
});

test("GetRecord maps identifier and prefix onto the record file", async () => {
  const res = await ask("verb=GetRecord&metadataPrefix=oai_marcxml&identifier=ride.4.2");
  assert.equal(errorCode(res.body), undefined);
  assert.deepEqual(ids(res.body), ["ride.4.2"]);
  assert.match(res.body, /<request verb="GetRecord" metadataPrefix="oai_marcxml" identifier="ride.4.2">/);
});

test("ListRecords filters by datestamp", async () => {
  const all = await ask("verb=ListRecords&metadataPrefix=oai_dc");
  assert.deepEqual(ids(all.body).sort(), ["ride.16.0", "ride.4.2"]);
  const recent = await ask("verb=ListIdentifiers&metadataPrefix=oai_doajxml&from=2020-01-01");
  assert.deepEqual(ids(recent.body), ["ride.16.0"]);
  const none = await ask("verb=ListRecords&metadataPrefix=oai_dc&from=2030-01-01");
  assert.equal(errorCode(none.body), "noRecordsMatch");
});

test("protocol errors match the live endpoint", async () => {
  assert.equal(errorCode((await ask("verb=Foo")).body), "badVerb");
  assert.equal(errorCode((await ask("verb=Identify&x=1")).body), "badArgument");
  assert.equal(errorCode((await ask("verb=ListRecords&metadataPrefix=xyz")).body), "cannotDisseminateFormat");
  assert.equal(
    errorCode((await ask("verb=GetRecord&metadataPrefix=oai_dc&identifier=nope")).body),
    "idDoesNotExist",
  );
  assert.equal(errorCode((await ask("verb=ListIdentifiers&metadataPrefix=oai_dc&set=x")).body), "noSetHierarchy");
  assert.equal(errorCode((await ask("verb=ListSets")).body), "noSetHierarchy");
  assert.equal(errorCode((await ask("verb=ListRecords&resumptionToken=abc")).body), "badResumptionToken");
  assert.equal(errorCode((await ask("verb=ListRecords&metadataPrefix=oai_dc&from=2020")).body), "badArgument");
  assert.equal(errorCode((await ask("verb=Identify&verb=Identify")).body), "badArgument");
});
