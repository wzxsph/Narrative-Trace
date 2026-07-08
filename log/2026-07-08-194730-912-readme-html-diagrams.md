# 2026-07-08 19:47:30.912 - README HTML 流程图重构

## 背景

用户指出 README 中的 `Iteration Rule` 属于 agent 操作准则，不应放在对外 README 中；同时希望 README 更简洁，并通过多种 HTML 流程图增强图文表达。

## 本轮变更

- 重写 `README.md`：
  - 标题更新为 `Narrative Trace`。
  - 保留线上体验链接与体验截图。
  - 删除 README 中的 `Iteration Rule` 内容。
  - 将长命令清单折叠到 `<details>` 中，减少主阅读负担。
  - 使用 HTML table 绘制多种流程图：
    - Game Loop。
    - Interaction Map。
    - Runtime Architecture。
    - AI Generation Pipeline。
    - Release Gates。
    - Project Map。
    - Product Boundary。
- 更新 `agent.md`：
  - 明确 README 不承载内部迭代规则。
  - 将“每次有意义迭代写 log”和“更新 PRD/技术文档前归档旧版”的规则保留在 agent 操作准则中。

## 验证

- `git diff --check`
- 检查 README 引用的截图、关键脚本、关键数据与入口文件均存在。
- 检查 README 中不再出现 `Iteration Rule`、`每次有意义的迭代`、`更新 PRD`、`doc/prd/old version` 等内部迭代规则文本。

## 备注

- 本轮未修改 PRD。
- 本轮未部署 Worker，因为只修改 README、agent.md 和 log。
