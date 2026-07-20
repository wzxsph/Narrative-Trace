# 2026-07-20 框架头脑风暴：FRAMEWORK V1 定义文档

- 开始时间：2026-07-20 12:55:00.000 +0800（头脑风暴会话开始，估计值）
- 结束时间：2026-07-20 13:30:37.860 +0800

## 本次迭代做了什么

通过 brainstorming 流程（逐问澄清 -> 方案对比 -> 分节评审）把用户的"AI 原生互动叙事游戏框架"想法收敛为框架定义文档。

六个关键决策（均由用户确认）：

1. 产出物形态：框架定义文档，暂不动代码。
2. "被市场认可" = 玩家用行为数据认可具体作品。
3. 框架不变量 = 契约层固定，玩法循环可插拔。
4. 质量保证 = 分级玩法包（Verified / Experimental），agent 默认只能填充 Verified 包。
5. 多媒介 = Surface 抽象进契约层（text / image / html 共享观察语义），V1 只要求 text 参考实现。
6. 平台化 = 内容包独立分发 + 契约标准化，统一聚合入口不在 V1。

设计要点：

- 四层架构：L1 契约层（六项契约：状态/Surface/行动/进程/存档/验收与追溯）、L2 玩法包层、L3 内容包层、L4 运行时与分发层。
- 调查循环（Investigation Loop）从现有工程抽象为第一个玩法包，标记为 Verified(债务)——playtest 未完成即为债务，首轮 playtest 不达标则降级。
- G1–G6 门禁链：G1–G5 对应现有验证脚本全家桶，G6 为真人 playtest。
- agent 管线契约：brief -> state_schema_design -> scene_blueprint -> scene_artifacts -> 内容包，四个人类引导点。
- 框架成功标准四条：纸面第二玩法包推演、agent 生产测试、playtest 债务清偿、text->image surface 替换零契约改动。

## 文件变更

- 新增：`doc/framework/FRAMEWORK_V1_互动叙事框架定义.md`（框架定义文档 V1.0-draft）
- 新增：`log/2026-07-20-133037-859-framework-v1-brainstorm.md`（本文件）
- 未修改任何 PRD、代码、schema。

## 验证

- 本次为纯文档迭代，无代码变更，未运行测试套件。
- 文档自审已完成：无 TBD/占位符；决策记录与各章节一致；范围切割（11 节）与成功标准（13 节）无矛盾；调查循环包的 Verified 债务声明与 PRD 17.2 的"playtest 未完成"事实对齐。

## 遗留问题 / 下一步

1. 用户评审 `doc/framework/FRAMEWORK_V1_互动叙事框架定义.md`。
2. 评审通过后进入实现规划（writing-plans），建议首个里程碑：契约层拆库 + 调查循环包归拢 + playtest 债务落账。
3. 开放问题已记录在文档第 14 节：html surface 安全边界、多玩法包混排、玩法包版本化。
