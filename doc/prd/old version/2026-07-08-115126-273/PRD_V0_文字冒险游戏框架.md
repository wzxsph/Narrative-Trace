# PRD V0：文字版底特律式互动叙事游戏框架

版本：V0.20
日期：2026-07-08  
文档目标：定义第一版本文字游戏本身的框架、具体形态、用户 UI/UX  
保留文档：`PRD_AI文字冒险游戏.md` 继续保留，作为后续 AI 创作 Agent 和长期路线参考  
当前文档不定义：AI 创作 Agent、商业化、UGC 平台、完整技术架构

---

## 1. V0 一句话定义

V0 要做的不是普通文字小说，也不是自由输入的 AI Dungeon，而是：

> 一个竖屏手机界面的互动叙事游戏。玩家通过阅读背景文字，在文字中展开隐藏观察内容，层层发现嵌套线索，解锁新的选择，并在章节结尾看见自己走过的分支与未触达的可能。

更短一点：

> 玩家读一段文字，以为自己在看故事；点开文字里的异物，发现自己在调查世界；做出选择后，世界记住了他。

第一版本只证明这个核心体验：

```text
背景文字 -> 隐藏观察 -> 嵌套观察 -> 解锁 choice -> 承担后果 -> 章节流图复盘
```

---

## 2. 核心对标：文字版《Detroit: Become Human》学什么，不学什么

### 2.1 需要学习的不是 IP，而是形式

《Detroit: Become Human》的官方定位是强选择后果的叙事冒险。PlayStation 页面强调它是一个由选择与后果构成的情感旅程，玩家会进入三位关键角色的视角，选择会决定角色、城市甚至更大范围的命运。Quantic Dream 官方页面强调它有复杂分支、道德困境、角色生死、数千选择和多个结局。

V0 要学习的是这些形式：

- 章节制，而不是开放世界。
- 有限场景中的密集调查，而不是无限自由。
- 选择前的信息收集影响选择质量。
- 选择会影响角色关系、后续可选项、结局。
- 章节结束后用 flowchart 让玩家看见路径、错过内容和未解锁分支。
- 失败、遗漏、迟疑也能成为一种路径，而不是简单 game over。

V0 不学习这些东西：

- 不复刻仿生人题材、角色、剧情、场景。
- 不追求电影化 3D 演出。
- 不做 QTE 动作操作。
- 不在第一版做三主角大体量交叉叙事。
- 不承诺“每个微小选择都有巨大分支”，避免伪宣传。

### 2.2 Detroit 机制到文字版的转译

| Detroit 机制 | 玩家感受 | 文字版 V0 转译 |
|---|---|---|
| R2 扫描环境 | 我在主动观察，不只是看剧情 | 背景文字里的可展开隐藏观察点 |
| 调查线索提高成功率 | 观察会改变后续谈判/行动质量 | observe 解锁 choice 或改变 choice 文案/风险 |
| 对话选择 | 我必须在不完整信息中表态 | choice 区展示明确、不可撤销的行动 |
| 关系/公众舆论/软件不稳定 | 世界在暗中记录我的立场 | 隐藏状态轴，不显示数值，只给文本回声 |
| 倒计时场景 | 信息不完整但必须行动 | 章节压力条或倒计时节点 |
| 角色死亡后故事继续 | 失败不是终止，而是分支 | 失败、遗漏、沉默进入专属后果线 |
| 章节 flowchart | 我看见原来还有别的路 | 章节结束显示“痕迹图/路径图” |
| 杂志和背景资料 | 世界不是只围着主线转 | 可选深层文本补充世界观和价值冲突 |

### 2.3 对 Detroit 的批判性学习

Detroit 的强项是“选择后果被可视化”。它的 flowchart 会把玩家已经走过的路径和错过的路径展示出来，极强地刺激复盘和二周目欲望。

但它也暴露了分支叙事的结构问题：很多选择最终会重新合流，部分选择只是局部差异。外部评论也指出，Detroit 的分支会在若干大结局附近重新集中，flowchart 反而让这种“选择幻觉”变得可见。

所以 V0 的设计原则是：

> 不承诺每个点击都改变世界。只承诺每个关键选择都有可感知回声，每个关键 observe 都能改变玩家理解或解锁行动。

这句话比“所有选择都会影响结局”更诚实，也更可执行。

---

## 3. 产品哲学：文字游戏到底是什么

### 3.1 它不是“文本 + 按钮”

如果只是给玩家一段文字，再给三个按钮，那它是低成本视觉小说，不是我们要做的东西。

本产品的文字有三层身份：

- 叙事文本：告诉玩家当前发生了什么。
- 可调查界面：文字本身可以被点开、展开、层层深入。
- 状态入口：玩家点开的内容会改变他知道什么、能做什么、未来会如何被回应。

因此 V0 的核心不是“选择”，而是“阅读变成调查”。

### 3.2 玩家真正玩的不是剧情，而是不确定性

玩家的乐趣不来自“我可以点很多选项”，而来自：

- 我注意到了一句不对劲的话。
- 我点开它，发现里面藏着另一层信息。
- 我用这层信息解锁了一个新行动。
- 我做了这个行动，但不确定后面会不会反噬。
- 后来某个角色的态度、某个结局标签或某个章节节点回应了它。

这个过程的本质是：

```text
怀疑 -> 查证 -> 理解 -> 表态 -> 承担
```

### 3.3 observe 是认识世界，choice 是改变世界

V0 里必须严格区分 observe 和 choice。

`observe`：

- 是可逆的。
- 主要改变玩家知道什么。
- 可以解锁更深 observe。
- 可以解锁新的 choice。
- 可以写入隐藏状态，但不能直接造成重大不可逆后果，除非明确提示风险。

`choice`：

- 通常不可逆。
- 主要改变世界状态。
- 会进入新节点、改变关系、锁定分支或影响结局。
- 必须让玩家感到自己在承担立场。

一句话：

> observe 让玩家看见更多；choice 让玩家失去某些可能。

---

## 4. V0 产品范围

### 4.1 V0 只定义玩家端游戏

V0 只做：

- 竖屏手机 UI。
- 章节制文字互动叙事。
- 背景文字隐藏 observe。
- observe 嵌套展开。
- observe 解锁 choice。
- 隐藏状态与文本回声。
- 章节结束路径图。
- 结局复盘。

V0 不做：

- AI 自动生成剧本。
- 作者工具后台。
- 玩家自由输入行动。
- 复杂 3D 或视频演出。
- 商业化系统。
- 社交分享和排行榜。
- 大规模多主角长篇。

### 4.2 推荐内容规模

V0 Demo 推荐规模：

- 章节数：3 章。
- 单次通关时长：20 到 30 分钟。
- 每章场景节点：3 到 5 个。
- 每个节点背景文字：1 到 3 屏。
- 每个节点隐藏 observe：5 到 10 个。
- 嵌套 observe 深度：最多 3 层。
- 每个节点可见 choice：2 到 4 个。
- 主结局：3 到 4 个。
- 结局标签：6 到 10 个。

第一版宁可短，也要让玩家相信：

> 我点开的东西不是废信息，我做过的事不会消失。

---

## 5. 用户体验叙事

### 5.1 用户第一分钟

用户打开游戏，看到的不是宣传页，而是一个竖屏手机界面。

第一屏应该完成四件事：

