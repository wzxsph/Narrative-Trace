export const SAVE_SCHEMA_VERSION = "narrative_save_v1";
export const LEGACY_SAVE_KEY = "game_writer_missing_phone_runtime_v1";
export const LEGACY_SAVE_VERSION = 2;

export function saveKeyFor(manifest) {
  return `narrative_trace.save.${manifest.pack_id}.${manifest.version}`;
}

export function restoreProgress(runtime, storage = safeStorage()) {
  if (!storage) {
    return { restored: false, notice: null, source: "none" };
  }
  const saveKey = saveKeyFor(runtime.manifest);
  const currentRaw = storage.getItem(saveKey);
  if (currentRaw !== null) {
    return restoreCurrent(runtime, storage, saveKey, currentRaw);
  }
  if (runtime.manifest.pack_id !== "missing_phone") {
    return { restored: false, notice: null, source: "none" };
  }
  const legacyRaw = storage.getItem(LEGACY_SAVE_KEY);
  if (legacyRaw === null) {
    return { restored: false, notice: null, source: "none" };
  }
  return migrateLegacy(runtime, storage, saveKey, legacyRaw);
}

export function saveProgress(runtime, storage = safeStorage()) {
  if (!storage) {
    return false;
  }
  try {
    storage.setItem(saveKeyFor(runtime.manifest), JSON.stringify(serializeProgress(runtime)));
    return true;
  } catch {
    return false;
  }
}

export function clearProgress(runtime, storage = safeStorage()) {
  if (!storage) {
    return;
  }
  storage.removeItem(saveKeyFor(runtime.manifest));
  if (runtime.manifest.pack_id === "missing_phone") {
    storage.removeItem(LEGACY_SAVE_KEY);
  }
}

export function serializeProgress(runtime) {
  return {
    schema_version: SAVE_SCHEMA_VERSION,
    pack_id: runtime.manifest.pack_id,
    pack_version: runtime.manifest.version,
    kernel_version: runtime.manifest.kernel_version,
    scene_id: runtime.sceneId,
    state: { ...runtime.state },
    opened_anchors: [...runtime.openedAnchors],
    active_anchor_path_by_scene: clonePathMap(runtime.activeAnchorPathByScene),
    unlocked_actions: [...runtime.unlockedActions],
    active_guidance: runtime.activeGuidance ? { ...runtime.activeGuidance } : null,
    seen_guidance: [...runtime.seenGuidance],
    highlighted_actions: [...runtime.highlightedActions],
    visited_scenes: [...runtime.visitedScenes],
    chosen_actions: [...runtime.chosenActions],
    action_outcomes: [...runtime.actionOutcomes],
    ending_id: runtime.endingId || null,
    review: runtime.review
      ? {
          from_scene_id: runtime.review.fromSceneId,
          next_scene_id: runtime.review.nextSceneId,
          action_id: runtime.review.actionId,
          outcome: runtime.review.outcome || "",
        }
      : null,
  };
}

export function hydrateProgress(runtime, payload) {
  runtime.sceneId = payload.scene_id;
  runtime.state = { ...payload.state };
  runtime.openedAnchors = new Set(payload.opened_anchors);
  runtime.activeAnchorPathByScene = clonePathMap(payload.active_anchor_path_by_scene);
  runtime.unlockedActions = new Set(payload.unlocked_actions);
  runtime.activeGuidance = payload.active_guidance ? { ...payload.active_guidance } : null;
  runtime.seenGuidance = new Set(payload.seen_guidance);
  runtime.highlightedActions = new Set(payload.highlighted_actions);
  runtime.visitedScenes = new Set(payload.visited_scenes);
  runtime.chosenActions = [...payload.chosen_actions];
  runtime.actionOutcomes = [...payload.action_outcomes];
  runtime.endingId = payload.ending_id || "";
  runtime.review = payload.review
    ? {
        fromSceneId: payload.review.from_scene_id,
        nextSceneId: payload.review.next_scene_id,
        actionId: payload.review.action_id,
        outcome: payload.review.outcome || "",
      }
    : null;
}

export function validateSavePayload(payload, runtime) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return false;
  }
  if (
    payload.schema_version !== SAVE_SCHEMA_VERSION ||
    payload.pack_id !== runtime.manifest.pack_id ||
    payload.pack_version !== runtime.manifest.version ||
    payload.kernel_version !== runtime.manifest.kernel_version
  ) {
    return false;
  }
  if (!runtime.catalog.scenes.has(payload.scene_id)) {
    return false;
  }
  if (payload.ending_id !== null && !runtime.catalog.endings.has(payload.ending_id)) {
    return false;
  }
  if (!validState(payload.state, runtime.stateRegistry.states)) {
    return false;
  }
  if (
    !idArrayWithin(payload.opened_anchors, runtime.catalog.anchors) ||
    !validPathMap(payload.active_anchor_path_by_scene, runtime.catalog.scenes, runtime.catalog.anchors) ||
    !idArrayWithin(payload.unlocked_actions, runtime.catalog.actions) ||
    !stringArray(payload.seen_guidance) ||
    !idArrayWithin(payload.highlighted_actions, runtime.catalog.actions) ||
    !idArrayWithin(payload.visited_scenes, runtime.catalog.scenes) ||
    !idArrayWithin(payload.chosen_actions, runtime.catalog.actions) ||
    !stringArray(payload.action_outcomes)
  ) {
    return false;
  }
  if (!validGuidance(payload.active_guidance)) {
    return false;
  }
  return validReview(payload.review, runtime);
}

