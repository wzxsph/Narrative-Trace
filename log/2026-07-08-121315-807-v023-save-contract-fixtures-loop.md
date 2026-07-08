# V0.23 存档合同 Fixture 迭代

开始时间：2026-07-08 12:07:55.937 +0800  
结束时间：2026-07-08 12:15:13.861 +0800

## 本轮目标

继续执行产品迭代循环。V0.22 有了存档迁移骨架，但迁移样本仍只存在于浏览器 smoke 的临时构造中。本轮把典型存档状态沉淀成 fixture 合同，并增加独立校验门禁。

## 关键节点

- 12:07:55.937：归档 V0.22 PRD/技术文档到 `doc/prd/old version/2026-07-08-120755-937`。
- 12:09 左右：新增 `examples/fixtures/save_contract/save_cases.json`。
- 12:10 左右：新增 `gamegen/save_contract.py`，提供迁移模拟、payload 校验和 fallback 预期校验。
- 12:10 左右：新增 `scripts/validate_save_contract.py`。
- 12:11 左右：新增 `tests/test_save_contract.py`。
- 12:11：聚焦验证 `python3 scripts/validate_save_contract.py`、`python3 -m unittest tests.test_save_contract -v`、`python3 -m py_compile ...` 通过。
- 12:12-12:13：更新 README、PRD、技术文档和产品推衍记录到 V0.23。
- 12:14-12:15：跑完整验证矩阵，所有检查通过。

## 文件变化

新增：

- `examples/fixtures/save_contract/save_cases.json`
- `gamegen/save_contract.py`
- `scripts/validate_save_contract.py`
- `tests/test_save_contract.py`
- `log/2026-07-08-121315-807-v023-save-contract-fixtures-loop.md`

修改：

- `README.md`
- `doc/prd/PRD_V0_文字冒险游戏框架.md`
- `doc/prd/PRD_V0_产品推衍记录.md`
- `doc/prd/agent_game_generation_technical_design_v0.md`

归档：

- `doc/prd/old version/2026-07-08-120755-937/PRD_V0_文字冒险游戏框架.md`
- `doc/prd/old version/2026-07-08-120755-937/PRD_V0_产品推衍记录.md`
- `doc/prd/old version/2026-07-08-120755-937/agent_game_generation_technical_design_v0.md`

## 已完成验证

局部验证已通过：

```bash
python3 scripts/validate_save_contract.py
python3 -m unittest tests.test_save_contract -v
python3 -m py_compile gamegen/save_contract.py scripts/validate_save_contract.py tests/test_save_contract.py
```

结果：

- 当前 save contract fixture 通过。
- 坏 scene 引用、重复 case id、fallback 缺恢复提示都会失败。

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
python3 scripts/browser_e2e_matrix.py
python3 -m py_compile gamegen/*.py scripts/*.py tests/*.py
node --check src/app.js
python3 -m unittest discover -s tests -v
git diff --check
```

全部通过。单元测试当前为 41 个。

## 产品判断

V0.23 把“存档迁移必须兼容哪些旧状态”从临时测试逻辑提升为可审计合同。以后新增字段级迁移时，应该先新增旧存档样本，再实现迁移。

仍未解决：

- 复杂字段迁移和迁移链。
- 浏览器逐条注入所有 save contract fixture。
- 多存档、云同步、坏存档导出或错误报告。

## 待补验证

本轮工程验证已完成。后续仍需：

- 复杂字段迁移和迁移链。
- 浏览器逐条注入所有 save contract fixture。
- 多存档、云同步、坏存档导出或错误报告。