1. 立刻建立身份：玩家正在查看一部不属于自己的手机，或一套被授权/被迫接触的记录系统。
2. 立刻建立压力：远程清除、倒计时、来电、追踪、系统锁定、他人逼问。
3. 立刻建立异常：背景文字里有一处看似普通但可展开的内容。
4. 立刻建立反馈：玩家点开隐藏 observe 后，界面出现新信息，并解锁一个新 choice。

第一分钟示例：

```text
任务：在 06:00 前确认失踪者最后联系的人。

背景：
手机亮起，锁屏通知停在 02:13。
一条未发送的短信只剩下半句：“如果我没回来，不要相信陈...”
屏幕右上角显示：远程清除排队中。

可点隐藏内容：
02:13
未发送的短信
陈...
远程清除
```

玩家点开“02:13”，看到：

```text
系统日志显示，02:13 时手机短暂开启定位。
定位地点不是林的家，而是城北废弃地铁站。
```

界面提示：

```text
新选择已出现：前往废弃地铁站
```

### 5.2 单个节点的体验节奏

每个节点的体验节奏是：

```text
看见背景 -> 点开可疑文字 -> 发现隐藏信息 -> 继续点开深层信息 -> 选择是否行动
```

节点内不要一开始给玩家所有选择。V0 的关键体验是“选择通过观察长出来”。

### 5.3 章节结束体验

每章结束后，玩家进入“路径图”。

路径图不是普通总结，而是 Detroit flowchart 的文字版：

- 显示玩家进入过的节点。
- 显示已打开的 observe。
- 显示由 observe 解锁的 choice。
- 显示已选择的 choice。
- 显示灰色未发现节点，但不直接剧透内容。
- 标记“跨章节影响”，但不展示完整公式。

目标感受：

> 原来刚才那句话真的能点开。原来我漏掉了一个线索。原来我还可以走另一条路。

---

## 6. UI/UX 总体结构

### 6.1 竖屏布局

V0 使用固定竖屏手机布局，优先适配 390x844 到 430x932 的手机视口。

基础结构：

```text
┌────────────────────┐
│ 顶部状态栏          │
│ 章节 / 任务 / 压力  │
├────────────────────┤
│                    │
│ 主文本区            │
│ 背景文字 + 隐藏点   │
│                    │
├────────────────────┤
│ observe 展开层      │
│ 证据卡 / 嵌套内容   │
├────────────────────┤
│ choice 行动区       │
│ 可见选择按钮        │
└────────────────────┘
```

### 6.2 顶部状态栏

顶部状态栏展示：

- 当前章节名。
- 当前任务。
- 压力提示，例如倒计时、追踪进度、警报状态。
- 轻量系统状态，例如“已发现 3/7 条线索”。

不展示：

- 好感度数值。
- 结局分数。
- 完整变量名。

状态栏的作用是制造处境压力，不是暴露系统公式。

### 6.3 主文本区

主文本区承载背景文字。背景文字中包含隐藏 observe 入口。

隐藏入口的设计原则：

- 它们不是独立按钮，而是嵌入文字的可疑片段。
- 它们可以是时间、地点、人名、物件、系统提示、语气异常、被删除文本、重复出现的词。
- 关键路径入口必须有可发现的视觉暗示。
- 非关键彩蛋入口可以更隐蔽。

入口视觉状态：

| 状态 | 表现 | 用途 |
|---|---|---|
| 未打开 | 轻微下划线、浅色标记或可疑留白 | 告诉玩家这里可查 |
| 已打开 | 颜色变暗、旁边出现小标记 | 防止重复迷路 |
| 有深层内容 | 展开卡片内出现新的可疑片段 | 支持嵌套观察 |
| 已影响 choice | 出现“新行动可用”的轻提示 | 建立 observe 到 choice 的因果 |

### 6.4 observe 展开层

点击隐藏入口后，不跳新页面，优先在当前上下文中展开一张“证据卡”。

证据卡包含：

- 标题：被观察对象。
- 正文：新信息。
- 状态变化提示：只用自然语言表达，不显示变量。
- 嵌套 observe：卡片正文中的新可点内容。
- 收起/返回：保留玩家阅读位置。

示例：

```text
[02:13]
系统日志显示，02:13 时手机短暂开启定位。
定位地点不是林的家，而是城北废弃地铁站。
日志后有一段 4 秒空白，像是被手动剪掉。

可继续观察：
城北废弃地铁站
4 秒空白
```

### 6.5 choice 行动区

choice 行动区固定在底部，展示当前可执行行动。

规则：

- choice 必须是清晰行动，不是抽象态度。
- choice 数量默认 2 到 4 个。
- 新解锁 choice 从底部滑入或高亮一次。
- 不可逆 choice 需要二次确认或明显文案提示。
- choice 的短标签和长说明要分离，避免按钮过长。

示例：

```text
前往废弃地铁站
你会离开安全地点，可能错过后续来电。

联系陈警官
你会把目前线索交给警方，但陈可能正是短信里被警告的人。

删除远程清除队列
你会保住手机内容，也会留下入侵记录。
```

### 6.6 章节路径图

章节路径图是 V0 的关键复盘界面。

它至少包含：

- 本章主路径。
- 已发现 observe。
- 未发现 observe 的灰色占位。
- 已解锁 choice。
- 未解锁 choice 的灰色占位。
- 已触发跨章节影响的标记。

路径图不应该像开发调试图，而应该像“案件痕迹图”。

视觉语言：

- 已经历节点：实线。
- 未发现节点：虚线或灰色。
- 关键 choice：粗线。
- 跨章节影响：小标签，例如“后续影响”。
- 失败/遗漏路径：保留显示，不羞辱玩家。

---

## 7. 隐藏 observe 系统

### 7.1 定义

隐藏 observe 是嵌入背景文字或证据卡文本中的可展开内容。

它不是传统按钮，也不是完全不可见的像素点。它是一种“文字里的缝隙”：玩家通过阅读发现异常，通过点击展开更多信息。

### 7.2 三层隐藏

V0 定义三层隐藏深度：

```text
L1：背景层隐藏
L2：证据卡隐藏
L3：深层证据隐藏
```

L1 示例：

```text
背景文字：“未发送短信只剩半句：不要相信陈...”
可点：“陈...”
```

L2 示例：

```text
点开“陈...”后：
通讯录里有三个姓陈的人，但只有一个号码被手动改过备注。
可点：“手动改过备注”
```

L3 示例：

```text
点开“手动改过备注”后：
备注修改时间是 02:13，和定位开启时间一致。
解锁 choice：“质问陈警官”
```

### 7.3 嵌套深度限制

V0 最大嵌套深度为 3。

原因：

- 超过 3 层会让玩家迷路。
- 移动端阅读空间有限。
- 深层结构难以维护。
- 玩家会从“调查”变成“翻抽屉”。

如果某条线索需要超过 3 层，应该拆成多个节点或多个 observe，而不是继续嵌套。

### 7.4 关键路径与可发现性

隐藏 observe 分三类：

| 类型 | 可发现性 | 是否影响主线 |
|---|---|---|
| 关键线索 | 明显暗示，必须公平 | 可以解锁关键 choice |
| 补充线索 | 中等暗示 | 改变文案、风险、关系 |
| 彩蛋线索 | 弱暗示 | 不影响主线和关键结局 |

强规则：

> 影响主结局的隐藏 observe，不能完全不可见。

用户可以漏掉它，但不能因为 UI 不公平而漏掉它。

### 7.5 observe 解锁 choice 的规则

observe 可以通过以下方式影响 choice：

