# Narrative Trace

竖屏文字冒险游戏与 AI 辅助创作管线。

<table>
  <tr>
    <td width="50%">
      <strong>在线体验</strong><br>
      <a href="https://game-writer-missing-phone.samsong-1a3.workers.dev/">打开《失踪者的手机》Cloudflare Worker Demo</a>
    </td>
    <td width="50%">
      <strong>当前状态</strong><br>
      <code>medium-length playable vertical slice</code>
    </td>
  </tr>
</table>

这个项目不是“AI 实时随机写剧情”，而是一个确定性互动叙事实验：玩家在有限信息里观察、判断、行动，系统用隐藏状态记住选择，并在章节复盘和结局画像里回放玩家留下的痕迹。

## Experience

<table>
  <tr>
    <td align="center" width="25%">
      <a href="screenshots/01-start-screen.jpg"><img src="screenshots/thumb-01-start-screen.jpg" width="112" alt="Start screen with vertical story text, observe anchors, and bottom choices"></a>
      <br>
      <sub>Start</sub>
    </td>
    <td align="center" width="25%">
      <a href="screenshots/02-observe-unlocks-choice.jpg"><img src="screenshots/thumb-02-observe-unlocks-choice.jpg" width="112" alt="Observe interaction unlocks an additional visible choice"></a>
      <br>
      <sub>Observe unlock</sub>
    </td>
    <td align="center" width="25%">
      <a href="screenshots/03-chapter-review-flow.jpg"><img src="screenshots/thumb-03-chapter-review-flow.jpg" width="112" alt="Chapter review screen showing path flow and missing evidence"></a>
      <br>
      <sub>Chapter review</sub>
    </td>
    <td align="center" width="25%">
      <a href="screenshots/04-ending-portrait.jpg"><img src="screenshots/thumb-04-ending-portrait.jpg" width="112" alt="Ending portrait showing key observations, actions, stance, and ending tags"></a>
      <br>
      <sub>Ending portrait</sub>
    </td>
  </tr>
</table>

## Game Loop

<table>
  <tr>
    <td align="center"><strong>Observe</strong><br><sub>展开观察</sub></td>
    <td align="center">→</td>
    <td align="center"><strong>Interpretation</strong><br><sub>改变理解</sub></td>
    <td align="center">→</td>
    <td align="center"><strong>Choice</strong><br><sub>承担行动</sub></td>
    <td align="center">→</td>
    <td align="center"><strong>State</strong><br><sub>写入痕迹</sub></td>
    <td align="center">→</td>
    <td align="center"><strong>Echo</strong><br><sub>后续回声</sub></td>
    <td align="center">→</td>
    <td align="center"><strong>Ending</strong><br><sub>组合画像</sub></td>
  </tr>
</table>

核心规则很简单：正文可以滚动阅读，底部选项应完整可见；隐藏内容不做关键点击陷阱，而是通过 observe 解锁新的可见 choice。

## Interaction Map

<table>
  <tr>
    <th align="center">Scene</th>
    <th align="center">Observe</th>
    <th align="center">Hidden State</th>
    <th align="center">Visible Choice</th>
    <th align="center">Later Echo</th>
  </tr>
  <tr>
    <td rowspan="3" align="center">场景正文</td>
    <td>短信、日志、票据</td>
    <td><code>clues</code> / <code>flags</code></td>
    <td>解锁行动</td>
    <td>章节复盘</td>
  </tr>
  <tr>
    <td>NPC 反应</td>
    <td><code>trust</code> / <code>suspicion</code></td>
    <td>改变措辞</td>
    <td>关系回声</td>
  </tr>
  <tr>
    <td>关键遗漏</td>
    <td>未满足条件</td>
    <td>保持隐藏</td>
    <td>显示缺少证据</td>
  </tr>
</table>

## Runtime Architecture

<table>
  <tr>
    <th align="center">Content</th>
    <th align="center">Validation</th>
    <th align="center">Runtime</th>
    <th align="center">Player UI</th>
  </tr>
  <tr>
    <td align="center"><code>examples/briefs</code><br><code>game.json</code></td>
    <td align="center"><code>schemas</code><br><code>scripts/validate_*.py</code></td>
    <td align="center"><code>src/app.js</code><br><code>localStorage save</code></td>
    <td align="center"><code>index.html</code><br><code>src/styles.css</code></td>
  </tr>
  <tr>
    <td align="center">叙事素材</td>
    <td align="center">结构闸门</td>
    <td align="center">确定性状态机</td>
    <td align="center">纸墨竖屏界面</td>
  </tr>
</table>

## AI Generation Pipeline

当前 Agent 是创作辅助流水线，不是全自动作者。它把主题 brief 编译成结构化 artifact，再经过校验、审查和发布闸门生成可玩的 `game.json`。

