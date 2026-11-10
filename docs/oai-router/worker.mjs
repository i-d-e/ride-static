// Cloudflare Worker entry for the OAI-PMH router (copy-ready, see README.md).
//
// SNAPSHOT is the absolute URL of the static snapshot directory, for example
// https://ride.i-d-e.de/oai/ ; it is set as a Worker variable, not in code.
import { handle } from "./router.mjs";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    let params = url.searchParams;
    if (request.method === "POST") {
      params = new URLSearchParams(await request.text());
    } else if (request.method !== "GET") {
      return new Response("Method not allowed\n", { status: 405 });
    }
    const loadFile = async (path) => {
      const response = await fetch(new URL(path, env.SNAPSHOT), { cf: { cacheTtl: 300 } });
      return response.ok ? response.text() : null;
    };
    const now = new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
    const result = await handle(params, loadFile, now, `${url.origin}${url.pathname}`);
    return new Response(result.body, {
      status: result.status,
      headers: { "content-type": "text/xml; charset=utf-8" },
    });
  },
};
