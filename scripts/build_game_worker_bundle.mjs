import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const outDir = path.join(rootDir, "dist");
const outFile = path.join(outDir, "game-worker-bundle.js");

const assetSpecs = [
  {
    routes: ["/", "/index.html"],
    source: "index.html",
    contentType: "text/html; charset=utf-8",
  },
  {
    routes: ["/src/app.js"],
    source: "src/app.js",
    contentType: "text/javascript; charset=utf-8",
  },
  {
    routes: ["/src/styles.css"],
    source: "src/styles.css",
    contentType: "text/css; charset=utf-8",
  },
  {
    routes: ["/generated/missing_phone_v0/game.json"],
    source: "generated/missing_phone_v0/game.json",
    contentType: "application/json; charset=utf-8",
  },
];

const assets = [];
for (const spec of assetSpecs) {
  const body = await readFile(path.join(rootDir, spec.source), "utf8");
  for (const route of spec.routes) {
    assets.push([route, { body, contentType: spec.contentType }]);
  }
}

const workerSource = `const ASSETS = new Map(${JSON.stringify(assets)});

export default {
  async fetch(request) {
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("Method Not Allowed", {
        status: 405,
        headers: { allow: "GET, HEAD" },
      });
    }

    const url = new URL(request.url);
    const pathname = normalizePath(url.pathname);
    const asset = ASSETS.get(pathname) || (pathname.includes(".") ? null : ASSETS.get("/"));
    if (!asset) {
      return new Response("Not Found", {
        status: 404,
        headers: securityHeaders({ "content-type": "text/plain; charset=utf-8" }),
      });
    }

    return new Response(request.method === "HEAD" ? null : asset.body, {
      status: 200,
      headers: securityHeaders({
        "content-type": asset.contentType,
        "cache-control": "public, max-age=60",
      }),
    });
  },
};

function normalizePath(pathname) {
  if (!pathname || pathname === "/") {
    return "/";
  }
  return pathname.endsWith("/") ? pathname.slice(0, -1) : pathname;
}

function securityHeaders(headers) {
  return {
    ...headers,
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
    "permissions-policy": "camera=(), microphone=(), geolocation=()",
  };
}
`;

await mkdir(outDir, { recursive: true });
await writeFile(outFile, workerSource, "utf8");

for (const [route, asset] of assets) {
  console.log(`${route} ${asset.contentType}`);
}
console.log(outFile);
