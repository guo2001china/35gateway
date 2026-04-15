# Self-Hosting

`35gateway` 的默认模式是单机自托管。

## Default Mode

- 单机部署
- `sqlite` 默认
- 本地文件存储默认
- 不依赖 `Postgres`
- 不依赖 `Redis`

## Good Fit

- 本地开发
- 单机云主机
- 小团队内部部署
- 代理商做最小可交付环境

## Not The Goal

- 多实例集群
- 分布式会话
- 复杂多区域容灾

## Provider Model

- provider 定义由平台内置
- 平台 env 只决定是否预置平台凭证
- 用户可以在控制台里录入自己的 provider account

## External Positioning

- self-hosted by default
- bring your own keys
- visible pricing, logs, and async tasks
