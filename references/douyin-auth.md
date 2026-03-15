# 抖音授权参考

## 官方来源

- 获取授权码：<https://developer.open-douyin.com/docs/resource/zh-CN/dop/develop/openapi/account-permission/douyin-get-permission-code>
- 获取 access_token：<https://developer.open-douyin.com/docs/resource/zh-CN/dop/develop/openapi/account-permission/get-access-token>
- 刷新 access_token：<https://developer.open-douyin.com/docs/resource/zh-CN/dop/develop/openapi/account-permission/refresh-access-token>
- 续期 refresh_token：<https://developer.open-douyin.com/docs/resource/zh-CN/dop/develop/openapi/account-permission/refresh-token>

## 最小流程

1. 生成授权链接，让用户在抖音完成授权
2. 用授权回调里的 `code` 换 `access_token`
3. 持久化保存：
   - `access_token`
   - `refresh_token`
   - `open_id`
   - 过期时间
4. access_token 过期前刷新

## 关键接口

### 授权链接

脚本使用：

- `https://open.douyin.com/platform/oauth/connect/`

关键参数：

- `client_key`
- `response_type=code`
- `scope`
- `redirect_uri`
- 可选 `state`

### 用 code 换 access_token

- URL：`https://open.douyin.com/oauth/access_token/`
- Method：`POST`
- Content-Type：`application/x-www-form-urlencoded`

关键字段：

- `client_key`
- `client_secret`
- `code`
- `grant_type=authorization_code`

### 刷新 access_token

- URL：`https://open.douyin.com/oauth/refresh_token/`
- Method：`POST`

关键字段：

- `client_key`
- `refresh_token`
- `grant_type=refresh_token`

### 续期 refresh_token

- URL：`https://open.douyin.com/oauth/renew_refresh_token/`
- Method：`POST`

关键字段：

- `client_key`
- `refresh_token`

## 存储建议

- token 尽量保存在服务端
- 不要只存 `access_token`，要一并保存 `refresh_token` 和 `open_id`
- 如果要自动发布，`open_id` 是必需的

## Skill 中的环境变量

- `DOUYIN_CLIENT_KEY`
- `DOUYIN_CLIENT_SECRET`
- `DOUYIN_REDIRECT_URI`
- `DOUYIN_ACCESS_TOKEN`
- `DOUYIN_REFRESH_TOKEN`
- `DOUYIN_OPEN_ID`
