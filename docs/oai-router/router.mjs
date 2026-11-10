// OAI-PMH request router over the static snapshot of ride-static.
//
// GitHub Pages ignores query strings, so `?verb=…` cannot reach a file there.
// This module is the whole protocol logic a thin host needs: it validates the
// request as OAI-PMH 2.0 prescribes, maps it onto the pre-rendered files under
// /oai/ (the mapping is the build's oai/routes.json) and answers protocol
// errors itself. Selective harvesting (from/until) filters the pre-rendered
// list by datestamp. It holds no state and issues no resumptionToken: the
// lists are complete, which the protocol leaves to the repository.
//
// Platform-neutral: `handle(params, loadFile, now)` takes the request
// parameters, a function that returns a snapshot file's text (or null) and the
// current time. worker.mjs wires it into a Cloudflare Worker; any other
// runtime with fetch works the same way.

const PREFIXES_KEY = "ListRecords";
const DAY = /^\d{4}-\d{2}-\d{2}$/;

const ARGS = {
  Identify: { required: [], optional: [] },
  ListMetadataFormats: { required: [], optional: ["identifier"] },
  ListSets: { required: [], optional: [], exclusive: "resumptionToken" },
  GetRecord: { required: ["identifier", "metadataPrefix"], optional: [] },
  ListIdentifiers: {
    required: ["metadataPrefix"],
    optional: ["from", "until", "set"],
    exclusive: "resumptionToken",
  },
  ListRecords: {
    required: ["metadataPrefix"],
    optional: ["from", "until", "set"],
    exclusive: "resumptionToken",
  },
};

const MESSAGES = {
  badVerb: "No valid request type",
  badArgument: "Illegal, missing or repeated argument",
  badResumptionToken: "This repository issues no resumption tokens",
  cannotDisseminateFormat: "Metadata format is not available",
  idDoesNotExist: "Identifier does not exist",
  noRecordsMatch: "No records match the request",
  noSetHierarchy: "No set structure available",
};

function escapeXml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function requestElement(baseUrl, args) {
  const attrs = Object.entries(args)
    .map(([k, v]) => ` ${k}="${escapeXml(v)}"`)
    .join("");
  return `<request${attrs}>${escapeXml(baseUrl)}</request>`;
}

function envelope(now, request, body) {
  return (
    '<?xml version="1.0" encoding="UTF-8"?>\n' +
    '<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"\n' +
    '         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n' +
    '         xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/ http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd">\n' +
    `  <responseDate>${now}</responseDate>\n  ${request}\n${body}\n</OAI-PMH>\n`
  );
}

function error(now, baseUrl, args, code) {
  // On badVerb and badArgument the request element carries no attributes.
  const echo = code === "badVerb" || code === "badArgument" ? {} : args;
  return {
    status: 200,
    body: envelope(now, requestElement(baseUrl, echo), `  <error code="${code}">${MESSAGES[code]}</error>`),
  };
}

// Replace responseDate and the request echo of a pre-rendered response.
function restamp(xml, now, baseUrl, args) {
  return xml
    .replace(/<responseDate>[^<]*<\/responseDate>/, `<responseDate>${now}</responseDate>`)
    .replace(/<request\b[^>]*>[^<]*<\/request>/, requestElement(baseUrl, args));
}

function filterByDate(xml, verb, from, until) {
  const item = verb === "ListRecords" ? "record" : "header";
  const re = new RegExp(`\\n    <${item}>[\\s\\S]*?\\n    </${item}>`, "g");
  let kept = 0;
  const out = xml.replace(re, (block) => {
    const stamp = (block.match(/<datestamp>([^<]+)<\/datestamp>/) || [])[1] || "";
    const inRange = (!from || stamp >= from) && (!until || stamp <= until);
    if (inRange) kept += 1;
    return inRange ? block : "";
  });
  return { xml: out, kept };
}

// `publicBase` is the router's own address; it replaces the snapshot path as
// baseURL in Identify and in every request echo, because harvesters check that
// the baseURL they harvest is the one Identify announces.
export async function handle(params, loadFile, now, publicBase = null) {
  const routesText = await loadFile("routes.json");
  if (routesText === null) return { status: 503, body: "OAI snapshot unavailable\n" };
  const routes = JSON.parse(routesText);
  const identify = await loadFile(routes.Identify);
  const baseUrl = publicBase || (identify.match(/<baseURL>([^<]*)<\/baseURL>/) || [])[1] || "";

  const args = {};
  for (const [key, value] of params) {
    if (key in args) return error(now, baseUrl, {}, "badArgument");
    args[key] = value;
  }
  const verb = args.verb;
  const spec = ARGS[verb];
  if (!spec) return error(now, baseUrl, args, "badVerb");
  const given = Object.keys(args).filter((k) => k !== "verb");
  if (spec.exclusive && given.includes(spec.exclusive)) {
    if (given.length > 1) return error(now, baseUrl, args, "badArgument");
    return error(now, baseUrl, args, "badResumptionToken");
  }
  const allowed = new Set([...spec.required, ...spec.optional]);
  if (given.some((k) => !allowed.has(k)) || spec.required.some((k) => !(k in args))) {
    return error(now, baseUrl, args, "badArgument");
  }
  for (const key of ["from", "until"]) {
    if (key in args && !DAY.test(args[key])) return error(now, baseUrl, args, "badArgument");
  }
  if (args.from && args.until && args.from > args.until) {
    return error(now, baseUrl, args, "badArgument");
  }

  const prefixes = Object.keys(routes[PREFIXES_KEY]);
  if ("metadataPrefix" in args && !prefixes.includes(args.metadataPrefix)) {
    return error(now, baseUrl, args, "cannotDisseminateFormat");
  }
  if ("identifier" in args && !(args.identifier in routes.identifiers)) {
    return error(now, baseUrl, args, "idDoesNotExist");
  }
  if ("set" in args) return error(now, baseUrl, args, "noSetHierarchy");

  let path;
  if (verb === "GetRecord") {
    path = routes.GetRecord[args.metadataPrefix].replace("{identifier}", args.identifier);
  } else if (verb === "ListIdentifiers" || verb === "ListRecords") {
    path = routes[verb][args.metadataPrefix];
  } else {
    path = routes[verb];
  }
  const text = await loadFile(path);
  if (text === null) return { status: 503, body: "OAI snapshot incomplete\n" };
  let xml = restamp(text, now, baseUrl, args);
  if (verb === "Identify") {
    xml = xml.replace(/<baseURL>[^<]*<\/baseURL>/, `<baseURL>${escapeXml(baseUrl)}</baseURL>`);
  }
  if ((verb === "ListIdentifiers" || verb === "ListRecords") && (args.from || args.until)) {
    const filtered = filterByDate(xml, verb, args.from, args.until);
    if (filtered.kept === 0) return error(now, baseUrl, args, "noRecordsMatch");
    xml = filtered.xml;
  }
  return { status: 200, body: xml };
}
