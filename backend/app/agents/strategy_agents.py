"""
多 Agent 协作 — 策略扫描 Agent。

每个 Agent 封装一个策略的扫描逻辑，独立并行执行。
Agent 之间通过 State 共享数据，不直接调用彼此。
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from app.agents.types import ScanState, StrategyResult, StockScanResult
from app.services.data_fetcher import get_all_stock_codes, TDX_SERVERS
from app.services.strategy import (
    check_ma_bullish_alignment,
    check_macd_golden_cross,
    check_macd_death_cross,
    check_arbitrage_signal,
    check_rubbing_strategy,
    compute_monthly_macd,
    compute_weekly_macd,
    run_strategy_pipeline,
    # 8个双K线影线策略
    check_continue_down,
    check_support_range,
    check_support_rebound,
    check_short_stop,
    check_diverge_start,
    check_diverge_strong,
    check_strong_support,
    check_weak_support,
    # 通达信策略1（合并版）和策略2
    check_tdx_strategy1,
    check_tdx_strategy2,
)

# ────────────────────────────────────────────
# 股票数据获取（复用 scanner.py 的逻辑）
# ────────────────────────────────────────────

MIN_DATA_DAYS = 65
SCAN_MAX_BARS = 100

# 扫描配置
MAX_CONCURRENT = 16
FETCH_TIMEOUT = 10


def _fast_fetch(code: str) -> Optional[list]:
    """快速拉取股票数据（优先本地 SQLite，降级 TDX）。"""
    from app.services.db import load_kline, get_last_refresh

    if get_last_refresh():
        df = load_kline(code, SCAN_MAX_BARS)
        if df is not None and len(df) >= MIN_DATA_DAYS:
            records = []
            for _, row in df.iterrows():
                d = row["date"]
                records.append({
                    "year": d.year, "month": d.month, "day": d.day,
                    "open": row["open"], "close": row["close"],
                    "high": row["high"], "low": row["low"],
                    "vol": row["volume"], "amount": row.get("amount", 0),
                })
            return records

    from pytdx.hq import TdxHq_API
    market = 1 if code.startswith(("6", "68")) else 0

    for ip, port in TDX_SERVERS:
        api = TdxHq_API()
        try:
            if not api.connect(ip, port):
                continue
            data = api.get_security_bars(9, market, code, 0, SCAN_MAX_BARS)
            api.disconnect()
            if data and len(data) > MIN_DATA_DAYS:
                return data
        except Exception:
            try:
                api.disconnect()
            except Exception:
                pass
            continue

    return None


def _parse_fast_data(raw_data: list) -> Optional["pd.DataFrame"]:
    """将 pytdx 原始数据转为 DataFrame。"""
    import pandas as pd
    records = []
    for d in raw_data:
        records.append({
            "date": pd.Timestamp(year=d["year"], month=d["month"], day=d["day"]),
            "open": d["open"],
            "close": d["close"],
            "high": d["high"],
            "low": d["low"],
            "volume": d["vol"],
        })
    df = pd.DataFrame(records)
    df = df.sort_values("date").reset_index(drop=True)
    return df


# ────────────────────────────────────────────
# 策略 Agent 基类
# ────────────────────────────────────────────

class StrategyAgent:
    """
    策略扫描 Agent。

    职责：
    - 从 stock_list 获取股票
    - 对每只股票运行策略检查
    - 返回匹配结果
    """

    def __init__(self, key: str, name: str):
        self.key = key
        self.name = name

    def scan(self, stock_list: list[dict]) -> StrategyResult:
        """执行扫描。子类可重写 scan_stock 方法。"""
        import pandas as pd

        matched = []
        total = 0

        for stock in stock_list:
            code = stock["code"]
            name = stock.get("name", "")
            total += 1

            raw_data = _fast_fetch(code)
            if not raw_data:
                continue

            df = _parse_fast_data(raw_data)
            if df is None or len(df) < MIN_DATA_DAYS:
                continue

            df = run_strategy_pipeline(df)

            if self.scan_stock(code, name, df):
                latest_close = round(float(df.iloc[-1]["close"]), 2)
                latest_date = str(df.iloc[-1]["date"].date())
                matched.append(StockScanResult(
                    code=code,
                    name=name,
                    close=latest_close,
                    latest_date=latest_date,
                    strategy_score=0,  # Merge Agent 会计算
                    matched_strategies=[self.key],
                    checks={self.key: True},
                ))

        return StrategyResult(
            strategy_key=self.key,
            strategy_name=self.name,
            matched_stocks=matched,
            total_scanned=total,
        )

    def scan_stock(self, code: str, name: str, df: "pd.DataFrame") -> bool:
        """检查单只股票是否满足策略条件。子类必须实现。"""
        raise NotImplementedError


# ────────────────────────────────────────────
# 具体策略 Agent
# ────────────────────────────────────────────

class MaBullishAgent(StrategyAgent):
    """均线多头排列 Agent。"""

    def __init__(self):
        super().__init__("ma_bullish", "均线多头排列")

    def scan_stock(self, code: str, name: str, df) -> bool:
        return check_ma_bullish_alignment(df)


class MacdGoldenAgent(StrategyAgent):
    """月 MACD 金叉 Agent。"""

    def __init__(self):
        super().__init__("macd_golden", "月MACD金叉")

    def scan_stock(self, code: str, name: str, df) -> bool:
        monthly_dif, monthly_dea = compute_monthly_macd(df)
        weekly_dif, weekly_dea = compute_weekly_macd(df)
        daily_dif = df.iloc[-1].get("dif")
        daily_dea = df.iloc[-1].get("dea")
        monthly_golden = check_macd_golden_cross(monthly_dif, monthly_dea)
        weekly_dead = check_macd_death_cross(weekly_dif, weekly_dea)
        daily_dead = check_macd_death_cross(daily_dif, daily_dea)
        return bool(monthly_golden and not weekly_dead and not daily_dead)


class ArbitrageAgent(StrategyAgent):
    """隔日套利信号 Agent。"""

    def __init__(self):
        super().__init__("arbitrage", "隔日套利信号")

    def scan_stock(self, code: str, name: str, df) -> bool:
        arb = check_arbitrage_signal(df)
        return arb["is_arbitrage_signal"]


class RubbingAgent(StrategyAgent):
    """揉搓线洗盘 Agent。"""

    def __init__(self):
        super().__init__("rubbing", "揉搓线洗盘")

    def scan_stock(self, code: str, name: str, df) -> bool:
        rub = check_rubbing_strategy(df)
        return rub["buy_signal"]


# ────────────────────────────────────────────
# 8个双K线影线策略 Agent
# ────────────────────────────────────────────

class ContinueDownAgent(StrategyAgent):
    """中继下跌 Agent。"""

    def __init__(self):
        super().__init__("continue_down", "中继下跌")

    def scan_stock(self, code: str, name: str, df) -> bool:
        result = check_continue_down(df)
        return result["signal"]


class SupportRangeAgent(StrategyAgent):
    """支撑位震荡选方向 Agent。"""

    def __init__(self):
        super().__init__("support_range", "支撑位震荡选方向")

    def scan_stock(self, code: str, name: str, df) -> bool:
        result = check_support_range(df)
        return result["signal"]


class SupportReboundAgent(StrategyAgent):
    """支撑位资金抢反弹 Agent。"""

    def __init__(self):
        super().__init__("support_rebound", "支撑位资金抢反弹")

    def scan_stock(self, code: str, name: str, df) -> bool:
        result = check_support_rebound(df)
        return result["signal"]


class ShortStopAgent(StrategyAgent):
    """短期止跌 Agent。"""

    def __init__(self):
        super().__init__("short_stop", "短期止跌")

    def scan_stock(self, code: str, name: str, df) -> bool:
        result = check_short_stop(df)
        return result["signal"]


class DivergeStartAgent(StrategyAgent):
    """开始有分歧 Agent。"""

    def __init__(self):
        super().__init__("diverge_start", "开始有分歧")

    def scan_stock(self, code: str, name: str, df) -> bool:
        result = check_diverge_start(df)
        return result["signal"]


class DivergeStrongAgent(StrategyAgent):
    """分歧但强势看新高 Agent。"""

    def __init__(self):
        super().__init__("diverge_strong", "分歧但强势看新高")

    def scan_stock(self, code: str, name: str, df) -> bool:
        result = check_diverge_strong(df)
        return result["signal"]


class StrongSupportAgent(StrategyAgent):
    """承接力度大只承接不追高 Agent。"""

    def __init__(self):
        super().__init__("strong_support", "承接力度大只承接不追高")

    def scan_stock(self, code: str, name: str, df) -> bool:
        result = check_strong_support(df)
        return result["signal"]


class WeakSupportAgent(StrategyAgent):
    """承接低可能出现短期顶 Agent。"""

    def __init__(self):
        super().__init__("weak_support", "承接低可能出现短期顶")

    def scan_stock(self, code: str, name: str, df) -> bool:
        result = check_weak_support(df)
        return result["signal"]


# ────────────────────────────────────────────
# 通达信策略 Agent（合并版）
# ────────────────────────────────────────────

class TdxStrategy1Agent(StrategyAgent):
    """通达信策略1 Agent（复合信号合并版）。"""

    def __init__(self):
        super().__init__("tdx_strategy1", "通达信策略1")

    def scan_stock(self, code: str, name: str, df) -> bool:
        result = check_tdx_strategy1(df)
        return result["signal"]


class TdxStrategy2Agent(StrategyAgent):
    """通达信策略2 Agent（主图量化策略）。"""

    def __init__(self):
        super().__init__("tdx_strategy2", "通达信策略2")

    def scan_stock(self, code: str, name: str, df) -> bool:
        result = check_tdx_strategy2(df)
        return result["signal"]


# ────────────────────────────────────────────
# Agent 注册表
# ────────────────────────────────────────────

AGENT_REGISTRY: dict[str, StrategyAgent] = {
    "ma_bullish": MaBullishAgent(),
    "macd_golden": MacdGoldenAgent(),
    "arbitrage": ArbitrageAgent(),
    "rubbing": RubbingAgent(),
    # 8个双K线影线策略
    "continue_down": ContinueDownAgent(),
    "support_range": SupportRangeAgent(),
    "support_rebound": SupportReboundAgent(),
    "short_stop": ShortStopAgent(),
    "diverge_start": DivergeStartAgent(),
    "diverge_strong": DivergeStrongAgent(),
    "strong_support": StrongSupportAgent(),
    "weak_support": WeakSupportAgent(),
    # 通达信策略（合并版）
    "tdx_strategy1": TdxStrategy1Agent(),
    "tdx_strategy2": TdxStrategy2Agent(),
}
