# Iteration Log: Log Time Granularity To Milliseconds

Start: 2026-07-08 09:36:21.857 +0800
End: 2026-07-08 09:36:26.344 +0800

## Summary

- 将项目迭代日志命名规范从秒级升级为毫秒级：`YYYY-MM-DD-HHMMSS-mmm-short-topic.md`。
- 在 `agent.md` 中补充日志正文必须记录开始时间和结束时间，格式建议包含毫秒与时区。
- 将既有秒级日志文件名统一补齐为毫秒格式。

## Files Changed

- `agent.md`
- `log/2026-07-08-091800-000-git-and-log-policy.md`
- `log/2026-07-08-091954-000-log-timestamp-granularity.md`
- `log/2026-07-08-093240-000-prd-demo-loop-iteration.md`
- `log/2026-07-08-093621-857-log-time-granularity-ms.md`

## Notes

- 历史日志统一使用 `000` 作为毫秒补位，表示原始记录只精确到秒，不伪造真实毫秒。
- 后续新日志应使用 `date '+%Y-%m-%d-%H%M%S-%3N'` 生成文件名前缀。

## Verification

- 已确认 `agent.md` 中的日志规范改为毫秒级。
- 已确认 `log/` 下现有日志文件名均符合新的毫秒级命名格式。
