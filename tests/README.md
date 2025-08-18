# tests/

目的：覆盖核心 flow，保证自动化测试可稳定运行并全部通过；统一使用 pytest。

变更摘要：
- 统一测试框架为 pytest（requirements.txt 新增 pytest/pytest-cov，新增 pytest.ini 与 tests/conftest.py）
- 新增/补充用例：
  - 字典与 CEDICT 加载、字符拆分 fallback
  - 输入解析与自动分词联合流程、缺失数据生成的开关组合
  - 导出服务 pptx/pdf 正常/异常路径
  - 预览 HTML（简单网格/页面预览）包含背景色、标记
- 统一 tests 内对源码导入：`from src...`/`from services...`
- 自动清理 out 目录：tests/conftest.py 在测试会话前后清空 out 内生成的文件

如何运行（pytest）：
- 快速运行：
  - `python -m pytest -q`
- 详细输出与失败即停：
  - `python -m pytest -vv --maxfail=1`
- 覆盖率（可选）：
  - `python -m pytest -q --cov=src --cov=services --cov-report=term-missing`

说明：
- 部分以 UI/HTML 演示为主的脚本（颜色按钮、无白边、实时预览等）主要用于手动验证，不作为自动化断言的用例；若需转换为可自动验证的快照/结构断言测试，请提 issue 指定范围。
