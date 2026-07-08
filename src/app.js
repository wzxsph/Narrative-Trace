const GAME_URL = "generated/missing_phone_v0/game.json";
const SAVE_KEY = "game_writer_missing_phone_runtime_v1";
const SAVE_VERSION = 2;
const STATE_LABELS = {
  "clues.archive_ready": "归档包",
  "clues.backup_copy": "备份副本",
  "clues.chen_casefile": "陈的旧案卷",
  "clues.chen_message_ready": "给陈的草稿",
  "clues.chen_motive": "陈的动机",
  "clues.chen_trimmed_location": "定位截断记录",
  "clues.cloud_admin": "云端管理员来源",
  "clues.edited_recording": "剪辑录音",
  "clues.final_message": "最后留言",
  "clues.freeze_token": "冻结令牌",
  "clues.hidden_camera": "隐藏摄像头",
  "clues.lin_confession": "林的自述",
  "clues.locker_a17": "A17 储物柜",
  "clues.public_packet_ready": "公开包",
  "clues.raw_recording": "原始录音",
  "clues.screen_recording": "屏幕录制会话",
  "clues.security_booth": "保安岗亭",
  "clues.station_entry_code": "旧员工入口码",
  "clues.station_location": "废弃地铁站定位",
  "clues.station_route_confirmed": "订单路线",
  "clues.victim_list": "受害者名单",
  "clues.voice_note": "语音便签",
  "clues.wipe_pause_window": "远程清除暂停窗口",
};

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

const runtime = {
  game: null,
  sceneId: "",
  state: {},
  openedAnchors: new Set(),
  activeAnchorPathByScene: {},
  unlockedChoices: new Set(),
  activeGuidance: null,
  seenGuidance: new Set(),
  highlightedChoices: new Set(),
  visitedScenes: new Set(),
  chosenChoices: [],
  choiceOutcomes: [],
  endingId: "",
  review: null,
  recoveryNotice: null,
};

init();

async function init() {
  dom.storyArea.appendChild(dom.loadingTemplate.content.cloneNode(true));
  syncPathPanelAccessibility(false);
  dom.mapButton.addEventListener("click", openPathPanel);
  dom.closeMapButton.addEventListener("click", () => closePathPanel());
  window.addEventListener("resize", () => syncPathPanelAccessibility(dom.pathPanel.classList.contains("open")));
  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && dom.pathPanel.classList.contains("open")) {
      closePathPanel();
    }
  });
  try {
    const response = await fetch(GAME_URL, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    runtime.game = await response.json();
    if (!restoreProgress()) {
      resetGame({ clearSave: false, preserveRecoveryNotice: true });
    }
    render();
  } catch (error) {
    dom.storyArea.innerHTML = "";
    const card = document.createElement("div");
    card.className = "loading-card";
    card.innerHTML = `<h2>案件资料未生成</h2><p>请先运行 <code>python3 scripts/generate_game.py</code>。错误：${escapeHtml(error.message)}</p>`;
    dom.storyArea.appendChild(card);
  }
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
    clearProgress();
  }
  runtime.sceneId = runtime.game.start_scene_id;
  runtime.state = cloneInitialState();
  runtime.openedAnchors = new Set();
  runtime.activeAnchorPathByScene = {};
  runtime.unlockedChoices = new Set();
  runtime.activeGuidance = null;
  runtime.seenGuidance = new Set();
  runtime.highlightedChoices = new Set();
  runtime.visitedScenes = new Set();
  runtime.chosenChoices = [];
  runtime.choiceOutcomes = [];
  runtime.endingId = "";
  runtime.review = null;
  if (!options.preserveRecoveryNotice) {
    runtime.recoveryNotice = null;
  }
}

function render() {
  if (runtime.review) {
    renderChapterReview();
    renderPathMap();
    saveProgress();
    return;
  }
  if (runtime.endingId) {
    renderEnding();
    renderPathMap();
    saveProgress();
    return;
  }
  const scene = currentScene();
  runtime.visitedScenes.add(scene.id);
  dom.chapterLabel.textContent = scene.chapter;
  dom.sceneTitle.textContent = scene.title;
  dom.taskText.textContent = scene.task;
  dom.pressureText.textContent = scene.pressure;
  renderOutcome();
  renderStory(scene);
  renderChoices(scene);
  renderPathMap();
  saveProgress();
}

function currentScene() {
  return findScene(runtime.sceneId);
}

function findScene(sceneId) {
  return runtime.game.scenes.find((scene) => scene.id === sceneId);
}

function findEnding(endingId) {
  return runtime.game.endings.find((ending) => ending.id === endingId);
}

