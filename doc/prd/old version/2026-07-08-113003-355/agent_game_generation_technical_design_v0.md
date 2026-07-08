# Agent Game Generation Technical Design V0

版本：V0.16
日期：2026-07-08  
文档类型：技术设计文档  
文件名规则：英文文件名，便于后续工程引用  
对齐准则：`/home/samsong/Desktop/game_writer/doc/prd/PRD_V0_文字冒险游戏框架.md`

---

## 1. Purpose

本文档定义一个面向本项目文字冒险游戏框架的生成 agent 技术方案 V0。

该 agent 的目标不是一次性“自动写完一整个游戏”，而是用简单、可验证、可迭代的工作流 loop 和脚本，辅助生成符合 PRD_V0 框架的结构化文字冒险游戏内容。

V0 技术目标：

- 使用简单脚本调用 OpenAI-compatible API。
- 用户只需要填写 `base_url` 和 `api_key`。
- Agent 面向本项目定义的文字冒险框架：背景文字、隐藏 observe、最多三层嵌套、observe 解锁 choice、状态回声、路径图。
- 避免让 LLM 直接生成庞大的复杂结构体。
- 尽可能让脚本承担确定性工作，让 LLM 只负责需要创造力和语义判断的部分。
- 产出可以被校验、修复、导出、最终接入游戏运行器的 JSON/YAML 内容。

---

## 2. Core Technical Judgment

本项目的内容结构不是普通剧情文本，而是嵌套结构体：

```text
Scene
  BackgroundBlock
    ObserveAnchor
      ObserveFragment
        nested ObserveAnchor
          nested ObserveFragment
            nested ObserveAnchor
  Choice
  Effects
  Conditions
  State
  PathGraph
```

直接让 LLM 一次性生成完整结构，会带来四类问题：

1. Token 浪费：每次 prompt 都携带完整 schema、完整上下文、完整章节内容，成本迅速膨胀。
2. 结构错误：括号、字段、ID、嵌套层级、requirements、effects 很容易不一致。
3. 因果断裂：observe 声称解锁 choice，但 choice 不存在；choice 读取的 clue 从未被写入。
4. 难以修复：一次性大 JSON 出错后，无法精准定位是文案问题、结构问题还是图问题。

因此 V0 采用：

> LLM 生成小块语义内容，脚本负责结构、ID、校验、拼装、图分析和修复循环。

更具体地说：

```text
LLM 做创造性草稿
脚本做确定性工程
校验器做质量闸门
repair loop 做局部修复
```

---

## 3. Non Goals

V0 不做：

- 不做可视化作者后台。
- 不做多 agent 协作框架。
- 不做运行时 AI 自由生成剧情。
- 不做玩家自由输入解析。
- 不做向量数据库或长期记忆系统。
- 不做自动发布到游戏客户端。
- 不做复杂模型路由、价格优化、微调或 RAG 平台。

V0 只做一个最小但可靠的生成流水线：

```text
读取输入 brief -> 分步生成 -> 脚本拼装 -> 校验 -> 局部修复 -> 导出结构化游戏内容
```

---

## 4. V1 Minimal Workflow Loop

这里的 V1 指 agent 的第一版可执行工作流，不是游戏产品版本。

### 4.1 Loop Overview

```text
1. Load config
2. Load project brief
3. Load PRD contract snapshot
4. Create deterministic skeleton
5. Generate scene briefs
6. Generate background blocks
7. Generate observe anchors and fragments
8. Generate choices from unlocked evidence
9. Deterministically assemble structured scenes
10. Validate schema and graph
11. Ask LLM to repair only failed parts
12. Export game JSON/YAML
13. Export human-readable report
```

关键原则：

- 不把整部游戏交给 LLM。
- 不要求 LLM 手写全局 ID。
- 不要求 LLM 自己维护全局状态图。
- 每一步只生成一个小范围 artifact。
- 每一步输出都进入脚本校验。

### 4.2 Suggested CLI

V0 可以先做成 CLI 脚本。

```bash
python scripts/generate_game.py \
  --brief examples/briefs/missing_phone.json \
  --out generated/missing_phone_v0
```

辅助命令：

```bash
python scripts/validate_game.py generated/missing_phone_v0/game.json
python scripts/repair_game.py generated/missing_phone_v0/game.json
python scripts/export_path_map.py generated/missing_phone_v0/game.json
```

### 4.3 User Configuration

用户只需要填写：

```env
LLM_BASE_URL=https://api.example.com/v1
LLM_API_KEY=your_api_key_here
```

高级选项可以有默认值，不要求普通用户填写：

```env
LLM_MODEL=default
LLM_TEMPERATURE=0.7
LLM_TIMEOUT_SECONDS=120
```

设计理由：

- `base_url` + `api_key` 即可兼容多数 OpenAI-compatible 服务。
- 模型名可以在项目配置中给默认值；如果供应商要求特定模型，再作为高级项暴露。
- API key 只读本地 `.env`，不得写入生成内容、日志或提交仓库。

### 4.4 OpenAI-Compatible Client Shape

V0 只依赖最小聊天补全能力：

```text
POST {base_url}/chat/completions
Authorization: Bearer {api_key}
Content-Type: application/json
```

请求体抽象：

```json
{
  "model": "default",
  "messages": [
    { "role": "system", "content": "..." },
    { "role": "user", "content": "..." }
  ],
  "temperature": 0.7
}
```

实现时应封装为一个 `LLMClient`：

```python
class LLMClient:
    def complete_json(self, system_prompt: str, user_prompt: str, schema_name: str) -> dict:
        ...

    def complete_text(self, system_prompt: str, user_prompt: str) -> str:
        ...
```

这样后续更换 SDK、接口或本地模型时，不影响生成流水线。

---

## 5. Script vs LLM Division of Labor

### 5.1 LLM Should Do

LLM 适合做：

- 把主题问题转化成章节问题。
- 生成场景处境、紧张点、背景文本草稿。
- 找出背景文本中的可疑词、时间、地点、人名、系统提示。
- 为 observe fragment 写自然语言证据卡。
- 为 choice 写玩家可理解的行动标签和风险描述。
- 为状态变化写自然语言反馈。
- 对失败校验项做局部修复建议。

### 5.2 Scripts Should Do

