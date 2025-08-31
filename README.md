# 🀄 Chinese Learning Cards Generator

A modern, framework-agnostic web application for generating printable Chinese learning cards with real-time preview and export capabilities. Features a comprehensive UI refactor with digest-driven caching, state management, and unified rendering pipeline.

## 📚 Documentation

### Core Documentation

- **[Architecture Guide](docs/ARCHITECTURE.md)** - Complete system architecture and design principles
- **[State Service](docs/STATE_SERVICE_README.md)** - State management and rule engine documentation
- **[Feature Flags](docs/FEATURE_FLAGS_GUIDE.md)** - Feature flag system and rollout management
- **[UI Adapters](docs/UI_ADAPTER_API.md)** - Framework-agnostic UI adapter system
- **[Testing Guide](docs/TESTING_GUIDE.md)** - Comprehensive testing strategy and examples

### Feature Documentation

- **[Feature Rollout Procedures](docs/FEATURE_ROLLOUT_PROCEDURES.md)** - Gradual rollout and A/B testing
- **[Migration Guide](docs/MIGRATION_GUIDE.md)** - Data migration and compatibility
- **[Performance Guide](docs/PERFORMANCE_GUIDE.md)** - Performance optimization and monitoring

### Legacy Documentation

- **[E2E Testing](docs/E2E_TESTS_DOCUMENTATION.md)** - End-to-end testing documentation
- **[Test Coverage](docs/TEST_COVERAGE_REPORT.md)** - Test coverage reports
- **[Integration Testing](docs/INTEGRATION_TESTS_SUMMARY.md)** - Integration test summaries
- **[CI E2E Testing](docs/CI_E2E_TESTING.md)** - Continuous integration testing

> 注：本仓库同时保留了最初的 CLI 文档作为补充说明（见 docs/要求.md）。

## 🚀 Key Features

### Modern Architecture
- **Framework-Agnostic Design**: UI adapter system enables testing and future framework migration
- **Digest-Driven Caching**: Intelligent cache invalidation based on content changes
- **State Management**: Centralized state service with rule engine and validation
- **Unified Rendering**: Shared render core ensures preview-export consistency

### Performance & Reliability
- **Advanced Caching**: Multi-level caching with TTL and size-based eviction
- **Performance Monitoring**: Built-in telemetry and performance tracking
- **Error Handling**: Comprehensive error handling with graceful degradation
- **Memory Management**: Efficient memory usage with automatic cleanup

### Development & Operations
- **Feature Flags**: Comprehensive feature flag system with gradual rollout
- **A/B Testing**: Built-in A/B testing and canary deployment capabilities
- **Comprehensive Testing**: Unit, integration, and end-to-end test coverage
- **Migration Support**: Automatic data migration with rollback capabilities

### User Experience
- **Real-time Preview**: Instant preview updates with intelligent caching
- **Responsive Design**: Optimized for different screen sizes and devices
- **Export Consistency**: Guaranteed consistency between preview and export
- **Browser Storage**: Client-side persistence with automatic cleanup

## 🏗️ Architecture Overview

The application follows a layered, framework-agnostic architecture:

```
┌─────────────────┐
│   UI Layer      │ ← Framework-agnostic components
├─────────────────┤
│ Service Layer   │ ← Business logic and data processing
├─────────────────┤
│  Core Layer     │ ← State management and utilities
├─────────────────┤
│Infrastructure   │ ← Caching, persistence, monitoring
└─────────────────┘
```

### Key Components

- **State Service**: Centralized state management with rule engine
- **UI Adapters**: Framework abstraction for testing and flexibility
- **Cache V2**: Advanced caching with schema versioning
- **Render Core**: Shared rendering logic for consistency
- **Feature Flags**: Gradual rollout and A/B testing system

# 一、目标与范围

## 目标

* 输入：一份词表（`汉字/词语, [可选]拼音, [可选]英文`）。
* 处理：若拼音/翻译缺失，自动生成：

  * 拼音：带声调的标准拼音；
  * 翻译：优先取词典首义项，可人工覆盖。
* 输出（任选其一或全部）：

  1. **PPTX（推荐）**：每页 3×3 独立方框（互不共享边线），可在 PowerPoint 里直接编辑与打印；
  2. **PDF**：同样的 3×3 布局，直接打印最稳定；
  3. **DOCX（备选）**：用表格+间距实现接近效果（Word 的表格边线天然共享，已知限制）。

**不做**（初版）：在线翻译接口调用、复杂多义项选择 UI、自动断行/缩放到极端字号。