function findChoice(choiceId) {
  for (const scene of runtime.game.scenes) {
    const choice = scene.choices.find((item) => item.id === choiceId);
    if (choice) {
      return choice;
    }
  }
  return null;
}

function renderOutcome() {
  const latest = runtime.choiceOutcomes.at(-1);
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
  scene.background_blocks.forEach((block) => {
    const wrapper = document.createElement("article");
    wrapper.className = "background-block";
    wrapper.appendChild(renderTextWithAnchors(block.text, block.observe_anchors, activePath));
    block.observe_anchors.forEach((anchor) => {
      if (activePath[0] === anchor.id) {
        wrapper.appendChild(renderFragment(anchor, activePath.slice(1)));
      }
    });
    dom.storyArea.appendChild(wrapper);
  });
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
  const echoes = (scene.state_echoes || []).filter((echo) =>
    (echo.requirements || []).every((requirement) => stateMatches(requirement))
  );
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

function renderTextWithAnchors(text, anchors, activePath = []) {
  const fragment = document.createDocumentFragment();
  const ranges = [];
  anchors.forEach((anchor) => {
    const index = text.indexOf(anchor.text_range);
    if (index >= 0) {
      ranges.push({ index, end: index + anchor.text_range.length, anchor });
    }
  });
  ranges.sort((a, b) => a.index - b.index);

  let cursor = 0;
  ranges.forEach((range) => {
    if (range.index < cursor) {
      return;
    }
    fragment.append(document.createTextNode(text.slice(cursor, range.index)));
    const button = document.createElement("button");
    button.type = "button";
    button.className = "anchor-button";
    if (runtime.openedAnchors.has(range.anchor.id)) {
      button.classList.add("opened");
    }
    if (activePath.includes(range.anchor.id)) {
      button.classList.add("active");
    }
    button.dataset.anchorId = range.anchor.id;
    button.textContent = text.slice(range.index, range.end);
    button.title = range.anchor.label;
    button.addEventListener("click", () => openAnchor(range.anchor));
    fragment.append(button);
    cursor = range.end;
  });
  fragment.append(document.createTextNode(text.slice(cursor)));
  return fragment;
}

function renderFragment(anchor, activePath = []) {
  const fragmentData = anchor.opens_fragment;
  const card = document.createElement("section");
  card.className = `evidence-card depth-${anchor.depth}`;
  card.dataset.anchorId = anchor.id;

  const title = document.createElement("h3");
  title.textContent = fragmentData.title;
  card.appendChild(title);

  const body = document.createElement("p");
  body.className = "evidence-body";
  body.appendChild(renderTextWithAnchors(fragmentData.body, fragmentData.nested_anchors || [], activePath));
  card.appendChild(body);

  const activeChildId = activePath[0];
  const activeChild = (fragmentData.nested_anchors || []).find((child) => child.id === activeChildId);
  if (activeChild) {
    card.appendChild(renderFragment(activeChild, activePath.slice(1)));
  }

  if (fragmentData.evidence_tags?.length) {
    const tags = document.createElement("div");
    tags.className = "evidence-tags";
    fragmentData.evidence_tags.forEach((tag) => {
      const tagNode = document.createElement("span");
      tagNode.className = "tag";
      tagNode.textContent = tag;
      tags.appendChild(tagNode);
    });
    card.appendChild(tags);
  }
  return card;
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
    applyEffects(anchor.effects || []);
    const unlockedChoiceIds = anchor.unlocks_choices || [];
    unlockedChoiceIds.forEach((choiceId) => runtime.unlockedChoices.add(choiceId));
    runtime.highlightedChoices = new Set(unlockedChoiceIds);
    maybeShowGuidance(anchor, unlockedChoiceIds);
  }
  render();
}

function getActiveAnchorPath(sceneId) {
  const path = runtime.activeAnchorPathByScene?.[sceneId];
  return Array.isArray(path) ? path : [];
}

function findAnchorPath(scene, anchorId) {
  for (const block of scene.background_blocks || []) {
    const path = findAnchorPathInAnchors(block.observe_anchors || [], anchorId, []);
    if (path.length) {
      return path;
    }
  }
  return [];
}

function findAnchorPathInAnchors(anchors, anchorId, parents) {
  for (const anchor of anchors) {
    const path = [...parents, anchor.id];
    if (anchor.id === anchorId) {
      return path;
    }
    const nestedPath = findAnchorPathInAnchors(anchor.opens_fragment?.nested_anchors || [], anchorId, path);
    if (nestedPath.length) {
      return nestedPath;
    }
  }
  return [];
}

