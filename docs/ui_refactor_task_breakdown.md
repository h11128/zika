## UI 重构实现任务分解（适用于 AI Agent）

本文件将 ui_refactor_design（英文/中文设计规范）转化为可执行、可追踪、可验证的实现任务，便于 AI agent 或自动化流水线逐步落地。文档采用“阶段 → 任务 → 子步骤/依赖/验收/回滚”的结构，并提供设计追溯矩阵与自查清单。

### 0. 目标与范围
- 目标：在保证一致性与可回滚的前提下，完成 UI 架构重构（State Service 统一写闸门、统一预览管线、持久化与冲突合并、缓存策略、错误边界、观测与运维）。
- 输出：
  - 新增/更新的核心模块：`ui/state.py`（含内部子模块）、`services/cache_v2`、`services/export`、`services/layout.py`、共享渲染核心（Shared-Render-Core）
  - 配置/Schema：Feature Flags、PREVIEW_CACHE_SCHEMA_VERSION、EXPORT_SCHEMA_VERSION、code_version
  - 文档：本任务分解、变更日志、运维手册
- 非目标：业务功能扩展（除必须支撑重构的最小变更），新后端存储（IndexedDB 仅作为演进方向，不在本阶段强制）

### 1. 基线与前置条件
- 代码基线：当前分支 `bug-fix`（含最近合并的文档与模板改动）
- 运行环境：Python 3.10+；`pip install -r requirements.txt`
- 质量门禁：必须通过 `scripts/run_tests.py` 与 `pytest -q`，并保持现有测试不回退
- 观测前置：启用最小遥测埋点（事件结构已在设计文档定义）

### 2. 阶段任务总览（映射设计实现计划 P1 - P9）
- P1 基础设施（Feature Flags + State Service 雏形 + 摘要/失效 + session_generation）
- P2 预览统一（controller 构建 AppConfig → dataclasses → render v2；legacy 委托）
- P3 组件与样式（去副作用；sticky preview；Color Palette 返回值/回调）
- P4 编辑器（稳定 UUID、按 id 合并、version 递增、单次失效）
- P5 持久化（快照、迁移、配额、禁用/降级）
- P6 模块化（拆分 `sections.py` 为 `ui/*` 子模块）
- P7 性能与观测（缓存策略、预热、预取、并发隔离、事件上报）
- P8 兼容性与迁移（数据/特性开关测试矩阵、回滚通道）
- P9 收尾与旗标清理（弃用旧路径、稳定键命名）

---

### 3. 阶段与任务明细（每项均含：子步骤 / 依赖 / 验收 / 回滚）

#### P1 基础设施
- T1-P1-FF：引入 Feature Flag 基础
  - 子步骤：
    1) 新增 `core/feature_flags.py` 提供 flag 读取（测试覆写 > 环境变量 > 配置文件 > 远程服务 > 默认值）
    2) 远程结果本地缓存 TTL=5 分钟，失败指数退避；提供测试覆写上下文管理器
  - 依赖：无
  - 验收：
    - 单测：flag 读取优先级、覆写生效
    - 集成：flag 控制旧/新预览路径选择
  - 回滚：关闭 flag 即回退到旧路径

- T2-P1-STATE：创建 State Service 雏形（门面 + 内部分层）
  - 子步骤：
    1) 目录 `ui/state/`：`store.py`、`rules.py`、`digest.py`、`invalidations.py`、`nav.py`、`ports.py`
    2) 门面 `ui/state.py`：selectors/setters/batch、hydrate/schedule/flush、invalidate_preview_cache
    3) `session_generation` 生成与持久策略（会话内一致）
  - 依赖：T1-P1-FF
  - 验收：
    - 单测：不变量（样例）、摘要计算、导航钳制
    - 集成：批处理只触发一次失效
  - 回滚：切回 `sections.py` 直写路径（flag）

- T3-P1-DIGEST：摘要与键规范
  - 子步骤：
    1) `normalize_for_digest`（浮点 4 位、集合排序、Decimal 字符串）
    2) processing/layout/style/preview_params_digest 计算
  - 依赖：T2-P1-STATE
  - 验收：
    - 单测：不同输入等价类的相等性；预览键不包含大内容
  - 回滚：切回旧键策略（flag）

#### P2 预览统一
- T1-P2-PIPE：统一预览管线（v2）
  - 子步骤：
    1) Controller 组装 AppConfig；边界转换为 dataclasses（使用 frozen，不可变且可哈希）
    2) `services/cache_v2`：加入 `PREVIEW_CACHE_SCHEMA_VERSION`、`code_version`
    3) 旧函数委托至 v2
  - 依赖：P1
  - 验收：
    - 集成/E2E：黄金对比（v1==v2）在 flag on/off 下相等
    - 缓存键必须包含 `session_generation`；严禁全局清缓存（仅允许分层清理）
  - 回滚：flag 关闭回旧路径

