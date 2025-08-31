# web_ui.py 重构方案（遵循最佳实践）

> 状态：已完成（Completed）。最终架构请参考《ARCHITECTURE.md》。以下步骤保留为历史记录与规范说明。

## 一、背景与目标

当前 `web_ui.py` 文件承载了页面配置、状态管理、数据处理、UI 组件、预览渲染、导出等多重职责，文件体量大、耦合高，不利于维护与测试。重构目标：

- 解耦关注点：将数据处理、UI 组件、状态、导出与预览分层
- 提升可测试性：将纯函数与渲染函数分离，便于单元测试与缓存治理
- 提升可维护性：目录清晰、命名统一、职责明确，降低修改范围
- 提升性能与体验：预览渲染可缓存，交互区域更细粒度更新

## 二、建议目录结构

参见《ARCHITECTURE.md》的“Directory Structure”和“Module Responsibilities”章节以获取最终实现版本与职责边界说明。

```text
web_ui.py                 # 应用入口（薄层 orchestrator）

core/
  state.py               # 统一的 session_state 初始化/读写门面
  constants.py           # 常量（预设颜色、字体、默认参数）
  types.py               # 类型别名/Pydantic 模型（可选）

services/
  processing.py          # 文本解析/生成缺失数据（纯函数）
  export.py              # 导出封装（整合 layout_pptx/layout_pdf）
  cache.py               # 预览/数据缓存封装（集中 st.cache_*）

ui/
  components.py          # 复用 UI 组件（颜色调色板/分页/预览占位等）
  sections.py            # 页面区块（侧边栏、输入、高级选项、预览、导出）
  styles.py              # 全局/局部 CSS 统一注入

docs/
  ARCHITECTURE.md        # 架构与约定（长期文档）
  WEB_UI_REFACTOR_PLAN.md# 本方案（当前文档）
```

## 二.1、当前目录组织（现状盘点）

- 根目录
  - `web_ui.py`：当前集成了页面配置、状态、数据处理、UI 组件、预览与导出
  - `layout_pptx.py`、`layout_pdf.py`：导出层实现
  - `pinyin_utils.py`、`dict_utils.py`：数据工具
  - `WEB_UI_GUIDE.md`、其他测试脚本（如 `test_*`）
- 存在问题
  - 入口文件过重，函数/样式/JS 零散
  - 纯函数与渲染函数混杂，难以测试与缓存
  - 没有统一的 constants/state/cache 管理

## 二.2、根目录（root）放置约定

- 顶层只放置：
  - `web_ui.py`（入口）、核心库模块（如 `layout_*`、工具类库）、README/指南类文档
- 迁移后不应再新增 UI/Services/Core 等子模块于根目录
- `docs/`、`ui/`、`services/`、`core/` 独立文件夹，用于分层管理

## 三、模块职责边界

- core.state
  - `init_state()`：初始化 `st.session_state` 所有键
  - 读写函数：封装对会话状态的读写，避免各处直接访问

- core.constants
  - 预设颜色、字体列表、默认参数、字符串常量

- services.processing（纯函数）
  - `parse_input_text(text) -> List[Card]`
  - `generate_missing_data(cards, auto_pinyin, auto_translate) -> List[Card]`
  - 不依赖 Streamlit，便于测试与缓存

- services.export
  - `export_cards(cards, format, options) -> bytes`
  - 对 `layout_pptx/layout_pdf` 进行统一封装，隔离 UI 与导出实现

- services.cache_v2
  - `cached_create_page_preview_html(...)`
  - `cached_create_simple_grid_html(...)`
  - 集中 `st.cache_data`/`st.cache_resource` 策略，统一键构造

- ui.styles
  - 集中管理 CSS 片段与主题注入，避免散落在多处 `st.markdown`

- ui.components
  - `render_color_palette(preset_colors)`：色板（按钮+JS 上色、选中态）
  - `render_page_nav(total_pages) -> int`：分页导航组件
  - `preview_placeholder()`：提供稳定占位符容器
  - 常用表单组件（字体/尺寸/间距等）

- ui.sections
  - `render_sidebar()`
  - `render_input_section()`
  - `render_advanced_options()`
  - `render_preview_section()`（内部使用缓存与占位符）
  - `render_export_section()`

## 四、入口文件职责（web_ui.py）

- 页面配置（`st.set_page_config`）
- 调用 `core.state.init_state()`
- 基于布局顺序，调用 `ui.sections.*` 渲染各区块
- 汇总状态，调用 `services.processing` 与 `services.cache_v2` 执行计算与预览
- 不包含大块 UI 实现与复杂逻辑，长度控制在 ~150 行

## 五、迁移步骤（小步安全演进）

1. 抽常量与缓存

