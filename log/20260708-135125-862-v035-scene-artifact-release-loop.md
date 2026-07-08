# V0.35 Scene Artifact Release Loop

时间：2026-07-08 13:51:25.862 Asia/Shanghai

## 本轮目标

给 `scene_artifacts.json` 增加审稿/锁定/release 语义，避免未审稿的 draft artifact 直接进入最终 game 编译。

## 变更内容

- 归档当前 PRD/技术文档到 `doc/prd/old version/20260708-134827-610/`。
- 将 `doc/prd/agent_game_generation_technical_design_v0.md` 更新为 V0.35。
- 在 `gamegen/scene_artifacts.py` 中新增：
  - artifact `review` 元数据。
  - `review_scene_artifacts`
  - `validate_scene_artifact_release`
  - compile 前 release gate。
- 在 `gamegen/agent_graph.py` 中新增：
  - `review_scene_artifacts`
  - `validate_scene_artifact_release`
- `draft_skeleton` 现在只消费 locked scene artifacts。
- 将 agent graph 版本标记更新为 `v0_35`。
- 扩展 `scripts/validate_scene_artifacts.py --release`。
- 更新 README 的 AI Pipeline 和 release 校验命令。
- 更新 `tests/test_scene_artifacts.py` 和 `tests/test_agent_graph.py`。
- 重新生成 `generated/missing_phone_agent_v0/` 导出物。

## 验证结果

- `python3 scripts/run_generation_agent.py --brief examples/briefs/missing_phone.json --out generated/missing_phone_agent_v0 --provider offline`
  - 通过，trace events: 19，repair attempts: 0。
- `python3 scripts/validate_state_schema_design.py generated/missing_phone_agent_v0/state_schema_design.json`
  - 通过。
- `python3 scripts/validate_scene_blueprint.py generated/missing_phone_agent_v0/scene_blueprint.json`
  - 通过。
- `python3 scripts/validate_scene_artifacts.py generated/missing_phone_agent_v0/scene_artifacts.json`
  - 通过。
- `python3 scripts/validate_scene_artifacts.py generated/missing_phone_agent_v0/scene_artifacts.json --release`
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
  - 67 tests passed。
- `git diff --check`
  - 通过。

## 当前判断

V0.35 建立了最小 release 状态机：draft artifact 不能直接编译，必须先 locked。下一步可以把 deterministic reviewer 替换为人类审稿 artifact、LLM 语义审查、或多版本 review comments。

仍未完成：

- 真正的人类审稿工作台。
- LLM 语义审稿和可玩性审稿。
- scene artifact 多版本 diff、review comment、rollback。
- 使用 LangGraph 原生 runtime 替换当前轻量 graph。