- T2-P2-SRC：抽取共享渲染核心（Shared-Render-Core）
  - 子步骤：
    1) 提炼断行/行高/字体回退与模板组合的共性渲染逻辑为共享模块
    2) `services/cache_v2` 与导出路径共同复用共享渲染核心
    3) 以统一参数（LayoutOptions/Typo/Visual）驱动，消除重复实现
  - 依赖：T1-P2-PIPE
  - 验收：
    - 预览/导出黄金对比一致；渲染差异集中在适配层
  - 回滚：保留旧渲染路径，flag 回退
  - API 草案:
    - `RenderOptions(dataclass)`: 包含字体、颜色、尺寸、边距等所有渲染所需参数。
    - `Card(dataclass)`: 包含卡片内容。
    - `render_page(cards: List[Card], options: RenderOptions) -> RenderResult`: 核心函数，返回包含 HTML/SVG 和元数据（如计算后的尺寸）的 `RenderResult` 对象。

#### P3 组件与样式
- T1-P3-UI：移除副作用失效；引入 表单语义 与去抖（由 UI 适配器封装）
  - 子步骤：
    1) 需要原子提交的控件纳入 表单语义（`on_submit → set_options_batch`），由适配器统一实现
    2) 即时交互：State Service 150–250ms 去抖合并
  - 依赖：P2
  - 验收：交互不抖动、无多次 rerun；相关集成用例通过；`schedule_refresh()` 每次用户操作最多触发一次刷新
  - 回滚：停用去抖/表单（flag）
- T2-P3-ADAPTER-Lite：UI 端口/适配器（定义 + 最小落地）
  - 子步骤：
    1) 新增 `ui/ports.py`：定义 `UIAdapter`、`UIInputsPort`、`UIPreviewPort`、`UINotificationPort`、`UIRefreshScheduler`、`UIFormContext`
    2) 新增 `ui/adapters/streamlit_adapter.py`：封装 rerun/去抖/表单语义（最小实现）
    3) 新增 `FakeAdapter`：记录事件与刷新调用次数，用于单元/集成测试
    4) 在 `ui/sections.py` 迁移一个小段（如颜色或分页）作为示范，flag 控制
  - 依赖：T1-P3-UI
  - 验收：
    - 单测：使用 `FakeAdapter` 能完整驱动“事件→状态→预览/导出”流程；一次操作最多一次刷新
    - 集成：示范段落在适配器与直连路径下行为一致（黄金对比），E2E 不回退
  - 回滚：flag 回退到直接使用框架路径

#### P4 编辑器
- T1-P4-ID：稳定 UUID、version 与按 id 合并
  - 子步骤：
    1) Card `{id(uuid), hanzi, pinyin, english, version, created_at}`
    2) Apply 按 UUID 合并；version 原子递增；一次性预览失效
    3) 规范化内容哈希仅用于重复检测，不作为主键
  - 依赖：P1-P3
  - 验收：
    - 单测/集成：合并正确、顺序稳定、仅一次失效
  - 回滚：临时使用内容哈希（仅开发模式）并提示风险

#### P5 持久化
- T1-P5-SNAPSHOT：快照/迁移/配额/禁用
  - 子步骤：
    1) UserSnapshot vN；migrate_snapshot；配额/禁用降级
    2) JSON 时间：ISO‑8601 UTC（Z）；只存原始可序列化类型
    3) 支持 `DISABLE_PERSISTENCE=true` Kill-switch（禁用浏览器持久化）
    4) `export_history: List[ExportRecord]` 与清理策略（最多 50 条/30 天）
  - 依赖：P4
  - 验收：
    - 单测：迁移覆盖与回退
    - 集成：禁用/配额不足时的降级与提示
  - 回滚：禁用持久化 kill-switch

- T2-P5-CONFLICT（延期）：多标签冲突合并
  - 状态：不在本期范围，后续阶段再纳入

#### P6 模块化
- T1-P6-SPLIT：拆分 `sections.py`
  - 子步骤：
    1) `ui/inputs.py`、`ui/options.py`、`ui/preview.py`、`ui/editor.py`、`ui/export.py`、`ui/sidebar.py`
    2) 从 `src/layout_pdf.py` 与 `src/layout_pptx.py` 抽取共性布局/排版逻辑至 `services/layout.py`，导出端差异保留在各自适配层
  - 依赖：P3-P5 逐步
