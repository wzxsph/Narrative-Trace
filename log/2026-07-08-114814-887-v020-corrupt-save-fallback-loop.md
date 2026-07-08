# V0.20 坏存档 fallback 浏览器验证迭代

开始时间：2026-07-08 11:46:44.796 +0800  
结束时间：2026-07-08 11:49:38.833 +0800

## 本轮目标

继续执行产品迭代循环。V0.19 验证了正常结局态刷新恢复和重开；V0.20 补坏存档 fallback 的浏览器回归，避免损坏 localStorage 把玩家卡死在故事外。

## 关键节点

- 11:46:44.796：归档 V0.19 PRD/技术文档到 `doc/prd/old version/2026-07-08-114644-796`。
- 11:47：扩展 `scripts/browser_smoke.py`，注入坏 JSON 存档和旧版本存档。
- 11:47：运行 `python3 scripts/browser_smoke.py` 通过，输出 `corrupt_save_recovered: True` 和 `invalid_save_recovered: True`。
- 11:47-11:48：更新 README、PRD、技术文档和产品推衍记录到 V0.20。
- 11:48-11:49：跑完整验证矩阵，所有检查通过。

## 文件变化

修改：

- `scripts/browser_smoke.py`
- `README.md`
- `doc/prd/PRD_V0_文字冒险游戏框架.md`
- `doc/prd/PRD_V0_产品推衍记录.md`
- `doc/prd/agent_game_generation_technical_design_v0.md`

新增：

- `log/2026-07-08-114814-887-v020-corrupt-save-fallback-loop.md`

归档：

- `doc/prd/old version/2026-07-08-114644-796/PRD_V0_文字冒险游戏框架.md`
- `doc/prd/old version/2026-07-08-114644-796/PRD_V0_产品推衍记录.md`
- `doc/prd/old version/2026-07-08-114644-796/agent_game_generation_technical_design_v0.md`

## 已完成验证

局部验证已通过：

```bash
python3 scripts/browser_smoke.py
```

结果：

- `corrupt_save_recovered: True`
- `invalid_save_recovered: True`

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

V0.20 先补坏存档最低线：坏 JSON 或旧版本 localStorage 不应让玩家白屏或卡死，而应该 fallback 回首场景。这不等于完整存档系统，但能避免技术状态阻断玩家重新进入故事。

仍未解决：

- 可见的损坏存档提示。
- 存档版本迁移。
- 多存档、云同步和损坏存档备份。

## 待补验证

本轮工程验证已完成。后续仍需：

- 可见的损坏存档提示。
- 存档迁移策略。
- 多存档与云同步。