脚本必须接管：

- ID 生成。
- schema 校验。
- 嵌套深度限制。
- `text_range` 是否真的存在于父文本中。
- `unlock_choices` 指向是否存在。
- choice requirements 是否可达。
- effects 字段标准化。
- state registry 管理。
- 场景图 reachability 检查。
- 未使用状态变量检测。
- 已写未读 / 已读未写检测。
- path map 数据导出。
- token prompt 打包与上下文裁剪。
- 失败项定位和 repair loop 切片。

### 5.3 Why This Matters

本项目的内容问题不是“写得不够多”，而是“结构必须可信”。

如果 LLM 负责全部结构，它会把结构当成文案的一部分；而游戏运行器需要结构是机器可执行的。

所以 V0 的原则是：

> 文案可以有弹性，结构必须有硬边界。

---

## 6. Data Contracts

### 6.1 Project Brief Input

项目 brief 是人类提供给 agent 的最小创作输入。

```yaml
project:
  id: missing_phone
  title: 失踪者的手机
  theme_question: 当真相会伤害无辜者时，你是否仍然有义务公开它？
  tone:
    - 悬疑
    - 克制
    - 道德压力
  target_duration_minutes: 25

world:
  interface: 竖屏手机
  premise: 玩家拿到一部即将被远程清除的手机。
  pressure: 远程清除倒计时

chapters:
  - id: ch01
    title: 锁屏上的半句话
    question: 你是否愿意侵犯隐私来寻找真相？
  - id: ch02
    title: 废弃地铁站
    question: 你是否愿意相信一个可能撒谎的人？
  - id: ch03
    title: 被保存的副本
    question: 当真相会伤害无辜者时，你是否公开它？

characters:
  - id: lin
    name: 林
    role: 失踪者
    public_face: 调查记者
    hidden_truth: 曾经伪造过一段关键录音
  - id: chen
    name: 陈警官
    role: 警方联系人
    public_face: 理性可靠
    hidden_truth: 被上级要求截断定位记录
```

### 6.2 PRD Contract Snapshot

不要每次把完整 PRD 喂给 LLM。脚本应内置一份从 PRD_V0 提炼出来的短合同。

示例：

```yaml
prd_contract:
  game_shape:
    - vertical_phone_ui
    - chapter_based
    - background_text_with_hidden_observe
    - nested_observe_max_depth_3
    - observe_unlocks_choice
    - hidden_state_textual_echo
    - chapter_path_map
  scene_rules:
    background_blocks_per_scene: [1, 3]
    observe_anchors_per_scene: [5, 10]
    choices_per_scene: [2, 4]
    max_observe_depth: 3
  observe_rules:
    - embedded_in_background_or_fragment
    - must_change_understanding_or_unlock_action
    - key_observe_must_be_discoverable
  choice_rules:
    - clear_action_not_abstract_attitude
    - irreversible_when_world_changing
    - must_have_state_effect
    - key_choice_requires_future_echo
```

这份 contract 由工程维护，不能让 LLM 自己改。

### 6.3 Generated Game Output

建议导出：

```text
generated/{project_id}/
  game.yaml
  game.json
  state_registry.yaml
  path_map.json
  validation_report.md
  generation_trace.jsonl
```

说明：

- `game.yaml`：人类可读主产物。
- `game.json`：运行器可读产物。
- `state_registry.yaml`：全部 state 的声明、写入点、读取点。
- `path_map.json`：章节路径图数据。
- `validation_report.md`：校验报告。
- `generation_trace.jsonl`：每一步 prompt 摘要、输出摘要、错误摘要，避免记录 API key。

---

## 7. Generation Pipeline Detail

### 7.1 Stage 0: Normalize Brief

输入：`brief.yaml`

脚本任务：

- 检查必填字段。
- 规范化项目 ID、章节 ID、角色 ID。
- 建立初始 state registry。
- 生成默认章节预算。

LLM 不参与。

输出：

```yaml
normalized_project:
  id: missing_phone
  chapters: [...]
  characters: [...]
  budgets:
    scenes_per_chapter: 4
    observe_per_scene: 6
    choices_per_scene: 3
    max_depth: 3
```

### 7.2 Stage 1: Chapter Beat Generation

LLM 只生成章节 beat，不生成完整结构。

输入：

- project brief。
- PRD contract snapshot。
- 当前章节标题和问题。

输出：

```yaml
chapter_beats:
  - id_hint: phone_lock
    situation: 手机锁屏显示半句短信。
    pressure: 远程清除倒计时。
    key_tension: 是否侵犯隐私来寻找真相。
    required_echo: later_chen_suspicion
```

脚本任务：

- 把 `id_hint` 转成稳定 scene ID。
- 限制每章 scene 数量。
- 检查每个 beat 是否有 pressure 和 tension。

### 7.3 Stage 2: Scene Skeleton Assembly

脚本生成 scene skeleton。

```yaml
Scene:
  id: ch01_phone_lock
  title: ""
  task: ""
  pressure: ""
  background_blocks: []
  choices: []
  exit_conditions: []
```

LLM 不应该手写完整 skeleton。它只提供标题、任务和紧张点候选。

### 7.4 Stage 3: Background Block Generation

LLM 生成背景文本，但不生成最终 observe 结构。

输入：

- scene skeleton。
- chapter question。
- required clues。
- max length。

输出：

```yaml
background_candidates:
  - text: >
      手机亮起。未发送短信停在输入框里：
      “如果我没回来，不要相信陈...”
      顶部通知显示：远程清除已排队。
    suspicious_spans:
      - 未发送短信
      - 陈...
      - 远程清除
```

脚本任务：

- 检查 `suspicious_spans` 是否存在于 `text`。
- 删除不存在的 span。
- 给合法 span 分配 `ObserveAnchor` ID。
- 如果关键 span 太少，请 LLM 局部补写背景，不重写整个 scene。

### 7.5 Stage 4: Observe Fragment Expansion

LLM 一次只展开一个 observe fragment。

输入：

- 父文本。
- anchor label。
- 当前 depth。
- 当前 scene tension。
- 允许解锁的 clue 类型。

输出：

