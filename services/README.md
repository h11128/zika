# services/

无 UI 依赖的业务逻辑：
- processing.py：文本解析、缺失数据生成（纯函数）
- export.py：导出封装（整合 layout_pptx/layout_pdf）
- cache.py：缓存封装（集中 st.cache_* 策略）