1. 新增 choice：发现地点后出现“前往地点”。
2. 改写 choice：原本“联系陈警官”变成“带着录音质问陈警官”。
3. 降低风险：同一个行动因为掌握线索而更安全。
4. 开启第三方案：原本只有 A/B，发现线索后出现 C。
5. 锁定选择：发现真相后，某个欺骗选项不再符合角色立场。

V0 优先使用 1、2、4。

### 7.6 observe 的反馈

observe 不能只是弹出一段文字。每次有效 observe 都要让玩家感到系统发生了变化。

反馈方式：

- 新 choice 出现。
- 任务描述更新。
- 路径图节点点亮。
- 文本区某个旧句子被追加解释。
- 角色消息发生变化。
- 压力状态变化。

---

## 8. choice 系统

### 8.1 choice 的定义

choice 是玩家把理解转化为行动的时刻。

合格 choice 应该具备：

- 明确行动对象。
- 明确即时意图。
- 隐含长期代价。
- 至少一个状态变化。
- 至少一个未来回声。

### 8.2 choice 类型

V0 定义七类 choice：

| 类型 | 含义 | 示例 |
|---|---|---|
| investigate | 深入调查 | 破解备份、前往现场 |
| reveal | 公开/告知 | 把录音交给警方 |
| conceal | 隐瞒/删除 | 删除定位记录 |
| confront | 对质 | 质问陈警官 |
| trust | 信任 | 接受林的求救 |
| betray | 背叛 | 把藏身点告诉公司 |
| wait | 等待/不行动 | 继续观察，不回复消息 |

等待也是行动。Detroit 的一个重要启发是：失败、迟疑、不完成目标也可以形成路径。V0 要允许“什么都不做”在少数节点成为有意义 choice。

### 8.3 不可逆提示

不可逆 choice 需要明确提醒，但不能把氛围破坏成系统警告。

推荐文案：

```text
这会留下记录。
```

```text
发出后，你无法撤回这条消息。
```

```text
如果离开，手机可能在你回来前被清除。
```

不推荐文案：

```text
警告：此操作将修改变量 privacy_violated。
```

### 8.4 choice 的后果反馈

后果反馈分三层：

1. 即时反馈：按钮后立刻出现结果文字。
2. 延迟反馈：后续节点或章节出现回声。
3. 复盘反馈：路径图和结局页显示影响轨迹。

V0 不要求每个 choice 都改变主结局，但要求关键 choice 至少有延迟反馈。

---

## 9. 状态系统

### 9.1 状态不等于数值面板

玩家不应该看到完整变量表。状态系统的作用不是让玩家优化分数，而是让世界记住玩家。

V0 状态分四类：

```text
clue：玩家知道什么
stance：玩家倾向什么立场
relationship：别人如何看待玩家
pressure：外部压力如何变化
```

### 9.2 推荐状态轴

```yaml
state:
  clues:
    station_location: false
    chen_alias_modified: false
    remote_wipe_source: false
  stance:
    truth_first: 0
    protect_person: 0
    obey_system: 0
  relationships:
    chen:
      trust: 0
      suspicion: 0
    lin:
      trust: 0
      bond: 0
  pressure:
    remote_wipe_seconds: 360
    company_alert: 0
```

### 9.3 状态反馈原则

状态变化不显示为数值，而显示为世界反应。

示例：

```text
不显示：陈 trust -1
显示：陈的回复慢了三秒，只发来一句：“你刚才为什么会知道这个？”
```

```text
不显示：company_alert +2
显示：屏幕顶部短暂闪过一个新图标，像是远程会话正在重连。
```

---

## 10. 章节框架

### 10.1 单章结构

每章由四段组成：

```text
进入处境 -> 观察扩展 -> 关键选择 -> 路径复盘
```

每章必须有一个小问题。

示例：

```text
第一章：你是否愿意侵犯隐私来寻找真相？
第二章：你是否愿意相信一个可能撒谎的人？
第三章：当真相会伤害无辜者时，你是否公开它？
```

### 10.2 单节点结构

每个节点包含：

```yaml
Scene:
  id: string
  title: string
  task: string
  pressure: string
  background_blocks: BackgroundBlock[]
  choices: Choice[]
  exit_conditions: Condition[]
```

### 10.3 背景文字结构

```yaml
BackgroundBlock:
  id: string
  text: string
  observe_anchors: ObserveAnchor[]
```

### 10.4 隐藏观察结构

```yaml
ObserveAnchor:
  id: string
  text_range: string
  label: string
  discoverability: enum[obvious, subtle, hidden_optional]
  depth: number
  opens_fragment: ObserveFragment
  effects: Effect[]
  unlocks_choices: string[]
```

```yaml
ObserveFragment:
  id: string
  title: string
  body: string
  nested_anchors: ObserveAnchor[]
  evidence_tags: string[]
```

### 10.5 选择结构

```yaml
Choice:
  id: string
  label: string
  description: string
  requirements: Condition[]
  effects: Effect[]
  next_scene: string
  irreversible: boolean
  consequence_level: enum[local, chapter, global, ending]
```

### 10.6 示例：一个完整节点

```yaml
Scene:
  id: ch01_phone_lock
  title: 锁屏上的半句话
  task: 在远程清除前确认林最后联系的人。
  pressure: 远程清除 06:00
  background_blocks:
    - id: bg_01
      text: >
        手机亮起。未发送短信停在输入框里：
        “如果我没回来，不要相信陈...”
        顶部通知显示：远程清除已排队。
      observe_anchors:
        - id: obs_unsent_sms
          text_range: 未发送短信
          label: 查看短信草稿
          discoverability: obvious
          depth: 1
          opens_fragment:
            id: frag_unsent_sms
            title: 未发送的短信
            body: >
              草稿创建于 02:13，最后一次编辑停在“陈”字后。
              输入法候选里，第一个词是“陈警官”，第二个词是“陈述”。
            nested_anchors:
              - id: obs_0213
                text_range: 02:13
                label: 对照系统日志
                discoverability: subtle
                depth: 2
                opens_fragment:
                  id: frag_0213_log
                  title: 02:13 的系统日志
                  body: >
                    02:13 时手机短暂开启定位，地点是城北废弃地铁站。
                    4 秒后，定位记录被手动截断。
                  nested_anchors:
                    - id: obs_trimmed_gap
                      text_range: 手动截断
                      label: 检查截断痕迹
                      discoverability: subtle
                      depth: 3
                      opens_fragment:
                        id: frag_trimmed_gap
                        title: 被截断的 4 秒
                        body: >
                          截断命令来自一个备注为“陈”的联系人号码。
                          这不是系统自动清理。
                        nested_anchors: []
                      effects:
                        - set: { clues.chen_trimmed_location: true }
                      unlocks_choices:
                        - choice_confront_chen
                effects:
                  - set: { clues.station_location: true }
                unlocks_choices:
                  - choice_go_station
          effects:
            - set: { clues.unsent_warning: true }
          unlocks_choices: []
  choices:
    - id: choice_call_chen
      label: 联系陈警官
      description: 你会把目前情况告诉他，但短信正在警告你不要相信“陈”。
      requirements: []
      effects:
        - add: { relationships.chen.trust: 1 }
      next_scene: ch01_call_chen
      irreversible: true
      consequence_level: chapter
    - id: choice_go_station
      label: 前往废弃地铁站
      description: 你会离开安全地点，手机可能在路上被清除。
      requirements:
        - equals: { clues.station_location: true }
      effects:
        - add: { stance.truth_first: 1 }
      next_scene: ch02_station
      irreversible: true
      consequence_level: global
    - id: choice_confront_chen
      label: 带着截断记录质问陈警官
      description: 你掌握了他改动定位的痕迹，但摊牌会让他知道你已经查到这里。
      requirements:
        - equals: { clues.chen_trimmed_location: true }
      effects:
        - add: { relationships.chen.suspicion: 2 }
        - add: { pressure.company_alert: 1 }
      next_scene: ch01_confront_chen
      irreversible: true
      consequence_level: global
```

