# V0.34 Scene Artifact Layer Loop

时间：2026-07-08 13:47:05.834 Asia/Shanghai

## 本轮目标

把 scene 从代码函数里的隐含库，升级为 `scene_artifacts.json` 中间产物。目标是为后续逐场景生成、审稿、替换、回滚打基础。

## 变更内容

- 归档当前 PRD/技术文档到 `doc/prd/old version/20260708-134348-954/`。
- 将 `doc/prd/agent_game_generation_technical_design_v0.md` 更新为 V0.34。
- 新增 `gamegen/scene_artifacts.py`：
  - `build_scene_artifacts_from_library`
  - `validate_scene_artifacts`
  - `compile_game_from_scene_artifacts`
- 新增 `scripts/validate_scene_artifacts.py` 独立 CLI。
- 在 `gamegen/agent_graph.py` 中新增：
  - `draft_scene_artifacts`
  - `validate_scene_artifacts`
- `draft_skeleton` 改为消费 `scene_artifacts` 编译完整 game。
- 将 agent graph 版本标记更新为 `v0_34`。
- 导出 `generated/missing_phone_agent_v0/scene_artifacts.json`。
- 更新 README 的 AI Pipeline 说明和 scene artifact 校验命令。
- 新增 `tests/test_scene_artifacts.py`，并更新 graph trace/artifact 测试。
- 重新生成 `generated/missing_phone_agent_v0/` 导出物。

## 验证结果

- `python3 scripts/run_generation_agent.py --brief examples/briefs/missing_phone.json --out generated/missing_phone_agent_v0 --provider offline`
  - 通过，trace events: 17，repair attempts: 0。
- `python3 scripts/validate_state_schema_design.py generated/missing_phone_agent_v0/state_schema_design.json`
  - 通过。
- `python3 scripts/validate_scene_blueprint.py generated/missing_phone_agent_v0/scene_blueprint.json`
  - 通过。
- `python3 scripts/validate_scene_artifacts.py generated/missing_phone_agent_v0/scene_artifacts.json`
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
  - 65 tests passed。
- `git diff --check`
  - 通过。

## 当前判断

V0.34 让 scene 成为独立 artifact。下一步可以围绕单场景 artifact 做 LLM draft、人工审稿状态、或 artifact 版本锁定。

仍未完成：

- LLM 自动生成 scene artifact。
- 人类审稿工作台和 artifact lock/release 流程。
- scene artifact 多版本 diff 和回滚。
- 使用 LangGraph 原生 runtime 替换当前轻量 graph。
