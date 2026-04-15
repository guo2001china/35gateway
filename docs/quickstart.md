# Quickstart

`35gateway` 默认是单机自托管，开发态双端口，构建后单端口。

## Prerequisites

- `Node.js`
- `Python 3.11+`
- `uv`

## Install

```bash
cd api
uv sync

cd ../
npm install
```

## Start

```bash
bash scripts/dev/restart.sh
```

默认地址：

- API: `http://127.0.0.1:8025`
- 开发态 Web: `http://127.0.0.1:5185`
- 构建后 Console: `http://127.0.0.1:8025/console`
- Docs: `http://127.0.0.1:8025/docs`

## First API Path

1. 打开 `http://127.0.0.1:5185`，或构建后访问 `http://127.0.0.1:8025/console`
2. 登录或注册
3. 获取系统默认 key 或创建自定义 key
4. `GET /v1/models`
5. 调一个公开模型接口
6. 回控制台看日志和任务

## Runtime

- 默认数据库：`sqlite`
- 默认数据库文件：`api/data/35gateway.sqlite3`
- 默认不依赖 `Postgres`
- 默认不依赖 `Redis`

## Validation

```bash
npm run build:web
npm run test:console-backend
npm run test:audit
```
