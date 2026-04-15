# 35gateway Console API

Console API 承载：
- platform：认证、账户、日志、文件、模型能力
- site：官网与公开页面

它不再承载 Creator 的 workflow/studio 运行时。

## 启动

```bash
cd api
uv sync
uv run console-api
```

默认端口：`8025`

开源默认模式是单机 `sqlite`，默认数据库文件为 `api/data/35gateway.sqlite3`。

## API 文档

启动后可通过以下入口查看接口文档：

- 交互文档：`http://127.0.0.1:8025/docs`
- 原始 OpenAPI：`http://127.0.0.1:8025/openapi.json`
- 构建后的单端口控制台：`http://127.0.0.1:8025/console`

当前公开接口已包含：

- OpenAI / Responses 文本接口
- Nano Banana / Seedream 图片接口
- Kling / Wan / Veo / Vidu 视频接口
- `/v1/tasks/{id}` 异步任务查询与 `/v1/tasks/{id}/content` 内容下载

当前已验证可真实交付使用的 Ksyun 托底文本模型：

- `gpt-5`
- `gpt-5.2`
- `gpt-5.4`

真实 UAT 建议关闭热更新，避免 watch reload 打断长任务：

```bash
cd api
uv run console-api-stable
```

## 目录

```text
api/
  app/
    api/
    core/
    db/
    domains/
```

测试源码统一放在仓库根目录 [tests/README.md](/Users/libn/dev/project/me/35gateway/tests/README.md)。
