# FRAMEWORK V1 内容包与 G1–G4 门禁迭代

- 开始时间：2026-07-20 19:52:00.000 +0800
- 结束时间：2026-07-20 20:05:31.428 +0800

## 本轮完成

- 新增调查玩法包 `investigation@1.0.0`，交付玩法定义、封闭 schema extension、G3/G4 验收规则、体验指标和 playtest 模板。
- 新增 V1 内容包加载器，内容入口和玩法包版本均由 `pack.json` 决定，并阻断绝对路径、目录穿越和缺失文件。
- 将《失踪者的手机》确定性迁移为 `content_packs/missing_phone/v1/`：使用 `surfaces + actions`、递归 fragment、唯一状态注册表、结局画像和 provenance 清单。
- 新增 G1–G4 统一门禁与 `validate_pack` CLI。G4 使用有限状态搜索自动寻找每个场景与结局的 witness path，不依赖固定通关脚本；证明完成后立即终止无意义的组合枚举。
- 保留 V0 生成目录，当前阶段未修改 PRD、旧 URL、旧 CLI 或玩家运行时。

## 文件范围

- 新增：`loop_packages/loop-package.schema.json`
- 新增：`loop_packages/investigation/v1/*`
- 新增：`content_packs/missing_phone/v1/*`
- 新增：`gamegen/content_pack.py`、`gamegen/gates.py`、`gamegen/v1_migration.py`
- 新增：`scripts/migrate_v0_pack.py`、`scripts/validate_pack.py`
- 新增：`tests/test_framework_v1_pack.py`

## 验证

- `python3 scripts/validate_pack.py content_packs/missing_phone/v1 --through G4`：通过；9 个场景可达，3 个结局均生成可重放 witness path。
- `python3 -m unittest tests.test_framework_v1_pack -v`：9 项通过。
- `python3 -m unittest discover -s tests -v`：93 项通过，原 81 项基线保持通过。

## 遗留与下一步

- G5 尚未接入包驱动浏览器运行时。
- 旧 JSON/CLI 兼容投影将在 Agent 管线改造时补齐；旧存档迁移将在运行时阶段实现。
- 调查玩法包继续保持 `tier=verified` 且 `verification.status=debt`，等待 G6 真人证据。