---

## 11. 结局与复盘

### 11.1 结局不是判分

结局页不说“好结局/坏结局”，而是给玩家一份行动画像。

结局页回答四个问题：

```text
你最终保护了谁？
你最终伤害了谁？
你选择相信什么？
哪些早期观察改变了这条路？
```

### 11.2 结局页结构

```text
主结局标题
一段结局叙事
关键选择回放
关键 observe 回放
关系/立场变化的自然语言总结
未发现路径提示
重新开始/回到章节路径图
```

### 11.3 路径图与结局图关系

章节路径图解决：

> 我刚才还有哪些地方没探索？

结局图解决：

> 我一路上成为了什么样的人？

两者不能混成一个界面。

---

## 12. 内容设计规则

### 12.1 背景文字规则

每段背景文字必须有调查价值。

合格背景文字：

- 有明确处境。
- 有至少 2 个可疑观察点。
- 有至少 1 个情绪或价值压力。
- 不超过移动端一屏半。

不合格背景文字：

- 大段设定说明。
- 没有可互动内容。
- 只是气氛描写。
- 玩家读完不知道该怀疑什么。

### 12.2 hidden observe 规则

每个关键 observe 必须回答：

```text
它让玩家知道了什么？
它改变了玩家对谁的判断？
它解锁或改变了什么 choice？
它未来在哪里被回应？
```

如果四个问题都答不上来，就删除或改成普通文本。

### 12.3 choice 规则

每个关键 choice 必须回答：

```text
玩家为什么会想选它？
玩家为什么会犹豫？
它改变了什么状态？
它关闭了什么可能？
它在后续哪里回声？
```

### 12.4 节奏规则

单节点推荐节奏：

- 30 秒理解处境。
- 60 到 120 秒探索隐藏 observe。
- 15 到 30 秒做 choice。
- 10 秒接收后果反馈。

如果一个节点需要玩家阅读 5 分钟还不能做决定，它太重。

---

## 13. 可用性与公平性

### 13.1 隐藏不等于刁难

V0 最容易失败在“隐藏内容”上。

错误做法：

- 完全没有视觉暗示。
- 关键线索藏在普通标点或随机空白。
- 玩家必须乱点才能发现。
- 漏掉线索直接坏结局。

正确做法：

- 关键线索有文本异常或视觉暗示。
- 漏掉线索会进入另一条合理路径，而不是惩罚。
- 章节路径图告诉玩家确实漏过东西。
- 二周目能明显更快发现另一种解法。

### 13.2 新手引导

第一章第一个节点必须教学，但不能做教程弹窗堆叠。

推荐方式：

- 第一个隐藏 observe 使用明显样式。
- 点开后展示“文字中有些内容可以展开”。
- 第一次解锁 choice 时展示“观察可能改变可选行动”。
- 之后不再反复提示。

### 13.3 可访问性

V0 至少满足：

- 所有隐藏 observe 不能只靠颜色区分。
- 可点击文本要有下划线、标记或触觉/动画反馈。
- 字号可读，正文不低于 16px。
- 底部 choice 触控高度不低于 44px。
- 长 choice 使用标题 + 描述，不把整段塞进按钮。

---

## 14. 成功标准

### 14.1 定性成功

V0 成功时，测试用户会说：

- “我发现原来那句话可以点。”
- “我漏了一个线索，怪不得后面不能选。”
- “这个选择不是单纯好坏，我有点犹豫。”
- “我想重玩看看另一条线。”
- “结局里提到我前面做过的事，这个很爽。”

V0 失败时，测试用户会说：

- “我不知道哪里能点。”
- “我就是一路点按钮。”
- “选择好像没区别。”
- “这像小说，不像游戏。”
- “隐藏内容太阴间，我只能乱点。”

### 14.2 量化验收

首轮 5 到 8 名内部测试用户：

- 80% 能在第一分钟理解“文字可以展开”。
- 70% 能在第一章主动发现至少 60% 的关键 observe。
- 70% 能说出一个 observe 解锁 choice 的例子。
- 60% 能说出一个选择带来的后续影响。
- 50% 愿意查看路径图并表达重玩意愿。
- 0 人因为关键隐藏点完全不可发现而卡死。

---

## 15. V0 信息架构清单

必须有：

- 开始游戏。
- 章节主界面。
- 背景文字区。
- observe 展开卡。
- 嵌套 observe。
- choice 底部行动区。
- 后果反馈。
- 章节路径图。
- 结局页。
- 重新开始或回到章节。

暂不做：

- 账号。
- 云存档。
- 分享图。
- 成就系统。
- 外部作者编辑器。
- AI 生成入口。

---

## 16. V0 资料来源

底特律机制参考：

- PlayStation 官方页：choice and consequences、三位角色、选择影响角色和城市命运  
  https://www.playstation.com/en-us/games/detroit-become-human/
- Quantic Dream 官方页：复杂分支、道德困境、角色生死、数千选择和多个结局  
  https://www.quanticdream.com/en/detroit-become-human
- PlayStation Blog：三主角视角、章节 flowchart、错过路径与复盘价值  
  https://blog.playstation.com/2019/01/01/editors-choice-why-detroit-become-human-is-one-of-the-best-games-of-2018/
- WIRED 评测：失败也能打开独特路径、flowchart 呈现重要行动、叙事仍有总体框架  
  https://www.wired.com/story/detroit-become-human-review/
- Detroit Wiki：角色死亡后故事继续、早期选择锁定后续对话/行动、flowchart 和回滚机制  
  https://detroit-become-human.fandom.com/wiki/Detroit%3A_Become_Human
- The Hostage 章节资料：调查线索影响成功概率、调查内容解锁谈判选项  
  https://detroit-become-human.fandom.com/wiki/The_Hostage
- PowerPyx Partners 攻略：调查、重构、关系影响、跨章节影响示例  
  https://www.powerpyx.com/detroit-become-human-partners-walkthrough-100/
- Interactive Pasts 批评：分支叙事会重新合流，flowchart 暴露选择幻觉  
  https://interactivepasts.com/how-games-tell-tales-part-3-detroit-become-human-freedom-of-choice-and-intended-play/

本地参考：

- `/home/samsong/Desktop/game_writer/reference/gpt的前期调研/gpt的前期调研.md`
- `/home/samsong/Desktop/game_writer/reference/gpt的前期调研/本工具前期的大道探索.md`
- `/home/samsong/Desktop/game_writer/doc/prd/PRD_V0_产品推衍记录.md`
- `/home/samsong/Desktop/game_writer/doc/prd/agent_game_generation_technical_design_v0.md`

---

## 17. 当前 Demo 纵切状态与产品级差距

本节用于把当前工程状态与本 PRD 对齐。它不是降低 V0 目标，而是明确目前 demo 已证明什么、还没有证明什么。

### 17.1 当前已实现的 Demo 纵切

当前工程已有一个可运行 demo：

