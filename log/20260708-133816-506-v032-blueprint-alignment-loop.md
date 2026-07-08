# V0.32 Blueprint Alignment Loop

时间：2026-07-08 13:38:16.506 Asia/Shanghai

## 本轮目标

让 `scene_blueprint.json` 不再只是生成前规划，而是成为最终 `game.json` 必须满足的契约。新增蓝图/成品对齐门禁，抓出 planned observe、choice、state write、next scene、ending 未落地的问题。

## 变更内容

- 归档当前 PRD/技术文档到 `doc/prd/old version/20260708-133340-277/`。
- 将 `doc/prd/agent_game_generation_technical_design_v0.md` 更新为 V0.32。
- 新增 `gamegen/blueprint_alignment.py`：
  - 校验 `game.start_scene_id` 与蓝图 entry 对齐。
  - 校验蓝图 scene 均存在于 game。
  - 校验蓝图 observe targets 出现在对应 scene 的 anchors 中，包含 nested anchors。
  - 校验蓝图 choice targets 出现在对应 scene 的 choices 中。
  - 校验蓝图 next scene / ending targets 被 choice path 指向。
  - 校验蓝图 state writes 在对应 scene 的 observe/choice effects 中真实写入。
- 新增 `scripts/validate_blueprint_alignment.py` 独立 CLI。
- 在 `gamegen/agent_graph.py` 中新增 `validate_blueprint_alignment` 节点，位于 `draft_skeleton` 之后、`optional_llm_polish` 之前。
- 将 agent graph 版本标记更新为 `v0_32`。
- 收紧并修正 `gamegen/scene_blueprint.py` 的场景责任，使其只声明已在 state schema 中存在且当前 game 真实落地的状态写入。
- 更新 README 的 AI Pipeline 说明和 alignment 校验命令。
- 新增 `tests/test_blueprint_alignment.py`，并更新 graph trace 测试。
- 重新生成 `generated/missing_phone_agent_v0/` 导出物。

## 验证结果

- `python3 scripts/run_generation_agent.py --brief examples/briefs/missing_phone.json --out generated/missing_phone_agent_v0 --provider offline`
  - 通过，trace events: 15，repair attempts: 0。
- `python3 scripts/validate_state_schema_design.py generated/missing_phone_agent_v0/state_schema_design.json`
  - 通过。
- `python3 scripts/validate_scene_blueprint.py generated/missing_phone_agent_v0/scene_blueprint.json`
  - 通过。
- `python3 scripts/validate_blueprint_alignment.py generated/missing_phone_agent_v0/game.json`
  - 通过。
- `python3 scripts/validate_json_schema.py generated/missing_phone_agent_v0/game.json`
  - 通过。
- `python3 scripts/validate_game.py generated/missing_phone_agent_v0/game.json`
  - 通过。
- `python3 scripts/content_qa_report.py generated/missing_phone_agent_v0/game.json`
  - 0 errors，0 warnings。
- `python3 scripts/smoke_playthrough.py generated/missing_phone_agent_v0/game.json`
  - 通过，抵达 `ending_publish`。
- `python3 scripts/repair_game.py generated/missing_phone_agent_v0/game.json`
  - 无需 repair。
- `python3 scripts/validate_model_output_archive.py`
  - 通过。
- `python3 scripts/validate_save_contract.py`
  - 通过。
- `python3 -m py_compile gamegen/*.py scripts/*.py tests/*.py`
  - 通过。
- `python3 -m unittest discover -s tests -v`
  - 58 tests passed。
- `git diff --check`
  - 通过。

## 当前判断

V0.32 让蓝图成为最终成品的真实约束。下一步可以开始拆 `draft_skeleton`，让它逐步消费蓝图生成 scene，而不是一次性调用固定 Demo 模板。

仍未完成：

- 根据 scene blueprint 动态生成最终 `game.json`。
- LLM 自动生成任意 brief 的完整 observe/choice 正文。
- 使用 LangGraph 原生 runtime 替换当前轻量 graph。
- 自动评估文本质量、节奏和商业可玩性。
