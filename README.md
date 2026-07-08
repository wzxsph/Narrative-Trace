# Game Writer

竖屏文字冒险游戏与 AI 辅助创作流水线的 V0 工程仓库。

当前产品准则以 `/home/samsong/Desktop/game_writer/doc/prd` 为准；执行项目时先读 `agent.md`。

## Current Slice

- 玩家端：`index.html`、`src/app.js`、`src/styles.css`
- 生成器：`scripts/generate_game.py`
- 校验器：`scripts/validate_game.py`
- 冒烟游玩：`scripts/smoke_playthrough.py`
- Demo 内容：`generated/missing_phone_v0/game.json`

当前 demo 已覆盖：

- 竖屏手机 UI。
- 3 章 x 每章 3 个主场景，共 9 个主场景。
- 背景文字中的 observe anchor。
- 最多三层嵌套观察。
- observe 写入隐藏状态并解锁行动。
- choice 写入状态并进入后续章节或结局。
- 章节结束基础 flowchart 复盘、路径图、结局行动画像。
- 隐藏关系变量在后续场景触发叙事回声。
- 本地刷新恢复进度。
- 冒烟路径穿过 9 个主场景并抵达 `ending_publish`。

## Quick Start

生成 deterministic demo：

```bash
python3 scripts/generate_game.py \
  --brief examples/briefs/missing_phone.json \
  --out generated/missing_phone_v0 \
  --provider offline
```

校验结构：

```bash
python3 scripts/validate_game.py generated/missing_phone_v0/game.json
```

跑冒烟路径：

```bash
python3 scripts/smoke_playthrough.py generated/missing_phone_v0/game.json
```

跑测试：

```bash
python3 -m unittest discover -s tests -v
```

启动本地静态服务：

```bash
python3 -m http.server 4173
```

浏览器打开：

```text
http://127.0.0.1:4173/
```

## Optional LLM Polish

复制 `.env.example` 并填写 OpenAI-compatible 配置后，可使用可选 LLM polish。不要把 `.env` 或 API key 写入日志、PRD 或提交记录。

```bash
cp .env.example .env
```

## Iteration Loop

每轮迭代遵循：

```text
s1 完成/修复目前已有的 PRD 内容，更新 log
s2 测试是否跑通已有 PRD 内容
s3 如果没跑通或效果不及预期，返回 s1
s4 深度评估距离完整产品级产品的距离，更新 PRD 与技术文档
s5 返回 s1
```

更新 PRD 或技术文档前，先把旧版快照归档到 `/home/samsong/Desktop/game_writer/doc/prd/old version`。