- 入口：`/home/samsong/Desktop/game_writer/index.html`
- 生成内容：`/home/samsong/Desktop/game_writer/generated/missing_phone_v0/game.json`
- 生成脚本：`/home/samsong/Desktop/game_writer/scripts/generate_game.py`
- JSON Schema：`/home/samsong/Desktop/game_writer/schemas/game.schema.json`
- Prompt Manifest：`/home/samsong/Desktop/game_writer/prompts/manifest.json`
- 模型输出样本归档脚本：`/home/samsong/Desktop/game_writer/scripts/archive_model_output_sample.py`
- 模型输出样本校验脚本：`/home/samsong/Desktop/game_writer/scripts/validate_model_output_archive.py`
- Schema 校验脚本：`/home/samsong/Desktop/game_writer/scripts/validate_json_schema.py`
- 局部修复脚本：`/home/samsong/Desktop/game_writer/scripts/repair_game.py`
- 校验脚本：`/home/samsong/Desktop/game_writer/scripts/validate_game.py`
- 内容 QA 脚本：`/home/samsong/Desktop/game_writer/scripts/content_qa_report.py`
- 冒烟游玩脚本：`/home/samsong/Desktop/game_writer/scripts/smoke_playthrough.py`
- 浏览器冒烟脚本：`/home/samsong/Desktop/game_writer/scripts/browser_smoke.py`
- 多结局浏览器 E2E 矩阵：`/home/samsong/Desktop/game_writer/scripts/browser_e2e_matrix.py`
- 生成失败样本库：`/home/samsong/Desktop/game_writer/examples/fixtures/generation_failures/fixture_cases.json`
- 模型输出样本库：`/home/samsong/Desktop/game_writer/examples/fixtures/model_outputs/sample_manifest.json`

它已经覆盖本 PRD 的关键体验闭环：

```text
背景文字 -> 隐藏 observe -> 嵌套 observe -> 解锁 choice -> 承担后果 -> 路径图/结局复盘
```

已具备：

- 竖屏手机 UI。
- 背景文字中的可点击 observe anchor。
- observe 展开证据卡。
- 最多三层嵌套 observe。
- observe 写入状态并解锁 choice。
- choice 写入状态并进入下一场景或结局。
- 结局页。
- 案件痕迹图/路径图。
- 章节结束复盘屏：跨章节选择后先复盘本章观察、行动、状态回声与未触达可能，再进入下一章。
- 章节复盘基础 flowchart：章节结束时展示本章节点、已到达状态、观察/行动计数和分支列表。
- 章节 flowchart 分支解释：已选择、可选未走、已解锁未选、未解锁原因会在复盘中显示。
- 第一章叙事内轻教学：首次展开 observe 时出现剧情内系统反馈，首次由 observe 长出行动时高亮新增 choice。
- 结局行动画像：结局页展示关键 observe、关键 choice、最终立场与结局标签。
- 本地保存/恢复：刷新页面后可恢复当前场景、已展开观察、选择路径、章节复盘或结局状态。
- 内容规模达到 3 章 x 每章 3 个主场景，共 9 个主场景。
- 隐藏关系变量的叙事回声：`relationships.chen.trust`、`relationships.chen.suspicion`、`relationships.lin.bond` 会在后续场景中触发条件文本。
- 生成产物的结构校验。
- 自动内容 QA 检查：关键场景必须有明显 observe 入口，`hidden_optional` 不能解锁章节/全局后果 choice，choice 必须有描述和后果文案，结局必须可达并具备画像标签。
- 浏览器级移动视口 smoke：验证轻教学、新行动高亮、章节复盘、未解锁原因、刷新恢复、坏存档 fallback 和移动端横向溢出。
- 多路径/多结局浏览器 E2E：使用真实浏览器点击 3 条路径，覆盖 `ending_publish`、`ending_bury`、`ending_confront`，并检查章节复盘、结局标签、结局画像区、结局刷新恢复、重新开始和移动端横向溢出。
- 局部 repair：能修复常见生成硬伤，包括坏 `start_scene_id`、坏 `next_scene`、缺失 anchor 文本、错误 observe depth、坏 unlock choice 引用。
- 显式 JSON Schema 契约：验证游戏数据的字段形状、必填项、枚举、递归 observe 结构和基础类型。
- 生成导出门禁：`generate_game.py` 默认在写文件前通过 JSON Schema 和结构 validator，失败时阻断导出。
- 生成失败 fixture：用 mutation case 覆盖 schema gate、validator gate、repair gate 的典型坏输出。
- Prompt/模型版本管理：`generation_trace.jsonl` 记录 `prompt_set`、`provider`、`model`，为未来真实 LLM 输出样本提供追溯维度。
- 模型输出样本归档合同：真实模型输出进入样本库前必须脱敏，并记录 provider、model、prompt_set、source、schema、checksum。
- 模型输出样本库校验门禁：检查 manifest、文件引用、prompt_set 声明、checksum 和未脱敏敏感信息，避免样本库本身变成风险源。
- 基础测试入口：`/home/samsong/Desktop/game_writer/tests/test_demo_contract.py`
- 内部测试记录模板：`/home/samsong/Desktop/game_writer/doc/testing/internal_playtest_record_template.md`
- 内部测试批次模板：`/home/samsong/Desktop/game_writer/examples/playtests/internal_playtest_batch_template.json`
- 内部测试汇总脚本：`/home/samsong/Desktop/game_writer/scripts/summarize_playtest_batch.py`
- 运行说明：`/home/samsong/Desktop/game_writer/README.md`

### 17.2 当前 Demo 与完整 V0 的差距

当前 demo 是工程纵切，不是完整产品级 V0。

主要差距：

- 内容规模已达到 3 章 x 每章 3 个主场景，但真实阅读时长、节奏和质量尚未通过用户测试证明能稳定达到 15 到 20 分钟以上。
- 章节复盘已从轻量列表升级为基础 flowchart，并能解释未解锁分支缺少的证据；但还不是完整 Detroit 式全路径图，缺少节点坐标、二周目提示和跨章路径关系。
- 隐藏状态已经影响 choice、章节复盘、场景回声和结局画像，但 NPC 关系回声仍是基础实现，尚未通过用户测试证明“可感知且不黑箱”。
- 结局行动画像已能被三条浏览器路径稳定抵达并展示基本结构，但还没有充分回答“保护了谁、伤害了谁、相信了什么、哪些 observe 改变路径”。
- 第一章轻教学已有基础实现，但还没有通过内部用户测试证明玩家能稳定理解“文字可展开”和“观察会长出行动”。
- 已建立内部测试记录模板和批次汇总脚本，但尚未实际完成 5 到 8 名内部用户测试，因此第 14 节量化指标尚未验证。
- 保存/恢复已支持单机本地状态，并已有浏览器 smoke 覆盖章节复盘刷新恢复、坏 JSON 存档 fallback 和旧版本存档 fallback；但还没有多存档、云端同步、版本迁移或异常恢复 UI。
- 浏览器自动化已覆盖核心路径、三主结局路径、结局刷新恢复和重新开始，但还没有真实移动设备、多浏览器、触控细节和无障碍验收。
- 内容 QA 已有基础自动检查，但还不能判断“选择是否真的让人犹豫”或“隐藏线索是否在语义上公平”。
- 结局画像已有自动完整性检查，但还不能判断结局是否有足够情感重量。
- 已有模型输出样本归档工具和空样本库合同，但还没有沉淀真实 LLM 输出样本，因此不能证明 agent 生成链路在真实模型下稳定。

### 17.3 下一轮产品优先级

下一轮不要先扩技术栈，应优先补强体验闭环：

