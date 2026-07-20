import { mkdir, readdir, readFile, realpath, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const args = parseArgs(process.argv.slice(2));
if (!args.pack) {
  throw new Error("--pack is required; a worker bundle must contain exactly one content pack");
}
const packDir = await realpath(path.resolve(rootDir, args.pack));
const contentRoot = await realpath(path.join(rootDir, "content_packs"));
if (!isWithin(contentRoot, packDir)) {
  throw new Error("--pack must resolve inside content_packs/");
}

const manifest = await readJson(path.join(packDir, "pack.json"));
if (String(manifest.kernel_version || "").split(".")[0] !== "1") {
  throw new Error(`Unsupported Kernel version: ${manifest.kernel_version}`);
}
const gamePath = resolvePackFile(packDir, manifest.entrypoints?.game, "game");
const statePath = resolvePackFile(packDir, manifest.entrypoints?.state_registry, "state_registry");
const provenancePath = resolvePackFile(packDir, manifest.entrypoints?.provenance, "provenance");
const [game, provenance] = await Promise.all([readJson(gamePath), readJson(provenancePath)]);
const packRouteRoot = `/content_packs/${manifest.pack_id}/${manifest.version}`;
const runtimeConfig = JSON.stringify(
  {
    schema_version: "narrative_runtime_config_v1",
    runtime_version: "1.0.0",
    pack: packRouteRoot.slice(1),
  },
  null,
  2
) + "\n";

const assetSpecs = [
  { routes: ["/", "/index.html"], source: path.join(rootDir, "index.html") },
  { routes: ["/runtime-config.json"], body: runtimeConfig, contentType: "application/json; charset=utf-8" },
];
for (const source of await walkFiles(path.join(rootDir, "src"))) {
  assetSpecs.push({ routes: [`/${path.relative(rootDir, source).split(path.sep).join("/")}`], source });
}

const packFiles = new Set([path.join(packDir, "pack.json"), gamePath, statePath, provenancePath]);
for (const artifact of provenance.artifacts || []) {
  packFiles.add(resolvePackFile(packDir, artifact.path, "provenance artifact"));
}
for (const relative of surfaceAssets(game)) {
  packFiles.add(resolvePackFile(packDir, relative, "surface asset"));
}
for (const source of packFiles) {
  const relative = path.relative(packDir, source).split(path.sep).join("/");
  assetSpecs.push({ routes: [`${packRouteRoot}/${relative}`], source });
}

const assets = [];
for (const spec of assetSpecs) {
  const contentType = spec.contentType || contentTypeFor(spec.source);
  const binary = !isTextContent(contentType);
  const body = spec.body ?? (binary ? await readFile(spec.source) : await readFile(spec.source, "utf8"));
  const encoded = binary ? body.toString("base64") : body;
  for (const route of spec.routes) {
    assets.push([route, { body: encoded, contentType, encoding: binary ? "base64" : "text" }]);
  }
}

const workerSource = `const ASSETS = new Map(${JSON.stringify(assets)});

export default {
  async fetch(request) {
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("Method Not Allowed", { status: 405, headers: { allow: "GET, HEAD" } });
    }
    const pathname = normalizePath(new URL(request.url).pathname);
    const asset = ASSETS.get(pathname) || (pathname.includes(".") ? null : ASSETS.get("/"));
    if (!asset) {
      return new Response("Not Found", { status: 404, headers: securityHeaders({ "content-type": "text/plain; charset=utf-8" }) });
    }
    const body = request.method === "HEAD" ? null : decodeBody(asset);
    return new Response(body, {
      status: 200,
      headers: securityHeaders({ "content-type": asset.contentType, "cache-control": "public, max-age=60" }),
    });
  },
};

function decodeBody(asset) {
  if (asset.encoding !== "base64") return asset.body;
  return Uint8Array.from(atob(asset.body), (character) => character.charCodeAt(0));
}

function normalizePath(pathname) {
  if (!pathname || pathname === "/") return "/";
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

const outFile = path.resolve(rootDir, args.output || "dist/game-worker-bundle.js");
await mkdir(path.dirname(outFile), { recursive: true });
await writeFile(outFile, workerSource, "utf8");
console.log(JSON.stringify({ pack: `${manifest.pack_id}@${manifest.version}`, output: outFile, routes: assets.map(([route]) => route) }, null, 2));

function parseArgs(values) {
  const parsed = {};
  for (let index = 0; index < values.length; index += 1) {
    const key = values[index];
    if (key === "--pack" || key === "--output") {
      parsed[key.slice(2)] = values[index + 1];
      index += 1;
    } else {
      throw new Error(`Unknown argument: ${key}`);
    }
  }
  return parsed;
}

function resolvePackFile(root, relative, label) {
  if (typeof relative !== "string" || !relative || path.isAbsolute(relative)) {
    throw new Error(`${label} must be a relative path`);
  }
  const resolved = path.resolve(root, relative);
  if (!isWithin(root, resolved)) {
    throw new Error(`${label} escapes the content pack`);
  }
  return resolved;
}

function isWithin(parent, candidate) {
  const relative = path.relative(parent, candidate);
  return relative === "" || (!relative.startsWith("..") && !path.isAbsolute(relative));
}

async function readJson(file) {
  return JSON.parse(await readFile(file, "utf8"));
}

async function walkFiles(directory) {
  const output = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const child = path.join(directory, entry.name);
    if (entry.isDirectory()) output.push(...(await walkFiles(child)));
    else if (entry.isFile()) output.push(child);
  }
  return output.sort();
}

function* surfaceAssets(game) {
  for (const scene of game.scenes || []) {
    for (const surface of scene.surfaces || []) yield* assetsFromSurface(surface);
  }
}

function* assetsFromSurface(surface) {
  if ((surface.type === "image" || surface.type === "html") && typeof surface.content?.asset === "string") {
    yield surface.content.asset;
  }
  for (const anchor of surface.anchors || []) {
    for (const child of anchor.fragment?.surfaces || []) yield* assetsFromSurface(child);
  }
}

function contentTypeFor(file) {
  const extension = path.extname(file).toLowerCase();
  return {
    ".css": "text/css; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".jsonl": "application/x-ndjson; charset=utf-8",
    ".svg": "image/svg+xml; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
  }[extension] || "application/octet-stream";
}

function isTextContent(contentType) {
  return contentType.startsWith("text/") || contentType.includes("json") || contentType.includes("svg");
}
