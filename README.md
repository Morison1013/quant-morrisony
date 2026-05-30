# Quant_Morrisony — A 股量化看盘助手

> 个人 A 股复盘分析系统：通达信(pytdx)行情 + Pandas 向量化计算 + FastAPI 原子接口 + Next.js 可视化看板

## 架构

```
Quant_Morrisony/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/             # 原子化 API 路由
│   │   ├── services/        # 数据获取(pytdx) + 策略计算(Pandas)
│   │   ├── schemas/         # Pydantic 数据模型
│   │   ├── config.py        # 全局配置
│   │   └── main.py          # FastAPI 入口
│   ├── tests/               # 单元测试
│   └── requirements.txt
├── frontend/                # Next.js 前端
│   ├── src/
│   │   ├── app/             # App Router 页面
│   │   ├── components/      # 图表 & 指标面板
│   │   └── lib/             # API 客户端
│   └── package.json
└── docs/                    # 需求 / 规格 / 里程碑
    ├── requirements/
    ├── specs/
    └── milestones/
```

## 快速开始

### 后端

```bash
cd backend
pip install -r requirements.txt

# 首次运行：刷新本地数据库（约 4 分钟）
python scripts/refresh_daily.py

# 启动服务
python run.py
# → http://localhost:8000
# → API 文档: http://localhost:8000/docs
```

> 💡 **本地数据库**：扫描速度从 23 分钟降至 ~80 秒。每天收盘后运行 `refresh_daily.py` 更新数据。

### 前端

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

## API 接口

| 路由 | 说明 | 参数 |
|------|------|------|
| `GET /api/stock/history` | 带策略指标的历史 K 线 | `symbol`(代码), `limit`(条数) |
| `GET /api/stock/summary` | 最新策略复盘摘要 | `symbol` |
| `GET /api/scanner/scan` | 全市场扫描（多策略过滤） | `ma_bullish`, `macd_golden`, `arbitrage`, `rubbing` |
| `GET /api/scanner/strategies` | 可用策略列表 | — |
| `GET /health` | 健康检查 | — |

## 数据源：通达信 (pytdx)

使用 [pytdx](https://github.com/rainx/pytdx) 协议直连通达信行情服务器，内置主站池自动 fallback：
- 上海行情（6xxxxx / 68xxxx）→ market=1
- 深圳行情（0xxxxx / 3xxxxx）→ market=0
- 默认返回前复权数据
- 每次拉取 800 条（约 3 年日线），自动去重

## 策略指标

### 1. 均线多头排列
60/55/30/20/10/5 日均线全部向上（MA5 > MA10 > MA20 > MA30 > MA55 > MA60）

### 2. MACD 多周期验证
- 月线 MACD 金叉（趋势看多）
- 周线未死叉（中期安全）
- 日线未死叉（短期安全）

### 3. 成交量异动 — 隔日套利信号
- 近 3 日成交量逐日递减
- 最新日成交量低于近 20 日均量
→ 标记为「可隔日套利」（量缩价稳）

### 综合打分
| 条件 | 分值 |
|------|------|
| 均线多头排列 | +30 |
| 月 MACD 金叉且周/日未死叉 | +25 |
| 触发隔日套利信号 | +20 |
| 触发红色揉搓线 | +25 |
| **满分** | **100** |

## 技术栈

- **后端:** Python 3.10+, FastAPI, pytdx（通达信行情）, Pandas, Pydantic
- **前端:** Next.js (App Router), Tailwind CSS, ECharts
- **测试:** pytest (38/38 passed)

## 开发路线

- [x] 量化基座：通达信数据 + 策略计算 + API 暴露 + 前端可视化
- [x] 全市场扫描器（沪深主板，4 策略过滤）
- [ ] 实时推送：SSE (Async Generator → Server-Sent Events)
- [ ] 自选股管理
- [ ] 更多策略因子 & 回测引擎

---
⚠️ 仅供个人复盘参考，不构成投资建议。
