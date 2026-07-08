# Iteration Log: V0.39 README HTML Flowcharts and Review Policy

时间：2026-07-08 14:19:20.886 Asia/Shanghai

## Scope

- 更新 `README.md` 的体验截图展示，改为 HTML `<figure>` 截图画廊。
- 在 `README.md` 增加纯 HTML 绘制的算法结构图：
  - 玩家端核心循环：`Observe -> Interpretation -> Choice / Action -> State -> Echo -> Ending`
  - Agent 生成主链路
  - Artifact 发布闸门
- 收尾 V0.39 review issue release policy：
  - 新增 `review_issue_policy.json` 导出。
  - Agent graph 增加 `evaluate_review_issue_release_policy` 与 `validate_review_issue_release_policy`。
  - release policy 改为明确 `blocking=true` 的 active issue 才阻断。
  - LLM 自动审稿 issue 默认 `blocking=false`，作为 warning 进入治理记录。
- 同步技术文档 V0.39，并保留旧文档快照到 `doc/prd/old version/20260708-141259-115/`。

## Critical Fix

- 修复 `AgentState.add_trace()` metric 使用 `status=` 导致与方法参数冲突的问题，改为 `policy_status=`。
- 修复 review policy 列表推导中的条件位置，避免运行时错误。

## Verification

- `python3 scripts/run_generation_agent.py --brief examples/briefs/missing_phone.json --out generated/missing_phone_agent_v0 --provider offline`
- `python3 scripts/llm_env_smoke_test.py`
- `python3 scripts/llm_scene_review_smoke.py --out /tmp/game_writer_llm_scene_review.json`
- `rm -rf /tmp/game_writer_llm_agent_smoke && python3 scripts/run_generation_agent.py --brief examples/briefs/missing_phone.json --out /tmp/game_writer_llm_agent_smoke --provider llm`
- `python3 scripts/validate_review_issues.py generated/missing_phone_agent_v0/review_issues.json`
- `python3 scripts/validate_review_issues.py generated/missing_phone_agent_v0/review_issue_policy.json --policy`
- `python3 scripts/validate_review_issues.py /tmp/game_writer_llm_agent_smoke/review_issues.json`
- `python3 scripts/validate_review_issues.py /tmp/game_writer_llm_agent_smoke/review_issue_policy.json --policy`
- `python3 scripts/validate_state_schema_design.py generated/missing_phone_agent_v0/state_schema_design.json`
- `python3 scripts/validate_scene_blueprint.py generated/missing_phone_agent_v0/scene_blueprint.json`
- `python3 scripts/validate_scene_artifacts.py generated/missing_phone_agent_v0/scene_artifacts.json --release`
- `python3 scripts/validate_blueprint_alignment.py generated/missing_phone_agent_v0/game.json`
- `python3 scripts/validate_json_schema.py generated/missing_phone_agent_v0/game.json`
- `python3 scripts/validate_game.py generated/missing_phone_agent_v0/game.json`
- `python3 scripts/content_qa_report.py generated/missing_phone_agent_v0/game.json`
- `python3 scripts/smoke_playthrough.py generated/missing_phone_agent_v0/game.json`
- `python3 scripts/repair_game.py generated/missing_phone_agent_v0/game.json`
- `python3 scripts/validate_model_output_archive.py`
- `python3 scripts/validate_save_contract.py`
- `python3 -m py_compile gamegen/*.py scripts/*.py tests/*.py`
- `python3 -m unittest discover -s tests -v`
- `git diff --check`

## Result

- Offline generation passed and exported 24 trace events with 0 repairs.
- `.env` LLM smoke passed with `model=Minimax-M3`.
- `.env` LLM scene review passed with `verdict=revise`.
- `.env` LLM agent smoke passed and produced non-blocking warning issues:
  - `missing_observe_payoff` major warning
  - `state_echo_missing` minor warning
- Full unit suite passed: 81 tests.

## Product Judgment

本轮把 README 从“能说明”推进到“能展示”：截图、玩家循环、生成管线、发布闸门都能在仓库首页直接读懂。

V0.39 的 policy 也从简单阻断逻辑推进到更接近生产治理：模型可以发现风险，但不能直接绑架发布；真正阻断必须来自明确的 blocking 标记。