1. 组织 5 到 8 名内部用户测试，填充 playtest 批次数据，用第 14 节指标判断 demo 是否真正跑通。
2. 检查 9 场景内容节奏，删掉只是在“加长度”的场景，保留真正改变理解或行动的场景。
3. 继续打磨关系回声文案，确保它是文本暗示，不是数值播报。
4. 将章节基础 flowchart 继续升级为更完整的路径复盘，包括空间化布局、二周目提示与跨章影响。
5. 继续补移动端真实设备与无障碍验收，验证触控、滚动、可读性和屏幕阅读器基础体验。

### 17.4 产品级距离判断

距离“完整产品级产品”仍有明显距离。

当前处于：

```text
中等长度可运行工程纵切 / medium-length playable vertical slice
```

尚未达到：

```text
可发布 MVP / shippable MVP
```

产品级至少还需要：

- 内容生产流程稳定，能持续生成多章内容而不崩坏，并有真实模型输出样本支撑失败回归。
- 前端 UI 在移动端真实设备上验证触控、滚动、可读性。
- 路径图、结局画像、新手引导形成更强闭环，并通过真实玩家数据验证它们不是“看起来完整”。
- 保存/重开能力从本地单存档升级到可解释、可恢复、可迁移的产品级存档。
- 有一轮内部测试数据，证明 observe/choice/路径图确实被用户理解。
- 有更严格的语义内容 QA，避免隐藏内容变成乱点找按钮。

### 17.5 V0.1 版本变更记录

V0.1 相比 V0 的实质变化：

- 旧版 PRD 和技术文档已归档到 `/home/samsong/Desktop/game_writer/doc/prd/old version/2026-07-08-093752-079`。
- 前端加入本地保存/恢复，避免刷新后丢失当前路径。
- 前端加入章节结束复盘屏，让跨章节选择产生节奏性回看。
- 结局页升级为基础“行动画像”，展示观察、行动、状态回声和结局标签。
- 工程加入 `tests/` 和 `README.md`，让 demo 生成、校验、冒烟和人工游玩流程更可复现。

### 17.6 V0.2 版本变更记录

V0.2 相比 V0.1 的实质变化：

- 旧版 V0.1 PRD 和技术文档已归档到 `/home/samsong/Desktop/game_writer/doc/prd/old version/2026-07-08-094711-784`。
- deterministic demo 从 3 个主场景扩展为 9 个主场景，满足 3 章 x 每章 3 个主场景的结构目标。
- 保留原有核心路径，但在每章中加入更细的调查、过渡和道德判断节点。
- 冒烟路径升级为完整穿过 9 场景的主路径，而不是跳章路径。
- 测试升级：要求 schema 为 `game_writer_demo_v0_2`、总场景数为 9、每章 3 场景、每个场景至少有一个 observe 解锁本场景 choice。

V0.2 不能被误读为产品级完成：

- 场景数量达标不等于节奏达标。
- 9 场景仍是单一案件样章，不是可持续内容生产体系。
- 还缺少真实用户读完后的理解、疲劳、复盘欲望数据。

### 17.7 V0.3 版本变更记录

V0.3 相比 V0.2 的实质变化：

- 旧版 V0.2 PRD 和技术文档已归档到 `/home/samsong/Desktop/game_writer/doc/prd/old version/2026-07-08-100034-256`。
- 新增 `state_echoes` 字段，允许场景根据隐藏状态显示叙事回声。
- 前端新增“此前的回声”渲染，用于在场景正文前展示符合条件的关系反馈。
- validator 和 `state_registry.json` 已纳入 `state_echoes.requirements` 的状态读取。
- 测试新增关系回声覆盖要求：关键关系变量至少在两个不同后续场景产生回声。

V0.3 的边界：

- 关系回声不是好感度条，也不直接替玩家解释数值。
- 回声必须是文本暗示，不能黑箱改写 choice 的含义。
- 当前只是基础实现，仍需内部用户测试验证玩家是否能感到“被记住”。

### 17.8 V0.4 版本变更记录

V0.4 相比 V0.3 的实质变化：

- 旧版 V0.3 PRD 和技术文档已归档到 `/home/samsong/Desktop/game_writer/doc/prd/old version/2026-07-08-101018-737`。
- 章节复盘新增基础 flowchart 模块：展示本章场景节点、已到达/未到达状态、当前节点、观察计数、行动计数和分支标签。
- 前端新增 `renderChapterFlow()`、`renderChapterFlowNode()` 和 `buildFlowMeta()`。
- 测试新增静态 hook，防止章节复盘退化回纯列表。

V0.4 的边界：

- 当前 flowchart 仍是线性章节节点图，不是完整空间化分支图。
- 它能帮助玩家复盘“本章走过什么”，但还不能完整表达“为什么某条分支被锁住”。
- 下一步应补内部测试和第一章轻教学，而不是继续堆 UI 装饰。

### 17.9 V0.5 版本变更记录

V0.5 相比 V0.4 的实质变化：

- 旧版 V0.4 PRD 和技术文档已归档到 `/home/samsong/Desktop/game_writer/doc/prd/old version/2026-07-08-101914-651`。
- 新增第一章叙事内轻教学：`observe` 首次展开时显示剧情内系统反馈，避免把玩家丢进纯样式猜谜。
- 新增 observe 解锁 choice 的即时反馈：由证据长出的行动会在底部行动栏高亮一次。
- 新增 `guidance` / `unlock_guidance` 可选数据字段，用于把轻教学写进内容结构，而不是硬编码在 UI 文案里。
- validator 和测试已覆盖轻教学字段，避免后续生成器产出缺 id、缺标题或缺正文的提示。

V0.5 的边界：

- 轻教学不是新手教程系统，也不是帮助中心。
- 当前只覆盖第一章关键路径，不代表所有章节都需要提示。
- 真正的问题仍要由内部用户测试回答：玩家是否自然理解了“文字可以展开”和“观察会改变行动栏”。

### 17.10 V0.6 版本变更记录

V0.6 相比 V0.5 的实质变化：

- 旧版 V0.5 PRD 和技术文档已归档到 `/home/samsong/Desktop/game_writer/doc/prd/old version/2026-07-08-102506-185`。
- 新增内部 playtest 记录模板，直接对齐第 14 节定性问题和量化指标。
- 新增 playtest 批次 JSON 模板，用于汇总 5 到 8 名内部测试用户结果。
- 新增 `scripts/summarize_playtest_batch.py`，把“第一分钟理解”“observe 解锁 choice”“路径图重玩意愿”“关键隐藏点卡死”等指标计算成 pass/fail。
- 新增 `tests/test_playtest_summary.py`，确保汇总脚本不会把空模板误判为真实数据，也能识别关键隐藏点卡死失败。

V0.6 的边界：

- V0.6 只是具备测试机制，不代表已经完成用户测试。
- 批次模板里的空值必须由真实观察记录填充；模板本身运行汇总脚本会得到 INVALID。
- 下一轮产品判断不应继续靠主观感觉，应优先跑 5 到 8 人内部测试。

### 17.11 V0.7 版本变更记录

V0.7 相比 V0.6 的实质变化：

- 旧版 V0.6 PRD 和技术文档已归档到 `/home/samsong/Desktop/game_writer/doc/prd/old version/2026-07-08-102957-278`。
- 新增 `scripts/content_qa_report.py`，对生成内容做自动内容 QA。
- QA 硬规则包括：主场景必须有明显 observe 入口、`hidden_optional` 不能解锁章节/全局后果 choice、choice 必须有描述和 outcome、首场景应有轻教学提示。
- 新增 `tests/test_content_qa.py`，覆盖当前 demo 0 error、隐藏关键入口失败、无明显 observe 入口失败、choice 缺描述/后果失败。
- README 增加内容 QA 命令入口。

