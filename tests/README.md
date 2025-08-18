# tests/

目的：覆盖核心 flow，保证自动化测试可稳定运行并全部通过；统一使用 pytest。

目录结构：
- `tests/unit/`          单元测试（默认执行，排除 slow）
- `tests/integration/`   集成测试（标记为 integration）
- `tests/ui/`            UI/预览相关测试（多为轻量/快照/结构断言）

标记（markers）：
- `integration`：跨模块/分层的集成测试
- `e2e`：端到端流程测试
- `ui`：UI/预览/布局相关（HTML 生成、组件结构、样式）
- `performance`：性能与缓存行为（也会被标记为 `slow`）
- `slow`：慢速测试（默认不执行）

默认行为：
- pytest.ini 配置了 `addopts = -q --maxfail=1 -m "not slow"`，默认忽略 slow/performance

Makefile 常用命令：
- `make test`              快速运行（默认过滤 slow）
- `make test-integration`  仅运行集成测试
- `make test-e2e`          仅运行端到端测试
- `make test-slow`         运行性能/慢速测试
- `make test-unit`         仅运行单元测试（排除 integration/slow）
- `make test-ui`           仅运行 UI/预览相关测试
- `make coverage`          生成覆盖率报告

如何运行（pytest 原生命令）：
- 快速运行：
  - `python -m pytest -q`
- 详细输出与失败即停：
  - `python -m pytest -vv --maxfail=1`
- 仅集成测试：
  - `python -m pytest -m integration -q`
- 仅 E2E：
  - `python -m pytest -m e2e -q`
- 仅慢速/性能：
  - `python -m pytest -m "performance or slow" -v`
- 覆盖率（可选）：
  - `python -m pytest -q --cov=src --cov=services --cov=ui --cov=core --cov-report=term-missing`

说明：
- 部分以 UI/HTML 演示为主的脚本（颜色按钮、无白边、实时预览等）主要用于手动验证，不作为自动化断言的用例；若需转换为可自动验证的快照/结构断言测试，请提 issue 指定范围。
