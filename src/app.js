const GAME_URL = "generated/missing_phone_v0/game.json";
const SAVE_KEY = "game_writer_missing_phone_runtime_v1";
const SAVE_VERSION = 1;

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
  unlockedChoices: new Set(),
  visitedScenes: new Set(),
  chosenChoices: [],
  choiceOutcomes: [],
  endingId: "",
  review: null,
};

init();

async function init() {
  dom.storyArea.appendChild(dom.loadingTemplate.content.cloneNode(true));
  dom.mapButton.addEventListener("click", () => {
    dom.pathPanel.classList.add("open");
    renderPathMap();
  });
  dom.closeMapButton.addEventListener("click", () => dom.pathPanel.classList.remove("open"));
  try {
    const response = await fetch(GAME_URL, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    runtime.game = await response.json();
    if (!restoreProgress()) {
      resetGame({ clearSave: false });
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

function resetGame(options = {}) {
  if (options.clearSave !== false) {
    clearProgress();
  }
  runtime.sceneId = runtime.game.start_scene_id;
  runtime.state = cloneInitialState();
  runtime.openedAnchors = new Set();
  runtime.unlockedChoices = new Set();
  runtime.visitedScenes = new Set();
  runtime.chosenChoices = [];
  runtime.choiceOutcomes = [];
  runtime.endingId = "";
  runtime.review = null;
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
  renderStateEchoes(scene);
  scene.background_blocks.forEach((block) => {
    const wrapper = document.createElement("article");
    wrapper.className = "background-block";
    wrapper.appendChild(renderTextWithAnchors(block.text, block.observe_anchors));
    block.observe_anchors.forEach((anchor) => {
      if (runtime.openedAnchors.has(anchor.id)) {
        wrapper.appendChild(renderFragment(anchor));
      }
    });
    dom.storyArea.appendChild(wrapper);
  });
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

function renderTextWithAnchors(text, anchors) {
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
    button.className = `anchor-button ${runtime.openedAnchors.has(range.anchor.id) ? "opened" : ""}`;
    button.textContent = text.slice(range.index, range.end);
    button.title = range.anchor.label;
    button.addEventListener("click", () => openAnchor(range.anchor));
    fragment.append(button);
    cursor = range.end;
  });
  fragment.append(document.createTextNode(text.slice(cursor)));
  return fragment;
}

function renderFragment(anchor) {
  const fragmentData = anchor.opens_fragment;
  const card = document.createElement("section");
  card.className = `evidence-card depth-${anchor.depth}`;

  const title = document.createElement("h3");
  title.textContent = fragmentData.title;
  card.appendChild(title);

  const body = document.createElement("p");
  body.className = "evidence-body";
  body.appendChild(renderTextWithAnchors(fragmentData.body, fragmentData.nested_anchors || []));
  card.appendChild(body);

  (fragmentData.nested_anchors || []).forEach((child) => {
    if (runtime.openedAnchors.has(child.id)) {
      card.appendChild(renderFragment(child));
    }
  });

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
  const firstOpen = !runtime.openedAnchors.has(anchor.id);
  runtime.openedAnchors.add(anchor.id);
  if (firstOpen) {
    applyEffects(anchor.effects || []);
    (anchor.unlocks_choices || []).forEach((choiceId) => runtime.unlockedChoices.add(choiceId));
  }
  render();
}

function renderChoices(scene) {
  dom.choiceArea.innerHTML = "";
  let visibleCount = 0;
  scene.choices.forEach((choice) => {
    if (!isChoiceVisible(choice)) {
      return;
    }
    visibleCount += 1;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "choice-button";

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
  const fromScene = currentScene();
  applyEffects(choice.effects || []);
  runtime.chosenChoices.push(choice.id);
  runtime.choiceOutcomes.push(choice.outcome || "");

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

  screen.prepend(heading, body);
  dom.storyArea.appendChild(screen);

  const continueButton = document.createElement("button");
  continueButton.type = "button";
  continueButton.className = "choice-button continue-button";
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
    unlockedChoices: Array.from(runtime.unlockedChoices),
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
    const payload = JSON.parse(raw);
    if (!isValidSave(payload)) {
      return false;
    }
    runtime.sceneId = payload.sceneId;
    runtime.state = payload.state;
    runtime.openedAnchors = new Set(payload.openedAnchors);
    runtime.unlockedChoices = new Set(payload.unlockedChoices);
    runtime.visitedScenes = new Set(payload.visitedScenes);
    runtime.chosenChoices = payload.chosenChoices;
    runtime.choiceOutcomes = payload.choiceOutcomes;
    runtime.endingId = payload.endingId;
    runtime.review = payload.review;
    return true;
  } catch {
    clearProgress();
    return false;
  }
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
    typeof payload.state === "object" &&
    Array.isArray(payload.openedAnchors) &&
    Array.isArray(payload.unlockedChoices) &&
    Array.isArray(payload.visitedScenes) &&
    Array.isArray(payload.chosenChoices) &&
    Array.isArray(payload.choiceOutcomes)
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