V0.7 的边界：

- 自动 QA 只能挡结构和硬文案错误，不能替代真实玩家对“是否公平”“是否犹豫”“是否想重玩”的判断。
- 当前 QA 不做 LLM 语义评审，也不判断剧情审美。
- 下一轮仍应优先跑内部 playtest 或补浏览器自动化测试。

### 17.12 V0.8 版本变更记录

V0.8 相比 V0.7 的实质变化：

- 旧版 V0.7 PRD 和技术文档已归档到 `/home/samsong/Desktop/game_writer/doc/prd/old version/2026-07-08-103534-623`。
- 章节 flowchart 的分支标签从“只列 choice 名称”升级为“choice 名称 + 分支状态”。
- 分支状态包括：已选择、可选未走、已解锁未选、未解锁。
- 未解锁分支会显示缺少的证据标签，例如缺少“废弃地铁站定位”或“远程清除暂停窗口”。
- 前端新增 `buildChoiceBranchState()`、`describeRequirements()`、`describeRequirement()` 和状态标签映射。
- 测试新增静态 hook，防止 flowchart 锁定原因退化。

V0.8 的边界：

- 当前锁定原因基于运行时最终状态和已解锁 choice 记录，不是逐节点时间旅行回放。
- 当前仍不是空间化全路径图，也没有跨章因果线。
- 未解锁原因是线索级提示，不直接剧透隐藏 observe 的完整正文。

### 17.13 V0.9 版本变更记录

V0.9 相比 V0.8 的实质变化：

- 旧版 V0.8 PRD 和技术文档已归档到 `/home/samsong/Desktop/game_writer/doc/prd/old version/2026-07-08-103947-854`。
- 内容 QA 扩展到结局画像完整性检查。
- 自动检查每个 ending 是否有标题、足够正文、至少 3 个画像标签、是否被 choice 指向。
- 自动检查通往 ending 的 choice 是否为 `consequence_level: ending`，且是否写入至少一个状态值，避免结局画像和玩家轨迹脱节。
- `tests/test_content_qa.py` 新增结局不可达、结局 tag 不足、ending choice 不写状态的失败用例。

V0.9 的边界：

- 自动 QA 能检查结局画像的结构完整性，不能判断结局文案是否真正有冲击力。
- 结局 tag 仍是字符串标签，还不是完整的“保护了谁、伤害了谁、相信了什么”的结构化画像。
- 下一步仍应通过真实 playtest 验证玩家是否觉得结局回应了自己的选择。

### 17.14 V0.10 版本变更记录

V0.10 相比 V0.9 的实质变化：

- 旧版 V0.9 PRD 和技术文档已归档到 `/home/samsong/Desktop/game_writer/doc/prd/old version/2026-07-08-104252-500`。
- 新增 `scripts/browser_smoke.py`，脚本会自行启动临时静态服务并用 Python Playwright + Chrome 跑真实浏览器交互。
- 浏览器 smoke 使用 390x844 移动视口，验证首章轻教学、observe 解锁 choice 高亮、章节 flowchart、未解锁原因、刷新恢复和横向溢出。
- README 增加浏览器 smoke 命令入口。

V0.10 的边界：

- 当前浏览器 smoke 是核心路径自动验收，不是完整 E2E 矩阵。
- 它依赖本机 Python `playwright` 包和 Chrome/Chromium；若环境缺失，需要先安装或设置 `BROWSER_EXECUTABLE`。
- 尚未覆盖真实设备触控、屏幕阅读器和多浏览器兼容性。

### 17.15 V0.11 版本变更记录

V0.11 相比 V0.10 的实质变化：

- 旧版 V0.10 PRD 和技术文档已归档到 `/home/samsong/Desktop/game_writer/doc/prd/old version/2026-07-08-104836-346`。
- `scripts/repair_game.py` 从 report-only 工具升级为保守局部修复器。
- repair 支持修复坏 `start_scene_id`、坏 `next_scene`、缺失 anchor 文本、错误 observe depth、坏 unlock choice 引用。
- CLI 支持 `--out` 和 `--in-place`，默认不写文件，只报告可执行修复。
- 新增 `tests/test_repair_game.py`，覆盖常见局部生成错误和不可修复 unlock 引用删除。

V0.11 的边界：

- repair 只处理确定性结构硬伤，不重写剧情文案，也不生成新的复杂 choice。
- 对不可确定的 invalid unlock choice，repair 会删除引用而不是幻想补剧情。
- 这仍不是完整 LLM repair loop；下一步需要 prompt 版本、失败样本 fixtures 和显式 schema。

### 17.16 V0.12 版本变更记录

V0.12 相比 V0.11 的实质变化：

- 旧版 V0.11 PRD 和技术文档已归档到 `/home/samsong/Desktop/game_writer/doc/prd/old version/2026-07-08-105355-476`。
- 新增 `schemas/game.schema.json`，作为玩家端游戏数据的显式 JSON Schema。
- 新增 `scripts/validate_json_schema.py`，使用 Draft 2020-12 JSON Schema 校验生成物。
- 新增 `tests/test_json_schema_contract.py`，覆盖当前生成物通过 schema、缺少必填字段失败、非法 `consequence_level` 失败、observe fragment 缺 `nested_anchors` 失败。
- README 增加 schema 文件和 schema 校验命令。

V0.12 的边界：

- JSON Schema 只验证字段形状、类型、必填项和枚举。
- `start_scene_id` 是否真实存在、choice/observe ID 是否互相指向、隐藏内容是否公平，仍由 `validate_game.py` 和 `content_qa_report.py` 负责。
- 这不是完整内容质量保证，但它减少了前端、生成器、repair 和 validator 之间的隐式契约。

### 17.17 V0.13 版本变更记录

V0.13 相比 V0.12 的实质变化：

- 旧版 V0.12 PRD 和技术文档已归档到 `/home/samsong/Desktop/game_writer/doc/prd/old version/2026-07-08-105917-784`。
- 新增 `gamegen/schema_contract.py`，让生成器、脚本和测试共享同一套 schema 校验逻辑。
- `export_game()` 在写任何 artifact 前先运行 JSON Schema 校验和 `validate_game()`，存在 error 时直接抛错并阻断导出。
- `generation_trace.jsonl` 增加 `schema` 字段，记录本次导出使用的 schema contract。
- 新增 `tests/test_export_contract.py`，覆盖正常导出和坏数据阻断写文件。
- `scripts/validate_json_schema.py` 改为复用 `gamegen.schema_contract`。

V0.13 的边界：

- 导出门禁只阻断 schema 和 validator 的 error；content QA 仍是独立验收命令。
- 当前还没有模型输出 fixtures 和失败样本库。
- 这仍不是 LLM 语义 repair loop，但已把生成入口的硬合同前移到写文件之前。

### 17.18 V0.14 版本变更记录

V0.14 相比 V0.13 的实质变化：

- 旧版 V0.13 PRD 和技术文档已归档到 `/home/samsong/Desktop/game_writer/doc/prd/old version/2026-07-08-110530-731`。
- 新增 `examples/fixtures/generation_failures/fixture_cases.json`，用 mutation 描述典型坏模型输出。
- fixture 覆盖 schema gate、validator gate 和 repair gate：缺必填字段、坏 `next_scene`、anchor 文本漂移、unlock choice typo、坏 `start_scene_id`。
- 新增 `tests/test_generation_failure_fixtures.py`，按 fixture 预期验证 schema error、validator error 和 repair 是否能清除 validator error。
- README 增加生成失败样本入口。

