# V0.28 Generation Plan Node 迭代

开始时间：2026-07-08 13:14:09.157 +0800
结束时间：2026-07-08 13:16:35.578 +0800

## 本轮目标

继续执行工业级 agent 循环。V0.27 已经有 graph wrapper，但 `draft_skeleton` 仍然直接调用 deterministic demo。V0.28 将生成过程继续拆开：在组装 game JSON 之前，新增 `plan_story_structure` node，并导出可审计的 `generation_plan.json`。

## 关键节点

- 13:14:09.157：归档 V0.27 文档到 `doc/prd/old version/2026-07-08-131409-157`。
- 13:14：更新 agent 技术文档到 V0.28，定义 generation plan node 和 plan contract。
- 13:15：`gamegen/agent_graph.py` 新增 `generation_plan` state、`plan_story_structure()` 和 `build_generation_plan()`。
- 13:15：agent 导出阶段新增 `generation_plan.json`。
- 13:15：`tests/test_agent_graph.py` 增加 plan artifact 和 trace node 断言。
- 13:15：`README.md` 同步 graph agent node 顺序和新增 artifact。
- 13:16：修复 `write_validation_report()` 在无消息时产生 EOF 空行的问题。
- 13:16：重跑 graph agent，刷新 `generated/missing_phone_agent_v0`。

## 文件变化

新增：

- `generated/missing_phone_agent_v0/generation_plan.json`
- `log/2026-07-08-131635-579-v028-generation-plan-node-loop.md`

修改：

- `README.md`
- `doc/prd/agent_game_generation_technical_design_v0.md`
- `gamegen/agent_graph.py`
- `gamegen/validator.py`
- `tests/test_agent_graph.py`
- `generated/missing_phone_agent_v0/agent_trace.jsonl`
- `generated/missing_phone_agent_v0/game.json`
- `generated/missing_phone_agent_v0/game.yaml`
- `generated/missing_phone_agent_v0/generation_trace.jsonl`
- `generated/missing_phone_agent_v0/path_map.json`
- `generated/missing_phone_agent_v0/state_registry.json`
- `generated/missing_phone_agent_v0/validation_report.md`

归档：

- `doc/prd/old version/2026-07-08-131409-157/PRD_V0_文字冒险游戏框架.md`
- `doc/prd/old version/2026-07-08-131409-157/PRD_V0_产品推衍记录.md`
- `doc/prd/old version/2026-07-08-131409-157/agent_game_generation_technical_design_v0.md`

## 验证

```bash
python3 scripts/run_generation_agent.py --brief examples/briefs/missing_phone.json --out generated/missing_phone_agent_v0 --provider offline
python3 scripts/validate_json_schema.py generated/missing_phone_agent_v0/game.json
python3 scripts/validate_game.py generated/missing_phone_agent_v0/game.json
python3 scripts/content_qa_report.py generated/missing_phone_agent_v0/game.json
python3 scripts/smoke_playthrough.py generated/missing_phone_agent_v0/game.json
python3 scripts/repair_game.py generated/missing_phone_agent_v0/game.json
python3 scripts/validate_model_output_archive.py
python3 scripts/validate_save_contract.py
python3 -m py_compile gamegen/*.py scripts/*.py tests/*.py
python3 -m unittest discover -s tests -v
git diff --check
```

结果：

- graph agent 离线导出成功，trace events 从 9 个增加到 10 个。
- `agent_trace.jsonl` 包含 `plan_story_structure`。
- `generation_plan.json` 包含 `plan_schema_version`、`project_id`、`theme_question`、`chapter_count`、`scene_count`、`chapters`、`state_axes`、`ending_targets` 和 `non_goals`。
- agent 产物通过 schema、validator、content QA 和 smoke playthrough。
- 修复器确认 agent 产物无需修复。
- 全量 44 个单元测试通过。

## 边界判断

V0.28 仍不是“任意 brief -> 任意完整游戏”的工业 agent。它只是把章节规划这层中间 artifact 固化出来，让下一步可以替换成 LLM planner 或多候选 planner。下一轮应优先做 plan validator 或将 state schema 设计拆成独立 node。