<table>
  <tr>
    <td align="center"><strong>Brief</strong><br><code>missing_phone.json</code></td>
    <td align="center">→</td>
    <td align="center"><strong>Plan</strong><br><code>generation_plan</code></td>
    <td align="center">→</td>
    <td align="center"><strong>State</strong><br><code>state_schema</code></td>
    <td align="center">→</td>
    <td align="center"><strong>Blueprint</strong><br><code>scene_blueprint</code></td>
  </tr>
  <tr>
    <td align="center" colspan="7">↓</td>
  </tr>
  <tr>
    <td align="center"><strong>Trace</strong><br><code>agent_trace.jsonl</code></td>
    <td align="center">←</td>
    <td align="center"><strong>Export</strong><br><code>game.json</code></td>
    <td align="center">←</td>
    <td align="center"><strong>Validate / Repair</strong><br>schema + QA</td>
    <td align="center">←</td>
    <td align="center"><strong>Artifacts</strong><br><code>scene_artifacts</code></td>
  </tr>
</table>

## Release Gates

<table>
  <tr>
    <td align="center"><strong>Schema</strong><br><sub>字段完整</sub></td>
    <td align="center">→</td>
    <td align="center"><strong>Structure</strong><br><sub>无孤儿节点</sub></td>
    <td align="center">→</td>
    <td align="center"><strong>Content QA</strong><br><sub>选择有后果</sub></td>
    <td align="center">→</td>
    <td align="center"><strong>Browser E2E</strong><br><sub>三结局可达</sub></td>
    <td align="center">→</td>
    <td align="center"><strong>A11y Smoke</strong><br><sub>键盘可用</sub></td>
  </tr>
</table>

## Quick Start

```bash
python3 scripts/generate_game.py \
  --brief examples/briefs/missing_phone.json \
  --out generated/missing_phone_v0 \
  --provider offline

python3 -m http.server 4173
```

打开：

```text
http://127.0.0.1:4173/
```

运行生成 Agent：

```bash
python3 scripts/run_generation_agent.py \
  --brief examples/briefs/missing_phone.json \
  --out generated/missing_phone_agent_v0 \
  --provider offline
```

部署玩家端到 Cloudflare Worker：

```bash
scripts/build_game_worker_bundle.sh
npx --yes wrangler deploy
```

## Project Map

<table>
  <tr>
    <th align="left">Area</th>
    <th align="left">Files</th>
  </tr>
  <tr>
    <td>玩家端</td>
    <td><code>index.html</code>, <code>src/app.js</code>, <code>src/styles.css</code></td>
  </tr>
  <tr>
    <td>Demo 内容</td>
    <td><code>generated/missing_phone_v0/game.json</code></td>
  </tr>
  <tr>
    <td>生成管线</td>
    <td><code>scripts/run_generation_agent.py</code>, <code>prompts/manifest.json</code></td>
  </tr>
  <tr>
    <td>结构约束</td>
    <td><code>schemas/game.schema.json</code>, <code>scripts/validate_game.py</code></td>
  </tr>
  <tr>
    <td>浏览器验证</td>
    <td><code>scripts/browser_smoke.py</code>, <code>scripts/browser_e2e_matrix.py</code>, <code>scripts/browser_a11y_smoke.py</code></td>
  </tr>
</table>

<details>
  <summary><strong>Full Verification Commands</strong></summary>

```bash
python3 scripts/validate_json_schema.py generated/missing_phone_v0/game.json
python3 scripts/validate_game.py generated/missing_phone_v0/game.json
python3 scripts/content_qa_report.py generated/missing_phone_v0/game.json
python3 scripts/smoke_playthrough.py generated/missing_phone_v0/game.json
python3 scripts/validate_save_contract.py
python3 scripts/browser_smoke.py
python3 scripts/browser_save_contract.py
python3 scripts/browser_a11y_smoke.py
python3 scripts/browser_omission_paths.py
python3 scripts/browser_e2e_matrix.py
python3 -m unittest discover -s tests -v
```

</details>

<details>
  <summary><strong>LLM / Artifact Checks</strong></summary>

```bash
python3 scripts/llm_env_smoke_test.py
python3 scripts/llm_scene_review_smoke.py
python3 scripts/validate_state_schema_design.py generated/missing_phone_agent_v0/state_schema_design.json
python3 scripts/validate_scene_blueprint.py generated/missing_phone_agent_v0/scene_blueprint.json
python3 scripts/validate_scene_artifacts.py generated/missing_phone_agent_v0/scene_artifacts.json
python3 scripts/validate_blueprint_alignment.py generated/missing_phone_agent_v0/game.json
python3 scripts/validate_model_output_archive.py
```

</details>

## Product Boundary

<table>
  <tr>
    <th align="center">已完成</th>
    <th align="center">仍未完成</th>
  </tr>
  <tr>
    <td>
      3 章可玩 demo、observe 解锁 choice、章节复盘、存档恢复、三条主结局、基础 Agent 管线。
    </td>
    <td>
      真实 5-8 人 playtest、真实移动设备验收、多浏览器验收、屏幕阅读器质量验证、更多真实 LLM 输出样本。
    </td>
  </tr>
</table>

产品准则以 <code>doc/prd</code> 为准；Agent 执行规则见 <code>agent.md</code>。
