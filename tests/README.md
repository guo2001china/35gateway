# Tests

测试源码统一收口到根目录 `tests/`。

当前分层：

- `tests/api/`
  后端 pytest 测试与共享 fixture
- `tests/audit/`
  发布前的契约审计与结构检查
- `tests/live/`
  真实环境 smoke 与联调脚本

约束：

- 测试代码进 Git
- 测试运行产物不进 Git
- Playwright 会话、截图草稿、trace、html report 等都视为本地产物

常用入口：

```bash
npm run test:console-backend
npm run test:audit
npm run test:live
npm run test:live:mixed
npm run test:live:journey
```

说明：

- `npm run test:live` 走公开模型单链 smoke
- `npm run test:live:mixed` 走混合供应商矩阵 smoke
- `npm run test:live:journey` 走发布前真实用户旅程 smoke
- `test:live:mixed` 默认读取 `api/.env` 里的主供应商配置
  - 例如 `yunwu_openai` 需要：
    - `API35_YUNWU_OPENAI_BASE_URL`
    - `API35_YUNWU_OPENAI_API_KEY`
- `test:live:mixed` 与 `test:live:journey` 默认都会使用独立 sqlite 文件，不依赖本地已有开发库