```yaml
fragment:
  title: 02:13 的系统日志
  body: >
    02:13 时手机短暂开启定位，地点是城北废弃地铁站。
    4 秒后，定位记录被手动截断。
  nested_span_candidates:
    - 城北废弃地铁站
    - 手动截断
  semantic_effects:
    - clue: station_location
```

脚本任务：

- depth >= 3 时强制 `nested_anchors = []`。
- 检查 nested span 是否存在于 body。
- 将 `semantic_effects` 映射到标准 `Effect`。
- 更新 state registry。

### 7.6 Stage 5: Choice Generation

Choice 不应在 scene 一开始全部生成。应在 observe scaffold 完成后生成。

输入：

- scene task。
- discovered clues。
- unlocked clue map。
- state registry。
- PRD choice rules。

LLM 输出：

```yaml
choice_candidates:
  - label: 前往废弃地铁站
    description: 你会离开安全地点，手机可能在路上被清除。
    trigger_clue: station_location
    choice_type: investigate
    likely_effects:
      - stance.truth_first +1
```

脚本任务：

- 将 `trigger_clue` 转成 `requirements`。
- 将 `likely_effects` 转成标准 `effects`。
- 自动生成 choice ID。
- 确保每个 scene 有 2 到 4 个 choice。
- 确保至少一个 choice 是默认可见，至少一个 choice 由 observe 解锁。

### 7.7 Stage 6: Echo Planning

LLM 可以提出“回声建议”，但脚本必须记录并验证。

输出：

```yaml
echo_plan:
  - source_effect: clues.chen_trimmed_location
    echo_type: dialogue_change
    target_scene_hint: ch02_station
    natural_language_echo: 陈警官回复时避开了“定位”这个词。
```

脚本任务：

- 建立 source -> target 映射。
- 检查 target scene 是否存在。
- 如果不存在，标为 pending，而不是让 LLM 自造 target scene。
- 后续校验所有关键 effect 是否至少有一个 echo。

### 7.8 Stage 7: Deterministic Assembly

脚本把所有小块拼装成最终结构。

LLM 不参与。

### 7.9 Stage 8: Validation

校验器必须先于人工审稿。

必检项：

- JSON/YAML 结构合法。
- scene ID 唯一。
- choice ID 唯一。
- observe ID 唯一。
- max observe depth <= 3。
- observe `text_range` 存在于父文本。
- nested anchor depth = parent depth + 1。
- `unlock_choices` 指向存在的 choice。
- choice requirements 引用已声明 state。
- effects 写入已声明或可自动登记 state。
- next_scene 指向存在 scene。
- 所有 scene 可达或被明确标记为 optional/hidden。
- 关键 choice 至少有一个 future echo。
- 关键 observe 至少改变理解或解锁行动。

### 7.10 Stage 9: Repair Loop

repair loop 只修失败片段，不重写整部游戏。

错误示例：

```yaml
error:
  type: missing_text_range
  location: ch01_phone_lock.obs_0213
  message: text_range "02:13日志" not found in parent text
```

修复 prompt 只包含：

- 错误位置。
- 父文本。
- 当前 fragment。
- 允许修改字段。

禁止 repair loop 修改：

- project theme。
- chapter question。
- PRD contract。
- unrelated scenes。

### 7.11 Stage 10: Export

导出三类产物：

1. 运行器产物：`game.json`
2. 作者审稿产物：`game.yaml`
3. QA 产物：`validation_report.md` + `path_map.json`

---

## 8. Prompt Strategy

### 8.1 Prompt Principles

- 每次 prompt 只解决一个局部问题。
- prompt 中放短 contract，不放完整 PRD。
- 输出要求机器可解析，但不要让 LLM 管全局结构。
- 所有 JSON/YAML 输出都必须经脚本解析和校验。
- 修复 prompt 要给明确失败原因和允许修改范围。

### 8.2 System Prompt Skeleton

```text
You are a narrative systems designer for a vertical mobile text adventure.
You write content for a game where background text contains hidden observe anchors.
Observe anchors can open nested evidence fragments up to depth 3.
Observe can unlock choices.
Choices are irreversible actions with state effects and future echoes.
Do not invent UI features outside the contract.
Do not copy existing IP.
Return only the requested structured output.
```

### 8.3 Scene Background Prompt

```text
Generate one background block for the scene.

Constraints:
- It must fit a vertical mobile text screen.
- It must contain 3 to 5 suspicious spans.
- Suspicious spans must be exact substrings in the background text.
- At least 1 span should be able to unlock a future choice.
- Do not generate choices yet.

Return:
background text
suspicious_spans
why_each_span_matters
```

### 8.4 Observe Fragment Prompt

```text
Expand this observe anchor into one evidence fragment.

Constraints:
- Current depth: {depth}
- Max depth: 3
- If depth is 3, do not propose nested spans.
- Fragment must change player understanding or unlock a choice.
- Nested spans must be exact substrings in fragment body.

Return:
title
body
nested_span_candidates
semantic_effects
possible_choice_unlocks
```

### 8.5 Choice Prompt

```text
Generate choices for this scene after observe generation.

Constraints:
- 2 to 4 choices.
- At least one default visible choice.
- At least one choice unlocked by a clue.
- Each choice is a concrete action, not an abstract attitude.
- Each key choice must include immediate risk and likely future echo.

Return:
choice_candidates
```

---

## 9. Validator Design

### 9.1 Validator Modules

```text
validators/
  schema_validator.py
  id_validator.py
  anchor_validator.py
  depth_validator.py
  state_validator.py
  graph_validator.py
  echo_validator.py
  gameplay_validator.py
```

### 9.2 Anchor Validator

核心检查：

```python
assert anchor.text_range in parent_text
assert anchor.depth in [1, 2, 3]
assert child.depth == parent.depth + 1
```

错误级别：

- `error`: key anchor text not found。
- `warning`: optional anchor text not found。
- `error`: depth > 3。

### 9.3 State Validator

检查：

- every requirement references a known state。
- every effect writes to a known or auto-registerable state。
- every key clue has at least one reader。
- every key choice effect has at least one echo。

### 9.4 Graph Validator

检查：

- entry scene exists。
- all non-optional scenes reachable。
- every choice `next_scene` exists。
- path map can be generated。
- no scene is a dead end unless it is ending scene。

### 9.5 Gameplay Validator

PRD-specific checks：

