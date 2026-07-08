# Iteration Log: Cloudflare Worker Game Deploy

开始时间：2026-07-08 14:53:00.000 +0800  
结束时间：2026-07-08 15:01:27.685 +0800

## 本次迭代

- 将项目的玩家端游戏部分部署到 Cloudflare Worker。
- 部署范围只包含：
  - `/index.html`
  - `/src/app.js`
  - `/src/styles.css`
  - `/generated/missing_phone_v0/game.json`
- 未部署 agent、测试、PRD、reference、log、截图、`.env` 或其他非玩家端文件。
- 在 README 顶部新增显眼在线体验链接：
  - `https://game-writer-missing-phone.samsong-1a3.workers.dev/`

## 新增/修改文件

- 新增 `wrangler.toml`
- 新增 `scripts/build_game_worker_bundle.mjs`
- 新增 `scripts/build_game_worker_bundle.sh`
- 修改 `.gitignore`，忽略 `dist/` 和 `.wrangler/`
- 修改 `README.md`，增加在线体验入口和 Cloudflare Worker 部署命令。

## 技术实现

- 最初尝试 Workers Assets 静态资源绑定，但远程入口页和部分资源出现 assets fallback 不一致。
- 为降低部署面和不确定性，改为自包含 Worker bundle：
  - 构建脚本读取四个玩家端文件。
  - 生成 `dist/game-worker-bundle.js`。
  - Worker 根据路径直接返回对应静态内容。
  - 对未知非文件路径 fallback 到 `/`，便于直接访问体验页。

## 部署结果

- Worker 名称：`game-writer-missing-phone`
- 体验链接：`https://game-writer-missing-phone.samsong-1a3.workers.dev/`
- 当前部署版本：`dd741818-e45f-41b9-a0f3-90422a4cadee`

## 验证

- `npx --yes wrangler deploy --dry-run`
- `npx --yes wrangler deploy`
- 远程 HTTP 检查：
  - `/` -> 200
  - `/src/app.js` -> 200
  - `/src/styles.css` -> 200
  - `/generated/missing_phone_v0/game.json` -> 200
- 远程浏览器 smoke：
  - 打开线上链接。
  - 清空 localStorage。
  - 加载首场景 `锁屏上的半句话`。
  - 点击 observe `未发送短信`。
  - 点击嵌套 observe `02:13`。
  - 确认解锁 choice `前往废弃地铁站`。
  - 点击 choice 后进入下一场景 `云端控制台`。
- 本地验证：
  - `python3 scripts/validate_json_schema.py generated/missing_phone_v0/game.json`
  - `python3 scripts/validate_game.py generated/missing_phone_v0/game.json`
  - `python3 scripts/smoke_playthrough.py generated/missing_phone_v0/game.json`
  - `git diff --check`

## 遗留问题

- 当前 Worker bundle 是适合 V0 demo 的轻量方案；如果后续游戏资源明显增多，应回到 Workers Assets 或 Pages 的静态资源方案。
