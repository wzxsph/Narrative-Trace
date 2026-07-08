# V0.19 结局恢复与重开 E2E 迭代

开始时间：2026-07-08 11:42:02.185 +0800  
结束时间：2026-07-08 11:45:20.827 +0800

## 本轮目标

继续执行产品迭代循环。V0.16 已证明三主结局可达，但还没有证明结局态能刷新恢复，也没有证明“重新开始”能清掉旧路径。本轮把这两个结束态能力加入多结局浏览器 E2E。

## 关键节点

- 11:42:02.185：归档 V0.18 PRD/技术文档到 `doc/prd/old version/2026-07-08-114202-185`。
- 11:42-11:43：扩展 `scripts/browser_e2e_matrix.py`，新增结局断言、结局刷新恢复断言和结局重开断言。
- 11:43：运行 `python3 scripts/browser_e2e_matrix.py` 通过，三条结局路径均显示 `restored, restart`。
- 11:43：更新 README、PRD、技术文档和产品推衍记录到 V0.19。
- 11:44-11:45：跑完整验证矩阵，所有检查通过。

## 文件变化

修改：

- `scripts/browser_e2e_matrix.py`
- `README.md`
- `doc/prd/PRD_V0_文字冒险游戏框架.md`
- `doc/prd/PRD_V0_产品推衍记录.md`
- `doc/prd/agent_game_generation_technical_design_v0.md`

新增：

- `log/2026-07-08-114358-409-v019-ending-persistence-restart-loop.md`

归档：

- `doc/prd/old version/2026-07-08-114202-185/PRD_V0_文字冒险游戏框架.md`
- `doc/prd/old version/2026-07-08-114202-185/PRD_V0_产品推衍记录.md`
- `doc/prd/old version/2026-07-08-114202-185/agent_game_generation_technical_design_v0.md`

## 已完成验证

局部验证已通过：

```bash
python3 scripts/browser_e2e_matrix.py
```

结果：

- `ending_publish`：公开的真相，restored, restart。
- `ending_bury`：沉默的备份，restored, restart。
- `ending_confront`：被迫摊牌，restored, restart。

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

V0.19 把三主结局从“能到达”推进到“正常结束态可恢复、可清除”。这对“世界记住玩家”的体验承诺很重要：结局不能只是一次渲染成功的截图，刷新后也应该还原；重开后也不应残留旧路径。

仍未解决：

- 损坏存档。
- 多存档。
- 版本迁移。
- 真实设备、多浏览器和无障碍。

## 待补验证

本轮工程验证已完成。后续仍需：

- 损坏存档处理。
- 多存档和版本迁移。
- 多浏览器、真实设备和无障碍验收。