- each scene has 1 to 3 background blocks。
- each scene has 2 to 4 choices after unlocks。
- each main scene has at least one observe-unlocked choice。
- each key background block has at least 2 suspicious observe anchors。
- max nesting depth is 3。
- key observe is discoverable, not `hidden_optional`。

---

## 10. Token Optimization Strategy

### 10.1 Do Not Send Full Project Every Time

每个生成步骤只发送：

- 当前任务所需的局部 scene。
- 当前章节问题。
- 少量已知 state。
- PRD contract snapshot。
- 相关角色短描述。

不要发送：

- 完整 PRD。
- 完整游戏结构。
- 所有章节内容。
- 所有历史 prompt。

### 10.2 Keep Deterministic Memory Outside LLM

脚本维护：

- state registry。
- ID registry。
- scene graph。
- chapter budget。
- generated artifact index。

LLM 只在需要时看到摘要。

### 10.3 Use Summaries, Not Raw Dumps

当后续 scene 需要知道前文时，脚本生成摘要：

```yaml
prior_context:
  discovered_clues:
    - station_location
    - chen_trimmed_location
  player_possible_stances:
    - truth_first
    - protect_person
  unresolved_tensions:
    - whether_chen_can_be_trusted
```

---

## 11. Suggested Repository Structure

V0 实现可以从这个结构开始：

```text
game_writer/
  agent.md
  doc/
    prd/
      PRD_V0_文字冒险游戏框架.md
      agent_game_generation_technical_design_v0.md
  scripts/
    generate_game.py
    validate_game.py
    repair_game.py
    export_path_map.py
  gamegen/
    llm_client.py
    config.py
    contracts/
      prd_contract_v0.yaml
      game_schema_v0.json
    pipeline/
      normalize.py
      generate_chapters.py
      generate_backgrounds.py
      generate_observes.py
      generate_choices.py
      assemble.py
      repair.py
    validators/
      schema_validator.py
      anchor_validator.py
      depth_validator.py
      state_validator.py
      graph_validator.py
      echo_validator.py
      gameplay_validator.py
    exporters/
      yaml_exporter.py
      json_exporter.py
      path_map_exporter.py
  examples/
    briefs/
      missing_phone.yaml
  generated/
    .gitkeep
```

V0 可以先不实现完整包结构，只要脚本边界按这个方向组织即可。

---

## 12. Security and Secrets

必须遵守：

- API key 只放 `.env` 或本地环境变量。
- 不在 prompt trace 中记录 API key。
- 不在 validation report 中记录 API key。
- 不提交 `.env`。
- generation trace 只保存 prompt 摘要和输出摘要，除非用户明确开启 debug。

建议 `.env.example`：

```env
LLM_BASE_URL=https://api.example.com/v1
LLM_API_KEY=
LLM_MODEL=default
```

---

## 13. Error Handling

### 13.1 LLM Output Parse Failure

处理：

1. 尝试提取 JSON/YAML fenced block。
2. 失败则发起一次 format-only repair。
3. 仍失败则记录错误并跳过该 fragment。

### 13.2 Invalid Anchor

处理：

1. 如果 optional，删除 anchor。
2. 如果 key，要求 LLM 在父文本中选择现有 substring。
3. 不允许脚本凭空插入关键剧情文本，除非进入 background repair。

### 13.3 Missing Choice Unlock

处理：

1. 检查 choice 是否被生成。
2. 如果不存在，让 LLM 基于该 clue 生成一个局部 choice。
3. 脚本生成 ID 和 requirements。

### 13.4 Graph Dead End

处理：

1. 如果是 ending scene，合法。
2. 如果不是，脚本生成 repair request。
3. LLM 只补充 transition choice，不重写 scene。

---

## 14. Quality Gates

生成内容进入人工审稿前，必须通过以下 gate：

### Gate A: Structure

- Schema valid。
- ID unique。
- No broken references。
- Max observe depth <= 3。

### Gate B: Gameplay

- 每个主 scene 有隐藏 observe。
- 每个主 scene 至少有一个 observe 解锁 choice。
- 每个 key choice 有 state effect。
- 每个 key choice 有 future echo plan。

### Gate C: PRD Alignment

- 是竖屏手机互动叙事。
- 背景文字中包含隐藏观察点。
- observe 可以嵌套展开。
- choice 是明确行动，不是抽象态度。
- 路径图数据可导出。
- 不引入自由输入、AI 运行时生成、作者后台等 V0 非目标。

### Gate D: Human Review Readiness

- `game.yaml` 可读。
- `validation_report.md` 清晰。
- 所有 remaining warnings 有位置和原因。
- 人类可以局部编辑，不需要重写整部游戏。

---

## 15. Implementation Phases

### Phase 1: Offline Skeleton

目标：

- 不调用 LLM。
- 定义 schema。
- 定义 brief。
- 定义 validators。
- 手写一个最小 game.yaml。

验收：

- validator 可以跑通。
- path map 可以从手写 game 导出。

### Phase 2: LLM Background and Observe Generation

目标：

- 配置 `base_url` 和 `api_key`。
- 调用 OpenAI-compatible API。
- 生成 background blocks。
- 生成 observe fragments。
- 校验 anchors 和 depth。

验收：

- 一章内容可生成。
- 每个 observe text_range 都能在父文本中找到。
- depth 不超过 3。

### Phase 3: Choice Generation and State Registry

目标：

- 根据 observe effects 生成 choice。
- 自动生成 requirements。
- 建立 state registry。

验收：

- 每个主 scene 至少一个 observe unlocks choice。
- no missing state references。

### Phase 4: Repair Loop

目标：

- validator 输出机器可读错误。
- repair loop 局部修复错误。

验收：

- 故意制造的 broken anchor、missing choice、missing next_scene 可以被修复。

### Phase 5: Export Review Package

目标：

- 输出 `game.yaml`、`game.json`、`path_map.json`、`validation_report.md`。

验收：

- 人类可以阅读和修改生成结果。
- 运行器可以读取 `game.json`。

---

## 16. Example End-to-End Flow

```bash
cp .env.example .env
# 用户只填写 LLM_BASE_URL 和 LLM_API_KEY

python scripts/generate_game.py \
  --brief examples/briefs/missing_phone.json \
  --out generated/missing_phone_v0

python scripts/validate_game.py \
  generated/missing_phone_v0/game.json

python scripts/export_path_map.py \
  generated/missing_phone_v0/game.json \
  --out generated/missing_phone_v0/path_map.json
```

