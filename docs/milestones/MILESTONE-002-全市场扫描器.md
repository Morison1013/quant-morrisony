# MILESTONE-002 — 全市场扫描器

**完成日期：** 2026-05-30

## 交付内容

### 后端
- `backend/app/services/scanner.py` — 全市场扫描服务
  - `scan_stocks(strategies)` 并发扫描（4 线程并发，15 秒超时）
  - 策略过滤：ma_bullish / macd_golden / arbitrage / rubbing
  - 结果按 strategy_score 降序排列
- `backend/app/api/scanner.py` — 扫描 API 路由
  - `GET /api/scanner/scan` — 多策略扫描
  - `GET /api/scanner/strategies` — 可用策略列表
- `backend/app/services/data_fetcher.py` — 新增 `get_all_stock_codes()` 函数
  - 深圳股票从 TDX 服务器拉取（00xxxx，仅主板）
  - 上海股票从模式生成（600/601/603/605）
  - 5 分钟缓存机制，验证后保留
- `backend/tests/test_scanner.py` — 7 个单元测试

### 前端
- `frontend/src/app/scanner/page.tsx` — 全市场扫描页面
  - 4 个策略 checkbox 勾选面板
  - 扫描中进度条
  - 结果表格（排名/代码/名称/最新价/打分/匹配策略/详情跳转）
- `frontend/src/app/stock/[symbol]/page.tsx` — 股票详情页
  - 复用 KLineChart + SummaryCard
  - 从扫描页跳转 / 从查询页跳转
- `frontend/src/components/Header.tsx` — 公共导航组件
  - 股票查询 | 全市场扫描 标签切换

### 扫描范围
- 沪深主板 ~5500 只（排除创业板/科创板/北交所）

## 测试结果

| 模块 | 通过数 |
|------|--------|
| test_scanner.py | 7/7 |
| 全系统测试 | 38/38 |
