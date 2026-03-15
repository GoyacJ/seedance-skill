---
name: seedance-skill
description: Use when users want to turn an idea or prompt into a short-form video with 豆包 Seedance and optionally prepare or publish it to 抖音/Douyin, including requests like 根据想法生成短视频, 发布到抖音, 直发抖音, 生成抖音文案/封面, H5 投稿, or manual upload packaging.
metadata: {"openclaw":{"skillKey":"seedance-skill","requires":{"anyBins":["python3","python"]},"primaryEnv":"ARK_API_KEY"}}
---

# Seedance Skill

## Overview

把用户的想法转成短视频，并在需要时继续走抖音发布链路。

默认只做文生视频。默认先预览，只有用户明确说“发布”“直发抖音”“走 H5 投稿”时，才进入发布阶段。

在 OpenClaw 里，`{baseDir}` 指向当前 skill 的安装目录；在其他兼容 AgentSkills 的运行时里，如果当前工作目录已经是 skill 根目录，就把 `{baseDir}` 视作 `.` 来理解即可。

## Decision Flow

1. 判断用户是否明确要求发布。
2. 如果没有明确要求发布：使用 `preview`。
3. 如果明确要求自动发布，且具备抖音 OpenAPI 凭证与权限：使用 `openapi`。
4. 如果明确要求发布，但不具备自动发布条件：优先使用 `h5`；如果 H5 也不具备条件，则退回 `manual-package`。

## Safety Gate

- 没有明确发布指令时，不要触发任何外部发布动作。
- 遇到营销导流、明显非原创、低质拼接、纯文字截图等风险内容，先提示合规风险，再继续生成或包装。
- 自动发布链路不要用浏览器模拟代替官方能力。拿不到权限时，回退到 `h5` 或 `manual-package`。

## Default Creation Spec

文生视频默认参数固定如下：

- `model=doubao-seedance-2-0-260128`
- `ratio=9:16`
- `duration=5`
- `resolution=720p`
- `generate_audio=true`
- `watermark=false`
- `return_last_frame=true`

输出目录默认为 `outputs/<timestamp>/`。如果调用脚本时传了 `--output-dir`，就直接写入该目录。

## Workflow

### 1. 识别意图

先把用户请求归到以下模式之一：

- `preview`
- `openapi`
- `h5`
- `manual-package`

如果用户只说“做一个抖音短视频”，默认 `preview`。

### 2. 生成视频

先用 `{baseDir}/scripts/generate_video.py` 产出视频。这个脚本不再提供 `--dry-run`，缺少 `ARK_API_KEY` 时直接视为不可用。

```bash
python3 {baseDir}/scripts/generate_video.py \
  --prompt "清晨的老街早餐摊，暖色纪实镜头，9:16"
```

真实调用时需要：

- `ARK_API_KEY`
- 可选 `ARK_BASE_URL`
- 兼容旧变量：`LAS_API_KEY`、`LAS_BASE_URL`

脚本会写出：

- `request.json`
- `generation.json`
- 成功时尽量下载 `video.mp4`
- 如果拿到尾帧则写 `cover.png`；拿不到则尝试从视频抽帧

Seedance 详细参数与异步流程见 [references/seedance.md](references/seedance.md)。

### 3. 生成抖音发布物料

无论后续是否发布，都先用 `{baseDir}/scripts/prepare_publish_package.py` 生成标题、话题和发布清单。

```bash
python3 {baseDir}/scripts/prepare_publish_package.py \
  --idea "做一个关于老街早餐摊的抖音短视频" \
  --prompt "清晨的老街早餐摊，暖色纪实镜头，9:16" \
  --video-path outputs/20260315-000000/video.mp4 \
  --cover-path outputs/20260315-000000/cover.png \
  --mode preview
```

脚本会写出：

- `publish.json`
- `publish.md`

### 4. 选择发布路径

#### `preview`

只返回视频、封面、标题、hashtags 和建议发布方式，不做外部发布。

#### `openapi`

只有在用户明确要求自动发布，且已经具备下面条件时才使用：

- 抖音应用已开通对应视频发布能力
- 已完成用户授权
- 已拿到 `access_token`
- 能提供 `open_id`

调用：

```bash
python3 {baseDir}/scripts/douyin_openapi_publish.py \
  --video-path outputs/20260315-000000/video.mp4 \
  --title "城市清晨 #烟火日常 #抖音灵感" \
  --open-id "$DOUYIN_OPEN_ID"
```

如果凭证不全，会明确阻塞自动发布，并返回 `manual-package` 回退建议。

OpenAPI 细节见 [references/douyin-openapi-video.md](references/douyin-openapi-video.md)。

#### `h5`

当用户明确要投稿，但自动发布条件不足时，优先走 H5 投稿。

```bash
python3 {baseDir}/scripts/douyin_h5_publish.py \
  --video-path "https://example.com/video.mp4" \
  --title "城市雨夜漫游" \
  --hashtag "城市漫游" \
  --share-to-publish
```

脚本会生成：

- `h5_publish.json`
- `qr_payload.txt`

它输出的是 schema 和二维码 payload，而不是直接生成二维码图片。

如果缺少 H5 投稿所需凭证，脚本会直接阻塞，而不是生成占位结果。

H5 投稿与能力边界见 [references/douyin-publish.md](references/douyin-publish.md)。

#### `manual-package`

当用户只需要手动上传物料，或者抖音能力未开通时，直接交付：

- `video.mp4`
- `cover.png`
- `publish.json`
- `publish.md`

## Auth Flow

如果需要抖音 OAuth：

```bash
python3 {baseDir}/scripts/douyin_auth.py authorize
python3 {baseDir}/scripts/douyin_auth.py exchange --code "<code>"
python3 {baseDir}/scripts/douyin_auth.py refresh --refresh-token "<refresh_token>"
```

认证与 token 细节见 [references/douyin-auth.md](references/douyin-auth.md)。

## Environment Variables

- `ARK_API_KEY`
- `ARK_BASE_URL`
- `LAS_API_KEY`
- `LAS_BASE_URL`
- `DOUYIN_CLIENT_KEY`
- `DOUYIN_CLIENT_SECRET`
- `DOUYIN_REDIRECT_URI`
- `DOUYIN_ACCESS_TOKEN`
- `DOUYIN_REFRESH_TOKEN`
- `DOUYIN_OPEN_ID`
- 可选 `DOUYIN_OPEN_TICKET`

## References

- [references/seedance.md](references/seedance.md)
- [references/douyin-auth.md](references/douyin-auth.md)
- [references/douyin-publish.md](references/douyin-publish.md)
- [references/douyin-openapi-video.md](references/douyin-openapi-video.md)