预期输出：

```text
generated/missing_phone_v0/
  game.yaml
  game.json
  state_registry.json
  path_map.json
  validation_report.md
  generation_trace.jsonl
```

---

## 17. Technical Risks

### 17.1 LLM Still Produces Invalid Structure

应对：

- 更小粒度 prompt。
- 更强 validator。
- repair only failed fields。
- 对复杂字段使用脚本生成。

### 17.2 Generated Content Is Playable but Boring

应对：

- gameplay validator 检查每个 choice 是否有犹豫点。
- prompt 要求每个 choice 写出 immediate gain 和 hidden cost。
- 人工审稿保留最终判断。

### 17.3 Token Cost Grows with Project Size

应对：

- 不传完整项目。
- 使用 scene-level generation。
- 使用 deterministic summaries。
- 只对 failed part repair。

### 17.4 PRD Drift

应对：

- `prd_contract_v0.yaml` 从 PRD_V0 手工提炼。
- contract 由工程维护，不让 LLM 改。
- validation gate 检查是否引入 V0 非目标。

### 17.5 Secret Leakage

应对：

- `.env` 不提交。
- trace 不写 API key。
- debug log 默认关闭。

---

## 18. V0 Success Criteria

技术 V0 成功条件：

- 用户只填写 URL 和 API key 即可跑通生成脚本。
- 能生成至少 1 章符合 PRD_V0 框架的结构化内容。
- 生成内容包含背景文字、隐藏 observe、嵌套 observe、observe 解锁 choice。
- validator 能发现结构错误。
- repair loop 能局部修复常见错误。
- 导出 `game.yaml` 和 `path_map.json`。
- 生成器和校验器运行过程中不自动修改 PRD 文件。

产品对齐成功条件：

- 生成结果仍然是竖屏手机文字互动叙事。
- 不滑向普通小说。
- 不滑向自由输入 AI 聊天。
- 不滑向作者后台。
- 不让 LLM 直接生成不可控的大结构体。

---

## 19. Final Recommendation

V0 agent 不要追求“聪明”，要追求“可控”。

最好的第一版不是一个会自由创作的庞大 agent，而是一条朴素但可靠的生成流水线：

```text
小 prompt
小输出
强 schema
强校验
局部 repair
人工可审
运行器可读
```

这条路线最符合当前 PRD_V0 的产品本质：玩家体验依赖结构可信，而结构可信不能交给 LLM 的自由发挥。

---

## 20. Current Demo Implementation Status

当前工程已有一个 demo 级实现，位置如下：

```text
index.html
src/app.js
src/styles.css
scripts/generate_game.py
scripts/validate_game.py
scripts/smoke_playthrough.py
gamegen/demo_agent.py
gamegen/validator.py
gamegen/llm_client.py
examples/briefs/missing_phone.json
generated/missing_phone_v0/game.json
```

已实现：

- 离线 deterministic demo generator。
- 可选 OpenAI-compatible `LLMClient`，通过 `.env` 读取 `LLM_BASE_URL` 和 `LLM_API_KEY`。
- 生成 `game.json`、`game.yaml`、`path_map.json`、`state_registry.json`、`validation_report.md`。
- 校验 observe depth、anchor text range、choice target、state references、path graph。
- 静态前端加载 `generated/missing_phone_v0/game.json` 并提供可玩体验。
- 冒烟脚本验证从嵌套 observe 解锁 choice 并抵达结局。
- 前端通过 `localStorage` 保存/恢复单机进度，包括场景、已打开 observe、选择轨迹、章节复盘和结局状态。
- 前端在跨章节 choice 后展示章节复盘屏，再进入下一章。
- 前端结局页展示基础行动画像，包括关键观察、关键行动、状态回声和结局标签。
- `tests/test_demo_contract.py` 提供最小 unittest 回归入口。
- `README.md` 记录生成、校验、测试和本地启动流程。
- deterministic demo 已扩展为 3 章 x 每章 3 个主场景，共 9 个主场景。
- 测试已覆盖 V0.2 schema、9 场景结构、每章 3 场景、每场景 observe 解锁 action。
- `state_echoes` 支持场景根据隐藏状态显示叙事回声。
- validator、path map、state registry 和测试已覆盖 `state_echoes`。
- 章节复盘屏新增基础 flowchart runtime，展示本章节点、到达状态和分支标签。
- 第一章新增可选 `guidance` / `unlock_guidance` 内容字段，运行时可显示叙事内轻教学并高亮新出现的 action。
- validator 校验 guidance 的 `id`、`title`、`text`，测试覆盖首章轻教学契约。
- 新增内部 playtest 记录模板、批次 JSON 模板和汇总脚本，用于验证 PRD 第 14 节成功指标。
- 新增自动内容 QA 报告脚本，用于检查隐藏 observe 可发现性和 choice 代价文案硬伤。
- 自动内容 QA 已覆盖结局画像完整性硬伤。
- 章节 flowchart 分支可显示已选择、可选未走、已解锁未选、未解锁原因。
- 新增浏览器级 smoke，覆盖移动视口、轻教学、高亮、章节复盘、未解锁原因和刷新恢复。
- `repair_game.py` 已从 report-only 升级为保守局部修复器。
- 新增显式 JSON Schema 和 schema 校验脚本。
- `export_game()` 已将 JSON Schema 和结构 validator 接入默认导出门禁。
- 新增生成失败 fixture，覆盖 schema gate、validator gate、repair gate 的典型坏输出。
- 新增 prompt manifest，generation trace 记录 active `prompt_set`。

当前技术状态：

```text
Medium-length playable vertical slice with basic runtime resilience: achieved
Basic relationship echo runtime: achieved
Basic chapter flow review runtime: achieved
Diegetic first-chapter guidance runtime: achieved
Internal playtest metric pipeline: achieved
Automated content QA hard-error gate: achieved
Chapter flow locked-branch explanation: achieved
Ending portrait completeness gate: achieved
Browser smoke for core mobile path: achieved
Browser E2E matrix for all current main endings: achieved
Conservative local repair tool: achieved
Explicit JSON Schema contract: achieved
Schema and validator export gate: achieved
Generation failure fixtures: achieved
Prompt manifest traceability: achieved
Production-grade generation pipeline: not achieved
```

