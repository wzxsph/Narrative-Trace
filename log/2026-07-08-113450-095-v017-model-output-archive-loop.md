# V0.17 模型输出样本归档合同迭代

开始时间：2026-07-08 11:30:03.355 +0800  
结束时间：2026-07-08 11:36:09.356 +0800

## 本轮目标

继续执行产品迭代循环。本轮聚焦 V0.16 之后的主要缺口：真实模型输出样本尚未可追溯。由于当前没有可安全提交的真实 provider response，本轮先建立样本归档合同和脱敏工具，不伪造真实样本。

## 关键节点

- 11:30:03.355：归档 V0.16 PRD/技术文档到 `doc/prd/old version/2026-07-08-113003-355`。
- 11:31 左右：梳理现有 `prompts/manifest.json`、`generation_trace.jsonl`、失败 fixture 与 prompt manifest 测试。
- 11:32 左右：`gamegen/demo_agent.py` 为 generation metadata 和 trace 增加 `model`。
- 11:32-11:33：新增模型输出样本归档模块和 CLI。
- 11:33-11:34：新增模型输出样本空 manifest、README 和脱敏/归档测试。
- 11:34：更新 README、PRD、技术文档和产品推衍记录到 V0.17。
- 11:35-11:36：跑完整验证矩阵，所有检查通过。

## 文件变化

新增：

- `gamegen/model_output_archive.py`
- `scripts/archive_model_output_sample.py`
- `examples/fixtures/model_outputs/README.md`
- `examples/fixtures/model_outputs/sample_manifest.json`
- `tests/test_model_output_archive.py`
- `log/2026-07-08-113450-095-v017-model-output-archive-loop.md`

修改：

- `gamegen/demo_agent.py`
- `gamegen/prompt_manifest.py`
- `tests/test_prompt_manifest.py`
- `README.md`
- `doc/prd/PRD_V0_文字冒险游戏框架.md`
- `doc/prd/PRD_V0_产品推衍记录.md`
- `doc/prd/agent_game_generation_technical_design_v0.md`

归档：

- `doc/prd/old version/2026-07-08-113003-355/PRD_V0_文字冒险游戏框架.md`
- `doc/prd/old version/2026-07-08-113003-355/PRD_V0_产品推衍记录.md`
- `doc/prd/old version/2026-07-08-113003-355/agent_game_generation_technical_design_v0.md`

## 已完成验证

局部验证已通过：

```bash
python3 -m unittest tests.test_model_output_archive -v
python3 -m unittest tests.test_prompt_manifest -v
python3 -m py_compile gamegen/model_output_archive.py scripts/archive_model_output_sample.py
```

完整验证命令：

```bash
python3 scripts/generate_game.py --brief examples/briefs/missing_phone.json --out generated/missing_phone_v0 --provider offline
python3 scripts/validate_json_schema.py generated/missing_phone_v0/game.json
python3 scripts/validate_game.py generated/missing_phone_v0/game.json
python3 scripts/content_qa_report.py generated/missing_phone_v0/game.json
python3 scripts/repair_game.py generated/missing_phone_v0/game.json
python3 scripts/smoke_playthrough.py generated/missing_phone_v0/game.json
python3 scripts/browser_smoke.py
python3 scripts/browser_e2e_matrix.py
python3 -m py_compile gamegen/*.py scripts/*.py tests/*.py
node --check src/app.js
python3 -m unittest discover -s tests -v
git diff --check
```

全部通过。

生成 trace 已确认包含：

```json
{"trace_schema_version":"generation_trace_v0_2","provider":"offline","model":"deterministic_demo_v0","prompt_set":"demo_agent_v0_15"}
```

## 产品判断

V0.17 解决的是“真实模型输出样本进入项目之前的合同”：

- 样本必须带 `provider`、`model`、`prompt_set`、`source`、`schema`。
- 样本必须先脱敏，再进入 `examples/fixtures/model_outputs`。
- generation trace 现在记录 `provider`、`model`、`prompt_set`，未来可以把样本与生成策略关联起来。

这不是完整 agent 生产能力。当前样本库仍为空，后续必须接入真实 provider response，并把样本与 schema/validator/repair/content QA 的结果关联起来。

## 待补验证

本轮工程验证已完成。后续仍需：

- 用归档工具沉淀首批真实 provider response。
- 将真实样本与 schema/validator/repair/content QA 结果关联。
- 扩展脱敏规则，覆盖未来可能出现的手机号、真实姓名、私有 URL 等敏感信息。
