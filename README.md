# seedance-skill

`seedance-skill` 是一个面向 AgentSkills / OpenClaw 运行时的短视频生成 skill。它接收用户输入的创意、描述或 prompt，调用豆包 Seedance 生成短视频，并继续准备抖音发布所需的标题、话题、封面与发布清单；在凭证和权限完备时，还支持抖音 OpenAPI 自动发布或 H5 投稿链路。

`SKILL.md` 是给 agent 运行时读取的入口文件，这份 `README.md` 则是给项目维护者和使用者看的项目说明。

## 能力概览

- 根据一句想法或详细 prompt 生成竖版短视频
- 默认参数固定为 `9:16 / 5s / 720p / 生成音频 / 无水印 / 返回尾帧`
- 自动生成标题、hashtags、封面策略和发布清单
- 支持 4 种模式：`preview`、`openapi`、`h5`、`manual-package`
- 默认只预览；只有用户明确要求“发布/直发”才进入发布链路

## 当前边界

- V1 仅支持文生视频
- 不做浏览器模拟发布，只走抖音官方能力
- 没有抖音权限时，会自动回退到 `h5` 或 `manual-package`
- 没有必需凭证时，对应能力不可用

## 目录结构

```text
.
├── SKILL.md
├── README.md
├── references/
│   ├── seedance.md
│   ├── douyin-auth.md
│   ├── douyin-publish.md
│   └── douyin-openapi-video.md
├── scripts/
│   ├── generate_video.py
│   ├── prepare_publish_package.py
│   ├── douyin_auth.py
│   ├── douyin_h5_publish.py
│   ├── douyin_openapi_publish.py
│   └── seedance_skill_common.py
├── tests/
│   └── test_seedance_skill.py
└── dist/
    └── seedance-skill.skill
```

## 核心脚本

- `scripts/generate_video.py`
  - 生成 Seedance 请求体
  - 发起异步任务、轮询状态、下载 `video.mp4` 和 `cover.png`
  - 缺少 `ARK_API_KEY` 时直接阻塞
- `scripts/prepare_publish_package.py`
  - 生成 `publish.json` 与 `publish.md`
  - 自动产出标题、hashtags 和封面建议
- `scripts/douyin_auth.py`
  - 处理抖音 OAuth 授权码、换 token、刷新 token
- `scripts/douyin_h5_publish.py`
  - 生成 H5 投稿 schema 和二维码 payload
- `scripts/douyin_openapi_publish.py`
  - 封装抖音 OpenAPI 自动发布
  - 缺少权限或凭证时返回回退建议

## 产物约定

默认输出目录为 `outputs/<timestamp>/`，常见产物如下：

- `request.json`
- `generation.json`
- `video.mp4`
- `cover.png`
- `publish.json`
- `publish.md`
- `h5_publish.json`
- `qr_payload.txt`

## 环境变量

视频生成相关：

- `ARK_API_KEY`
- `ARK_BASE_URL`

抖音授权与发布相关：

- `DOUYIN_CLIENT_KEY`
- `DOUYIN_CLIENT_SECRET`
- `DOUYIN_REDIRECT_URI`
- `DOUYIN_ACCESS_TOKEN`
- `DOUYIN_REFRESH_TOKEN`
- `DOUYIN_OPEN_ID`
- 可选 `DOUYIN_OPEN_TICKET`

## 快速开始

### 1. 生成视频

```bash
python3 scripts/generate_video.py \
  --prompt "清晨的老街早餐摊，暖色纪实镜头，9:16"
```

运行前需要先配置 `ARK_API_KEY`。

### 2. 生成发布清单

```bash
python3 scripts/prepare_publish_package.py \
  --idea "做一个关于老街早餐摊的抖音短视频" \
  --prompt "清晨的老街早餐摊，暖色纪实镜头，9:16" \
  --video-path outputs/20260315-000000/video.mp4 \
  --cover-path outputs/20260315-000000/cover.png \
  --mode preview
```

### 3. 打包 skill

```bash
python3 /Users/goya/.codex/skills/skill-creator/scripts/quick_validate.py .
stage=$(mktemp -d)
mkdir -p "$stage/seedance-skill"
cp SKILL.md "$stage/seedance-skill/"
(cd . && tar --exclude='__pycache__' -cf - scripts references) | (cd "$stage/seedance-skill" && tar -xf -)
python3 /Users/goya/.codex/skills/skill-creator/scripts/package_skill.py "$stage/seedance-skill" dist
```

已打好的包位于 `dist/seedance-skill.skill`。

## 在 OpenClaw 中使用

这份 skill 已补齐 OpenClaw 所需的 `metadata.openclaw` 信息，并在 `SKILL.md` 中使用 `{baseDir}` 引用脚本路径。

推荐两种方式：

1. 把解压后的 `seedance-skill/` 放到 OpenClaw workspace 的 `skills/` 目录下
2. 把“包含 `seedance-skill/` 目录的父目录”加入 `skills.load.extraDirs`

这份项目已经做过 OpenClaw 真机验证：

- `openclaw skills info seedance-skill --json` 可识别为 `eligible`
- `openclaw skills list` 显示为 `ready`
- `openclaw agent --local` 能真实触发 skill，并进入 `preview` 工作流

## 在 Codex / 其他兼容 AgentSkills 的运行时中使用

- 运行时入口是 `SKILL.md`
- 如果当前工作目录就是 skill 根目录，可以直接使用相对路径脚本
- 如果运行时支持类似 OpenClaw 的 `{baseDir}` 变量，则按 `SKILL.md` 中的绝对 skill 根路径逻辑执行

## 参考文档

- `references/seedance.md`
- `references/douyin-auth.md`
- `references/douyin-publish.md`
- `references/douyin-openapi-video.md`

## 验证状态

当前仓库已经完成这些验证：

- 单元测试通过
- `quick_validate.py` 校验通过
- `.skill` 打包成功
- OpenClaw 已完成真实 agent 触发验证

## 后续可扩展方向

- 图生视频
- 多段视频续写
- 自定义时长、分辨率、比例
- 自动生成二维码图片而不只是 payload
- 发布结果自动轮询与回查