## 21. Product-Grade Technical Gap

距离产品级还需要补齐：

### 21.1 Generation Robustness

- 当前 LLM 只做可选 polish，不是真正多阶段生成。
- repair loop 已能修复常见确定性结构错误，但还不是 LLM 驱动的语义局部重写。
- 已有生成失败 mutation fixtures，但还缺少真实模型输出样本库。
- 已有 prompt manifest 和 trace 记录，但还缺少真实模型输出样本与 prompt/model/provider 版本映射。
- deterministic demo 规模已扩到 9 场景，但仍是手写结构，不证明 agent 能稳定生成同等规模内容。

### 21.2 Runtime Robustness

- 当前前端已有本地单存档，但没有多存档、版本迁移、损坏存档提示或云端同步。
- 已有基础章节 flowchart 复盘和未解锁原因说明，但还不是完整 flowchart 级路径复盘。
- 已有基础 `state_echoes` 渲染，但还没有复杂优先级、互斥回声或节奏控制。
- 已有第一章叙事内轻教学，但还没有用户测试数据证明提示强度刚好。
- 已有浏览器级移动视口 smoke 和三主结局 E2E 矩阵，但缺少真实设备、多浏览器和触控细节测试。
- 缺少无障碍键盘导航和屏幕阅读器检查。

### 21.3 Content QA

- 当前 validator 偏结构，较少判断 choice 是否真的有犹豫点。
- 已有内部 playtest 记录模板和汇总脚本，但还没有真实用户批次数据。
- 已有基础自动内容 QA，但只能发现硬性 contract 问题，不能判断语义公平性和真实犹豫感。
- 结局画像已有前端呈现和自动完整性检查，但缺少情感质量和语义画像 QA。
- 关系回声已有覆盖测试，但缺少人工 QA 判断文案是否自然、是否过度解释数值。

### 21.4 Engineering Hygiene

- 已引入最小 `tests/`、浏览器 smoke 和三主结局 E2E，但还不是完整测试矩阵。
- 已有统一 JSON Schema、基础生成失败 fixtures、prompt manifest 和结局路径 E2E，但还需要真实模型输出样本和 provider/model 版本映射。
- 需要把 generated demo 内容与手写 fixture 的边界定义清楚。
- 已增加 README，但仍需要持续同步真实命令和产品边界。

## 22. Next Technical Iteration

下一轮建议按这个顺序推进：

1. 积累真实模型输出 fixtures，并记录对应 prompt/model/provider 版本。
2. 建立真实模型输出样本的脱敏/归档规则。
3. 跑一轮内部 playtest 批次，使用 `summarize_playtest_batch.py` 生成 pass/fail 报告。
4. 增加真实设备与无障碍测试，覆盖触控、滚动、可读性、键盘导航和屏幕阅读器。
5. 将浏览器 E2E 继续扩展到刷新恢复、失败/遗漏路径、多浏览器和可访问性断言。

## 23. V0.1 Implementation Delta

本轮 V0.1 的工程变化：

- PRD 和技术文档旧版已归档到 `doc/prd/old version/2026-07-08-093752-079`。
- `src/app.js` 增加保存/恢复、章节复盘、结局行动画像。
- `src/styles.css` 增加复盘屏、行动画像、已到达路径标记样式。
- `tests/test_demo_contract.py` 增加结构、冒烟路径、V0 demo shape 和前端 hook 检查。
- `README.md` 增加 quick start、测试命令和迭代规则。

本轮没有解决：

- 多阶段 LLM 生成。
- 局部自动 repair。
- 产品级移动端兼容测试。
- 更长内容规模和内部用户数据。

## 24. V0.2 Implementation Delta

本轮 V0.2 的工程变化：

- PRD 和技术文档旧版已归档到 `doc/prd/old version/2026-07-08-094711-784`。
- `gamegen/demo_agent.py` 的 deterministic demo 从 3 个 scene 扩展到 9 个 scene：
  - 第一章：锁屏、云端控制台、联系人追踪。
  - 第二章：旧员工入口、废弃站台、储物柜后的维护间。
  - 第三章：解密备份、最后留言串、发布页。
- `scripts/smoke_playthrough.py` 的主路径升级为穿过 9 场景后抵达 `ending_publish`。
- `tests/test_demo_contract.py` 增加 V0.2 结构约束：schema、9 场景、每章 3 场景、每场景 observe 解锁 action。
- `generated/missing_phone_v0/*` 已由 V0.2 generator 重新生成。

本轮没有解决：

- 自动 repair。
- 显式 JSON schema。
- 浏览器自动化测试进入常规 test suite。
- 真实用户测试与内容节奏数据。

## 25. V0.3 Implementation Delta

本轮 V0.3 的工程变化：

- PRD 和技术文档旧版已归档到 `doc/prd/old version/2026-07-08-100034-256`。
- `gamegen/demo_agent.py` 新增 `make_echo()` 和场景级 `state_echoes`。
- `src/app.js` 新增 `renderStateEchoes()`，在场景正文前渲染满足条件的叙事回声。
- `src/styles.css` 新增关系回声样式。
- `gamegen/validator.py` 校验 `state_echoes` 的 id、text 和状态读取。
- `state_registry.json` 记录 `state_echoes` 对隐藏状态的读取。
- `tests/test_demo_contract.py` 要求 `relationships.chen.trust`、`relationships.chen.suspicion`、`relationships.lin.bond` 至少在两个不同场景中产生回声。

本轮没有解决：

- 章节复盘 flowchart 化。
- 第一章叙事内轻教学。
- 关系回声文案的人工 QA 和用户测试。
- 回声优先级、互斥规则和复杂冲突处理。

## 26. V0.4 Implementation Delta

本轮 V0.4 的工程变化：

- PRD 和技术文档旧版已归档到 `doc/prd/old version/2026-07-08-101018-737`。
- `src/app.js` 新增 `renderChapterFlow()`、`renderChapterFlowNode()`、`buildFlowMeta()`。
- `src/styles.css` 新增 `.chapter-flow`、`.chapter-flow-node`、`.flow-branches` 等样式。
- `tests/test_demo_contract.py` 增加章节 flow review hook 检查。

