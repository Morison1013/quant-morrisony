# MILESTONE-003 — 数据看板（指数 + 板块）

**完成日期：** 2026-05-30

## 交付内容

### 后端
- `backend/app/services/data_fetcher_index.py` — 指数数据获取
  - 四大指数：上证指数(000001)、深证成指(399001)、创业板指(399006)、科创50(000688)
  - 支持日K/周K/月K/5分钟数据
- `backend/app/services/data_fetcher_sector.py` — 板块指数数据获取
  - 53 个通达信板块（行业 + 概念/题材）
  - 自动分类：行业板块、科技/AI、新能源、大消费、军工/高端制造、医药、概念题材
  - 使用 `get_index_bars` 获取数据（避免 pytdx 板块数据 bug）
- `backend/app/api/dashboard.py` — 数据看板 API 路由
  - `GET /api/dashboard/indices` — 指数列表
  - `GET /api/dashboard/index/{symbol}/history` — 指数历史（支持频率切换）
  - `GET /api/dashboard/sectors` — 板块列表
  - `GET /api/dashboard/sector-categories` — 按类别分组的板块
  - `GET /api/dashboard/sector/{symbol}/history` — 板块历史（支持频率切换）
- `backend/app/schemas/dashboard.py` — Pydantic Schema

### 前端
- `frontend/src/app/dashboard/page.tsx` — 数据看板主页
  - 4 大指数多宫格并列显示
  - 周期切换（日K/周K/月K/分时）
  - 板块指数分类列表（点击跳转详情）
- `frontend/src/app/dashboard/sector/[symbol]/page.tsx` — 板块详情页
  - K 线图 + 成交量副图 + 均线系统
  - 周期切换
  - 其他板块快捷链接
- `frontend/src/components/DashboardChart.tsx` — 可复用看板图表组件
- `frontend/src/components/Header.tsx` — 新增「数据看板」导航标签
- `frontend/src/lib/api.ts` — 新增 Dashboard API 客户端

### 路由结构
```
/                              股票查询（个股）
/scanner                       全市场扫描
/dashboard                     数据看板（指数 + 板块列表）
/dashboard/sector/[symbol]     板块详情
/stock/[symbol]                个股详情（从扫描跳转）
```
