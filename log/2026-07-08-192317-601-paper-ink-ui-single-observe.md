# Iteration Log: Paper Ink UI and Single Observe Chain

开始时间：2026-07-08 18:50:00.000 +0800  
结束时间：2026-07-08 19:23:17.601 +0800

## 本次迭代

- 将玩家端 UI 调整为极简纸张/墨水风格。
- 将 observe 展开逻辑改为“当前场景只显示一条观察链”。
- 保留 `openedAnchors` 作为历史记录，不改变状态效果、choice 解锁、路径图、章节复盘和结局画像。
- 新增 `activeAnchorPathByScene` 作为只控制 UI 展示的当前 observe 链。
- 重构 choice 区域为更紧凑的纸条式行动栏，避免少量选项时被拉成大块、多选项时过度拥挤。
- 更新 browser smoke，覆盖 sibling observe 切换和 nested observe 单链展示。

## 修改文件

- `src/app.js`
- `src/styles.css`
- `scripts/browser_smoke.py`
- `tests/test_demo_contract.py`

## 验证

- `node --check src/app.js`
- `python3 -m py_compile scripts/browser_smoke.py`
- `python3 scripts/validate_json_schema.py generated/missing_phone_v0/game.json`
- `python3 scripts/validate_game.py generated/missing_phone_v0/game.json`
- `python3 scripts/smoke_playthrough.py generated/missing_phone_v0/game.json`
- `python3 -m unittest discover -s tests -v`
- `python3 scripts/browser_smoke.py`
- `python3 scripts/browser_omission_paths.py`
- `python3 scripts/browser_e2e_matrix.py`
- `python3 scripts/browser_a11y_smoke.py`
- `python3 scripts/validate_save_contract.py`
- `python3 scripts/browser_save_contract.py`
- `scripts/build_game_worker_bundle.sh`
- `npx --yes wrangler deploy --dry-run`
- `npx --yes wrangler deploy`
- 远程 smoke：
  - 打开 `https://game-writer-missing-phone.samsong-1a3.workers.dev/`
  - 点击 `未发送短信` 后只显示一个顶层 observe card。
  - 点击 sibling `远程清除` 后旧 observe card 收起。
  - 点击 nested `02:13` 后只显示 `obs_unsent_sms -> obs_0213_log` 当前链。
  - 已解锁 `前往废弃地铁站` 保持可用，并成功进入 `云端控制台`。

## 结果

- 本地单测：81 tests passed。
- 三条浏览器主结局路径通过。
- 存档迁移、坏存档 fallback、键盘/a11y smoke 均通过。
- Cloudflare Worker 已部署：
  - URL: `https://game-writer-missing-phone.samsong-1a3.workers.dev/`
  - Version ID: `38f8193f-2ce3-412e-8ea7-3ad8f744fa92`

## 遗留问题

- 当前纸墨风格未引入纹理图片或外部字体，保持轻量；如果后续追求更强品牌感，可单独做视觉资产迭代。