本轮没有解决：

- 空间化全分支 flowchart。
- 未解锁分支原因说明。
- 第一章轻教学。
- 内部用户测试记录模板。

## 27. V0.5 Implementation Delta

本轮 V0.5 的工程变化：

- PRD 和技术文档旧版已归档到 `doc/prd/old version/2026-07-08-101914-651`。
- `gamegen/demo_agent.py` 将 schema 升级为 `game_writer_demo_v0_5`，并为首章关键 observe 增加 `guidance` / `unlock_guidance`。
- `src/app.js` 新增 `activeGuidance`、`seenGuidance`、`highlightedChoices`、`renderGuidance()` 和 `maybeShowGuidance()`。
- `src/styles.css` 新增 `.guidance-panel` 与 `.choice-button.newly-unlocked` 样式。
- `gamegen/validator.py` 增加 guidance 字段校验。
- `tests/test_demo_contract.py` 增加首章叙事内轻教学契约检查。
- `generated/missing_phone_v0/game.json` 和 `game.yaml` 已由 V0.5 generator 重新生成。

本轮没有解决：

- 内部用户测试记录模板。
- 自动化浏览器测试进入常规 test suite。
- 全章节路径图的锁定原因说明。
- guidance 的强弱是否刚好，仍需真实试玩反馈。

## 28. V0.6 Implementation Delta

本轮 V0.6 的工程变化：

- PRD 和技术文档旧版已归档到 `doc/prd/old version/2026-07-08-102506-185`。
- 新增 `doc/testing/internal_playtest_record_template.md`，把第 14 节定性问题和量化指标变成可填写记录。
- 新增 `examples/playtests/internal_playtest_batch_template.json`，定义内部测试批次数据契约。
- 新增 `scripts/summarize_playtest_batch.py`，计算第 14 节 6 个量化指标并输出 pass/fail。
- 新增 `tests/test_playtest_summary.py`，覆盖达标批次、关键隐藏点卡死失败和空模板 INVALID。
- `README.md` 增加内部测试模板与汇总脚本入口。

本轮没有解决：

- 真实 5 到 8 人内部用户测试。
- 自动化浏览器测试进入常规 test suite。
- 全章节路径图的锁定原因说明。
- 内容 QA 的自动化公平性检测。

## 29. V0.7 Implementation Delta

本轮 V0.7 的工程变化：

- PRD 和技术文档旧版已归档到 `doc/prd/old version/2026-07-08-102957-278`。
- 新增 `scripts/content_qa_report.py`，输出 Markdown 风格内容 QA 报告，并在存在 error 时返回非零退出码。
- QA 检查覆盖主场景 obvious observe 入口、`hidden_optional` 解锁限制、choice 描述/outcome、consequence level、首场景 guidance。
- 新增 `tests/test_content_qa.py`，覆盖当前 demo 0 error、隐藏关键入口失败、主场景无 obvious 入口失败、choice 文案缺失失败。
- `README.md` 增加内容 QA 入口。

本轮没有解决：

- 真实 5 到 8 人内部用户测试。
- 浏览器自动化测试进入常规 test suite。
- 空间化全章节路径图和跨章因果线。
- LLM/人工语义 QA 对“是否公平、是否犹豫”的判断。

## 30. V0.8 Implementation Delta

本轮 V0.8 的工程变化：

- PRD 和技术文档旧版已归档到 `doc/prd/old version/2026-07-08-103534-623`。
- `src/app.js` 新增 `STATE_LABELS`、`buildChoiceBranchState()`、`describeRequirements()`、`describeRequirement()`。
- 章节 flowchart 分支新增状态：已选择、可选未走、已解锁未选、未解锁。
- 未解锁分支显示缺少的证据标签，避免玩家只看到灰色分支却不知道自己漏了什么类型的观察。
- `src/styles.css` 新增 `.flow-branches li.available`、`.unlocked`、`.locked` 样式。
- `tests/test_demo_contract.py` 增加静态 hook 检查。
- `README.md` 同步当前 flowchart 能力。

本轮没有解决：

- 真实 5 到 8 人内部用户测试。
- 浏览器自动化测试进入常规 test suite。
- 空间化全章节路径图和跨章因果线。
- 逐节点历史状态回放；当前锁定原因基于最终 runtime state 和已解锁 choice 记录。

## 31. V0.9 Implementation Delta

本轮 V0.9 的工程变化：

- PRD 和技术文档旧版已归档到 `doc/prd/old version/2026-07-08-103947-854`。
- `scripts/content_qa_report.py` 扩展 `validate_endings()` 和 `choice_writes_state()`。
- 内容 QA 现在检查 ending 标题、正文厚度、至少 3 个画像标签、是否被 choice 指向。
- 内容 QA 检查通往 ending 的 choice 是否为 `consequence_level: ending`，以及是否写入至少一个 state。
- `tests/test_content_qa.py` 新增结局不可达、结局 tag 不足、ending choice 不写状态的失败用例。
- `README.md` 同步内容 QA 的结局画像覆盖范围。

本轮没有解决：

- 真实 5 到 8 人内部用户测试。
- 浏览器自动化测试进入常规 test suite。
- 结局画像仍是字符串标签，不是完整结构化因果画像。
- 结局文案是否有情感重量，仍需人工 QA 或 playtest 判断。

## 32. V0.10 Implementation Delta

本轮 V0.10 的工程变化：

- PRD 和技术文档旧版已归档到 `doc/prd/old version/2026-07-08-104252-500`。
- 新增 `scripts/browser_smoke.py`，脚本自行启动临时静态服务并用 Python Playwright + Chrome 执行真实浏览器 smoke。
- 浏览器 smoke 使用 390x844 移动视口，验证：
  - 首次 observe 轻教学。
  - observe 解锁 choice 的高亮。
  - 第一章章节复盘 flowchart。
  - 未解锁分支原因。
  - 章节复盘刷新恢复。
  - 页面无横向溢出。
- `README.md` 增加浏览器 smoke 入口。

本轮没有解决：

- 真实 5 到 8 人内部用户测试。
- 真实移动设备测试。
- 无障碍键盘导航和屏幕阅读器检查。
- 完整多路径/多结局浏览器 E2E 矩阵。

