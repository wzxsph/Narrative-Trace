import {
  actionIsVisible,
  applyEffects as applyStateEffects,
  findAction as findRuntimeAction,
  findEnding as findRuntimeEnding,
  findScene as findRuntimeScene,
  matchingEchoes,
  resetRuntime,
  stateMatches as stateMatchesValue,
} from "./engine.js";
import { clearProgress, restoreProgress, saveProgress } from "./save.js";
import { collectAnchors, findAnchorPath, renderSceneSurfaces } from "./text-surface-renderer.js";

let runtime = null;
let stateLabels = {};

const dom = {
  chapterLabel: document.querySelector("#chapterLabel"),
  sceneTitle: document.querySelector("#sceneTitle"),
  taskText: document.querySelector("#taskText"),
  pressureText: document.querySelector("#pressureText"),
  storyArea: document.querySelector("#storyArea"),
  choiceArea: document.querySelector("#choiceArea"),
  outcomePanel: document.querySelector("#outcomePanel"),
  pathPanel: document.querySelector("#pathPanel"),
  mapButton: document.querySelector("#mapButton"),
  closeMapButton: document.querySelector("#closeMapButton"),
  pathMapContent: document.querySelector("#pathMapContent"),
  loadingTemplate: document.querySelector("#loadingTemplate"),
};

export function mountInvestigationUI(loadedRuntime) {
  runtime = loadedRuntime;
  stateLabels = Object.fromEntries(runtime.stateRegistry.states.map((item) => [item.key, item.label]));
  document.title = runtime.manifest.title;
  syncPathPanelAccessibility(false);
  dom.mapButton.addEventListener("click", openPathPanel);
  dom.closeMapButton.addEventListener("click", () => closePathPanel());
  window.addEventListener("resize", () => syncPathPanelAccessibility(dom.pathPanel.classList.contains("open")));
  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && dom.pathPanel.classList.contains("open")) {
      closePathPanel();
    }
  });
  const restored = restoreProgress(runtime);
  if (!restored.restored) {
    resetRuntime(runtime, { preserveRecoveryNotice: true });
    runtime.recoveryNotice = restored.notice;
  }
  render();
}

function openPathPanel() {
  dom.pathPanel.classList.add("open");
  syncPathPanelAccessibility(true);
  renderPathMap();
  if (isOverlayPathPanel()) {
    dom.closeMapButton.focus();
  }
}

function closePathPanel(options = {}) {
  dom.pathPanel.classList.remove("open");
  syncPathPanelAccessibility(false);
  if (options.returnFocus !== false && isOverlayPathPanel()) {
    dom.mapButton.focus();
  }
}

function syncPathPanelAccessibility(isOpen) {
  const overlay = isOverlayPathPanel();
  const visibleToAssistiveTech = !overlay || isOpen;
  dom.mapButton.setAttribute("aria-expanded", String(visibleToAssistiveTech));
  dom.pathPanel.setAttribute("aria-hidden", String(!visibleToAssistiveTech));
  dom.closeMapButton.tabIndex = visibleToAssistiveTech ? 0 : -1;
  if (visibleToAssistiveTech) {
    dom.pathPanel.removeAttribute("inert");
  } else {
    dom.pathPanel.setAttribute("inert", "");
  }
}

function isOverlayPathPanel() {
  return window.matchMedia("(max-width: 860px)").matches;
}

function resetGame(options = {}) {
  if (options.clearSave !== false) {
    clearProgress(runtime);
  }
  resetRuntime(runtime, options);
}

function render() {
  if (!runtime.experimentalAcknowledged) {
    renderExperimentalNotice();
    return;
  }
  if (runtime.review) {
    renderChapterReview();
    renderPathMap();
    saveProgress(runtime);
    return;
  }
  if (runtime.endingId) {
    renderEnding();
    renderPathMap();
    saveProgress(runtime);
    return;
  }
  const scene = currentScene();
  runtime.visitedScenes.add(scene.id);
  const metadata = investigationMetadata(scene);
  dom.chapterLabel.textContent = metadata.chapter_title;
  dom.sceneTitle.textContent = metadata.title;
  dom.taskText.textContent = metadata.task;
  dom.pressureText.textContent = metadata.pressure;
  renderOutcome();
  renderStory(scene);
  renderActions(scene);
  renderPathMap();
  saveProgress(runtime);
}

