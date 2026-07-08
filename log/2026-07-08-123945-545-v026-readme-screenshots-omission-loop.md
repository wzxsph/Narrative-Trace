# V0.26 README 截图与遗漏路径诚实性收口

开始时间：2026-07-08 12:32:00.974 +0800  
当前记录时间：2026-07-08 12:41:27.480 +0800

## 本轮目标

在用户明确表示“整理好 README，截几张体验截图就差不多”后，停止继续扩新产品切片，把当前工程收口到适合展示和接手的状态。同时修复本轮发现的一个体验诚实性问题：浅层 observe 不应让复盘误报“已解锁未选”。

## 关键节点

- 12:32:00.974：归档 V0.25 PRD/技术文档到 `doc/prd/old version/2026-07-08-123200-974`。
- 12:33-12:35：发现 4 处 `unlocks_choices` 与 choice requirements 不一致的问题。
- 12:34-12:35：修正 deterministic demo 源头，收紧浅层 observe 的 unlock 声明。
- 12:35：`src/app.js` 将章节复盘分支状态区分为 `unlocked` 与 `pending`。
- 12:35：`scripts/content_qa_report.py` 增加 unlock contract。
- 12:35：新增 `scripts/browser_omission_paths.py`，验证遗漏关键线索时 choice 不可见、复盘显示缺失证据。
- 12:36-12:37：截取 4 张真实浏览器体验截图并保存到 `screenshots/`。
- 12:38-12:39：重写 README，补充截图、快速运行、验证命令和产品边界。
- 12:39：同步 PRD、技术文档和产品推衍记录到 V0.26。
- 12:40-12:41：完成完整结构、内容、存档、浏览器、遗漏路径和全结局验证。

## 文件变化

新增：

- `screenshots/01-start-screen.jpg`
- `screenshots/02-observe-unlocks-choice.jpg`
- `screenshots/03-chapter-review-flow.jpg`
- `screenshots/04-ending-portrait.jpg`
- `scripts/browser_omission_paths.py`
- `log/2026-07-08-123945-545-v026-readme-screenshots-omission-loop.md`

修改：

- `README.md`
- `gamegen/demo_agent.py`
- `generated/missing_phone_v0/game.json`
- `generated/missing_phone_v0/game.yaml`
- `generated/missing_phone_v0/path_map.json`
- `scripts/content_qa_report.py`
- `src/app.js`
- `src/styles.css`
- `tests/test_content_qa.py`
- `doc/prd/PRD_V0_文字冒险游戏框架.md`
- `doc/prd/PRD_V0_产品推衍记录.md`
- `doc/prd/agent_game_generation_technical_design_v0.md`

归档：

- `doc/prd/old version/2026-07-08-123200-974/PRD_V0_文字冒险游戏框架.md`
- `doc/prd/old version/2026-07-08-123200-974/PRD_V0_产品推衍记录.md`
- `doc/prd/old version/2026-07-08-123200-974/agent_game_generation_technical_design_v0.md`

## 已完成局部验证

```bash
python3 scripts/content_qa_report.py generated/missing_phone_v0/game.json
python3 -m unittest tests.test_content_qa -v
python3 scripts/browser_omission_paths.py
node --check src/app.js
```

局部结果：

- Content QA 0 error / 0 warning。
- Content QA 单测通过。
- 浏览器遗漏路径回放通过。
- `node --check src/app.js` 通过。

## 完整验证

提交前完整验证矩阵已通过：

```bash
python3 scripts/generate_game.py --brief examples/briefs/missing_phone.json --out generated/missing_phone_v0 --provider offline
python3 scripts/validate_json_schema.py generated/missing_phone_v0/game.json
python3 scripts/validate_game.py generated/missing_phone_v0/game.json
python3 scripts/content_qa_report.py generated/missing_phone_v0/game.json
python3 scripts/repair_game.py generated/missing_phone_v0/game.json
python3 scripts/smoke_playthrough.py generated/missing_phone_v0/game.json
python3 scripts/validate_model_output_archive.py
python3 scripts/validate_save_contract.py
python3 scripts/browser_smoke.py
python3 scripts/browser_save_contract.py
python3 scripts/browser_a11y_smoke.py
python3 scripts/browser_omission_paths.py
python3 scripts/browser_e2e_matrix.py
python3 -m py_compile gamegen/*.py scripts/*.py tests/*.py
node --check src/app.js
python3 -m unittest discover -s tests -v
git diff --check
```

结果：

- JSON Schema、结构 validator、内容 QA、模型输出样本校验、存档合同校验均通过。
- 修复器确认当前生成物无需要修复的目标。
- deterministic smoke playthrough 到达 `ending_publish`。
- 浏览器基础 smoke 通过，覆盖章节复盘、刷新恢复、v1 迁移、损坏/不兼容存档 fallback 和恢复提示。
- 浏览器存档合同回放通过。
- 浏览器可访问性 smoke 通过。
- 浏览器遗漏路径回放通过，确认缺证据时 choice 不出现且复盘显示缺失证据。
- 浏览器三主结局矩阵通过。
- Python 编译、`node --check`、42 个单元测试和 `git diff --check` 均通过。

## 收口判断

本轮达到“先这样”的收口标准：README 可读、体验截图齐全、已知 unlock 误报被修复并有自动化回归。后续继续推进时，应优先组织真实内部 playtest，而不是继续堆自动化脚本。
