# V0.21 坏存档恢复提示迭代

开始时间：2026-07-08 11:51:26.273 +0800  
结束时间：2026-07-08 11:57:54.885 +0800

## 本轮目标

继续执行产品迭代循环。V0.20 已验证坏 JSON / 旧版本存档能 fallback 回首场景，但玩家看不到为什么被重置。本轮补可见恢复提示，避免系统沉默造成“世界突然失忆”的体验断裂。

## 关键节点

- 11:51:26.273：归档 V0.20 PRD/技术文档到 `doc/prd/old version/2026-07-08-115126-273`。
- 11:52-11:53：`src/app.js` 新增 `runtime.recoveryNotice`、`renderRecoveryNotice()` 和两类坏存档提示。
- 11:53：`src/styles.css` 新增 `.recovery-notice` 样式。
- 11:54：`scripts/browser_smoke.py` 增加恢复提示文案检查。
- 11:54：运行 `python3 scripts/browser_smoke.py` 通过。
- 11:55：更新 README、PRD、技术文档、产品推衍记录和测试静态 hook。
- 11:56-11:57：跑完整验证矩阵，所有检查通过。

## 文件变化

修改：

- `src/app.js`
- `src/styles.css`
- `scripts/browser_smoke.py`
- `tests/test_demo_contract.py`
- `README.md`
- `doc/prd/PRD_V0_文字冒险游戏框架.md`
- `doc/prd/PRD_V0_产品推衍记录.md`
- `doc/prd/agent_game_generation_technical_design_v0.md`

新增：

- `log/2026-07-08-115547-875-v021-save-recovery-notice-loop.md`

归档：

- `doc/prd/old version/2026-07-08-115126-273/PRD_V0_文字冒险游戏框架.md`
- `doc/prd/old version/2026-07-08-115126-273/PRD_V0_产品推衍记录.md`
- `doc/prd/old version/2026-07-08-115126-273/agent_game_generation_technical_design_v0.md`

## 已完成验证

局部验证已通过：

```bash
python3 scripts/browser_smoke.py
```

结果：

- 坏 JSON 存档 fallback 后显示“旧进度内容损坏，已为你开启新局。”
- 旧版本/不兼容存档 fallback 后显示“旧进度与当前案件不兼容，已为你开启新局。”

完整验证命令：

```bash
python3 scripts/generate_game.py --brief examples/briefs/missing_phone.json --out generated/missing_phone_v0 --provider offline
python3 scripts/validate_json_schema.py generated/missing_phone_v0/game.json
python3 scripts/validate_game.py generated/missing_phone_v0/game.json
python3 scripts/content_qa_report.py generated/missing_phone_v0/game.json
python3 scripts/repair_game.py generated/missing_phone_v0/game.json
python3 scripts/smoke_playthrough.py generated/missing_phone_v0/game.json
python3 scripts/validate_model_output_archive.py
python3 scripts/browser_smoke.py
python3 scripts/browser_e2e_matrix.py
python3 -m py_compile gamegen/*.py scripts/*.py tests/*.py
node --check src/app.js
python3 -m unittest discover -s tests -v
git diff --check
```

全部通过。单元测试当前为 37 个。

## 产品判断

V0.21 把坏存档 fallback 从“技术上不卡死”推进到“玩家能理解为什么重置”。这仍不是完整存档系统，但补上了最低限度的信任交代。

仍未解决：

- 存档版本迁移。
- 多存档、云同步和损坏存档备份。
- 错误报告或坏存档导出。

## 待补验证

本轮工程验证已完成。后续仍需：

- 存档版本迁移策略。
- 多存档、云同步和损坏存档备份。
- 错误报告或坏存档导出。
