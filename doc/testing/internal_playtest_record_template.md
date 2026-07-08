# Internal Playtest Record Template V0.6

用途：记录 5 到 8 名内部测试用户对当前竖屏文字冒险 demo 的理解、卡点和复盘欲望。此模板直接对应 `doc/prd/PRD_V0_文字冒险游戏框架.md` 第 14 节成功标准。

## Session Metadata

- Build schema version:
- Test date:
- Facilitator:
- Participant id:
- Device / viewport:
- Start time:
- End time:
- Total duration minutes:

## Rules For Facilitator

- 不提前解释 observe、choice、路径图或隐藏状态。
- 只在用户完全卡死超过 90 秒时提示“可以重新读屏幕上的异常文字”。
- 记录用户原话，不替用户润色。
- 用户通关后再提问，不在游玩中打断判断。

## Observation Checklist

| Metric | Record |
|---|---|
| 第一分钟是否理解文字可以展开 | yes / no |
| 第一章关键 observe 发现比例 | 0.0 - 1.0 |
| 是否能说出一个 observe 解锁 choice 的例子 | yes / no |
| 是否能说出一个选择带来的后续影响 | yes / no |
| 是否主动查看路径图并表达重玩意愿 | yes / no |
| 是否因关键隐藏点不可发现而卡死 | yes / no |

## Required Questions After Play

1. 你第一次意识到文字可以展开是在什么时候？
2. 有没有一个选择是你觉得“因为我看到了某条线索才出现”的？
3. 哪个选择最让你犹豫？为什么？
4. 你有没有感觉某个角色或系统记住了你之前做过的事？
5. 章节复盘或路径图有没有让你想重玩？
6. 哪个隐藏内容最不公平或最像乱点找按钮？

## Raw Quotes

- Positive:
- Confused:
- Friction:
- Replay interest:

## Facilitator Notes

- Observe discoverability:
- Choice consequence clarity:
- Relationship echo clarity:
- Chapter flow review clarity:
- Ending portrait clarity:

## Batch JSON Mapping

把本记录转写到 `examples/playtests/internal_playtest_batch_template.json` 时，字段对应如下：

| Markdown field | JSON field |
|---|---|
| 第一分钟是否理解文字可以展开 | `first_minute_understood_expandable_text` |
| 第一章关键 observe 发现比例 | `chapter1_key_observe_found_ratio` |
| 是否能说出一个 observe 解锁 choice 的例子 | `can_name_observe_unlock_choice` |
| 是否能说出一个选择带来的后续影响 | `can_name_choice_echo` |
| 是否主动查看路径图并表达重玩意愿 | `opened_path_map_and_wants_replay` |
| 是否因关键隐藏点不可发现而卡死 | `blocked_by_hidden_key_point` |
