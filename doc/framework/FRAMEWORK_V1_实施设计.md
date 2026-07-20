# FRAMEWORK V1 实施设计

版本：V1.0  
日期：2026-07-20  
对齐文档：`FRAMEWORK_V1_互动叙事框架定义.md`

## 1. 分层落点

```text
L1 Kernel       schemas/kernel/v1 + gamegen/kernel_*
L2 Loop         loop_packages/<loop>/<version>
L3 Content      content_packs/<pack>/<version>
L4 Runtime      index.html + src/runtime + src/surfaces + src/loops
```

依赖只允许 L3 → L2 → L1，L4 读取 L1 并按玩法包 id 选择已注册的 UI adapter。旧 V0 数据只允许通过兼容转换器进入系统，运行时不维护第二套内部模型。

## 2. 核心文档

- `pack.json` 是内容包唯一入口，精确锁定一个玩法包版本并声明 game、state registry 与 provenance。
- `game.json` 只保存进程、surface、action、echo 与玩法扩展；状态初值只保存在 `state_registry.json`。
- Surface 使用 `text | image | html` 判别联合。V1 runtime 只原生渲染 text，其他类型必须提供纯文本 fallback，HTML 永不执行。
- Kernel 文档默认封闭字段；玩法字段只能进入 `extensions.<loop_id>`，玩法包 schema 可增加约束但不能改变 Kernel 字段语义。

## 3. 版本与兼容

- Kernel 当前版本为 `1.0.0`；runtime 接受同主版本兼容范围。
- 内容包精确锁定玩法包版本，玩法包升级不自动改变旧作品。
- V1.0 保留旧数据路径、CLI 参数与 v1/v2 浏览器存档的一次迁移窗口；旧接口只生成或转换 V1 产物，不成为第二套运行时。
- V1.1 是否删除兼容层必须另行决策。

## 4. 门禁与人类决策

- G1–G6 均输出 `narrative_gate_result_v1`，以内容摘要保证可复算。
- G1–G5 自动执行；G6 接收匿名 playtest 原始记录和归因决策。
- brief、blueprint、release、playtest attribution 四个检查点使用 `narrative_decision_receipt_v1`，receipt 的 subject digest 必须与当前 artifact 一致。
- 自动门禁全绿只表示“允许发布”，不代表已经发布；bundle 生成仍要求 release receipt。

## 5. 冻结前证明

- `examples/framework_v1/negotiation_loop_paper.json` 证明谈判循环可完全落入六项契约和扩展命名空间。
- `examples/framework_v1/surface_equivalence/` 证明 text surface 替换为 image surface 时，状态、行动、进程和存档语义不变。
- `tests/test_framework_v1_contract_proof.py` 是两项证明的可执行回归门禁。
