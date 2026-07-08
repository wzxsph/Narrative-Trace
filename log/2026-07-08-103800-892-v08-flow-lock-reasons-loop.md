# Iteration Log: V0.8 Flow Lock Reasons Loop

Start: 2026-07-08 10:35:34.623 +0800
End: 2026-07-08 10:38:00.852 +0800

## Summary

- 按循环规则，在更新 PRD/技术文档前归档 V0.7 到 `doc/prd/old version/2026-07-08-103534-623`。
- 将当前 PRD、产品推衍记录和技术文档版本从 `V0.7` 迭代到 `V0.8`。
- 将章节 flowchart 分支从“只列 choice 名称”升级为“choice 名称 + 分支状态”。
- 新增未解锁原因说明：显示缺少的证据标签，例如“废弃地铁站定位”。
- 更新测试 hook，避免 flowchart 锁定原因退化。

## Files Changed

- `README.md`
- `doc/prd/PRD_V0_文字冒险游戏框架.md`
- `doc/prd/PRD_V0_产品推衍记录.md`
- `doc/prd/agent_game_generation_technical_design_v0.md`
- `doc/prd/old version/2026-07-08-103534-623/PRD_V0_文字冒险游戏框架.md`
- `doc/prd/old version/2026-07-08-103534-623/PRD_V0_产品推衍记录.md`
- `doc/prd/old version/2026-07-08-103534-623/agent_game_generation_technical_design_v0.md`
- `src/app.js`
- `src/styles.css`
- `tests/test_demo_contract.py`

## Verification

- `node --check src/app.js`
- `python3 -m unittest tests.test_demo_contract.DemoContractTest.test_static_runtime_includes_save_review_and_portrait_hooks -v`
- `python3 scripts/validate_game.py generated/missing_phone_v0/game.json`
- `python3 scripts/content_qa_report.py generated/missing_phone_v0/game.json`
- `python3 scripts/smoke_playthrough.py generated/missing_phone_v0/game.json`
- `python3 -m py_compile gamegen/*.py scripts/*.py tests/*.py`
- `python3 -m unittest discover -s tests -v`

## Product Assessment

- 本轮解决的是“flowchart 告诉玩家有分支，但不解释为什么没有解锁”的问题。
- V0.8 让分支遗憾更具体：玩家能看到自己是没选、没解锁，还是已解锁但没承担。
- 这仍不是完整 Detroit 式路径图；它只是基础分支解释层。

## Remaining Gaps

- 尚未实际完成 5 到 8 人内部 playtest。
- 仍缺少浏览器自动化测试进入常规 test suite。
- flowchart 尚无空间化布局和跨章因果线。
- 当前锁定原因基于最终 runtime state 和已解锁 choice 记录，不是逐节点时间旅行回放。