- 新建 `core/constants.py`：预设颜色、字体、默认值
- 新建 `services/cache.py`：迁移 `cached_create_page_preview_html`、`cached_create_simple_grid_html`
- `web_ui.py` 改为 `from services.cache_v2 import ...`

## 六.1、Cleanup Plan（清理计划）

- 阶段性清理（各步迁移完成后立即执行）
  - 删除或内联的 CSS/JS：从 `web_ui.py` 清理，迁移到 `ui/styles.py` 或组件内
  - 移除重复函数：被抽取后的老实现从 `web_ui.py` 移除
  - 修正导入路径：将直接导入的工具和实现改为 `core/services/ui` 对应模块
  - 删除未使用代码：如不再调用的助手函数/变量
- 收尾清理（全部步骤完成后）
  - 入口文件长度审查：`web_ui.py` 控制在 ~150 行
  - 搜索遗留 TODO/FIXME 并处理或记录到 issue
  - 统一风格检查：运行 linter/formatter；统一类型注解
  - 更新文档：补充 `docs/ARCHITECTURE.md` 与本计划进度
- 验证
  - 手动回归：颜色选择、预览更新、分页、导出
  - 脚本测试：运行现有测试脚本 `test_*`，增补 services 层单测

1. 抽 UI 组件

- 新建 `ui/components.py`：迁移 `render_color_palette`、分页导航、预览占位等
- `web_ui.py` 改为使用组件函数，删除重复/内联实现

1. 抽 Sections

- 新建 `ui/sections.py`：将“侧边栏/输入/高级选项/预览/导出”拆为独立函数
- `web_ui.py` 仅保留“调用顺序”和少量数据传递

1. 抽处理与导出

- 新建 `services/processing.py`：`parse_input_text`、`generate_missing_data`
- 新建 `services/export.py`：`export_cards`（封装现有 layout_* 调用）
- `web_ui.py` 改为从 `services` 导入

1. 抽 State

- 新建 `core/state.py`：session_state 初始化与读写门面
- `web_ui.py` 改为使用 `state.*` 函数

1. 清理与文档

- 移除散落的 CSS/JS，集中到 `ui/styles.py` 或组件内部
- 新建/更新 `docs/ARCHITECTURE.md`，记录模块边界、依赖关系、缓存策略

每步迁移完成后本地运行验证，再进行下一步，降低风险。

## 六、最佳实践与设计约束

- 纯函数优先：`services.*` 不依赖 Streamlit，便于测试与缓存
- UI 组件化：小而专注的组件函数，提高复用与可读性
- 状态门面：统一 `state` 访问，便于未来替换实现或持久化
- 缓存集中化：所有 `st.cache_*` 放在 `services/cache`，统一管理
- CSS 集中管理：`ui/styles` 统一注入，避免散落在多个 `st.markdown`
- 类型与数据模型：对 Card 等结构使用 `TypedDict/dataclass/Pydantic`（按需）
- 约定优于配置：命名规则与目录约定明确化，降低使用成本

## 七、文件清单

- `web_ui.py`（入口）
- `core/state.py`、`core/constants.py`、`core/types.py(可选)`
- `services/processing.py`、`services/export.py`、`services/cache.py`
- `ui/components.py`、`ui/sections.py`、`ui/styles.py`
- `docs/ARCHITECTURE.md`、`docs/WEB_UI_REFACTOR_PLAN.md`

## 八、时间评估（粗略）

- 第1步 常量+缓存抽取：0.5 天
- 第2步 组件化：0.5–1 天
- 第3步 Sections：1 天
- 第4步 处理与导出抽取：0.5 天
- 第5步 状态封装：0.5 天
- 第6步 清理与文档：0.5 天

总计约 3–4 天（含验证与小修）。

## 九、风险与缓解

- 风险：拆分过程中引入回归
  - 缓解：每步完成后本地跑通关键路径；加入最小单测（processing 与 cache）
- 风险：缓存键变动导致预览不更新
  - 缓解：集中缓存封装，键统一依赖输入参数与版本号
- 风险：跨模块循环依赖
  - 缓解：遵循自上而下依赖方向（web_ui -> ui -> services -> core），禁止反向依赖

## 十、验收标准

- `web_ui.py` 控制在 ~150 行以内
- 核心逻辑在 `services.*` 可被单元测试覆盖
- 颜色选择与预览更新交互流畅，无整页跳转感
- 导出功能与现有行为一致
- 文档与目录符合本方案

## 十一、后续演进（可选）

- 为 `generate_missing_data` 增加缓存策略
- 分页导航去除不必要的显式 `st.rerun`（保持单次重跑）
- 预览渲染按卡片层级增量化（进一步减少重绘）
- 引入更系统的主题与样式变量（深/浅色主题）

## 十二、变更记录

- v1.0：初始化文档与分层方案

```text
