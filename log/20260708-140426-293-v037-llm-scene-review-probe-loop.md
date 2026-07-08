# V0.37 LLM Scene Review Probe Loop

时间：2026-07-08 14:04:26.293 Asia/Shanghai

## 本轮目标

把 LLM 从第一段文本 polish 推进到 scene artifact 审查，但保持边界：LLM 只能输出结构化 review report，不能改 scene、不能锁定 artifact、不能替代 deterministic release gate。

## 变更内容

- 归档当前 PRD/技术文档到 `doc/prd/old version/20260708-140111-527/`。
- 将 `doc/prd/agent_game_generation_technical_design_v0.md` 更新为 V0.37。
- 新增 `gamegen/llm_scene_review.py`：
  - `review_scene_artifact_with_llm`
  - `normalize_llm_scene_review`
  - scene artifact / blueprint scene selector。
- 新增 `scripts/llm_scene_review_smoke.py`。
- 在 `gamegen/agent_graph.py` 中新增 `optional_llm_scene_review` 节点。
- `provider=offline` 时跳过 LLM scene review。
- `provider=llm` 时必须真实调用 `.env` 并产出 `llm_scene_review.json`。
- 更新 README 的 AI Pipeline 和 LLM scene review smoke 命令。
- 新增 `tests/test_llm_scene_review.py`，并更新 graph trace 测试。
- 重新生成 `generated/missing_phone_agent_v0/` offline 导出物。

## 真实 .env 调用记录

- `python3 scripts/llm_env_smoke_test.py`
  - 通过，model=`Minimax-M3`。
- `python3 scripts/llm_scene_review_smoke.py --out /tmp/game_writer_llm_scene_review.json`
  - 通过，scene_id=`ch01_phone_lock`，verdict=`pass`。
- `python3 scripts/run_generation_agent.py --brief examples/briefs/missing_phone.json --out /tmp/game_writer_llm_agent_smoke --provider llm`
  - 通过，trace events: 20，repair attempts: 0。
  - graph 中 `optional_llm_scene_review` 真实调用 `.env`，返回 verdict=`revise`，risk flags 数量为 2。
  - 导出 `/tmp/game_writer_llm_agent_smoke/llm_scene_review.json`。

LLM review 返回的 `revise` 未阻断 release，符合 V0.37 边界：它是 probe，不是 release gate。

## 验证结果

- Offline agent：
  - `python3 scripts/run_generation_agent.py --brief examples/briefs/missing_phone.json --out generated/missing_phone_agent_v0 --provider offline`
  - 通过，trace events: 20，repair attempts: 0。
- LLM agent：
  - `python3 scripts/run_generation_agent.py --brief examples/briefs/missing_phone.json --out /tmp/game_writer_llm_agent_smoke --provider llm`
  - 通过。
- LLM scene review CLI：
  - `python3 scripts/llm_scene_review_smoke.py --out /tmp/game_writer_llm_scene_review.json`
  - 通过。
- `/tmp/game_writer_llm_agent_smoke/game.json` 的 blueprint alignment、JSON schema、validator、content QA
  - 全部通过。
- `python3 scripts/validate_state_schema_design.py generated/missing_phone_agent_v0/state_schema_design.json`
  - 通过。
- `python3 scripts/validate_scene_blueprint.py generated/missing_phone_agent_v0/scene_blueprint.json`
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
  - 通过。
- `python3 scripts/repair_game.py generated/missing_phone_agent_v0/game.json`
  - 无需 repair。
- `python3 scripts/validate_model_output_archive.py`
  - 通过。
- `python3 scripts/validate_save_contract.py`
  - 通过。
- `python3 -m py_compile gamegen/*.py scripts/*.py tests/*.py`
  - 通过。
- `python3 -m unittest discover -s tests -v`
  - 75 tests passed。
- `git diff --check`
  - 通过。

## 当前判断

V0.37 证明 LLM 可以作为受控审稿参与 scene artifact 流程，但当前仍由 deterministic review/release gate 控制出品。下一步可以考虑把 LLM `revise` 结果转化为非阻断的 review issue artifact，或做人类审稿队列。

仍未完成：

- LLM 自动生成 scene artifact。
- LLM 审稿结果自动阻断 release。
- 人类审稿工作台。
- 使用 LangGraph 原生 runtime 替换当前轻量 graph。
