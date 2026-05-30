"""
指数数据获取服务。

通过 pytdx 获取四大指数及分时数据。
"""

import pandas as pd
from pytdx.hq import TdxHq_API

from app.services.data_fetcher import TDX_SERVERS, _detect_market

# 主要指数定义
INDICES = {
    "000001": {"name": "上证指数", "market": 1},
    "399001": {"name": "深证成指", "market": 0},
    "399006": {"name": "创业板指", "market": 0},
    "000688": {"name": "科创50", "market": 1},
}

# K 线频率常量
FREQ_5MIN = 8   # 5 分钟（当日分时替代）
FREQ_DAILY = 9  # 日线
FREQ_WEEKLY = 10  # 周线
FREQ_MONTHLY = 11  # 月线


def fetch_index_kline(symbol: str, frequency: int = FREQ_DAILY, max_bars: int = 2400) -> pd.DataFrame:
    """
    获取指数 K 线数据。

    Args:
        symbol: 指数代码（如 '000001'）
        frequency: K 线频率
        max_bars: 最大获取条数

    Returns:
        DataFrame with columns: date, open, close, high, low, volume, amount
    """
    if symbol not in INDICES:
        raise ValueError(f"Unknown index: {symbol}")

    market = INDICES[symbol]["market"]

    all_data = []
    batch_size = 800
    offset = 0

    for ip, port in TDX_SERVERS:
        api = TdxHq_API()
        try:
            if not api.connect(ip, port):
                continue

            while len(all_data) < max_bars:
                batch = api.get_index_bars(frequency, market, symbol, offset, batch_size)
                if not batch:
                    break
                all_data.extend(batch)
                offset += 1

            api.disconnect()
            if all_data:
                break
        except Exception:
            try:
                api.disconnect()
            except Exception:
                pass
            continue

    if not all_data:
        raise ConnectionError(f"无法获取指数 {symbol} 数据")

    df = pd.DataFrame(all_data)
    df = df.rename(columns={"vol": "volume"})
    df["date"] = pd.to_datetime(df["datetime"], errors="coerce")
    df = df.dropna(subset=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # 保留所有列
    keep_cols = [c for c in ["date", "open", "close", "high", "low", "volume", "amount"] if c in df.columns]
    df = df[keep_cols].copy()

    return df


def fetch_index_5min(symbol: str) -> pd.DataFrame:
    """
    获取指数最近 5 分钟 K 线数据（当日分时替代）。

    Returns:
        DataFrame with 5-min bars
    """
    df = fetch_index_kline(symbol, FREQ_5MIN, max_bars=48)  # 一天约 48 根 5 分钟
    return df


def list_indices() -> list[dict]:
    """返回所有可用指数列表。"""
    return [
        {"code": code, "name": info["name"], "market": info["market"]}
        for code, info in INDICES.items()
    ]