V0.14 的边界：

- 当前 fixture 是基于 deterministic demo 的 mutation 样本，不是真实 LLM 输出日志。
- fixture 只覆盖硬结构失败，不覆盖剧情质量和语义修复。
- 下一步应积累真实模型输出样本，并建立 prompt 版本与失败样本的对应关系。

### 17.19 V0.15 版本变更记录

V0.15 相比 V0.14 的实质变化：

- 旧版 V0.14 PRD 和技术文档已归档到 `/home/samsong/Desktop/game_writer/doc/prd/old version/2026-07-08-111048-389`。
- 新增 `prompts/manifest.json`，记录当前 active prompt set、适用生成入口、schema contract 和可选 LLM polish 的边界。
- 新增 `gamegen/prompt_manifest.py`，提供 prompt manifest 读取和 active prompt set 校验。
- `generation_trace.jsonl` 增加 `prompt_set` 字段，记录本次导出使用的 prompt set。
- 新增 `tests/test_prompt_manifest.py`，覆盖 active prompt set 已声明、导出 trace 记录 prompt set、未声明 active prompt set 会失败。

V0.15 的边界：

- 当前 prompt manifest 主要记录 deterministic demo 和可选 LLM polish 的元数据，不包含真实模型输出日志。
- prompt manifest 不存 API key，不读取 `.env`，不记录供应商私密配置。
- 下一步应把真实 LLM 输出样本和 prompt/model/provider 版本绑定起来。

### 17.20 V0.16 版本变更记录

V0.16 相比 V0.15 的实质变化：

- 旧版 V0.15 PRD 和技术文档已归档到 `/home/samsong/Desktop/game_writer/doc/prd/old version/2026-07-08-111916-707`。
- 前端 observe anchor、choice button、章节继续按钮和重开按钮增加稳定 `data-*` 测试标识。
- 新增 `scripts/browser_e2e_matrix.py`，用真实浏览器和 390x844 移动视口跑多路径/多结局 E2E。
- E2E 矩阵覆盖 3 个主结局：`ending_publish`、`ending_bury`、`ending_confront`。
- 每条路径都会真实点击 observe 解锁 choice，穿过两次章节复盘，并在结局页检查标题、画像区、结局标签和横向溢出。
- 单元测试新增 E2E 矩阵覆盖当前全部主结局的静态契约。

V0.16 的边界：

- 浏览器 E2E 证明当前 demo 的三主结局可达，不证明结局文案有足够情感重量。
- 它覆盖 Chrome/Chromium headless 移动视口，不等于真实手机、多浏览器或无障碍验收。
- 下一步仍应优先积累真实模型输出样本、跑内部用户测试，并补真实设备/无障碍验证。

### 17.21 V0.17 版本变更记录

V0.17 相比 V0.16 的实质变化：

- 旧版 V0.16 PRD 和技术文档已归档到 `/home/samsong/Desktop/game_writer/doc/prd/old version/2026-07-08-113003-355`。
- `generation_trace.jsonl` 增加 `trace_schema_version` 和 `model` 字段，离线生成默认记录 `deterministic_demo_v0`。
- 新增 `gamegen/model_output_archive.py`，定义模型输出样本归档、脱敏、checksum 和 manifest 更新逻辑。
- 新增 `scripts/archive_model_output_sample.py`，用于把真实模型输出文件脱敏后归档到样本库。
- 新增 `examples/fixtures/model_outputs/sample_manifest.json` 和 README，明确不提交原始未脱敏 provider response。
- 新增 `tests/test_model_output_archive.py`，覆盖 API key、bearer token、认证字段、`.env` token、邮箱脱敏，样本 manifest 写入，坏 sample id 和未声明 prompt_set 拒绝。

V0.17 的边界：

- 本轮建立的是样本归档合同，不是假装已经积累了真实模型输出样本。
- 脱敏工具只能覆盖常见密钥/邮箱形态，真实样本入库前仍需要人工复查。
- 下一步应使用该工具沉淀首批真实 LLM 成功/失败样本，并把样本与 repair/validator/content QA 结果关联起来。

### 17.22 V0.18 版本变更记录

V0.18 相比 V0.17 的实质变化：

- 旧版 V0.17 PRD 和技术文档已归档到 `/home/samsong/Desktop/game_writer/doc/prd/old version/2026-07-08-113713-481`。
- `gamegen/model_output_archive.py` 增加 `validate_model_output_archive()`，用于检查样本库 manifest 与样本文件。
- 新增 `scripts/validate_model_output_archive.py`，可在提交前校验模型输出样本库。
- 校验范围包括：manifest schema、sample id、重复 id、文件路径越界、文件缺失、prompt_set 未声明、schema 字段、sha256 漂移、未脱敏 API key / bearer token / auth 字段 / env token / 邮箱。
- `tests/test_model_output_archive.py` 增加空样本库通过、归档样本通过、篡改样本失败的覆盖。
- README 增加模型输出样本库校验命令。

V0.18 的边界：

- 样本库门禁只能保证已归档样本的基础安全和一致性，不会自动判断样本代表的生成失败是否重要。
- 当前样本库仍未沉淀真实 provider response；下一步仍需要用 V0.17/V0.18 的工具链归档首批真实样本。
- 真实样本入库前仍需要人工复查敏感信息，尤其是脱敏规则尚未覆盖的手机号、真实姓名、私有 URL 等。

### 17.23 V0.19 版本变更记录

V0.19 相比 V0.18 的实质变化：

- 旧版 V0.18 PRD 和技术文档已归档到 `/home/samsong/Desktop/game_writer/doc/prd/old version/2026-07-08-114202-185`。
- `scripts/browser_e2e_matrix.py` 的三结局路径新增结局态刷新恢复检查。
- `scripts/browser_e2e_matrix.py` 的三结局路径新增结局页“重新开始”检查，确认回到首场景并清除 ending screen。
- E2E 输出现在标明每条结局路径均完成 `restored` 与 `restart` 验证。
- README 同步多结局 E2E 的恢复/重开覆盖范围。

V0.19 的边界：

- 结局恢复/重开验证仍运行在 Chrome/Chromium headless 移动视口，不等于真实手机、多浏览器或存档迁移验收。
- 当前只验证正常存档恢复，不验证损坏存档、版本升级后的存档迁移或多存档。
- 下一步可继续补失败/遗漏路径、损坏存档处理、键盘导航和屏幕阅读器检查。

### 17.24 V0.20 版本变更记录

V0.20 相比 V0.19 的实质变化：

- 旧版 V0.19 PRD 和技术文档已归档到 `/home/samsong/Desktop/game_writer/doc/prd/old version/2026-07-08-114644-796`。
- `scripts/browser_smoke.py` 新增坏 JSON 存档 fallback 检查：写入 `not-json` 后刷新，必须回到首场景。
- `scripts/browser_smoke.py` 新增旧版本存档 fallback 检查：写入 `version: 999` 后刷新，必须回到首场景。
- 浏览器 smoke 输出新增 `corrupt_save_recovered` 和 `invalid_save_recovered`。
- README 同步坏存档 fallback 覆盖范围。

V0.20 的边界：

- 当前只验证坏存档不会卡死游戏并能回到首场景，没有做可见的异常恢复提示。
- 当前没有多存档、存档迁移、云同步或损坏存档备份。
- 下一步如继续做 runtime resilience，应补“损坏存档提示”和版本迁移策略，而不是只扩大测试。
