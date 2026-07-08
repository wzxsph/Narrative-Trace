# V0.24 浏览器存档合同回放迭代

开始时间：2026-07-08 12:16:17.980 +0800  
结束时间：2026-07-08 12:20:16.141 +0800

## 本轮目标

继续执行产品迭代循环。V0.23 有了存档合同 fixture 和 Python 校验门禁，但还没有逐条经过真实浏览器 runtime。本轮新增浏览器存档合同回放，验证合同样本在真实 UI 中恢复或 fallback。

## 关键节点

- 12:16:17.980：归档 V0.23 PRD/技术文档到 `doc/prd/old version/2026-07-08-121617-980`。
- 12:17 左右：新增 `scripts/browser_save_contract.py`。
- 12:17：运行 `python3 scripts/browser_save_contract.py` 通过。
- 12:18：更新 README、PRD、技术文档和产品推衍记录到 V0.24。
- 12:19-12:20：跑完整验证矩阵，所有检查通过。

## 文件变化

新增：

- `scripts/browser_save_contract.py`
- `log/2026-07-08-121831-533-v024-browser-save-contract-loop.md`

修改：

- `README.md`
- `doc/prd/PRD_V0_文字冒险游戏框架.md`
- `doc/prd/PRD_V0_产品推衍记录.md`
- `doc/prd/agent_game_generation_technical_design_v0.md`

归档：

- `doc/prd/old version/2026-07-08-121617-980/PRD_V0_文字冒险游戏框架.md`
- `doc/prd/old version/2026-07-08-121617-980/PRD_V0_产品推衍记录.md`
- `doc/prd/old version/2026-07-08-121617-980/agent_game_generation_technical_design_v0.md`

## 已完成验证

局部验证已通过：

```bash
python3 scripts/browser_save_contract.py
```

结果：

- `v1_chapter_review_migrates`: review
- `v2_publish_ending_restores`: ending
- `future_version_falls_back`: fallback
- `corrupt_json_falls_back`: fallback

完整验证命令：

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
python3 scripts/browser_e2e_matrix.py
python3 -m py_compile gamegen/*.py scripts/*.py tests/*.py
node --check src/app.js
python3 -m unittest discover -s tests -v
git diff --check
```

全部通过。单元测试当前为 41 个。

## 产品判断

V0.24 把存档合同从“文件层成立”推进到“真实浏览器 runtime 成立”。这能减少未来迁移样本与玩家端恢复逻辑之间的错位。

仍未解决：

- 多浏览器和真实设备回放。
- 更大规模 save fixture 覆盖。
- 多存档、云同步、坏存档导出或错误报告。

## 待补验证

本轮工程验证已完成。后续仍需：

- 多浏览器和真实设备回放。
- 更大规模 save fixture 覆盖。
- 多存档、云同步、坏存档导出或错误报告。
