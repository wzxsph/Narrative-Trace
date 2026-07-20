export function renderSceneSurfaces(scene, options) {
  const fragment = document.createDocumentFragment();
  for (const surface of scene.surfaces || []) {
    fragment.appendChild(renderSurface(surface, options, 1, true));
  }
  return fragment;
}

export function collectAnchors(scene) {
  const collected = [];
  for (const surface of scene.surfaces || []) {
    collectFromSurface(surface, 1, collected);
  }
  return collected;
}

export function findAnchorPath(scene, anchorId) {
  for (const surface of scene.surfaces || []) {
    const path = findInSurface(surface, anchorId, []);
    if (path.length) {
      return path;
    }
  }
  return [];
}

function renderSurface(surface, options, depth, topLevel = false) {
  const wrapper = document.createElement(topLevel ? "article" : "div");
  wrapper.className = topLevel ? "background-block" : "fragment-surface";
  wrapper.dataset.surfaceId = surface.id;
  wrapper.dataset.surfaceType = surface.type;

  if (surface.type === "text") {
    wrapper.appendChild(renderTextWithAnchors(surface.content.text, surface.anchors || [], options));
  } else {
    wrapper.appendChild(renderFallbackSurface(surface, options));
  }

  const activeAnchorId = options.activePath[depth - 1];
  const activeAnchor = (surface.anchors || []).find((anchor) => anchor.id === activeAnchorId);
  if (activeAnchor) {
    wrapper.appendChild(renderFragment(activeAnchor, options, depth));
  }
  return wrapper;
}

function renderTextWithAnchors(text, anchors, options) {
  const fragment = document.createDocumentFragment();
  const ranges = [];
  for (const anchor of anchors) {
    const locator = anchor.locator || {};
    if (locator.kind !== "text") {
      continue;
    }
    const index = nthIndexOf(text, locator.exact, locator.occurrence || 1);
    if (index >= 0) {
      ranges.push({ index, end: index + locator.exact.length, anchor });
    }
  }
  ranges.sort((left, right) => left.index - right.index || left.end - right.end);

  let cursor = 0;
  for (const range of ranges) {
    if (range.index < cursor) {
      continue;
    }
    fragment.append(document.createTextNode(text.slice(cursor, range.index)));
    fragment.appendChild(makeAnchorButton(range.anchor, text.slice(range.index, range.end), options));
    cursor = range.end;
  }
  fragment.append(document.createTextNode(text.slice(cursor)));
  return fragment;
}

function renderFallbackSurface(surface, options) {
  const fallback = document.createElement("section");
  fallback.className = "surface-fallback";
  fallback.dataset.fallbackFor = surface.type;
  const label = document.createElement("p");
  label.className = "surface-fallback-label";
  label.textContent = surface.type === "image" ? "图像内容（文本替代）" : "HTML 内容（安全文本替代）";
  const body = document.createElement("p");
  body.className = "surface-fallback-body";
  body.textContent = surface.fallback?.text || "该媒介在当前运行时不可用。";
  fallback.append(label, body);

  if ((surface.anchors || []).length) {
    const actions = document.createElement("div");
    actions.className = "fallback-anchors";
    for (const anchor of surface.anchors) {
      actions.appendChild(makeAnchorButton(anchor, anchor.label, options));
    }
    fallback.appendChild(actions);
  }
  return fallback;
}

function makeAnchorButton(anchor, text, options) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "anchor-button";
  if (options.openedAnchors.has(anchor.id)) {
    button.classList.add("opened");
  }
  if (options.activePath.includes(anchor.id)) {
    button.classList.add("active");
  }
  button.dataset.anchorId = anchor.id;
  button.textContent = text;
  button.title = anchor.label;
  button.addEventListener("click", () => options.onOpenAnchor(anchor));
  return button;
}

function renderFragment(anchor, options, depth) {
  const fragment = anchor.fragment;
  const card = document.createElement("section");
  card.className = `evidence-card depth-${depth}`;
  card.dataset.anchorId = anchor.id;

  const title = document.createElement("h3");
  title.textContent = fragment.title;
  card.appendChild(title);
  for (const surface of fragment.surfaces || []) {
    card.appendChild(renderSurface(surface, options, depth + 1));
  }
  if (fragment.evidence_tags?.length) {
    const tags = document.createElement("div");
    tags.className = "evidence-tags";
    for (const tag of fragment.evidence_tags) {
      const tagNode = document.createElement("span");
      tagNode.className = "tag";
      tagNode.textContent = tag;
      tags.appendChild(tagNode);
    }
    card.appendChild(tags);
  }
  return card;
}

function collectFromSurface(surface, depth, output) {
  for (const anchor of surface.anchors || []) {
    output.push({ anchor, depth });
    for (const childSurface of anchor.fragment?.surfaces || []) {
      collectFromSurface(childSurface, depth + 1, output);
    }
  }
}

function findInSurface(surface, anchorId, parents) {
  for (const anchor of surface.anchors || []) {
    const path = [...parents, anchor.id];
    if (anchor.id === anchorId) {
      return path;
    }
    for (const childSurface of anchor.fragment?.surfaces || []) {
      const nested = findInSurface(childSurface, anchorId, path);
      if (nested.length) {
        return nested;
      }
    }
  }
  return [];
}

function nthIndexOf(text, exact, occurrence) {
  let from = 0;
  let index = -1;
  for (let count = 0; count < occurrence; count += 1) {
    index = text.indexOf(exact, from);
    if (index < 0) {
      return -1;
    }
    from = index + exact.length;
  }
  return index;
}
