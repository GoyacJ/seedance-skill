# Seedance 文生视频参考

## 官方来源

- 火山引擎文档：<https://www.volcengine.com/docs/6492/2165104?lang=zh>

## 当前固定默认值

- 模型：`doubao-seedance-2-0-260128`
- 比例：`9:16`
- 时长：`5`
- 分辨率：`720p`
- 生成音频：`true`
- 水印：`false`
- 返回尾帧：`true`

## 能力边界

- 当前 V1 只做文生视频。
- Seedance 官方支持文生视频和图生视频，但本 skill 暂不实现图生视频。
- 视频生成是异步任务：先创建任务，再轮询任务状态。

## 请求路径

- 创建任务：`POST /api/v3/contents/generations/tasks`
- 查询任务：`GET /api/v3/contents/generations/tasks/{id}`

默认 Base URL 使用：

- `https://ark.cn-beijing.volces.com`

也可通过 `ARK_BASE_URL` 覆盖，兼容旧变量 `LAS_BASE_URL`。

## 典型请求体

```json
{
  "model": "doubao-seedance-2-0-260128",
  "content": [
    {
      "type": "text",
      "text": "清晨的老街早餐摊，暖色纪实镜头，9:16"
    }
  ],
  "ratio": "9:16",
  "duration": 5,
  "resolution": "720p",
  "generate_audio": true,
  "watermark": false,
  "return_last_frame": true
}
```

## 任务状态

脚本重点关注这些状态：

- `queued`
- `running`
- `succeeded`
- `failed`
- `expired`
- `cancelled`

只有 `succeeded` 才继续下载素材。

## 输出处理策略

- 优先下载任务结果里的视频 URL 到 `video.mp4`
- 优先下载任务结果里的尾帧 URL 到 `cover.png`
- 如果没有尾帧，尝试用 `ffmpeg` 从视频中抽取首个稳定帧

## 凭证

- 必需：`ARK_API_KEY`
- 可选：`ARK_BASE_URL`
- 兼容旧变量：`LAS_API_KEY`、`LAS_BASE_URL`

当前脚本不提供占位调用或 dry-run 模式。缺少 `ARK_API_KEY` 时，直接返回阻塞结果并退出。

## 未来升级点

- 图生视频
- 多段连续续写
- 更细的可配置参数，如 duration、resolution override
