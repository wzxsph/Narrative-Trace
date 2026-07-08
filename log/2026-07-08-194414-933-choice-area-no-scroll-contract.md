# 2026-07-08 19:44:14.933 - Choice 区非滚动契约

## 背景

用户明确产品交互原则：选项一般应无需滚动即可查看，背景正文才是需要滚动查看的区域。此前章节复盘曾出现行动选项显示不完整的问题，本轮将该原则固化为 UI 契约与浏览器回归测试。

## 本轮变更

- 在 `src/styles.css` 中为 `.choice-area` 显式设置 `max-height: none`，配合已有 `overflow: visible` 与手机容器 grid 布局，让行动栏按内容自然占用底部高度。
- 在 `scripts/browser_smoke.py` 中新增 `assert_choices_visible_without_scroll`：
  - 校验 choice 区不是内部滚动容器。
  - 校验 choice 区内容高度不超过自身可见高度。
  - 校验所有 `.choice-button` / `.choice-empty` 在移动视口内完整可见。
  - 校验按钮文本没有被裁切。
- 将该断言覆盖到初始场景、observe 解锁前后、章节复盘、复盘恢复、旧存档迁移和存档异常恢复路径。
- 重新构建并部署 Cloudflare Worker。

## 验证

- `python3 scripts/browser_smoke.py`
- `python3 scripts/validate_json_schema.py generated/missing_phone_v0/game.json`
- `python3 scripts/validate_game.py generated/missing_phone_v0/game.json`
- `python3 scripts/smoke_playthrough.py generated/missing_phone_v0/game.json`
- `python3 -m unittest discover -s tests -v`
- `python3 scripts/browser_omission_paths.py`
- `python3 scripts/browser_e2e_matrix.py`
- `python3 scripts/browser_a11y_smoke.py`
- `git diff --check`
- `scripts/build_game_worker_bundle.sh`
- `npx --yes wrangler deploy`
- 远程 Worker mobile smoke：通过

## 部署

- Worker URL: https://game-writer-missing-phone.samsong-1a3.workers.dev/
- Worker Version ID: `5f503208-3e4c-4903-9075-edd9a6d17e73`

## 备注

- 本轮未修改 PRD。
- 产品交互原则更新为：背景正文可滚动，行动选项应完整可见且不做内部滚动。
