# Iteration Log: README Thumbnail Gallery

开始时间：2026-07-08 16:51:58.062 +0800

## 本次迭代

- 将 README 中的四张体验截图从大图展示改为紧凑缩略图展示。
- 新增四张短缩略图：
  - `screenshots/thumb-01-start-screen.jpg`
  - `screenshots/thumb-02-observe-unlocks-choice.jpg`
  - `screenshots/thumb-03-chapter-review-flow.jpg`
  - `screenshots/thumb-04-ending-portrait.jpg`
- README 缩略图宽度设置为 `120`，点击后仍打开对应完整长图。

## 验证

- 确认四张缩略图尺寸均为 `240x360`。
- `git diff --check` 通过。

## 结果

- README 首屏图片占用空间明显降低。
- 保留完整截图查看路径，不损失细节检查能力。