- T2-P6-ADAPTER：UI 适配器全面迁移（去除直接 `st.*`）
  - 子步骤：
    1) 以段落为单位将 `sections.py` 全面改为通过 `UIAdapter` 调用
    2) 清理直连调用与临时兼容代码；完善适配器 API 细节
    3) 按功能灰度切换 `FEATURE_UI_ADAPTER`，达成对照一致后设为默认
  - 依赖：T2-P3-ADAPTER-Lite、P4、P5
  - 验收：
    - 集成/E2E：适配器路径与旧路径黄金对比一致；刷新次数/首帧/缓存命中指标不回退
    - 代码层：UI 代码不再直接依赖 `st.*`，仅通过 `UIAdapter`
  - 回滚：flag 回退到旧路径

#### P7 性能与观测
- T1-P7-CACHE：缓存策略（TTL/max_entries/LRU + 观测）
  - 子步骤：
    1) 默认值：预览缓存 TTL=3600s、max_entries=100；导出缓存 TTL=7200s、max_entries=50；会话缓存 TTL=1800s、max_entries=200；均采用 LRU 驱逐。观测指标：命中率、p95/p99、Top‑N 键大小、驱逐率
    2) 分层清理顺序：slice → preview → export → session
    3) 导出缓存键实现 `compute_export_key(export_params, cards_count, content_version_signal[, ...])`，其中 `content_version_signal = snapshot_last_modified OR cards_version` (定义为所有卡片 `(uuid, version)` 元组有序列表的哈希值)；删除旧的不含内容版本信号的实现
    4) 严禁调用全局清理 API（如 `st.cache_data.clear()`），仅允许按层级清理并记录结构化日志
  - 依赖：P2
  - 验收：
    - 性能基准：digest 变更后首帧 <500ms，缓存渲染 <100ms
    - 正确性：内容变更但数量不变时导出缓存必定失效（以黄金测试与日志验证）

- T2-P7-WARMUP：预热/预取与并发隔离
  - 子步骤：
    1) digest 变更后预渲染下一个 page-slice；nav_index ±1 预取
    2) 导出队列并发≤3、30s 超时、可取消；独立线程池
  - 依赖：T1-P7-CACHE
  - 验收：
    - 压测：10k+ 卡片、50+ 并发、8h 会话

- T3-P7-TELEM：性能事件模型与上报
  - 子步骤：
    1) 事件结构：`request_id, preview_params_digest, session_generation, elapsed_ms, op_name, cache_hit`
    2) 采样率：错误 100%、常规 10%、高频 1%；Beacon/退避重试
    3) 传输：空闲/卸载（beacon）批量发送；失败指数退避；开发态可本地落盘
  - 依赖：无
  - 验收：
    - 开发模式下，遥测事件可正确落盘本地文件，其结构与内容（如 correlation_id）符合规范；日志可串联，生产模式下阈值告警可触发。

#### P8 兼容性与迁移
- T1-P8-MIG：数据迁移实测（真实样本集）
  - 子步骤：
    1) 旧快照 → 新 Schema；回退验证
  - 验收：迁移成功率 100%，失败有提示与回退

- T2-P8-FF-TEST：特性开关一致性测试
  - 子步骤：
    1) v1/v2 黄金对比；flag 覆写工具
  - 验收：一致性通过方可默认开启

#### P9 收尾
- T1-P9-CLEAN：清理 legacy 与稳定键
  - 子步骤：
    1) 去除未使用路径；冻结命名/单位/键
  - 验收：
    - 测试绿、文档更新、运行手册同步

---

### 4. 横切任务（跨阶段）
- 安全：统一转义/清洗、CSP 边界（仅预览 HTML）、不在本地存敏感信息
- 设计一致性：DPI 常量（96DPI→1cm≈37.795px）、四舍五入（hash 前 4 位）
- 字段迁移与别名：核心配置对象 `core.config.LayoutConfig` 中的 `gap`/`margin` 字段迁移为 `gap_cm`/`margin_cm`，明确单位为厘米。在配置读取层提供别名适配以兼容旧格式快照；快照迁移时统一到带 `_cm` 后缀的新字段。
- UI 适配层：所有 UI 代码仅调用 `ui/ports.py` 定义的接口；rerun/去抖/表单提交必须封装在适配器内部；禁止在 UI 层直接清缓存/直接 rerun
- 代码版本：开发 `dev-{short_sha}-{YYYYMMDDHHMMSS}`（脏工作区追加 `-dirty`）；CI `ci-{BUILD_NUMBER}-{short_sha}`（缺失回退 sha）；生产 `v{semver}` 或 `v{semver}+build.{build_number}`
- 文档与示意图：Mermaid 已更新（共享渲染核心、缓存决策、错误回退）