## 33. V0.11 Implementation Delta

本轮 V0.11 的工程变化：

- PRD 和技术文档旧版已归档到 `doc/prd/old version/2026-07-08-104836-346`。
- `scripts/repair_game.py` 从 report-only 改为保守局部修复器。
- repair 支持：
  - 坏 `start_scene_id` 回退到第一个 scene。
  - 坏 `next_scene` 用近似 ID 或相邻 scene / ending 兜底。
  - 缺失 anchor `text_range` 补回父文本。
  - 错误 observe depth 修正为当前位置层级。
  - 坏 `unlocks_choices` 用近似 choice ID 修正，无法确定时删除。
- CLI 支持 `--out` 和 `--in-place`。
- 新增 `tests/test_repair_game.py` 覆盖常见局部生成错误。
- `README.md` 增加 repair 命令入口。

本轮没有解决：

- 显式 JSON schema。
- 模型输出 fixtures 和失败样本库。
- LLM 语义 repair prompt 版本管理。
- 新增复杂 choice 或重写剧情文案的能力。

## 34. V0.12 Implementation Delta

本轮 V0.12 的工程变化：

- PRD 和技术文档旧版已归档到 `doc/prd/old version/2026-07-08-105355-476`。
- 新增 `schemas/game.schema.json`，定义游戏数据的显式 Draft 2020-12 JSON Schema。
- 新增 `scripts/validate_json_schema.py`，用于校验生成物是否满足 schema contract。
- 新增 `tests/test_json_schema_contract.py`，覆盖当前生成物通过、缺少必填字段失败、非法 `consequence_level` 失败、observe fragment 缺 `nested_anchors` 失败。
- `README.md` 增加 schema 文件和 schema 校验命令。

本轮没有解决：

- 模型输出 fixtures 和失败样本库。
- schema 尚未接入 `generate_game.py` 的默认导出阻断链路。
- JSON Schema 不验证跨引用和语义质量；这些仍由 validator、content QA 和 playtest 处理。

## 35. V0.13 Implementation Delta

本轮 V0.13 的工程变化：

- PRD 和技术文档旧版已归档到 `doc/prd/old version/2026-07-08-105917-784`。
- 新增 `gamegen/schema_contract.py`，让生成器、CLI 和测试共享 schema 校验逻辑。
- `scripts/validate_json_schema.py` 改为复用 `gamegen.schema_contract`。
- `gamegen/demo_agent.py` 的 `export_game()` 在写文件前先运行 JSON Schema 和 `validate_game()`。
- 若 schema 或 validator 存在 error，导出会抛出 `ValueError`，不会写出 `game.json` 半成品。
- `generation_trace.jsonl` 增加 `schema` 字段。
- 新增 `tests/test_export_contract.py` 覆盖正常导出和坏数据阻断写文件。
- 重新生成 `generated/missing_phone_v0/generation_trace.jsonl`。

本轮没有解决：

- 模型输出 fixtures 和失败样本库。
- content QA 尚未并入生成默认阻断链路。
- LLM 语义 repair prompt 版本管理。

## 36. V0.14 Implementation Delta

本轮 V0.14 的工程变化：

- PRD 和技术文档旧版已归档到 `doc/prd/old version/2026-07-08-110530-731`。
- 新增 `examples/fixtures/generation_failures/fixture_cases.json`。
- fixture 使用 base game + mutation 描述坏生成物，避免复制整份大 JSON。
- fixture 覆盖：
  - schema gate：choice 缺 `consequence_level`。
  - validator gate：坏 `next_scene`。
  - repair gate：anchor 文本漂移、unlock choice typo、坏 `start_scene_id`。
- 新增 `tests/test_generation_failure_fixtures.py`，统一验证 schema/validator/repair 预期。
- `README.md` 增加生成失败样本入口。

本轮没有解决：

- 真实 LLM 输出样本库。
- prompt/model/provider 版本映射。
- LLM 语义 repair prompt 版本管理。
- 内容质量失败样本，例如“选择没有犹豫点”或“隐藏线索语义不公平”。

## 37. V0.15 Implementation Delta

本轮 V0.15 的工程变化：

- PRD 和技术文档旧版已归档到 `doc/prd/old version/2026-07-08-111048-389`。
- 新增 `prompts/manifest.json`，记录 active prompt set、生成入口、schema contract、可选 LLM polish prompt 摘要和允许/禁止修改范围。
- 新增 `gamegen/prompt_manifest.py`，提供 prompt manifest 读取和 active prompt set 校验。
- `gamegen/demo_agent.py` 的 `generation_trace.jsonl` 增加 `prompt_set` 字段。
- 新增 `tests/test_prompt_manifest.py`，覆盖 manifest 声明、trace 写入和非法 active prompt set。
- `README.md` 增加 Prompt Manifest 入口。

本轮没有解决：

- 真实 LLM 输出样本库。
- provider/model 版本记录。
- LLM 语义 repair prompt 版本管理。
- prompt 变更审批或 diff 流程。

## 38. V0.16 Implementation Delta

本轮 V0.16 的工程变化：

- PRD 和技术文档旧版已归档到 `doc/prd/old version/2026-07-08-111916-707`。
- `src/app.js` 为 observe anchor、choice button、章节继续按钮和重开按钮增加稳定 `data-*` 测试标识。
- 新增 `scripts/browser_e2e_matrix.py`，脚本复用临时静态服务与 Chrome/Chromium headless 移动视口，按结构 id 点击路径。
- 浏览器 E2E 矩阵覆盖 `ending_publish`、`ending_bury`、`ending_confront` 三个当前主结局。
- 每条路径验证两次章节复盘、结局标题、结局标签、结局画像区和移动端横向溢出。
- `tests/test_demo_contract.py` 增加静态契约，确保 E2E 矩阵覆盖全部当前主结局，且前端保留测试标识。
- `README.md` 增加多结局浏览器 E2E 命令入口。

本轮没有解决：

- 真实 LLM 输出样本库与脱敏归档。
- 多浏览器、真实移动设备和无障碍测试。
- 结局文案情感质量、选择犹豫感和隐藏线索公平性的人工判断。
- E2E 对刷新恢复、失败路径和存档异常的覆盖。
