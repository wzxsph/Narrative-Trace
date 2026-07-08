# V0.30 State Schema Validator Loop

时间：2026-07-08 13:27:24.941 Asia/Shanghai

## 本轮目标

把 `state_schema_design.json` 从普通导出 artifact 升级为 agent graph 的正式质量门禁，避免错误状态设计进入节点草稿生成阶段。

## 变更内容

- 归档当前 PRD/技术文档到 `doc/prd/old version/20260708-132402-058/`。
- 将 `doc/prd/agent_game_generation_technical_design_v0.md` 更新为 V0.30。
- 新增 `gamegen/state_schema_design.py`：
  - 校验顶层必填字段。
  - 校验必备状态轴。
  - 校验变量字段完整性、唯一性、类型、axis 引用。
  - 校验关系向量声明必须有对应 `relationships.<character>.<axis>` 变量。
  - 校验结局标签和设计规则。
- 新增 `scripts/validate_state_schema_design.py` 独立 CLI。
- 在 `gamegen/agent_graph.py` 中新增 `validate_state_schema_design` 节点。
- 将 agent graph 版本标记更新为 `v0_30`。
- 更新 README 的 AI Pipeline 说明和状态设计校验命令。
- 新增 `tests/test_state_schema_design.py`，并更新 graph trace 测试。
- 重新生成 `generated/missing_phone_agent_v0/` 导出物。

## 验证结果

- `python3 scripts/run_generation_agent.py --brief examples/briefs/missing_phone.json --out generated/missing_phone_agent_v0 --provider offline`
  - 通过，trace events: 12，repair attempts: 0。
- `python3 scripts/validate_state_schema_design.py generated/missing_phone_agent_v0/state_schema_design.json`
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
  - 48 tests passed。
- `git diff --check`
  - 通过。

## 当前判断

V0.30 让生成管线更接近工业 agent：状态设计现在是可独立检查、可失败、可被 CI 引用的中间契约。

仍未完成：

- 从任意 brief 动态推导完整状态系统。
- 用 LangGraph 持久化状态替换当前自研轻量 graph。
- LLM 深度审查状态变量语义质量。
- 根据 state schema 动态组装全新节点图。
