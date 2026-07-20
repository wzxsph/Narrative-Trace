# Framework V1 内部 Playtest 记录指南

用途：为调查玩法包记录 5–8 名真人玩家的 G6 证据。实际数据必须匹配 `loop_packages/investigation/v1/playtest-batch.schema.json`；`playtest_template.json` 只是空模板，不是验证证据。

## 隐私和同意

- 每人只用本批次内唯一的匿名 ID，例如 `p_01`。
- 录入前必须获得同意；未同意的记录不得进入批次。
- 不保存姓名、邮箱、设备标识、自由文本原话或精确位置。
- 只做本地手工归档，V1 不建立线上采集。

## 主持规则

- 不提前解释 anchor、action、章节复盘或路径图。
- 记录是否完成首周目、第一章关键 anchor 命中数/总数、是否因关键点不可发现而卡死、是否打开路径复盘和 ending ID。
- 通关后再记录第一分钟理解、因果理解、后果感知、重玩意愿与付费/主动传播意愿。
- 不手写汇总数；G6 必须从逐人记录复算。

## 固定阈值

| 指标 | 通过线 |
|---|---:|
| 完成率 | ≥ 80% |
| 首分钟理解 | ≥ 80% |
| 第一章关键 anchor 发现 | ≥ 70% 玩家命中 ≥ 60% |
| 因果理解率 | ≥ 70% |
| 后果感知率 | ≥ 60% |
| 重玩意愿 | ≥ 50% |
| 付费或主动传播意愿 | ≥ 50% |
| 卡死人数 | 0 |

## 本地流程

```bash
python3 scripts/evaluate_g6.py evaluate \
  --pack content_packs/missing_phone/v1 \
  --batch path/to/batch.json \
  --out path/to/g6-result.json
```

达标批次可直接用 `apply` 清除债务。未达标批次必须先运行 `attribute`，由人类选择 `content_issue`、`loop_issue` 或 `inconclusive`，再将 receipt 传给 `apply`。两步都会重算摘要，过期报告或 receipt 不会改变分级。