function renderExperimentalNotice() {
  dom.chapterLabel.textContent = "Experimental";
  dom.sceneTitle.textContent = runtime.manifest.title;
  dom.taskText.textContent = "确认实验内容标记";
  dom.pressureText.textContent = "未完成真人验证";
  dom.outcomePanel.hidden = true;
  dom.storyArea.innerHTML = "";
  dom.choiceArea.innerHTML = "";
  dom.pathMapContent.innerHTML = "";

  const notice = document.createElement("section");
  notice.className = "experimental-notice";
  notice.dataset.notice = "experimental";
  const title = document.createElement("h2");
  title.textContent = "这是实验内容包";
  const body = document.createElement("p");
  body.textContent = "该玩法或内容尚未完成 Verified 验证，体验指标与叙事稳定性可能变化。";
  notice.append(title, body);
  dom.storyArea.appendChild(notice);

  const start = document.createElement("button");
  start.type = "button";
  start.className = "choice-button continue-button";
  start.dataset.action = "acknowledge-experimental";
  const startTitle = document.createElement("span");
  startTitle.className = "choice-title";
  startTitle.textContent = "我已了解，开始体验";
  const description = document.createElement("span");
  description.className = "choice-description";
  description.textContent = "实验标记不会从内容包或发布产物中移除。";
  start.append(startTitle, description);
  start.addEventListener("click", () => {
    runtime.experimentalAcknowledged = true;
    render();
  });
  dom.choiceArea.appendChild(start);
}

function investigationMetadata(scene) {
  return scene.extensions?.investigation || {
    chapter_id: "unknown",
    chapter_title: "未分章",
    title: scene.id,
    task: "继续调查",
    pressure: "--",
  };
}

function currentScene() {
  return findScene(runtime.sceneId);
}

function findScene(sceneId) {
  return findRuntimeScene(runtime, sceneId);
}

function findEnding(endingId) {
  return findRuntimeEnding(runtime, endingId);
}

function findAction(actionId) {
  return findRuntimeAction(runtime, actionId);
}

function renderOutcome() {
  const latest = runtime.actionOutcomes.at(-1);
  if (!latest) {
    dom.outcomePanel.hidden = true;
    dom.outcomePanel.textContent = "";
    return;
  }
  dom.outcomePanel.hidden = false;
  dom.outcomePanel.textContent = latest;
}

function renderStory(scene) {
  dom.storyArea.innerHTML = "";
  renderRecoveryNotice();
  renderStateEchoes(scene);
  renderGuidance();
  const activePath = getActiveAnchorPath(scene.id);
  dom.storyArea.appendChild(
    renderSceneSurfaces(scene, {
      activePath,
      openedAnchors: runtime.openedAnchors,
      onOpenAnchor: openAnchor,
    })
  );
}

function renderRecoveryNotice() {
  const notice = runtime.recoveryNotice;
  if (!notice) {
    return;
  }
  const wrapper = document.createElement("aside");
  wrapper.className = "recovery-notice";
  wrapper.dataset.notice = "save-recovery";

  const title = document.createElement("h2");
  title.textContent = notice.title || "进度已重置";
  const body = document.createElement("p");
  body.textContent = notice.text || "旧进度无法恢复，已为你开启新局。";

  wrapper.append(title, body);
  dom.storyArea.appendChild(wrapper);
}

function renderGuidance() {
  const guidance = runtime.activeGuidance;
  if (!guidance) {
    return;
  }
  const wrapper = document.createElement("aside");
  wrapper.className = "guidance-panel";

  const title = document.createElement("h2");
  title.textContent = guidance.title || "系统痕迹";
  const body = document.createElement("p");
  body.textContent = guidance.text || "";

  wrapper.append(title, body);
  dom.storyArea.appendChild(wrapper);
}