---

# 二、技术选型（以“最快落地”为原则）

* **语言**：Python 3.10+
* **库**

  * 拼音：`pypinyin`（支持多音字、声调：`Style.TONE`）
  * 翻译词典：**CC-CEDICT**（离线开源中英词典）。做法：项目内自带一个**精简 JSON 词典**（常用字/词 2–5k 条，覆盖率高）；也支持用户放入完整 `cedict_ts.u8` 文件以提升覆盖率
  * 生成 PPT：`python-pptx`（每个卡片=独立矩形文本框，独立边线，编辑与打印友好）
  * 生成 PDF：`reportlab`（矢量方框，印刷级稳定）
  * 可选：`opencc`（繁简转换），`jieba`（需要时做分词，处理多字词）

---

# 三、目录结构（简化）

```text
.
├─ web_ui.py                  # Streamlit 应用入口
├─ core/                      # 常量、状态
├─ services/                  # 处理、导出、缓存
├─ ui/                        # 组件、区块、样式
├─ src/                       # 与框架无关的库模块（pinyin、dict、layout_*、脚本）
├─ docs/                      # 文档（见 docs/README.md）
├─ tests/                     # 测试
├─ data/                      # 词典数据
├─ samples/                   # 示例输入
└─ out/                       # 导出文件
```

---

# 四、输入格式（CSV/TSV/纯文本）

* **CSV（推荐）**：`hanzi,pinyin,english`
* 允许缺列或留空：缺失时自动补全
* 示例 `samples/words.csv`：

```csv
爱,,love
家,jiā,home
朋友,péngyou,friend
水,,water
火,huǒ,fire
山,,mountain
月,,moon
日,,sun
木,,wood
```

---

# 四、运行与使用

## 启动 Web UI

```bash
python -m streamlit run web_ui.py
```

然后在浏览器中打开 <http://localhost:8501>

## 导出

- PPTX 和 PDF 导出按钮位于主界面
- 导出文件会通过浏览器下载

## 测试

- 运行全部测试：
  - `python scripts/run_tests.py all`
- 快速冒烟测试：
  - `python scripts/run_tests.py quick`
- 直接使用 pytest：
  - 安装依赖：`pip install -r requirements.txt`
  - 运行：`python -m pytest -q`
  - 覆盖率：`pytest --cov --cov-report=term-missing --cov-report=xml`

# 五、CLI 用法（示例）

```bash
# 安装依赖
pip install pypinyin python-pptx reportlab opencc jieba

# 生成 PPTX（可编辑、独立边框）
python src/gen_cards.py \
  --in samples/words.csv \
  --out out/cards.pptx \
  --format pptx \
  --page A4 --card-size 6 --gap 0.6 --margin 1 \
  --font-hanzi 48 --font-pinyin 18 --font-en 14 \
  --auto-pinyin --auto-translate --dict data/mini_cedict.json

# 生成 PDF（直接打印）
python src/gen_cards.py \
  --in samples/words.csv \
  --out out/cards.pdf \
  --format pdf \
  --page A4 --card-size 6 --gap 0.6 --margin 1
```

## 关键参数

* `--page`：A4 / Letter
* `--card-size`：单卡片边长（cm，默认 6）
* `--gap`：卡片间距（cm，默认 0.6）
* `--margin`：页面外边距（cm，默认 1）
* 字体：`--font-hanzi` / `--font-pinyin` / `--font-en`（pt）
* 自动补全：`--auto-pinyin` / `--auto-translate`
* 词典：`--dict` 指向 `mini_cedict.json` 或完整 `cedict_ts.u8`

---

# 六、核心实现要点

## 1) 拼音生成

* 使用 `pypinyin`：

  * 多字词直接传整词，得到词级拼音；
  * 样式：`Style.TONE`（带声调），fallback：`Style.TONE3`（数字声调）；
  * 多音字策略：默认取**首个常用读音**；支持 `--heteronym` 输出多读音供人工挑选（可写入旁注列）。

## 2) 翻译生成

* 优先查**精简 JSON 词典**（覆盖常用字词，速度快、离线稳定）；
* 若未命中且提供 `cedict_ts.u8`，则解析 CEDICT，取**首义项**；找不到则留空；
* 用户手动补充翻译 → 程序优先使用用户给定值（不覆盖）。

## 3) 布局与样式（3×3 九宫格）

