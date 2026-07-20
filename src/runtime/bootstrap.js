import { createRuntime } from "./engine.js";
import { mountInvestigationUI } from "./investigation-ui.js";
import { loadConfiguredPack } from "./pack-loader.js";

export async function bootstrap() {
  const storyArea = document.querySelector("#storyArea");
  const loadingTemplate = document.querySelector("#loadingTemplate");
  storyArea.innerHTML = "";
  storyArea.appendChild(loadingTemplate.content.cloneNode(true));
  try {
    const pack = await loadConfiguredPack();
    const runtime = createRuntime(pack);
    document.documentElement.dataset.packId = pack.manifest.pack_id;
    document.documentElement.dataset.packVersion = pack.manifest.version;
    document.documentElement.dataset.loopTier = pack.manifest.loop_package.tier;
    mountInvestigationUI(runtime);
    return runtime;
  } catch (error) {
    renderLoadFailure(storyArea, error);
    throw error;
  }
}

function renderLoadFailure(storyArea, error) {
  storyArea.innerHTML = "";
  const card = document.createElement("div");
  card.className = "loading-card";
  const title = document.createElement("h2");
  title.textContent = "内容包无法载入";
  const body = document.createElement("p");
  body.textContent = `请检查 runtime-config.json 与内容包门禁。错误：${error.message}`;
  card.append(title, body);
  storyArea.appendChild(card);
}