function renderStateEchoes(scene) {
  const echoes = matchingEchoes(runtime, scene.echoes);
  if (!echoes.length) {
    return;
  }
  const wrapper = document.createElement("section");
  wrapper.className = "state-echoes";
  const title = document.createElement("h2");
  title.textContent = "此前的回声";
  wrapper.appendChild(title);
  echoes.forEach((echo) => {
    const item = document.createElement("article");
    item.className = "state-echo";
    const label = document.createElement("h3");
    label.textContent = echo.label;
    const text = document.createElement("p");
    text.textContent = echo.text;
    item.append(label, text);
    wrapper.appendChild(item);
  });
  dom.storyArea.appendChild(wrapper);
}

function openAnchor(anchor) {
  runtime.recoveryNotice = null;
  const scene = currentScene();
  const activePath = findAnchorPath(scene, anchor.id);
  if (activePath.length) {
    runtime.activeAnchorPathByScene[scene.id] = activePath;
  }
  const firstOpen = !runtime.openedAnchors.has(anchor.id);
  runtime.openedAnchors.add(anchor.id);
  if (firstOpen) {
    applyStateEffects(runtime.state, anchor.effects || []);
    const unlockedActionIds = anchor.unlocks_actions || [];
    unlockedActionIds.forEach((actionId) => runtime.unlockedActions.add(actionId));
    runtime.highlightedActions = new Set(unlockedActionIds);
    maybeShowGuidance(anchor, unlockedActionIds);
  }
  render();
}

function getActiveAnchorPath(sceneId) {
  const path = runtime.activeAnchorPathByScene?.[sceneId];
  return Array.isArray(path) ? path : [];
}

function maybeShowGuidance(anchor, unlockedActionIds) {
  const candidates = [];
  if (anchor.guidance) {
    candidates.push(anchor.guidance);
  }
  if (unlockedActionIds.length && anchor.unlock_guidance) {
    candidates.push(anchor.unlock_guidance);
  }
  const nextGuidance = candidates.find(
    (guidance) => guidance?.id && !runtime.seenGuidance.has(guidance.id)
  );
  if (!nextGuidance) {
    return;
  }
  runtime.activeGuidance = nextGuidance;
  runtime.seenGuidance.add(nextGuidance.id);
}

function renderActions(scene) {
  dom.choiceArea.innerHTML = "";
  dom.choiceArea.classList.remove("compact", "cozy");
  let visibleCount = 0;
  scene.actions.forEach((action) => {
    if (!isActionVisible(action)) {
      return;
    }
    visibleCount += 1;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "choice-button";
    button.dataset.actionId = action.id;
    button.dataset.choiceId = action.id;
    if (runtime.highlightedActions.has(action.id)) {
      button.classList.add("newly-unlocked");
    }

    const title = document.createElement("span");
    title.className = "choice-title";
    title.textContent = action.label;

    const description = document.createElement("span");
    description.className = "choice-description";
    description.textContent = action.consequence_hint;

    button.append(title, description);
    button.addEventListener("click", () => performAction(action));
    dom.choiceArea.appendChild(button);
  });
  if (visibleCount === 0) {
    const empty = document.createElement("div");
    empty.className = "choice-empty";
    empty.textContent = "当前没有稳妥行动。";
    dom.choiceArea.appendChild(empty);
  }
  dom.choiceArea.dataset.choiceCount = String(visibleCount);
  dom.choiceArea.classList.toggle("compact", visibleCount >= 4);
  dom.choiceArea.classList.toggle("cozy", visibleCount > 0 && visibleCount <= 2);
}

function isActionVisible(action) {
  return !runtime.chosenActions.includes(action.id) && actionIsVisible(runtime, action);
}

function stateMatches(requirement) {
  return stateMatchesValue(runtime.state, requirement);
}

