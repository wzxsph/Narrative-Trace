# Iteration Log: V0.13 Export Schema Gate Loop

Start: 2026-07-08 10:59:17.784 +0800
End: 2026-07-08 11:03:19.413 +0800

## Summary

- 按循环规则，在更新 PRD/技术文档前归档 V0.12 到 `doc/prd/old version/2026-07-08-105917-784`。
- 将当前 PRD、产品推衍记录和技术文档版本从 `V0.12` 迭代到 `V0.13`。
- 新增 `gamegen/schema_contract.py`，让生成器、CLI 和测试共享 JSON Schema 校验逻辑。
- `export_game()` 现在会在写 artifact 前运行 JSON Schema 和 `validate_game()`；有 error 时阻断导出。
- `generation_trace.jsonl` 增加 schema contract 记录。
- 新增 `tests/test_export_contract.py`，覆盖正常导出和坏数据阻断写文件。

## Files Changed

- `README.md`
- `doc/prd/PRD_V0_文字冒险游戏框架.md`
- `doc/prd/PRD_V0_产品推衍记录.md`
- `doc/prd/agent_game_generation_technical_design_v0.md`
- `doc/prd/old version/2026-07-08-105917-784/PRD_V0_文字冒险游戏框架.md`
- `doc/prd/old version/2026-07-08-105917-784/PRD_V0_产品推衍记录.md`
- `doc/prd/old version/2026-07-08-105917-784/agent_game_generation_technical_design_v0.md`
- `gamegen/demo_agent.py`
- `gamegen/schema_contract.py`
- `generated/missing_phone_v0/generation_trace.jsonl`
- `scripts/validate_json_schema.py`
- `tests/test_export_contract.py`
- `tests/test_json_schema_contract.py`

## Verification

- `python3 scripts/generate_game.py --brief examples/briefs/missing_phone.json --out generated/missing_phone_v0 --provider offline`
- `python3 scripts/validate_json_schema.py generated/missing_phone_v0/game.json`
- `python3 scripts/validate_game.py generated/missing_phone_v0/game.json`
- `python3 scripts/content_qa_report.py generated/missing_phone_v0/game.json`
- `python3 scripts/repair_game.py generated/missing_phone_v0/game.json`
- `python3 -m unittest tests.test_export_contract tests.test_json_schema_contract -v`
- `python3 scripts/smoke_playthrough.py generated/missing_phone_v0/game.json`
- `python3 scripts/browser_smoke.py`
- `python3 -m py_compile gamegen/*.py scripts/*.py tests/*.py`
- `node --check src/app.js`
- `python3 -m unittest discover -s tests -v`

## Product Assessment

- 本轮解决的是“schema 可手动跑，但生成导出仍可能绕过合同”的问题。
- V0.13 把硬合同前移到 artifact 写入前，减少坏生成物污染输出目录的风险。
- content QA 仍保持独立，因为它判断的是产品硬伤和体验风险，不是最低导出合同。

## Remaining Gaps

- 尚未建立模型输出 fixtures 和失败样本库。
- 尚未实际完成 5 到 8 人内部 playtest。
- 尚未实现 LLM 语义 repair prompt 版本管理。
- 尚未覆盖多路径、多结局浏览器 E2E。
