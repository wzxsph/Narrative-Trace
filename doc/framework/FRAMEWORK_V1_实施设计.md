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

## 6. Agent 分阶段管线

- `prepare` 固定 brief、精确玩法包版本和摘要，然后停在 brief 确认。
- brief receipt 通过后只生成 state design 与 blueprint；没有 blueprint receipt 不生成 scene artifacts。
- 内容包组装后按需运行 G1–G4 或 G1–G5；G5 全绿后产出 release candidate 摘要并再次停顿。
- 只有与当前 release candidate 摘要匹配的 release receipt 才能生成静态或 Worker bundle，命令不执行外部部署。
- `offline` 是 CI 使用的确定性模型替身；`examples/fixtures/model_outputs/` 保存脱敏回放样本。人工 live smoke 使用现有 OpenAI-compatible 配置，不在命令、trace、日志或仓库中写入密钥。

## 7. G6 债务边界

G1–G5 全绿与 G6 工具包就绪定义为本轮工程完成。调查玩法包在收到 5–8 人同意的真人原始记录、全部指标达标并写入 evidence digest 之前，仍保持 `tier=verified` + `verification.status=debt`。

G6 输入使用玩法包内的封闭 schema，只保存匿名 participant ID、同意状态、必要行为痕迹摘要和布尔访谈结果。`evaluate` 输出统一 `GateResult`；无效数据只会阻断评估。有效批次达标后，`apply` 写入 evidence digest 并清除债务；未达标时必须先用摘要绑定的 playtest attribution receipt 记录内容问题、玩法问题或不确定，然后将玩法包与依赖内容包降为 Experimental 并打开玩家可见标记。
