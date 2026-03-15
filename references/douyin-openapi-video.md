# 抖音视频 OpenAPI 参考

## 官方来源

- 上传视频：<https://developer.open-douyin.com/docs/resource/zh-CN/dop/develop/openapi/video-management/douyin/create-video/upload-video>
- 创建视频：<https://developer.open-douyin.com/docs/resource/zh-CN/dop/develop/openapi/video-management/douyin/create-video/video-create>
- 查询视频发布结果：<https://developer.open-douyin.com/docs/resource/zh-CN/dop/develop/openapi/video-management/douyin/search-video/video-share-result>

## 自动发布链路

1. 上传视频
2. 拿到 `video_id`
3. 创建视频
4. 如需追踪发布结果，再查视频发布结果接口

## 上传视频

- URL：`https://open.douyin.com/api/douyin/v1/video/upload_video/`
- Method：`POST`
- 认证头：`access-token`
- Query：需要 `open_id`
- 请求体：`multipart/form-data`

本仓库脚本默认使用字段名：

- `video`

说明：这是基于官方上传视频文档做的直接映射。

## 创建视频

- URL：`https://open.douyin.com/api/douyin/v1/video/create_video/`
- Method：`POST`
- 认证头：`access-token`
- Query：需要 `open_id`
- Scope：官方文档显示为 `video.create.bind`

脚本默认传这些字段：

- `video_id`
- `text`
- `cover_tsp`
- `download_type`
- `private_status`

## 发布结果查询

H5 投稿链路里，推荐用 `state/share_id` 串联查询发布结果。

本 skill 暂不自动轮询发布结果接口，但会把官方结果查询 URL 返回给调用者。

## 当前脚本的保守策略

- 如果缺少 `DOUYIN_CLIENT_KEY`、`DOUYIN_CLIENT_SECRET`、`DOUYIN_ACCESS_TOKEN`、`DOUYIN_OPEN_ID` 任一项，就不尝试自动发布
- 缺参时直接阻塞，并返回 `manual-package` 回退建议
- 自动发布失败时，也返回 `manual-package` 回退建议

## 额外说明

计划文档里只列了主要环境变量，但自动发布实际上还需要 `open_id`。因此脚本支持：

- `--open-id`
- 或环境变量 `DOUYIN_OPEN_ID`
