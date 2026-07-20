export function createRuntime(pack) {
  const runtime = {
    config: pack.config,
    manifest: pack.manifest,
    game: pack.game,
    stateRegistry: pack.stateRegistry,
    provenance: pack.provenance,
    catalog: buildCatalog(pack.game),
    sceneId: "",
    state: {},
    openedAnchors: new Set(),
    activeAnchorPathByScene: {},
    unlockedActions: new Set(),
    activeGuidance: null,
    seenGuidance: new Set(),
    highlightedActions: new Set(),
    visitedScenes: new Set(),
    chosenActions: [],
    actionOutcomes: [],
    endingId: "",
    review: null,
    recoveryNotice: null,
    experimentalAcknowledged: pack.manifest.loop_package.tier !== "experimental",
  };
  resetRuntime(runtime, { preserveRecoveryNotice: true });
  return runtime;
}

export function resetRuntime(runtime, options = {}) {
  runtime.sceneId = runtime.game.entry_scene_id;
  runtime.state = Object.fromEntries(
    runtime.stateRegistry.states.map((definition) => [definition.key, cloneScalar(definition.initial)])
  );
  runtime.openedAnchors = new Set();
  runtime.activeAnchorPathByScene = {};
  runtime.unlockedActions = new Set();
  runtime.activeGuidance = null;
  runtime.seenGuidance = new Set();
  runtime.highlightedActions = new Set();
  runtime.visitedScenes = new Set();
  runtime.chosenActions = [];
  runtime.actionOutcomes = [];
  runtime.endingId = "";
  runtime.review = null;
  if (!options.preserveRecoveryNotice) {
    runtime.recoveryNotice = null;
  }
}

export function findScene(runtime, sceneId) {
  return runtime.catalog.scenes.get(sceneId) || null;
}

export function findEnding(runtime, endingId) {
  return runtime.catalog.endings.get(endingId) || null;
}

export function findAction(runtime, actionId) {
  return runtime.catalog.actions.get(actionId) || null;
}

export function actionIsVisible(runtime, action) {
  return (action.requirements || []).every((requirement) => stateMatches(runtime.state, requirement));
}

export function stateMatches(state, requirement) {
  const current = state[requirement.state];
  if (Object.hasOwn(requirement, "equals")) {
    return current === requirement.equals;
  }
  if (Object.hasOwn(requirement, "min")) {
    return Number(current) >= Number(requirement.min);
  }
  if (Object.hasOwn(requirement, "max")) {
    return Number(current) <= Number(requirement.max);
  }
  return false;
}

export function applyEffects(state, effects) {
  (effects || []).forEach((effect) => {
    Object.entries(effect.set || {}).forEach(([key, value]) => {
      state[key] = cloneScalar(value);
    });
    Object.entries(effect.add || {}).forEach(([key, value]) => {
      state[key] = Number(state[key] || 0) + Number(value);
    });
  });
  return state;
}

export function matchingEchoes(runtime, echoes) {
  return (echoes || []).filter((echo) =>
    (echo.requirements || []).every((requirement) => stateMatches(runtime.state, requirement))
  );
}

export function buildCatalog(game) {
  const scenes = new Map();
  const endings = new Map();
  const actions = new Map();
  const anchors = new Map();
  for (const scene of game.scenes || []) {
    scenes.set(scene.id, scene);
    for (const action of scene.actions || []) {
      actions.set(action.id, action);
    }
    for (const surface of scene.surfaces || []) {
      collectSurfaceAnchors(surface, anchors);
    }
  }
  for (const ending of game.endings || []) {
    endings.set(ending.id, ending);
  }
  return { scenes, endings, actions, anchors };
}

function collectSurfaceAnchors(surface, anchors) {
  for (const anchor of surface.anchors || []) {
    anchors.set(anchor.id, anchor);
    for (const childSurface of anchor.fragment?.surfaces || []) {
      collectSurfaceAnchors(childSurface, anchors);
    }
  }
}

function cloneScalar(value) {
  return value;
}
