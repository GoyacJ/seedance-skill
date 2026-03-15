# 抖音发布方式参考

## 官方来源

- 抖音发布能力使用规范：<https://developer.open-douyin.com/docs/resource/zh-CN/dop/operation-standard/platform-capabilities/useclue>
- H5 投稿：<https://developer.open-douyin.com/docs/resource/zh-CN/dop/develop/sdk/web-app/h5/share-to-h5>

## 这个 skill 的 4 种模式

- `preview`
- `openapi`
- `h5`
- `manual-package`

## 选择规则

### `preview`

默认模式。用户没有明确说“发布/直发”时，用它。

### `openapi`

只有在以下条件全部满足时才用：

- 用户明确要求自动发布
- 应用已经开通抖音发布能力
- 已完成用户授权
- 有可用的 `access_token`
- 能提供 `open_id`

### `h5`

适合这些情况：

- 用户明确要投稿
- 自动发布条件不全
- 具备网页/H5 投稿能力

H5 投稿不是“服务端静默发布”，而是把内容带到抖音的编辑页或发布页，由用户在抖音里确认。

### `manual-package`

以下场景直接用：

- 用户只要素材包
- 没有抖音权限
- H5 场景也不具备条件

## H5 投稿关键点

- 需要先申请“发布内容至抖音”
- H5 场景还需要单独开通
- 生成 schema 时要带签名
- 可以通过 schema 生成二维码，让用户在抖音里扫码继续投稿

本仓库脚本输出的是 schema 和 `qr_payload.txt`，不负责生成二维码图片。

当前脚本不再提供 dry-run 或占位 schema 模式。缺少 H5 投稿所需凭证时，直接阻塞并建议回退到 `manual-package`。

## 自动发布与回退规则

如果自动发布缺少任何关键凭证，直接返回：

- `recommended_fallback = manual-package`

必要时也可以引导用户切换到 `h5`。

## 合规闸门

根据官方发布规范，默认避免：

- 明显营销导流
- 非原创搬运
- 低质同质化内容
- 纯文字截图类内容

当用户坚持发布高风险内容时，先提示风险，再继续包装，不要无提示直发。