### 5. 观测与运维（Ops）
- 仪表盘：命中率、p95/p99、Top‑N 键大小、驱逐率、导出队列长度
- 告警门限：命中率<80%，p95>500ms，内存>100MB，导出超时>5%
- 预热策略：digest 变更后预渲染 1 个后续页；内存感知上限 2-3 页
- 回收：导出结束主动清理、周期性驱逐；分层清理顺序；禁止全局清缓存

### 6. 测试任务矩阵（与仓库测试对齐）
- 单元测试（新增/覆盖）：
  - `ui/state/*`：rules/digest/invalidations/nav（属性测试 + 不变量）
  - `services/layout.py`：`compute_auto_card_size_cm`、`paginate`
  - 渲染核心：断行/行高/字体回退（可用样例集）
  - `ui/ports.py`：`FakeAdapter` 行为（事件记录、schedule_refresh 次数校验、表单提交回调）
- 集成测试：
  - 仅 style 变更不重置分页：`tests/ui/test_ui_sections_preview_wrapper.py`
  - 预览/导出一致性：`tests/ui/test_export_and_layout.py`、`tests/ui/test_preview_update_e2e.py`
  - （延期）冲突合并：本期不纳入
  - 导出缓存键内容版本信号：构造“内容变更但 cards_count 不变”的用例，断言缓存 miss，并记录 `content_version_signal` 变更
  - UI 适配器路径：使用 `FakeAdapter` 跑集成流，断言无直接 `st.*` 调用痕迹（通过 monkeypatch 或探针）
- E2E（Playwright）：
  - `tests/playwright-ts/tests/preview-modes.spec.ts`、`export-functionality.spec.ts`、`pagination-navigation.spec.ts` 等；记录首帧、rerun 次数与去抖效果（开发态指标）
- 压测/性能：本地基准脚本；集成到 CI 夜间任务

### 7. 设计追溯矩阵（Design → Tasks）
| 设计章节 | 关键点 | 任务 ID |
|---|---|---|
| 4.2 摘要与失效 | digest/preview_params_digest | T3-P1-DIGEST |
| 4.4 预览管线 | v2 统一/legacy 委托 | T1-P2-PIPE |
| 4.5 编辑器 | 稳定 UUID/按 id 合并/单次失效 | T1-P4-ID |
| 4.6 持久化 | 快照/迁移/JSON 时间/禁用 | T1-P5-SNAPSHOT |
| （延期）4.20 冲突合并 | 不在本期范围 | T2-P5-CONFLICT |
| 4.14 去抖与表单 | st.form + 150–250ms 合并 | T1-P3-UI |
| 4.17 缓存策略 | TTL/max_entries/LRU/观测 | T1-P7-CACHE |
| 4.23 并发隔离 | 预取/导出队列/超时取消 | T2-P7-WARMUP |
| 4.19 日志/关联 | request_id + session_generation 串联 | T3-P7-TELEM |
| 4.22 字体一致性 | DPI/断行/行高策略 | 覆盖到共享渲染核心 |

### 8. 里程碑与退出标准
- 里程碑：P1→P3→P5→P7→P9；每阶段需：测试绿、文档更新、flag 可控回退
- 退出标准：
  - 预览/导出共享渲染核心，黄金对比通过
  - 性能达标：首帧<500ms、缓存<100ms
  - 稳定：无全局清缓存、错误有回退路径

### 9. 回滚与风险
- 回滚：全部关键路径均由 Feature Flag 包裹，可单点关闭
- 风险：
  - 状态服务成为瓶颈 → 模块化/属性测试/API 稳定/监控
  - 多标签冲突 → 版本+时间戳、提示节流、回滚入口
  - 缓存/版本漂移 → 包含 schema/version+code_version；禁全清

### 10. 自查清单（Agent 执行前后使用）
- [ ] 所有新键/字段都在 digest/快照/Schema 中定义且有默认值与迁移
- [ ] 任何新交互已纳入 `st.form` 或 State Service 去抖
- [ ] 预览与导出均走共享渲染核心；导出缓存键含 `content_version_signal`
- [ ] 错误边界：每个 UI 段落有 try/except 与降级 UI
- [ ] 观测：事件结构、采样率与上报通路连通；阈值告警可触发
- [ ] 测试：单元/集成/E2E/性能/性质测试均覆盖关键路径
- [ ] 文档与示意图更新；可回滚路径验证通过

---

附注：执行顺序建议“旗标优先 + 可回滚”，并在每个阶段结束前完成“黄金对比与性能基线”校验。 