function performAction(action) {
  if (!isActionVisible(action)) {
    return;
  }
  runtime.recoveryNotice = null;
  const fromScene = currentScene();
  applyStateEffects(runtime.state, action.effects || []);
  runtime.chosenActions.push(action.id);
  runtime.actionOutcomes.push(action.outcome || "");
  runtime.activeGuidance = null;
  runtime.highlightedActions = new Set();

  const target = action.target;
  if (target.type === "ending") {
    runtime.endingId = target.id;
  } else {
    const nextScene = findScene(target.id);
    if (nextScene && investigationMetadata(nextScene).chapter_id !== investigationMetadata(fromScene).chapter_id) {
      runtime.review = {
        fromSceneId: fromScene.id,
        nextSceneId: nextScene.id,
        actionId: action.id,
        outcome: action.outcome || "",
      };
    } else {
      runtime.sceneId = target.id;
    }
  }
  render();
}

function renderChapterReview() {
  const review = runtime.review;
  const fromScene = findScene(review.fromSceneId);
  const nextScene = findScene(review.nextSceneId);
  const action = findAction(review.actionId);
  const openedInScene = collectAnchors(fromScene).filter(({ anchor }) => runtime.openedAnchors.has(anchor.id));
  const missedCount = collectAnchors(fromScene).length - openedInScene.length;

  dom.chapterLabel.textContent = "章节复盘";
  dom.sceneTitle.textContent = investigationMetadata(fromScene).title;
  dom.taskText.textContent = "确认你的路径";
  dom.pressureText.textContent = investigationMetadata(nextScene).chapter_title;
  dom.outcomePanel.hidden = true;
  dom.outcomePanel.textContent = "";
  dom.storyArea.innerHTML = "";
  dom.choiceArea.innerHTML = "";

  const screen = document.createElement("section");
  screen.className = "review-screen";

  const heading = document.createElement("h2");
  heading.textContent = "本章留下的痕迹";
  const body = document.createElement("p");
  body.className = "review-body";
  body.textContent = review.outcome || "这个选择把故事推向了下一章。";

  screen.append(heading, body, renderChapterFlow(fromScene));

  appendProfileSection(
    screen,
    "已展开观察",
    openedInScene.map(({ anchor }) => anchor.label),
    "本章没有展开关键观察。"
  );
  appendProfileSection(
    screen,
    "关键行动",
    action ? [action.label, action.consequence_hint] : [],
    "没有记录到本章行动。"
  );
  appendProfileSection(
    screen,
    "状态回声",
    buildStateEchoes(),
    "当前还没有形成明确的关系或立场回声。"
  );
  appendProfileSection(
    screen,
    "未触达可能",
    missedCount > 0 ? [`还有 ${missedCount} 条观察痕迹没有展开。`] : ["本章观察痕迹已全部展开。"],
    ""
  );

  dom.storyArea.appendChild(screen);

  const continueButton = document.createElement("button");
  continueButton.type = "button";
  continueButton.className = "choice-button continue-button";
  continueButton.dataset.action = "continue-review";
  const title = document.createElement("span");
  title.className = "choice-title";
  title.textContent = `进入${investigationMetadata(nextScene).chapter_title}`;
  const description = document.createElement("span");
  description.className = "choice-description";
  description.textContent = investigationMetadata(nextScene).title;
  continueButton.append(title, description);
  continueButton.addEventListener("click", continueFromReview);
  dom.choiceArea.appendChild(continueButton);
}

function renderChapterFlow(fromScene) {
  const chapterId = investigationMetadata(fromScene).chapter_id;
  const chapterScenes = runtime.game.scenes.filter(
    (scene) => investigationMetadata(scene).chapter_id === chapterId
  );
  const flow = document.createElement("section");
  flow.className = "chapter-flow";

  const title = document.createElement("h3");
  title.textContent = "本章路径图";
  flow.appendChild(title);

  const nodes = document.createElement("ol");
  nodes.className = "chapter-flow-nodes";
  chapterScenes.forEach((scene, index) => {
    nodes.appendChild(renderChapterFlowNode(scene, index, chapterScenes.length));
  });
  flow.appendChild(nodes);
  return flow;
}