* **PPTX**：用 `python-pptx` 在空白幻灯片上添加 9 个矩形 Shape（独立边框，不共享），每个 Shape 内部：

  * 行 1：汉字（加粗，大字号，行距 1.1）
  * 行 2：拼音（斜体，中字号）
  * 行 3：英文（小字号）
  * 文字居中（水平、垂直）
* **PDF**：`reportlab` 画 9 个方框（`rect`），再在中心写三行文本；同样的边距、间距、字号参数，保证与 PPTX 视觉一致。
* 页尺寸与边距：A4/Letter + 自定义 `margin`；栅格宽度＝`card-size*3 + gap*2`，按 `start_left/top = margin` 计算九宫格坐标。

---

# 七、最小代码骨架（节选）

**`pinyin_utils.py`**

```python
from pypinyin import pinyin, Style

def hanzi_to_pinyin(text: str) -> str:
    py = pinyin(text, style=Style.TONE, heteronym=False)
    return " ".join(syll[0] for syll in py)
```

**`dict_utils.py`**

```python
import json, re

def load_mini_dict(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def lookup_en(word: str, mini: dict, cedict=None) -> str | None:
    if word in mini: return mini[word][0]  # 取首义项
    if cedict:
        # 简化：假设 cedict 为 {hanzi: [defs...]}
        defs = cedict.get(word)
        if defs: return defs[0]
    return None
```

**`layout_pptx.py`（单页绘制核心）**

```python
from pptx import Presentation
from pptx.util import Cm, Pt
from pptx.enum.text import PP_ALIGN

def add_page(prs, cards, card_cm=6.0, gap_cm=0.6, margin_cm=1.0,
             f_hz=48, f_py=18, f_en=14):
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # 空白
    for i, card in enumerate(cards):
        r, c = divmod(i, 3)
        left = Cm(margin_cm + c * (card_cm + gap_cm))
        top  = Cm(margin_cm + r * (card_cm + gap_cm))
        width = height = Cm(card_cm)
        shape = slide.shapes.add_shape(
            1, left, top, width, height  # 1=MSO_SHAPE.RECTANGLE
        )
        shape.line.width = Pt(2)
        tf = shape.text_frame
        tf.clear()
        for text, size, bold, italic in [
            (card['hanzi'], f_hz, True, False),
            (card['pinyin'], f_py, False, True),
            (card['english'], f_en, False, False),
        ]:
            p = tf.add_paragraph() if tf.paragraphs[0].text else tf.paragraphs[0]
            p.text = text
            p.font.size = Pt(size); p.font.bold = bold; p.font.italic = italic
            p.alignment = PP_ALIGN.CENTER
        # 垂直居中
        tf.vertical_anchor = 2  # MSO_ANCHOR.MIDDLE
```

**`gen_cards.py`（主流程示意）**

```python
# 1) 读 CSV → rows
# 2) 对每行：若缺拼音→pypinyin；若缺英文→lookup
# 3) 分组每9个 → 调用 layout_pptx.add_page 或 layout_pdf.add_page
```

---

# 八、质量与边界策略

* 多音字：默认首读音；提供 `--heteronym` 导出辅助列供人工审核；
* 词典未命中：英文留空，不阻断流程；导出后可在 PPTX 手动补齐；
* 长词/专有名词：可在 CSV 中显式给定拼音/英文以覆盖自动结果；
* 字体：默认系统字体，用户可在 PPTX 中二次修改（宋体/思源黑体等）。

---

# 九、交付物

* `gen_cards.py` 可执行脚本
* 示例词表 `samples/words.csv`
* 预置 `data/mini_cedict.json`（常用词/字）
* 使用说明 `README.md`
* 生成样例：`out/cards.pptx`、`out/cards.pdf`

---

# 十、后续可选增强

* 更多导出格式（DOCX、HTML）
* 主题与样式系统（深/浅色主题、模板）
* 更丰富的词典来源与用户词典
* 插件式导出与布局

---

This project is open source. The CC-CEDICT dictionary data is licensed under Creative Commons Attribution-Share Alike 3.0.

## Contributing

Contributions welcome! See docs/ARCHITECTURE.md and docs/WEB_UI_GUIDE.md to get started.

### Testing

This project includes comprehensive E2E testing:

- **36 E2E tests** covering all major functionality
- **100% pass rate** with robust error detection
- **90% functional coverage** of user workflows
- See [E2E Testing Guide](tests/playwright-ts/README.md) for details

### Development Suggestions

- Additional output formats (DOCX, HTML)
- More dictionary sources
- UI/UX improvements
- Additional languages
- Test coverage improvements
