# FRAMEWORK V1 契约证明与冻结

- 开始时间：2026-07-20 19:43:00.000 +0800
- 结束时间：2026-07-20 19:51:46.630 +0800

## 本次迭代

- 新增 Kernel V1 的状态、Surface、行动、进程、内容包、追溯、存档、门禁结果与人类决策 JSON Schema。
- 新增谈判循环纸面扩展证明，确认新玩法只使用 Kernel 契约与 `extensions.negotiation`。
- 新增 text→image Surface 等价 fixture，确认媒介替换不改变状态、行动、进程与存档语义。
- 归档 `V1.0-draft`，将框架定义冻结为 V1.0，并新增实施设计文档。

## 主要文件

- `schemas/kernel/v1/`
- `examples/framework_v1/`
- `gamegen/kernel_contract.py`
- `tests/test_framework_v1_contract_proof.py`
- `doc/framework/FRAMEWORK_V1_互动叙事框架定义.md`
- `doc/framework/FRAMEWORK_V1_实施设计.md`

## 验证

- `python3 -m unittest tests.test_framework_v1_contract_proof -v`：3 项通过。
- `python3 -m unittest discover -s tests -v`：84 项通过。

## 遗留

- Kernel 语义门禁、调查玩法包和正式内容包在下一阶段落地。
- image/html 仍只有契约与 fallback，不包含专用 renderer。