export function migrateLegacyPayload(payload, runtime) {
  if (!payload || typeof payload !== "object" || ![1, LEGACY_SAVE_VERSION].includes(payload.version)) {
    return null;
  }
  if (payload.projectId !== runtime.manifest.pack_id) {
    return null;
  }
  const initialState = Object.fromEntries(
    runtime.stateRegistry.states.map((definition) => [definition.key, definition.initial])
  );
  const migratedState = { ...initialState };
  for (const definition of runtime.stateRegistry.states) {
    if (Object.hasOwn(payload.state || {}, definition.key)) {
      migratedState[definition.key] = payload.state[definition.key];
    }
  }
  return {
    schema_version: SAVE_SCHEMA_VERSION,
    pack_id: runtime.manifest.pack_id,
    pack_version: runtime.manifest.version,
    kernel_version: runtime.manifest.kernel_version,
    scene_id: payload.sceneId,
    state: migratedState,
    opened_anchors: arrayOrEmpty(payload.openedAnchors),
    active_anchor_path_by_scene: objectOrEmpty(payload.activeAnchorPathByScene),
    unlocked_actions: arrayOrEmpty(payload.unlockedChoices),
    active_guidance: payload.activeGuidance || null,
    seen_guidance: arrayOrEmpty(payload.seenGuidance),
    highlighted_actions: arrayOrEmpty(payload.highlightedChoices),
    visited_scenes: arrayOrEmpty(payload.visitedScenes),
    chosen_actions: arrayOrEmpty(payload.chosenChoices),
    action_outcomes: arrayOrEmpty(payload.choiceOutcomes),
    ending_id: payload.endingId || null,
    review: payload.review
      ? {
          from_scene_id: payload.review.fromSceneId,
          next_scene_id: payload.review.nextSceneId,
          action_id: payload.review.choiceId,
          outcome: payload.review.outcome || "",
        }
      : null,
  };
}

function restoreCurrent(runtime, storage, saveKey, raw) {
  let payload;
  try {
    payload = JSON.parse(raw);
  } catch {
    storage.removeItem(saveKey);
    return broken("旧进度内容损坏，已为你开启新局。", "current");
  }
  if (!validateSavePayload(payload, runtime)) {
    storage.removeItem(saveKey);
    return broken("旧进度与当前案件不兼容，已为你开启新局。", "current");
  }
  hydrateProgress(runtime, payload);
  return { restored: true, notice: null, source: "current" };
}

function migrateLegacy(runtime, storage, saveKey, raw) {
  let legacy;
  try {
    legacy = JSON.parse(raw);
  } catch {
    return broken("旧进度内容损坏，已为你开启新局。", "legacy");
  }
  const payload = migrateLegacyPayload(legacy, runtime);
  if (!validateSavePayload(payload, runtime)) {
    return broken("旧进度与当前案件不兼容，已为你开启新局。", "legacy");
  }
  try {
    storage.setItem(saveKey, JSON.stringify(payload));
  } catch {
    return broken("旧进度迁移写入失败，已载入新局；原进度仍保留。", "legacy");
  }
  storage.removeItem(LEGACY_SAVE_KEY);
  hydrateProgress(runtime, payload);
  return { restored: true, notice: null, source: "legacy", migrated: true };
}

function validState(state, definitions) {
  if (!state || typeof state !== "object" || Array.isArray(state)) {
    return false;
  }
  const expectedKeys = new Set(definitions.map((definition) => definition.key));
  if (Object.keys(state).length !== expectedKeys.size || Object.keys(state).some((key) => !expectedKeys.has(key))) {
    return false;
  }
  return definitions.every((definition) => scalarMatches(state[definition.key], definition.type));
}

function scalarMatches(value, type) {
  if (type === "number") {
    return typeof value === "number" && Number.isFinite(value);
  }
  return typeof value === type;
}

function idArrayWithin(value, catalog) {
  return stringArray(value) && new Set(value).size === value.length && value.every((id) => catalog.has(id));
}

function stringArray(value) {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function validPathMap(value, scenes, anchors) {
  return (
    value &&
    typeof value === "object" &&
    !Array.isArray(value) &&
    Object.entries(value).every(
      ([sceneId, path]) => scenes.has(sceneId) && idArrayWithin(path, anchors)
    )
  );
}

function validGuidance(value) {
  return (
    value === null ||
    (value &&
      typeof value === "object" &&
      typeof value.id === "string" &&
      typeof value.title === "string" &&
      typeof value.text === "string")
  );
}

function validReview(review, runtime) {
  if (review === null) {
    return true;
  }
  return Boolean(
    review &&
      runtime.catalog.scenes.has(review.from_scene_id) &&
      runtime.catalog.scenes.has(review.next_scene_id) &&
      runtime.catalog.actions.has(review.action_id) &&
      typeof review.outcome === "string"
  );
}

function clonePathMap(value) {
  return Object.fromEntries(Object.entries(value || {}).map(([sceneId, path]) => [sceneId, [...path]]));
}

function arrayOrEmpty(value) {
  return Array.isArray(value) ? [...value] : [];
}

function objectOrEmpty(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? clonePathMap(value) : {};
}

function broken(text, source) {
  return { restored: false, notice: { title: "进度已重置", text }, source };
}

function safeStorage() {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}
