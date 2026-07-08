# 2026-07-08 19:54:14.294 - README 渲染式流程图图片

## 背景

用户澄清 README 中的 HTML 流程图应理解为：先用 HTML/CSS 绘制流程图，再渲染生成图片放入 README，而不是直接把 HTML 流程表嵌在 README 中。

## 本轮变更

- 新增 `doc/readme_diagrams/readme_diagrams.html`：
  - 使用纸墨风格 HTML/CSS 绘制 README 流程图源文件。
  - 包含 `game-loop`、`interaction-map`、`runtime-architecture`、`ai-pipeline`、`release-gates`、`state-ending-map`、`product-boundary` 七张图。
- 新增 `scripts/render_readme_diagrams.py`：
  - 使用本地 Chrome/Chromium + Playwright 渲染 HTML。
  - 将指定 diagram 节点截图输出到 `screenshots/readme-diagrams/`。
- 新增 README 流程图图片：
  - `screenshots/readme-diagrams/game-loop.png`
  - `screenshots/readme-diagrams/interaction-map.png`
  - `screenshots/readme-diagrams/runtime-architecture.png`
  - `screenshots/readme-diagrams/ai-pipeline.png`
  - `screenshots/readme-diagrams/release-gates.png`
  - `screenshots/readme-diagrams/state-ending-map.png`
  - `screenshots/readme-diagrams/product-boundary.png`
- 更新 `README.md`：
  - 将原本直接嵌入的 HTML table 流程图替换为 PNG 图片引用。
  - 保留图源路径和重新生成命令。

## 验证

- `python3 scripts/render_readme_diagrams.py`
- README 图片引用完整性检查：通过。
- `git diff --check`

## 备注

- 本轮未修改 PRD。
- 本轮未部署 Worker，因为只更新 README、文档图源、渲染脚本和图片资产。