function maybeShowGuidance(anchor, unlockedChoiceIds) {
  const candidates = [];
  if (anchor.guidance) {
    candidates.push(anchor.guidance);
  }
  if (unlockedChoiceIds.length && anchor.unlock_guidance) {
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

function renderChoices(scene) {
  dom.choiceArea.innerHTML = "";
  dom.choiceArea.classList.remove("compact", "cozy");
  let visibleCount = 0;
  scene.choices.forEach((choice) => {
    if (!isChoiceVisible(choice)) {
      return;
    }
    visibleCount += 1;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "choice-button";
    button.dataset.choiceId = choice.id;
    if (runtime.highlightedChoices.has(choice.id)) {
      button.classList.add("newly-unlocked");
    }

    const title = document.createElement("span");
    title.className = "choice-title";
    title.textContent = choice.label;

    const description = document.createElement("span");
    description.className = "choice-description";
    description.textContent = choice.description;

    button.append(title, description);
    button.addEventListener("click", () => choose(choice));
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

function isChoiceVisible(choice) {
  if (!choice.requirements?.length) {
    return true;
  }
  return choice.requirements.every((requirement) => stateMatches(requirement));
}

function stateMatches(requirement) {
  const current = runtime.state[requirement.state];
  if ("equals" in requirement) {
    return current === requirement.equals;
  }
  if ("min" in requirement) {
    return Number(current || 0) >= requirement.min;
  }
  return Boolean(current);
}

function choose(choice) {
  if (!isChoiceVisible(choice)) {
    return;
  }
  runtime.recoveryNotice = null;
  const fromScene = currentScene();
  applyEffects(choice.effects || []);
  runtime.chosenChoices.push(choice.id);
  runtime.choiceOutcomes.push(choice.outcome || "");
  runtime.activeGuidance = null;
  runtime.highlightedChoices = new Set();

  const target = choice.next_scene;
  if (findEnding(target)) {
    runtime.endingId = target;
  } else {
    const nextScene = findScene(target);
    if (nextScene && nextScene.chapter !== fromScene.chapter) {
      runtime.review = {
        fromSceneId: fromScene.id,
        nextSceneId: nextScene.id,
        choiceId: choice.id,
        outcome: choice.outcome || "",
      };
    } else {
      runtime.sceneId = target;
    }
  }
  render();
}

function applyEffects(effects) {
  effects.forEach((effect) => {
    if (effect.set) {
      Object.entries(effect.set).forEach(([key, value]) => {
        runtime.state[key] = value;
      });
    }
    if (effect.add) {
      Object.entries(effect.add).forEach(([key, value]) => {
        runtime.state[key] = Number(runtime.state[key] || 0) + Number(value);
      });
    }
  });
}

function renderChapterReview() {
  const review = runtime.review;
  const fromScene = findScene(review.fromSceneId);
  const nextScene = findScene(review.nextSceneId);
  const choice = findChoice(review.choiceId);
  const openedInScene = collectAnchors(fromScene).filter((anchor) => runtime.openedAnchors.has(anchor.id));
  const missedCount = collectAnchors(fromScene).length - openedInScene.length;

  dom.chapterLabel.textContent = "章节复盘";
  dom.sceneTitle.textContent = fromScene.title;
  dom.taskText.textContent = "确认你的路径";
  dom.pressureText.textContent = nextScene.chapter;
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
    openedInScene.map((anchor) => anchor.label),
    "本章没有展开关键观察。"
  );
  appendProfileSection(
    screen,
    "关键行动",
    choice ? [choice.label, choice.description] : [],
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
  title.textContent = `进入${nextScene.chapter}`;
  const description = document.createElement("span");
  description.className = "choice-description";
  description.textContent = nextScene.title;
  continueButton.append(title, description);
  continueButton.addEventListener("click", continueFromReview);
  dom.choiceArea.appendChild(continueButton);
}

function renderChapterFlow(fromScene) {
  const chapterScenes = runtime.game.scenes.filter((scene) => scene.chapter === fromScene.chapter);
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
  title.textContent = scene.title;
  const meta = document.createElement("p");
  meta.className = "flow-meta";
  meta.textContent = buildFlowMeta(scene, visited);

  const branchList = document.createElement("ul");
  branchList.className = "flow-branches";
  scene.choices.forEach((choice) => {
    const branchState = buildChoiceBranchState(choice);
    const branch = document.createElement("li");
    branch.className = branchState.className;
    branch.dataset.choiceId = choice.id;
    branch.textContent = `${choice.label} · ${branchState.note}`;
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

function buildChoiceBranchState(choice) {
  if (runtime.chosenChoices.includes(choice.id)) {
    return { className: "chosen", note: "已选择" };
  }
  if (!choice.requirements?.length) {
    return { className: "available", note: "可选未走" };
  }
  if (isChoiceVisible(choice)) {
    return { className: "unlocked", note: "已解锁未选" };
  }
  if (runtime.unlockedChoices.has(choice.id)) {
    return { className: "pending", note: `线索已指向，仍缺：${describeRequirements(choice.requirements)}` };
  }
  return { className: "locked", note: `未解锁：${describeRequirements(choice.requirements)}` };
}

function describeRequirements(requirements) {
  return requirements.map((requirement) => describeRequirement(requirement)).join("、");
}

function describeRequirement(requirement) {
  const label = STATE_LABELS[requirement.state] || requirement.state || "未知证据";
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
  const opened = anchors.filter((anchor) => runtime.openedAnchors.has(anchor.id)).length;
  const choices = scene.choices.length;
  const chosen = scene.choices.filter((choice) => runtime.chosenChoices.includes(choice.id)).length;
  return `观察 ${opened}/${anchors.length}，行动 ${chosen}/${choices}`;
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
    collectAnchors(scene).forEach((anchor) => {
      if (runtime.openedAnchors.has(anchor.id)) {
        opened.push(`${scene.title}：${anchor.label}`);
      }
    });
  });
  return opened.slice(0, 8);
}

function buildChoiceTrail() {
  return runtime.chosenChoices
    .map((choiceId) => findChoice(choiceId))
    .filter(Boolean)
    .map((choice) => choice.label);
}

function buildStateEchoes() {
  const state = runtime.state;
  const echoes = [];
  if (state["stance.truth_first"]) {
    echoes.push("你把公开真相放在了关系安全之前。");
  }
  if (state["stance.protect_person"]) {
    echoes.push("你倾向先保护具体的人，再处理真相的代价。");
  }
  if (Number(state["relationships.chen.trust"] || 0) >= 2) {
    echoes.push("陈警官更愿意把你当成合作者。");
  }
  if (Number(state["relationships.chen.suspicion"] || 0) >= 2) {
    echoes.push("陈警官已经开始怀疑你掌握了不该掌握的东西。");
  }
  if (Number(state["relationships.lin.bond"] || 0) >= 2) {
    echoes.push("你和林的关联变强，结局更难把她当成单纯线索。");
  }
  if (Number(state["pressure.company_alert"] || 0) >= 2) {
    echoes.push("公司侧的警觉升高，后续行动会更难隐藏。");
  }
  return echoes;
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
    title.textContent = scene.title;
    section.appendChild(title);

    const observes = document.createElement("ul");
    observes.className = "path-list";
    collectAnchors(scene).forEach((anchor) => {
      const item = document.createElement("li");
      item.className = `path-pill ${runtime.openedAnchors.has(anchor.id) ? "active" : ""}`;
      item.innerHTML = `<span>${escapeHtml(anchor.label)}</span><span>L${anchor.depth}</span>`;
      observes.appendChild(item);
    });
    section.appendChild(observes);

    const choices = document.createElement("ul");
    choices.className = "path-list";
    scene.choices.forEach((choice) => {
      const item = document.createElement("li");
      item.className = `path-pill ${runtime.chosenChoices.includes(choice.id) ? "chosen" : ""}`;
      item.innerHTML = `<span>${escapeHtml(choice.label)}</span><span>${choice.consequence_level}</span>`;
      choices.appendChild(item);
    });
    section.appendChild(choices);
    dom.pathMapContent.appendChild(section);
  });
}

function collectAnchors(scene) {
  const anchors = [];
  scene.background_blocks.forEach((block) => {
    block.observe_anchors.forEach((anchor) => {
      collectAnchor(anchor, anchors);
    });
  });
  return anchors;
}

function collectAnchor(anchor, anchors) {
  anchors.push(anchor);
  (anchor.opens_fragment?.nested_anchors || []).forEach((child) => collectAnchor(child, anchors));
}

function cloneInitialState() {
  return JSON.parse(JSON.stringify(runtime.game.initial_state || {}));
}

function saveProgress() {
  if (!runtime.game || !hasStorage()) {
    return;
  }
  const payload = {
    version: SAVE_VERSION,
    projectId: runtime.game.project?.id || "",
    schemaVersion: runtime.game.schema_version || "",
    sceneId: runtime.sceneId,
    state: runtime.state,
    openedAnchors: Array.from(runtime.openedAnchors),
    activeAnchorPathByScene: runtime.activeAnchorPathByScene,
    unlockedChoices: Array.from(runtime.unlockedChoices),
    activeGuidance: runtime.activeGuidance,
    seenGuidance: Array.from(runtime.seenGuidance),
    highlightedChoices: Array.from(runtime.highlightedChoices),
    visitedScenes: Array.from(runtime.visitedScenes),
    chosenChoices: runtime.chosenChoices,
    choiceOutcomes: runtime.choiceOutcomes,
    endingId: runtime.endingId,
    review: runtime.review,
  };
  window.localStorage.setItem(SAVE_KEY, JSON.stringify(payload));
}

function restoreProgress() {
  if (!hasStorage()) {
    return false;
  }
  const raw = window.localStorage.getItem(SAVE_KEY);
  if (!raw) {
    return false;
  }
  try {
    const payload = migrateSavePayload(JSON.parse(raw));
    if (!isValidSave(payload)) {
      runtime.recoveryNotice = makeRecoveryNotice("旧进度与当前案件不兼容，已为你开启新局。");
      clearProgress();
      return false;
    }
    runtime.sceneId = payload.sceneId;
    runtime.state = payload.state;
    runtime.openedAnchors = new Set(payload.openedAnchors);
    runtime.activeAnchorPathByScene = payload.activeAnchorPathByScene || {};
    runtime.unlockedChoices = new Set(payload.unlockedChoices);
    runtime.activeGuidance = payload.activeGuidance || null;
    runtime.seenGuidance = new Set(payload.seenGuidance || []);
    runtime.highlightedChoices = new Set(payload.highlightedChoices || []);
    runtime.visitedScenes = new Set(payload.visitedScenes);
    runtime.chosenChoices = payload.chosenChoices;
    runtime.choiceOutcomes = payload.choiceOutcomes;
    runtime.endingId = payload.endingId;
    runtime.review = payload.review;
    return true;
  } catch {
    runtime.recoveryNotice = makeRecoveryNotice("旧进度内容损坏，已为你开启新局。");
    clearProgress();
    return false;
  }
}

function makeRecoveryNotice(text) {
  return {
    title: "进度已重置",
    text,
  };
}

function migrateSavePayload(payload) {
  if (!payload || typeof payload !== "object") {
    return null;
  }
  if (payload.version === SAVE_VERSION) {
    return payload;
  }
  if (payload.version === 1 && SAVE_VERSION === 2) {
    return {
      ...payload,
      version: SAVE_VERSION,
    };
  }
  return null;
}

function isValidSave(payload) {
  if (!payload || payload.version !== SAVE_VERSION) {
    return false;
  }
  if (payload.projectId !== (runtime.game.project?.id || "")) {
    return false;
  }
  if (payload.schemaVersion !== (runtime.game.schema_version || "")) {
    return false;
  }
  if (!payload.sceneId || !findScene(payload.sceneId)) {
    return false;
  }
  if (payload.endingId && !findEnding(payload.endingId)) {
    return false;
  }
  if (payload.review) {
    if (!findScene(payload.review.fromSceneId) || !findScene(payload.review.nextSceneId)) {
      return false;
    }
    if (!findChoice(payload.review.choiceId)) {
      return false;
    }
  }
  return (
    payload.state &&
    typeof payload.state === "object" &&
    !Array.isArray(payload.state) &&
    Array.isArray(payload.openedAnchors) &&
    isValidActiveAnchorPathByScene(payload.activeAnchorPathByScene) &&
    Array.isArray(payload.unlockedChoices) &&
    (payload.activeGuidance === undefined ||
      payload.activeGuidance === null ||
      typeof payload.activeGuidance === "object") &&
    (payload.seenGuidance === undefined || Array.isArray(payload.seenGuidance)) &&
    (payload.highlightedChoices === undefined || Array.isArray(payload.highlightedChoices)) &&
    Array.isArray(payload.visitedScenes) &&
    Array.isArray(payload.chosenChoices) &&
    Array.isArray(payload.choiceOutcomes)
  );
}

function isValidActiveAnchorPathByScene(value) {
  if (value === undefined) {
    return true;
  }
  return (
    value &&
    typeof value === "object" &&
    !Array.isArray(value) &&
    Object.values(value).every(
      (path) => Array.isArray(path) && path.every((anchorId) => typeof anchorId === "string")
    )
  );
}

function clearProgress() {
  if (hasStorage()) {
    window.localStorage.removeItem(SAVE_KEY);
  }
}

function hasStorage() {
  try {
    return Boolean(window.localStorage);
  } catch {
    return false;
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}
