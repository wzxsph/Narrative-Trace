# V0.22 存档版本迁移骨架迭代

开始时间：2026-07-08 11:59:13.183 +0800  
结束时间：2026-07-08 12:05:29.457 +0800

## 本轮目标

继续执行产品迭代循环。V0.21 有了坏存档恢复提示，但版本升级仍可能把旧玩家的可用进度直接判为不兼容。本轮建立最小存档迁移骨架，让 v1 存档可以迁移到 v2。

## 关键节点

- 11:59:13.183：归档 V0.21 PRD/技术文档到 `doc/prd/old version/2026-07-08-115913-183`。
- 12:00 左右：`src/app.js` 将 `SAVE_VERSION` 升到 2。
- 12:00 左右：新增 `migrateSavePayload()`，支持 v1 payload 升级到 v2。
- 12:01 左右：`scripts/browser_smoke.py` 增加 v1 章节复盘存档迁移检查。
- 12:01：聚焦验证 `python3 scripts/browser_smoke.py`、`python3 -m unittest tests.test_demo_contract -v`、`node --check src/app.js` 通过。
- 12:02-12:03：更新 README、PRD、技术文档和产品推衍记录到 V0.22。
- 12:04-12:05：跑完整验证矩阵，所有检查通过。

## 文件变化

修改：

- `src/app.js`
- `scripts/browser_smoke.py`
- `tests/test_demo_contract.py`
- `README.md`
- `doc/prd/PRD_V0_文字冒险游戏框架.md`
- `doc/prd/PRD_V0_产品推衍记录.md`
- `doc/prd/agent_game_generation_technical_design_v0.md`

新增：

- `log/2026-07-08-120331-220-v022-save-migration-skeleton-loop.md`

归档：

- `doc/prd/old version/2026-07-08-115913-183/PRD_V0_文字冒险游戏框架.md`
- `doc/prd/old version/2026-07-08-115913-183/PRD_V0_产品推衍记录.md`
- `doc/prd/old version/2026-07-08-115913-183/agent_game_generation_technical_design_v0.md`

## 已完成验证

局部验证已通过：

```bash
python3 scripts/browser_smoke.py
python3 -m unittest tests.test_demo_contract -v
node --check src/app.js
```

结果：

- v1 章节复盘存档刷新后仍恢复复盘页。
- 坏 JSON 和不兼容版本仍 fallback 并显示恢复提示。

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

V0.22 把存档版本号从“判死刑开关”推进为“先迁移再校验”的入口。当前只是 v1 到 v2 的最小迁移骨架，但它保护了已有本地进度不被版本号变化直接清掉。

仍未解决：

- 字段级复杂迁移。
- 存档合同 fixture。
- 多存档、云同步和坏存档导出。

## 待补验证

本轮工程验证已完成。后续仍需：

- 字段级复杂迁移。
- 存档合同 fixture。
- 多存档、云同步和坏存档导出。
