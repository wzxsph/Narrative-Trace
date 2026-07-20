import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { applyEffects, createRuntime, stateMatches } from "../src/runtime/engine.js";
import {
  LEGACY_SAVE_KEY,
  migrateLegacyPayload,
  restoreProgress,
  saveKeyFor,
  serializeProgress,
  validateSavePayload,
} from "../src/runtime/save.js";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const packRoot = path.join(root, "content_packs", "missing_phone", "v1");
const manifest = await loadJson(path.join(packRoot, "pack.json"));
const pack = {
  config: { schema_version: "narrative_runtime_config_v1" },
  manifest,
  game: await loadJson(path.join(packRoot, "game.json")),
  stateRegistry: await loadJson(path.join(packRoot, "state_registry.json")),
  provenance: await loadJson(path.join(packRoot, "provenance", "manifest.json")),
};
const saveFixtures = await loadJson(path.join(root, "examples", "fixtures", "save_contract", "save_cases.json"));

class MemoryStorage {
  constructor(failingKey = null) {
    this.values = new Map();
    this.failingKey = failingKey;
  }

  getItem(key) {
    return this.values.has(key) ? this.values.get(key) : null;
  }

  setItem(key, value) {
    if (key === this.failingKey) {
      throw new Error("fixture write failure");
    }
    this.values.set(key, String(value));
  }

  removeItem(key) {
    this.values.delete(key);
  }
}

const runtime = createRuntime(pack);
assert.equal(Object.keys(runtime.state).length, pack.stateRegistry.states.length);
assert.equal(runtime.sceneId, pack.game.entry_scene_id);
assert.equal(stateMatches({ score: 2 }, { state: "score", max: 2 }), true);
applyEffects(runtime.state, [{ add: { "relationships.chen.trust": 2 } }]);
assert.equal(runtime.state["relationships.chen.trust"], 2);

const serialized = serializeProgress(runtime);
assert.equal(validateSavePayload(serialized, runtime), true);
assert.equal(serialized.schema_version, "narrative_save_v1");
assert.equal(Object.hasOwn(serialized, "sceneId"), false);
assert.equal(saveKeyFor(manifest), "narrative_trace.save.missing_phone.1.0.0");
assert.notEqual(saveKeyFor({ ...manifest, pack_id: "another_story" }), saveKeyFor(manifest));

for (const fixture of saveFixtures.cases.filter((item) => [1, 2].includes(item.payload?.version))) {
  const migrated = migrateLegacyPayload(fixture.payload, createRuntime(pack));
  assert.ok(migrated, fixture.id);
  assert.equal(migrated.pack_id, "missing_phone");
  assert.equal(Object.keys(migrated.state).length, pack.stateRegistry.states.length);
}

const storage = new MemoryStorage();
storage.setItem(LEGACY_SAVE_KEY, JSON.stringify(saveFixtures.cases[0].payload));
const restoredRuntime = createRuntime(pack);
const restoreResult = restoreProgress(restoredRuntime, storage);
assert.equal(restoreResult.restored, true);
assert.equal(restoreResult.migrated, true);
assert.equal(storage.getItem(LEGACY_SAVE_KEY), null);
assert.ok(storage.getItem(saveKeyFor(manifest)));
assert.ok(restoredRuntime.review);

const failingStorage = new MemoryStorage(saveKeyFor(manifest));
failingStorage.values.set(LEGACY_SAVE_KEY, JSON.stringify(saveFixtures.cases[0].payload));
const failedResult = restoreProgress(createRuntime(pack), failingStorage);
assert.equal(failedResult.restored, false);
assert.match(failedResult.notice.text, /迁移写入失败/);
assert.ok(failingStorage.getItem(LEGACY_SAVE_KEY));

console.log(JSON.stringify({
  schema: serialized.schema_version,
  legacy_versions: [1, 2],
  write_failure_visible: true,
  payload: serialized,
}));

async function loadJson(file) {
  return JSON.parse(await readFile(file, "utf8"));
}