function renderChapterFlowNode(scene, index, total) {
  const item = document.createElement("li");
  const visited = runtime.visitedScenes.has(scene.id);
  const isCurrent = scene.id === runtime.review?.fromSceneId;
  item.className = `chapter-flow-node ${visited ? "visited" : "missed"} ${isCurrent ? "current" : ""}`;

  const marker = document.createElement("span");
  marker.className = "flow-marker";
  marker.textContent = String(index + 1);

  const body = document.createElement("div");
  body.className = "flow-body";

  const title = document.createElement("h4");
  title.textContent = investigationMetadata(scene).title;
  const meta = document.createElement("p");
  meta.className = "flow-meta";
  meta.textContent = buildFlowMeta(scene, visited);

  const branchList = document.createElement("ul");
  branchList.className = "flow-branches";
  scene.actions.forEach((action) => {
    const branchState = buildActionBranchState(action);
    const branch = document.createElement("li");
    branch.className = branchState.className;
    branch.dataset.actionId = action.id;
    branch.dataset.choiceId = action.id;
    branch.textContent = `${action.label} · ${branchState.note}`;
    branchList.appendChild(branch);
  });

  body.append(title, meta, branchList);
  item.append(marker, body);
  if (index < total - 1) {
    const connector = document.createElement("span");
    connector.className = "flow-connector";
    connector.textContent = "↓";
    item.appendChild(connector);
  }
  return item;
}

function buildActionBranchState(action) {
  if (runtime.chosenActions.includes(action.id)) {
    return { className: "chosen", note: "已选择" };
  }
  if (!action.requirements?.length) {
    return { className: "available", note: "可选未走" };
  }
  if (isActionVisible(action)) {
    return { className: "unlocked", note: "已解锁未选" };
  }
  if (runtime.unlockedActions.has(action.id)) {
    return { className: "pending", note: `线索已指向，仍缺：${describeRequirements(action.requirements)}` };
  }
  return { className: "locked", note: `未解锁：${describeRequirements(action.requirements)}` };
}

function describeRequirements(requirements) {
  return requirements.map((requirement) => describeRequirement(requirement)).join("、");
}

function describeRequirement(requirement) {
  const label = stateLabels[requirement.state] || requirement.state || "未知证据";
  if ("min" in requirement) {
    return `${label}达到 ${requirement.min}`;
  }
  if ("equals" in requirement && requirement.equals === false) {
    return `${label}未成立`;
  }
  return label;
}

function buildFlowMeta(scene, visited) {
  if (!visited) {
    return "未到达。";
  }
  const anchors = collectAnchors(scene);
  const opened = anchors.filter(({ anchor }) => runtime.openedAnchors.has(anchor.id)).length;
  const actions = scene.actions.length;
  const chosen = scene.actions.filter((action) => runtime.chosenActions.includes(action.id)).length;
  return `观察 ${opened}/${anchors.length}，行动 ${chosen}/${actions}`;
}

function continueFromReview() {
  if (!runtime.review) {
    return;
  }
  runtime.sceneId = runtime.review.nextSceneId;
  runtime.review = null;
  render();
}

