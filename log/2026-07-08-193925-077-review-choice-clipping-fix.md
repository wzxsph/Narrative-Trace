# Iteration Log: Chapter Review Choice Clipping Fix

开始时间：2026-07-08 19:24:00.000 +0800  
结束时间：2026-07-08 19:39:25.077 +0800

## 本次迭代

- 修复章节复盘中选项/分支有时只显示一半的问题。
- 根因：
  - `outcomePanel` 使用 `hidden` 后退出 grid 自动排布。
  - `storyArea` 在复盘页占错 grid 行，把底部继续按钮推到视口外。
  - 复盘路径图分支在移动端纵向占用过高，容易在 story 滚动区底部露出半截。
- 修复：
  - 为 `.status-bar`、`.task-strip`、`.outcome-panel`、`.story-area`、`.choice-area` 显式设置 grid row。
  - 移动端章节复盘路径图改为更紧凑的双列分支布局。
  - 压缩复盘节点间距、字体和连接线高度，确保首屏复盘路径图不再露半截分支。
  - 增加 browser smoke 断言，检查复盘分支文本不被裁切，且不会被底部行动栏遮住。

## 验证

- `python3 scripts/validate_json_schema.py generated/missing_phone_v0/game.json`
- `python3 scripts/validate_game.py generated/missing_phone_v0/game.json`
- `python3 scripts/smoke_playthrough.py generated/missing_phone_v0/game.json`
- `python3 scripts/browser_smoke.py`
- `python3 scripts/browser_omission_paths.py`
- `python3 scripts/browser_e2e_matrix.py`
- `python3 scripts/browser_a11y_smoke.py`
- `python3 scripts/browser_save_contract.py`
- `python3 -m unittest discover -s tests -v`
- `scripts/build_game_worker_bundle.sh`
- `npx --yes wrangler deploy --dry-run`
- `npx --yes wrangler deploy`
- 远程复盘裁切 smoke：
  - 线上复盘页继续按钮完整可见。
  - 所有 `.flow-branches li` 均无 `scrollHeight/clientHeight` 或 `scrollWidth/clientWidth` 裁切。
  - 所有复盘分支均未落到底部行动栏后方。

## 结果

- 本地单测：81 tests passed。
- Cloudflare Worker 已部署：
  - URL: `https://game-writer-missing-phone.samsong-1a3.workers.dev/`
  - Version ID: `e14a452a-310d-4a69-b564-52c00a6ab71f`
