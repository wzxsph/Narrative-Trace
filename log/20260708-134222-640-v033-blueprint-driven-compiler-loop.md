# V0.33 Blueprint Driven Compiler Loop

时间：2026-07-08 13:42:22.640 Asia/Shanghai

## 本轮目标

继续拆 `draft_skeleton` 固定整包 Demo 模板：让草稿生成开始消费 `scene_blueprint.json`，按蓝图顺序从当前 demo scene library 中装配 scenes。

## 变更内容

- 归档当前 PRD/技术文档到 `doc/prd/old version/20260708-134022-356/`。
- 将 `doc/prd/agent_game_generation_technical_design_v0.md` 更新为 V0.33。
- 新增 `compile_demo_game_from_blueprint(brief, scene_blueprint)`：
  - 按 `scene_blueprint.scenes[*].id` 从当前 demo scene library 选择并排序 scenes。
  - 设置 `game.start_scene_id = scene_blueprint.entry_scene_id`。
  - 写入 `generation.draft_source = scene_blueprint_demo_library_v0_1`。
  - 写入 `generation.compiled_scene_count`。
  - 当蓝图引用不存在的 scene id 时失败。
- 将 `gamegen/agent_graph.py` 的 `draft_skeleton` 从直接调用 `deterministic_demo_game` 改为调用 blueprint-driven compiler。
- 将 agent graph 版本标记更新为 `v0_33`。
- 更新 README，说明 `draft_skeleton` 已开始消费 `scene_blueprint.json`。
- 新增 `tests/test_blueprint_compiler.py`。
- 更新 graph trace 测试，检查 `draft_source`。
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
  - 61 tests passed。
- `git diff --check`
  - 通过。

## 当前判断

V0.33 没有宣称完成动态创作，但它把固定 Demo 从 `draft_skeleton` 的整包黑箱降级成了可替换的 scene library。下一步可以继续把单个 scene 从 library 替换为由 blueprint 派生的 scene artifact。

仍未完成：

- 根据 scene blueprint 自动生成全新 scene 正文。
- LLM 自动生成任意 brief 的完整 observe/choice。
- scene artifact 的人工审稿工作台。
- 使用 LangGraph 原生 runtime 替换当前轻量 graph。