function renderEnding() {
  const ending = findEnding(runtime.endingId);
  dom.chapterLabel.textContent = "结局";
  dom.sceneTitle.textContent = ending.title;
  dom.taskText.textContent = "复盘你的路径";
  dom.pressureText.textContent = "已结束";
  renderOutcome();
  dom.storyArea.innerHTML = "";
  const screen = document.createElement("section");
  screen.className = "ending-screen";
  screen.dataset.endingId = ending.id;

  const title = document.createElement("h2");
  title.textContent = ending.title;
  const body = document.createElement("p");
  body.className = "ending-body";
  body.textContent = ending.body;

  const tags = document.createElement("div");
  tags.className = "evidence-tags";
  ending.tags.forEach((tag) => {
    const node = document.createElement("span");
    node.className = "tag";
    node.textContent = tag;
    tags.appendChild(node);
  });

  appendProfileSection(screen, "关键观察", buildOpenedAnchorTrail(), "没有记录到关键观察。");
  appendProfileSection(screen, "关键行动", buildChoiceTrail(), "没有记录到关键行动。");
  appendProfileSection(screen, "最终立场", buildStateEchoes(), "没有形成明确立场。");
  appendProfileSection(screen, "你保护了", ending.portrait.protected, "");
  appendProfileSection(screen, "你伤害了", ending.portrait.harmed, "");
  appendProfileSection(screen, "你相信", ending.portrait.believed, "");
  appendProfileSection(screen, "结局标签", ending.tags, "没有结局标签。");

  const restart = document.createElement("button");
  restart.className = "restart-button";
  restart.type = "button";
  restart.dataset.action = "restart";
  restart.textContent = "重新开始";
  restart.addEventListener("click", () => {
    resetGame();
    render();
  });

  screen.prepend(title, body, tags);
  screen.appendChild(restart);
  dom.storyArea.appendChild(screen);
  dom.choiceArea.innerHTML = "";
}

function appendProfileSection(parent, title, items, emptyText) {
  const section = document.createElement("section");
  section.className = "profile-section";
  const heading = document.createElement("h3");
  heading.textContent = title;
  section.appendChild(heading);

  const list = document.createElement("ul");
  list.className = "profile-list";
  const values = items.filter(Boolean);
  if (values.length) {
    values.forEach((item) => {
      const listItem = document.createElement("li");
      listItem.textContent = item;
      list.appendChild(listItem);
    });
  } else if (emptyText) {
    const listItem = document.createElement("li");
    listItem.textContent = emptyText;
    list.appendChild(listItem);
  }
  section.appendChild(list);
  parent.appendChild(section);
}

function buildOpenedAnchorTrail() {
  const opened = [];
  runtime.game.scenes.forEach((scene) => {
    collectAnchors(scene).forEach(({ anchor }) => {
      if (runtime.openedAnchors.has(anchor.id)) {
        opened.push(`${investigationMetadata(scene).title}：${anchor.label}`);
      }
    });
  });
  return opened.slice(0, 8);
}

function buildChoiceTrail() {
  return runtime.chosenActions
    .map((actionId) => findAction(actionId))
    .filter(Boolean)
    .map((action) => action.label);
}

function buildStateEchoes() {
  return matchingEchoes(runtime, runtime.game.profile_echoes).map((echo) => echo.text);
}

function renderPathMap() {
  if (!runtime.game) {
    return;
  }
  dom.pathMapContent.innerHTML = "";
  runtime.game.scenes.forEach((scene) => {
    const section = document.createElement("section");
    section.className = `path-scene ${runtime.visitedScenes.has(scene.id) ? "visited" : ""}`;
    const title = document.createElement("h3");
    title.textContent = investigationMetadata(scene).title;
    section.appendChild(title);

    const observes = document.createElement("ul");
    observes.className = "path-list";
    collectAnchors(scene).forEach(({ anchor, depth }) => {
      const item = document.createElement("li");
      item.className = `path-pill ${runtime.openedAnchors.has(anchor.id) ? "active" : ""}`;
      item.innerHTML = `<span>${escapeHtml(anchor.label)}</span><span>L${depth}</span>`;
      observes.appendChild(item);
    });
    section.appendChild(observes);

    const actions = document.createElement("ul");
    actions.className = "path-list";
    scene.actions.forEach((action) => {
      const item = document.createElement("li");
      item.className = `path-pill ${runtime.chosenActions.includes(action.id) ? "chosen" : ""}`;
      item.innerHTML = `<span>${escapeHtml(action.label)}</span><span>${action.consequence_level}</span>`;
      actions.appendChild(item);
    });
    section.appendChild(actions);
    dom.pathMapContent.appendChild(section);
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}
