const CONFIG_URL = "runtime-config.json";
const SUPPORTED_KERNEL_MAJOR = 1;

export async function loadConfiguredPack(fetchImpl = window.fetch.bind(window)) {
  const configUrl = new URL(CONFIG_URL, window.location.href);
  const config = await fetchJson(fetchImpl, configUrl, "运行时配置");
  if (config.schema_version !== "narrative_runtime_config_v1") {
    throw new Error("不支持的运行时配置版本");
  }
  const packRootUrl = resolvePackRoot(configUrl, config.pack);
  const manifestUrl = new URL("pack.json", packRootUrl);
  const manifest = await fetchJson(fetchImpl, manifestUrl, "内容包清单");
  assertRuntimeCompatibility(manifest);

  const entrypoints = manifest.entrypoints || {};
  const [game, stateRegistry, provenance] = await Promise.all([
    fetchJson(fetchImpl, resolvePackFile(packRootUrl, entrypoints.game, "game"), "游戏内容"),
    fetchJson(fetchImpl, resolvePackFile(packRootUrl, entrypoints.state_registry, "state_registry"), "状态注册表"),
    fetchJson(fetchImpl, resolvePackFile(packRootUrl, entrypoints.provenance, "provenance"), "来源记录"),
  ]);
  assertPackShape(manifest, game, stateRegistry);
  return { config, manifest, game, stateRegistry, provenance, packRootUrl };
}

export function assertRuntimeCompatibility(manifest) {
  const major = Number(String(manifest.kernel_version || "").split(".")[0]);
  if (major !== SUPPORTED_KERNEL_MAJOR) {
    throw new Error(`当前运行时不支持 Kernel ${manifest.kernel_version || "<missing>"}`);
  }
  if (manifest.loop_package?.id !== "investigation") {
    throw new Error(`当前页面没有玩法适配器：${manifest.loop_package?.id || "<missing>"}`);
  }
}

export function resolvePackRoot(configUrl, relative) {
  if (typeof relative !== "string" || !relative || relative.startsWith("/") || hasTraversal(relative)) {
    throw new Error("runtime-config.pack 必须是安全的相对目录");
  }
  const normalized = relative.endsWith("/") ? relative : `${relative}/`;
  return new URL(normalized, configUrl);
}

export function resolvePackFile(packRootUrl, relative, label) {
  if (typeof relative !== "string" || !relative || relative.startsWith("/") || hasTraversal(relative)) {
    throw new Error(`pack.entrypoints.${label} 必须是安全的相对路径`);
  }
  const resolved = new URL(relative, packRootUrl);
  if (!resolved.href.startsWith(packRootUrl.href)) {
    throw new Error(`pack.entrypoints.${label} 越出内容包目录`);
  }
  return resolved;
}

async function fetchJson(fetchImpl, url, label) {
  const response = await fetchImpl(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`${label}载入失败（HTTP ${response.status}）`);
  }
  try {
    return await response.json();
  } catch {
    throw new Error(`${label}不是有效 JSON`);
  }
}

function assertPackShape(manifest, game, stateRegistry) {
  if (manifest.schema_version !== "narrative_content_pack_v1") {
    throw new Error("内容包不是 Framework V1");
  }
  if (game.schema_version !== "narrative_game_v1" || !Array.isArray(game.scenes)) {
    throw new Error("游戏内容不符合 Kernel V1");
  }
  if (stateRegistry.schema_version !== "narrative_state_registry_v1" || !Array.isArray(stateRegistry.states)) {
    throw new Error("状态注册表不符合 Kernel V1");
  }
}

function hasTraversal(value) {
  return value.split("/").some((part) => part === ".." || decodeURIComponentSafe(part) === "..");
}

function decodeURIComponentSafe(value) {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}
