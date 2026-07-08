# V0.18 模型输出样本库校验门禁迭代

开始时间：2026-07-08 11:37:13.481 +0800  
结束时间：2026-07-08 11:41:07.901 +0800

## 本轮目标

继续执行产品迭代循环。V0.17 建立了模型输出样本归档/脱敏入口，但还缺少提交前校验门禁。本轮目标是确保未来样本库不会出现 manifest 悬空、checksum 漂移、未脱敏敏感信息或 prompt_set 失效。

## 关键节点

- 11:37:13.481：归档 V0.17 PRD/技术文档到 `doc/prd/old version/2026-07-08-113713-481`。
- 11:37-11:38：`gamegen/model_output_archive.py` 增加 `validate_model_output_archive()`。
- 11:38：新增 `scripts/validate_model_output_archive.py`。
- 11:38-11:39：扩展 `tests/test_model_output_archive.py`，覆盖空 manifest、正常归档样本和被篡改样本。
- 11:39：更新 README、PRD、技术文档和产品推衍记录到 V0.18。
- 11:40-11:41：跑完整验证矩阵，所有检查通过。

## 文件变化

新增：

- `scripts/validate_model_output_archive.py`
- `log/2026-07-08-113951-279-v018-model-output-archive-validation-loop.md`

修改：

- `gamegen/model_output_archive.py`
- `tests/test_model_output_archive.py`
- `README.md`
- `doc/prd/PRD_V0_文字冒险游戏框架.md`
- `doc/prd/PRD_V0_产品推衍记录.md`
- `doc/prd/agent_game_generation_technical_design_v0.md`

归档：

- `doc/prd/old version/2026-07-08-113713-481/PRD_V0_文字冒险游戏框架.md`
- `doc/prd/old version/2026-07-08-113713-481/PRD_V0_产品推衍记录.md`
- `doc/prd/old version/2026-07-08-113713-481/agent_game_generation_technical_design_v0.md`

## 已完成验证

局部验证已通过：

```bash
python3 -m unittest tests.test_model_output_archive -v
python3 scripts/validate_model_output_archive.py
python3 -m py_compile gamegen/model_output_archive.py scripts/validate_model_output_archive.py tests/test_model_output_archive.py
```

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

V0.18 让模型输出样本库从“可归档”变成“可校验”。这不是为了多一层流程，而是为了防止样本库成为新的污染源：悬空文件、路径越界、失效 prompt_set、checksum 漂移和未脱敏敏感信息。

仍未解决：

- 样本库仍没有真实 provider response。
- 校验门禁不判断样本是否代表重要失败。
- 脱敏规则仍需随真实样本继续扩展。

## 待补验证

本轮工程验证已完成。后续仍需：

- 归档首批真实 provider response。
- 为真实样本生成 gate 结果报告。
- 持续扩展脱敏规则。
